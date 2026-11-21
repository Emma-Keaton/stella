/**
 * @stella/adapters - Claude (Anthropic) adapter
 */

import { BaseAdapter, ChatCompletionRequest, ChatCompletionResponse, ChatMessage, AdapterConfig } from './base';
import { ModelOption, ProviderType, AdapterType } from '@stella/types';

export class ClaudeAdapter extends BaseAdapter {
  readonly id = 'claude';
  readonly name = 'Anthropic Claude';
  readonly type: AdapterType = 'claude';
  readonly provider: ProviderType = 'anthropic';
  readonly models: ModelOption[] = [
    {
      id: 'claude-3-5-sonnet-20241022',
      name: 'Claude 3.5 Sonnet',
      provider: 'anthropic',
      tier: 'frontier',
      description: 'Most capable Claude model for complex reasoning',
      contextWindow: '200K tokens',
      isAuthorized: true,
      capabilities: ['chat', 'tools', 'vision'],
    },
    {
      id: 'claude-3-haiku-20240307',
      name: 'Claude 3 Haiku',
      provider: 'anthropic',
      tier: 'fast',
      description: 'Fast, lightweight model for simple tasks',
      contextWindow: '200K tokens',
      isAuthorized: true,
      capabilities: ['chat', 'tools', 'vision'],
    },
  ];

  constructor(config: AdapterConfig) {
    super(config);
  }

  async connect(): Promise<void> {
    if (!this.config.apiKey) {
      throw new Error('Anthropic API key not configured');
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
    // Placeholder - actual implementation would call Anthropic API
    return {
      id: 'claude-' + Date.now(),
      model: request.model,
      created: Math.floor(Date.now() / 1000),
      choices: [
        {
          index: 0,
          message: {
            role: 'assistant',
            content: 'Claude adapter response placeholder',
          },
          finish_reason: 'stop',
        },
      ],
    };
  }

  toString(): string {
    return `ClaudeAdapter(id=${this.id}, models=${this.models.length})`;
  }
}
