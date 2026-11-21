/**
 * @stella/types - MCP (Model Context Protocol) types
 */

import { JSONSchema } from './skill';

export interface MCPServerInfo {
  name: string;
  version: string;
}

export interface MCPCapability {
  [key: string]: JSONValue;
}

export interface MCPInitializeParams {
  protocolVersion: string;
  capabilities: MCPCapability;
  clientInfo: MCPServerInfo;
}

export interface MCPInitializeResult {
  protocolVersion: string;
  capabilities: MCPCapability;
  serverInfo: MCPServerInfo;
}

export interface MCPResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}

export interface MCPTool {
  name: string;
  description?: string;
  inputSchema: JSONSchema;
}

export interface MCPCallToolRequest {
  name: string;
  arguments: Record<string, JSONValue>;
}

export interface MCPCallToolResult {
  content: Array<{ type: string; text?: string; data?: string }>;
  isError?: boolean;
}

export interface MCPListResourcesResult {
  resources: MCPResource[];
}

export interface MCPReadResourceRequest {
  uri: string;
}

export interface MCPReadResourceResult {
  contents: Array<{ uri: string; mimeType?: string; text?: string; blob?: string }>;
}
