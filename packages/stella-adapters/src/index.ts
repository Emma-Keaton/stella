/**
 * @stella/adapters - LLM provider adapters
 * 
 * Exports all adapter implementations and the base adapter class.
 */

export { BaseAdapter } from './base';
export type {
  ChatMessage,
  ChatCompletionRequest,
  ChatCompletionResponse,
  ToolDefinition,
  JSONSchema,
  JSONSchemaProperty,
  AdapterConfig,
} from './base';

export { ClaudeAdapter } from './claude';
export { OpenAIAdapter } from './openai';
export { GoogleAdapter } from './google';
export { OllamaAdapter } from './ollama';

export type { AdapterType, ProviderType, ModelOption } from '@stella/types';
