"""core/mcp/marketplace.py - MCP marketplace for server discovery.

Manages a catalog of MCP servers that Stella can connect to. Servers are
discovered from provider configuration and can be added/removed at runtime.
Each server entry includes health status and capability information.

Modeled after pocketstrike-ai's MCP marketplace pattern.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .client import MCPClient, discover_mcp_server


@dataclass
class MarketplaceEntry:
    """Represents a discovered MCP server in the marketplace."""
    id: str
    name: str
    endpoint: str
    transport: str = "sse"
    capabilities: list[str] = field(default_factory=list)
    available: bool = False
    tool_count: int = 0
    error: Optional[str] = None
    client: Optional[MCPClient] = None


class MCPMarketplace:
    """Manages discovery and connection to MCP servers.

    The marketplace maintains a registry of known MCP servers and can
    connect to them on demand. Servers can be added/removed at runtime,
    and each connection is lazily established when first needed.
    """

    def __init__(self):
        self._servers: dict[str, MarketplaceEntry] = {}
        self._clients: dict[str, MCPClient] = {}

    def register_server(self, server_id: str, name: str, endpoint: str,
                        transport: str = "sse",
                        capabilities: list[str] | None = None) -> MarketplaceEntry:
        """Register a new MCP server in the marketplace.

        Does not connect immediately - connection is established lazily
        when tools are first requested.
        """
        entry = MarketplaceEntry(
            id=server_id,
            name=name,
            endpoint=endpoint,
            transport=transport,
            capabilities=capabilities or [],
        )
        self._servers[server_id] = entry
        return entry

    def unregister_server(self, server_id: str) -> bool:
        """Unregister and disconnect an MCP server."""
        if server_id in self._clients:
            try:
                # Note: We can't easily close async clients from sync code,
                # but we remove the reference so it can be GC'd
                del self._clients[server_id]
            except Exception:
                pass
        if server_id in self._servers:
            del self._servers[server_id]
            return True
        return False

    def list_servers(self) -> list[MarketplaceEntry]:
        """Return all registered marketplace entries."""
        return list(self._servers.values())

    def get_entry(self, server_id: str) -> Optional[MarketplaceEntry]:
        """Get a marketplace entry by server ID."""
        return self._servers.get(server_id)

    async def connect_server(self, server_id: str) -> MCPClient:
        """Connect to an MCP server and return the client.

        If already connected, returns the existing client.
        Raises on connection failure.
        """
        if server_id in self._clients:
            return self._clients[server_id]

        entry = self._servers.get(server_id)
        if not entry:
            raise ValueError(f"Unknown server: {server_id}")

        client = await discover_mcp_server(
            server_id, entry.name, entry.endpoint
        )
        self._clients[server_id] = client

        # Update entry status
        entry.available = client.is_available
        entry.tool_count = len(client.tools)
        entry.error = client.error

        return client

    async def get_client(self, server_id: str) -> Optional[MCPClient]:
        """Get an existing client or connect if not yet connected."""
        if server_id in self._clients:
            return self._clients[server_id]

        entry = self._servers.get(server_id)
        if not entry:
            return None

        try:
            return await self.connect_server(server_id)
        except Exception:
            return None

    async def list_tools_from_server(self, server_id: str) -> list:
        """List tools from a specific server."""
        client = await self.get_client(server_id)
        if client:
            return client.tools
        return []

    async def call_tool(self, server_id: str, tool_name: str,
                        arguments: dict) -> dict:
        """Call a tool on a specific server."""
        client = await self.get_client(server_id)
        if not client:
            raise RuntimeError(f"Cannot connect to server: {server_id}")
        return await client.call_tool(tool_name, arguments)

    async def call_tool_by_name(self, tool_name: str,
                                arguments: dict) -> dict:
        """Call a tool by name across all connected servers.

        Searches all connected clients for a tool with the given name
        and calls it on the first server that has it.
        """
        for client in self._clients.values():
            for tool in client.tools:
                if tool.name == tool_name:
                    return await client.call_tool(tool_name, arguments)
        raise RuntimeError(f"Tool not found on any server: {tool_name}")

    async def discover_all(self) -> dict[str, list]:
        """Discover tools from all registered servers.

        Returns dict of server_id -> list of tools.
        """
        results = {}
        for server_id, entry in self._servers.items():
            try:
                client = await self.connect_server(server_id)
                results[server_id] = [t.name for t in client.tools]
            except Exception:
                results[server_id] = []
        return results

    async def shutdown(self):
        """Close all client connections."""
        for client in self._clients.values():
            try:
                await client.close()
            except Exception:
                pass
        self._clients.clear()
