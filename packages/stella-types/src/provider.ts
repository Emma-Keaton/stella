/**
 * @stella/types - Provider / Model Types
 */

import { ID, Timestamp } from './entity';

export type ProviderType =
  | 'gemini'
  | 'nvidia'
  | 'openrouter'
  | 'openai'
  | 'groq'
  | 'anthropic'
  | 'google_maps'
  | 'local_gguf'
  | 'ollama';

export interface ProviderConfig {
  provider: ProviderType;
  apiKeyRef?: string;
  models: ModelOption[];
  isKeyTested: boolean;
  authLevel?: string;
}

export interface ModelOption {
  id: string;
  name: string;
  provider: ProviderType;
  tier: string;
  description: string;
  contextWindow?: string;
  isAuthorized: boolean;
  capabilities: string[];
}
