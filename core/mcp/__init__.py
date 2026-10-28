"""core/mcp - Model Context Protocol client and marketplace.

Stella's MCP subsystem lets it connect to external MCP servers (SSE transport)
and expose its own tools as an MCP server. Modeled after pocketstrike-ai's MCP
integration and god's-eye-view's provider pattern.

Architecture
------------
- MCPClient  - SSE-based client that connects to remote MCP servers,
  discovers tools, and routes tool calls to them.
- MCPServer  - stdio-based server that exposes Stella's own tools as MCP
  capabilities so external agents can drive Stella.
- Marketplace - Discovery and registration of MCP servers from provider
  configurations, with health checking and capability advertising.
"""

from .client import MCPClient, MCPTool, MCPServerInfo
from .server import MCPServer
from .marketplace import MCPMarketplace, MarketplaceEntry

__all__ = [
    "MCPClient",
    "MCPTool",
    "MCPServerInfo",
    "MCPServer",
    "MCPMarketplace",
    "MarketplaceEntry",
]
