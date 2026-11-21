/**
 * @stella/mcp - MCP (Model Context Protocol) client for Stella AI
 * 
 * Connects Stella to MCP servers for tool/resource access.
 */

export { MCPClient } from './client';
export type {
  MCPServerInfo,
  MCPCapability,
  MCPTool,
  MCPResource,
  MCPCallToolRequest,
  MCPCallToolResult,
} from '@stella/types';
