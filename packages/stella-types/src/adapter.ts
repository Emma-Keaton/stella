/**
 * @stella/types - Adapter types (LLM provider adapters - Paperclip adapter pattern)
 */

import { Entity, ID, JSONValue, Timestamp } from './entity';

export type AdapterType = 'mcp' | 'claude' | 'codex' | 'openai' | 'google' | 'xai' | 'ollama' | 'local-gguf' | 'custom';

export interface Adapter extends Entity {
  name: string;
  type: AdapterType;
  endpoint?: string;
  apiKeyRef?: string;
  models: string[];
  capabilities: string[];
  config: Record<string, JSONValue>;
  isConnected: boolean;
  lastHealthCheck?: Timestamp;
  metadata: Record<string, JSONValue>;
}

export interface AdapterCreateInput {
  name: string;
  type: AdapterType;
  endpoint?: string;
  apiKeyRef?: string;
  models?: string[];
  capabilities?: string[];
  config?: Record<string, JSONValue>;
}
