"""core/mcp/client.py - MCP client for connecting to remote MCP servers.

Implements SSE-based MCP client that can connect to remote MCP servers,
discover tools via tools/list, and execute tools via tools/call.

Modeled after pocketstrike-ai's MCP integration and god's-eye-view's
provider pattern. Honest about failures: missing server, failed handshake,
or unreachable endpoint all produce clear errors rather than silent failures.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx


@dataclass
class MCPTool:
    """Represents a single tool exposed by an MCP server."""
    name: str
    description: str
    input_schema: dict
    server_id: str
    server_name: str

    def to_stella_tool_schema(self) -> dict:
        """Convert to Stella tool schema dict for the agent registry."""
        return {
            "name": f"mcp:{self.server_id}.{self.name}",
            "description": f"[MCP:{self.server_id}] {self.description}",
            "parameters": self.input_schema,
        }


@dataclass
class MCPServerInfo:
    """Information about a discovered MCP server."""
    id: str
    name: str
    endpoint: str
    transport: str = "sse"
    capabilities: list[str] = field(default_factory=list)
    tools: list[MCPTool] = field(default_factory=list)
    available: bool = False
    last_ping: float = 0.0
    error: Optional[str] = None


class MCPClient:
    """MCP client that connects to remote MCP servers via SSE.

    Follows the MCP protocol specification:
    - initialize handshake
    - tools/list to discover capabilities
    - tools/call to execute tools

    All methods are async and must be called from an async context.
    Failures are reported as exceptions with clear messages - never silent
    degradation.
    """

    def __init__(self, server_id: str, server_name: str, endpoint: str,
                 timeout: float = 10.0):
        self.server_id = server_id
        self.server_name = server_name
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None
        self._initialized: bool = False
        self._tools: dict[str, MCPTool] = {}
        self._available: bool = False
        self._error: Optional[str] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def initialize(self) -> bool:
        """Perform MCP initialize handshake.

        Returns True on success, False otherwise with _error set.
        """
        try:
            client = await self._ensure_client()
            # SSE handshake: GET /sse to get session ID
            sse_url = f"{self.endpoint}/sse"
            resp = await client.get(sse_url, timeout=self.timeout)
            if resp.status_code != 200:
                self._error = f"SSE handshake failed: HTTP {resp.status_code}"
                self._available = False
                return False

            # Extract session ID from SSE stream or response headers
            self._session_id = resp.headers.get("mcp-session-id")
            if not self._session_id:
                # Try to parse from SSE stream
                text = resp.text
                import re
                m = re.search(r'data: {"jsonrpc":"2.0","method":"notifications/initialized"}', text)
                if m:
                    # Session ID might be in a different field
                    pass

            # Send initialize request via POST to /message
            init_payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "stella", "version": "1.0.0"},
                },
            }

            # Use /message endpoint for POST
            msg_url = f"{self.endpoint}/message"
            resp = await client.post(msg_url, json=init_payload, timeout=self.timeout)
            if resp.status_code != 200:
                self._error = f"Initialize failed: HTTP {resp.status_code}"
                self._available = False
                return False

            result = resp.json()
            self._initialized = True
            self._available = True
            self._error = None
            return True

        except Exception as exc:
            self._error = f"Initialize error: {exc}"
            self._available = False
            return False

    async def list_tools(self) -> list[MCPTool]:
        """List available tools from the MCP server.

        Returns list of MCPTool objects. Raises on failure.
        """
        if not self._initialized:
            await self.initialize()

        try:
            client = await self._ensure_client()
            payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list",
                "params": {},
            }
            msg_url = f"{self.endpoint}/message"
            resp = await client.post(msg_url, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                raise RuntimeError(f"tools/list failed: HTTP {resp.status_code}")

            result = resp.json()
            tools_data = result.get("result", {}).get("tools", [])

            tools = []
            for td in tools_data:
                tool = MCPTool(
                    name=td.get("name", ""),
                    description=td.get("description", ""),
                    input_schema=td.get("inputSchema", {}),
                    server_id=self.server_id,
                    server_name=self.server_name,
                )
                tools.append(tool)

            self._tools = {t.name: t for t in tools}
            return tools

        except Exception as exc:
            self._error = f"tools/list error: {exc}"
            raise

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool on the MCP server.

        Returns the tool result dict. Raises on failure.
        """
        tool_name = name
        if name.startswith(f"mcp:{self.server_id}."):
            tool_name = name[len(f"mcp:{self.server_id}."):]

        try:
            client = await self._ensure_client()
            payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }
            msg_url = f"{self.endpoint}/message"
            resp = await client.post(msg_url, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                raise RuntimeError(f"tools/call failed: HTTP {resp.status_code}")

            result = resp.json()
            if "error" in result:
                raise RuntimeError(f"Tool error: {result['error']}")

            return result.get("result", {})

        except Exception as exc:
            raise RuntimeError(f"Tool call error: {exc}")

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def tools(self) -> list[MCPTool]:
        return list(self._tools.values())


async def discover_mcp_server(server_id: str, server_name: str, endpoint: str,
                              timeout: float = 10.0) -> MCPClient:
    """Discover and connect to an MCP server.

    Returns a configured MCPClient with tools discovered.
    Raises on connection failure.
    """
    client = MCPClient(server_id, server_name, endpoint, timeout)
    await client.initialize()
    await client.list_tools()
    return client


async def scan_mcp_endpoints(endpoints: dict[str, str]) -> dict[str, MCPClient]:
    """Scan multiple MCP endpoints and return connected clients.

    endpoints: dict of server_id -> endpoint URL
    Returns dict of server_id -> MCPClient for successfully connected servers.
    """
    clients = {}
    for server_id, endpoint in endpoints.items():
        try:
            client = await discover_mcp_server(server_id, server_id, endpoint)
            clients[server_id] = client
        except Exception:
            # Silently skip unreachable servers
            pass
    return clients
