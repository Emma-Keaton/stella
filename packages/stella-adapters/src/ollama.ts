/**
 * @stella/adapters - Ollama / Local GGUF adapter
 * 
 * Connects to locally running Ollama or llama.cpp server for on-device models.
 */

import { BaseAdapter, ChatCompletionRequest, ChatCompletionResponse, ChatMessage, AdapterConfig } from './base';
import { ModelOption, ProviderType, AdapterType } from '@stella/types';

export class OllamaAdapter extends BaseAdapter {
  readonly id = 'ollama';
  readonly name = 'Ollama / Local GGUF';
  readonly type: AdapterType = 'local-gguf';
  readonly provider: ProviderType = 'local_gguf';
  readonly models: ModelOption[] = [];

  private discoveredModels: ModelOption[] = [];

  constructor(config: AdapterConfig) {
    super(config);
    // Default local endpoint
    if (!this.config.baseURL) {
      this.config.baseURL = 'http://localhost:11434';
    }
  }

  async connect(): Promise<void> {
    try {
      await this.discoverModels();
      this.isConnected = true;
    } catch {
      this.isConnected = false;
    }
  }

  async disconnect(): Promise<void> {
    this.isConnected = false;
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.discoverModels();
      return this.isConnected;
    } catch {
      return false;
    }
  }

  async listModels(): Promise<ModelOption[]> {
    return this.discoveredModels;
  }

  private async discoverModels(): Promise<void> {
    // Placeholder - actual implementation would call Ollama API /api/tags
    this.discoveredModels = [
      {
        id: 'llama-3.1-8b',
        name: 'Llama 3.1 8B',
        provider: 'local_gguf',
        tier: 'local',
        description: 'Local GGUF model via Ollama',
        contextWindow: '128K tokens',
        isAuthorized: true,
        capabilities: ['chat', 'tools'],
      },
    ];
    this.models = this.discoveredModels;
  }

  async chatCompletion(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    return {
      id: 'ollama-' + Date.now(),
      model: request.model,
      created: Math.floor(Date.now() / 1000),
      choices: [
        {
          index: 0,
          message: {
            role: 'assistant',
            content: 'Ollama/Local GGUF adapter response placeholder',
          },
          finish_reason: 'stop',
        },
      ],
    };
  }

  toString(): string {
    return `OllamaAdapter(id=${this.id}, endpoint=${this.config.baseURL})`;
  }
}
