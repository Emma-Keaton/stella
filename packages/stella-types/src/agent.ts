/**
 * @stella/types - Agent types (Paperclip-inspired agent orchestration)
 */

import { Entity, ID, JSONValue, Timestamp } from './entity';

export type AgentStatus = 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'stopped';

export interface Agent extends Entity {
  name: string;
  description?: string;
  systemPrompt?: string;
  model: string;
  provider: string;
  apiKeyRef?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  status: AgentStatus;
  capabilities: string[];
  skills: ID[];
  teamId?: ID;
  metadata: Record<string, JSONValue>;
}

export interface AgentCreateInput {
  name: string;
  description?: string;
  systemPrompt?: string;
  model: string;
  provider: string;
  apiKeyRef?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  capabilities?: string[];
  skills?: ID[];
  teamId?: ID;
  metadata?: Record<string, JSONValue>;
}

export interface AgentUpdateInput {
  name?: string;
  description?: string;
  systemPrompt?: string;
  model?: string;
  provider?: string;
  apiKeyRef?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  capabilities?: string[];
  skills?: ID[];
  teamId?: ID;
  metadata?: Record<string, JSONValue>;
}
