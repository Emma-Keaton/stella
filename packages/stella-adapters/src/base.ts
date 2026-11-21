/**
 * @stella/adapters - Base adapter class
 * 
 * Paperclip-inspired adapter pattern for LLM providers.
 * All adapters implement a common interface for chat completions,
 * tool calling, and model management.
 */

import {
  Adapter,
  AdapterType,
  ModelOption,
  ProviderType,
  JSONValue,
} from '@stella/types';

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  name?: string;
  toolCallId?: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  stream?: boolean;
  tools?: ToolDefinition[];
  toolChoice?: 'none' | 'auto' | 'required';
}

export interface ToolDefinition {
  name: string;
  description?: string;
  parameters: JSONSchema;
}

export interface ChatCompletionResponse {
  id: string;
  model: string;
  created: number;
  choices: Array<{
    index: number;
    message: ChatMessage;
    finish_reason: 'stop' | 'length' | 'tool_calls' | 'content_filter';
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface JSONSchema {
  type: string;
  properties?: Record<string, JSONSchemaProperty>;
  required?: string[];
  [key: string]: JSONValue;
}

export interface JSONSchemaProperty {
  type: string;
  description?: string;
  enum?: string[];
  [key: string]: JSONValue;
}

export interface AdapterConfig {
  apiKey?: string;
  baseURL?: string;
  timeout?: number;
  maxRetries?: number;
  [key: string]: JSONValue;
}

export abstract class BaseAdapter {
  abstract readonly id: string;
  abstract readonly name: string;
  abstract readonly type: AdapterType;
  abstract readonly provider: ProviderType;
  abstract readonly models: ModelOption[];

  protected config: AdapterConfig;
  protected isConnected: boolean = false;

  constructor(config: AdapterConfig = {}) {
    this.config = config;
  }

  abstract connect(): Promise<void>;
  abstract disconnect(): Promise<void>;
  abstract healthCheck(): Promise<boolean>;
  abstract listModels(): Promise<ModelOption[]>;
  abstract chatCompletion(request: ChatCompletionRequest): Promise<ChatCompletionResponse>;
  abstract streamChatCompletion?(request: ChatCompletionRequest): AsyncGenerator<ChatCompletionResponse>;

  toAdapter(): Adapter {
    return {
      id: this.id,
      name: this.name,
      type: this.type,
      endpoint: this.config.baseURL,
      apiKeyRef: this.config.apiKey ? '*' : undefined,
      models: this.models,
      capabilities: this.getCapabilities(),
      config: this.config,
      isConnected: this.isConnected,
      lastHealthCheck: undefined,
      metadata: {},
    };
  }

  protected getCapabilities(): string[] {
    const caps = ['chat'];
    if (this.streamChatCompletion) caps.push('stream');
    if (this.supportsTools()) caps.push('tools');
    return caps;
  }

  protected supportsTools(): boolean {
    return false;
  }

  abstract toString(): string;
}
