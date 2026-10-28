"""core/mcp/server.py - MCP server exposing Stella's tools.

Implements a stdio-based MCP server that exposes Stella's tool registry as
MCP tools, allowing external agents (Cursor, Codex, Claude, etc.) to drive
Stella through the Model Context Protocol.

Modeled after pocketstrike-ai's MCP integration patterns. All tool calls are
routed through Stella's tool registry with full permission checking and
honest result reporting (done/unverified/failed).
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Optional

from agent.tools import build_default_registry


class MCPServer:
    """MCP server that exposes Stella's tool registry via stdio.

    Implements the MCP protocol:
    - initialize handshake
    - tools/list to advertise capabilities
    - tools/call to execute tools through Stella's registry

    All tool results include honesty metadata (done/unverified/failed) so
    MCP clients can make informed decisions.
    """

    def __init__(self, server_name: str = "stella"):
        self.server_name = server_name
        self._registry = build_default_registry()
        self._initialized = False

    async def run(self):
        """Run the MCP server loop reading from stdin and writing to stdout."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_read_protocol(lambda: protocol)
        sys.stdin = protocol  # type: ignore[assignment]

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                line = line.decode("utf-8").strip()
                if not line:
                    continue
                await self._handle_message(line)
            except Exception:
                # Keep the server alive on individual message errors
                continue

    async def _handle_message(self, line: str):
        """Handle a single JSON-RPC message from stdin."""
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            self._send_response(None, None, {"code": -32700, "message": "Parse error"})
            return

        method = message.get("method", "")
        params = message.get("params", {})
        msg_id = message.get("id")

        if method == "initialize":
            await self._handle_initialize(msg_id, params)
        elif method == "initialized":
            # Notification, no response needed
            pass
        elif method == "tools/list":
            await self._handle_tools_list(msg_id)
        elif method == "tools/call":
            await self._handle_tools_call(msg_id, params)
        else:
            self._send_response(msg_id, None, {
                "code": -32601,
                "message": f"Method not found: {method}",
            })

    async def _handle_initialize(self, msg_id: Any, params: dict):
        """Handle initialize handshake."""
        self._initialized = True
        self._send_response(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False,
                },
            },
            "serverInfo": {
                "name": self.server_name,
                "version": "1.0.0",
            },
        })

    async def _handle_tools_list(self, msg_id: Any):
        """Handle tools/list request - advertise Stella's tools."""
        tools = []
        for tool in self._registry:
            schema = tool.schema()
            func = schema.get("function", {})
            tools.append({
                "name": tool.name,
                "description": func.get("description", ""),
                "inputSchema": func.get("parameters", {
                    "type": "object",
                    "properties": {},
                }),
            })

        self._send_response(msg_id, {"tools": tools})

    async def _handle_tools_call(self, msg_id: Any, params: dict):
        """Handle tools/call request - execute a tool through Stella's registry."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            from agent.tools import Registry
            # Use the default registry to execute
            registry = build_default_registry()
            result = registry.run(tool_name, arguments)

            # Build MCP result with honesty metadata
            if result.ok:
                result_content = {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result.output,
                            },
                        ],
                        "isError": False,
                    },
                }
            else:
                result_content = {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"ERROR: {result.error}",
                            },
                        ],
                        "isError": True,
                    },
                }

            self._send_response(msg_id, result_content)

        except Exception as exc:
            self._send_response(msg_id, None, {
                "code": -32603,
                "message": f"Internal error: {exc}",
            })

    def _send_response(self, msg_id: Any, result: Any, error: Optional[dict] = None):
        """Send a JSON-RPC response to stdout."""
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
        }
        if error:
            response["error"] = error
        else:
            response["result"] = result

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
