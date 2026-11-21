/**
 * @stella/acp - ACP Client
 * 
 * Implements the Agent Client Protocol for Stella AI inter-agent
 * and client-to-agent communication.
 */

import {
  ACPEnvelope,
  ACPMessage,
  ACPMessageType,
  ACPHelloPayload,
  ACPExecutePayload,
  ACPResultPayload,
  ID,
} from '@stella/types';

export interface ACPClientConfig {
  agentId: ID;
  agentName: string;
  capabilities: string[];
  onMessage?: (message: ACPMessage) => void;
  onError?: (error: Error) => void;
}

export class ACPClient {
  private config: ACPClientConfig;
  private connected: boolean = false;
  private pendingRequests: Map<string, { resolve: (val: any) => void; reject: (err: Error) => void }> = new Map();
  private messageHandlers: Map<ACPMessageType, ((msg: ACPMessage) => void)[]> = new Map();

  constructor(config: ACPClientConfig) {
    this.config = config;
  }

  async connect(): Promise<void> {
    // Placeholder - actual implementation would establish WebSocket/transport
    this.connected = true;
    await this.send({
      type: 'hello',
      payload: {
        device_id: this.config.agentId,
        device_name: this.config.agentName,
        platform: 'desktop',
        capabilities: this.config.capabilities,
      } as ACPHelloPayload,
    });
  }

  async disconnect(): Promise<void> {
    this.connected = false;
    this.pendingRequests.clear();
  }

  isConnected(): boolean {
    return this.connected;
  }

  async send(envelope: ACPEnvelope): Promise<void> {
    if (!this.connected) {
      throw new Error('ACP client not connected');
    }
    // Placeholder - actual implementation would send over transport
    console.log('[ACP] Sending:', envelope.type, envelope.request_id);
  }

  async request<T = any>(
    type: ACPMessageType,
    payload: Record<string, any>,
    timeoutMs: number = 30000
  ): Promise<T> {
    const requestId = crypto.randomUUID();
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error(`ACP request timeout: ${type}`));
      }, timeoutMs);

      this.pendingRequests.set(requestId, { resolve, reject });

      this.send({
        type,
        request_id: requestId,
        timestamp: new Date().toISOString(),
        payload,
      } as ACPEnvelope).catch(reject);
    });
  }

  onMessage(type: ACPMessageType, handler: (msg: ACPMessage) => void): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)!.push(handler);
  }

  offMessage(type: ACPMessageType, handler: (msg: ACPMessage) => void): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx >= 0) {
        handlers.splice(idx, 1);
      }
    }
  }

  private handleIncoming(envelope: ACPEnvelope): void {
    const message: ACPMessage = {
      id: envelope.request_id,
      type: envelope.type,
      payload: envelope.payload,
      timestamp: envelope.timestamp,
    };

    // Resolve pending request if this is a response
    const pending = this.pendingRequests.get(envelope.request_id);
    if (pending) {
      this.pendingRequests.delete(envelope.request_id);
      clearTimeout((pending as any).timeout);
      pending.resolve(envelope.payload);
      return;
    }

    // Dispatch to message handlers
    const handlers = this.messageHandlers.get(envelope.type);
    if (handlers) {
      handlers.forEach(h => h(message));
    }

    // Call global callback
    this.config.onMessage?.(message);
  }

  toJSON(): any {
    return {
      config: {
        agentId: this.config.agentId,
        agentName: this.config.agentName,
        capabilities: this.config.capabilities,
      },
      connected: this.connected,
      pendingRequests: this.pendingRequests.size,
    };
  }
}
