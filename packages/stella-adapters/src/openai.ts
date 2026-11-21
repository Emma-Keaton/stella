/**
 * @stella/adapters - OpenAI adapter
 */

import { BaseAdapter, ChatCompletionRequest, ChatCompletionResponse, ChatMessage, AdapterConfig } from './base';
import { ModelOption, ProviderType, AdapterType } from '@stella/types';

export class OpenAIAdapter extends BaseAdapter {
  readonly id = 'openai';
  readonly name = 'OpenAI';
  readonly type: AdapterType = 'openai';
  readonly provider: ProviderType = 'openai';
  readonly models: ModelOption[] = [
    {
      id: 'gpt-4o',
      name: 'GPT-4o',
      provider: 'openai',
      tier: 'frontier',
      description: 'Multimodal model with advanced reasoning',
      contextWindow: '128K tokens',
      isAuthorized: true,
      capabilities: ['chat', 'tools', 'vision', 'audio'],
    },
    {
      id: 'gpt-4o-mini',
      name: 'GPT-4o Mini',
      provider: 'openai',
      tier: 'fast',
      description: 'Fast, affordable small model',
      contextWindow: '128K tokens',
      isAuthorized: true,
      capabilities: ['chat', 'tools', 'vision'],
    },
  ];

  constructor(config: AdapterConfig) {
    super(config);
  }

  async connect(): Promise<void> {
    if (!this.config.apiKey) {
      throw new Error('OpenAI API key not configured');
    }
    this.isConnected = true;
  }

  async disconnect(): Promise<void> {
    this.isConnected = false;
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.listModels();
      return this.isConnected;
    } catch {
      return false;
    }
  }

  async listModels(): Promise<ModelOption[]> {
    return this.models;
  }

  async chatCompletion(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    return {
      id: 'openai-' + Date.now(),
      model: request.model,
      created: Math.floor(Date.now() / 1000),
      choices: [
        {
          index: 0,
          message: {
            role: 'assistant',
            content: 'OpenAI adapter response placeholder',
          },
          finish_reason: 'stop',
        },
      ],
    };
  }

  toString(): string {
    return `OpenAIAdapter(id=${this.id}, models=${this.models.length})`;
  }
}
