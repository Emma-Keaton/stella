// Stella WebSocket Connection Manager
// Provides a single persistent WebSocket connection to the Python backend
// at ws://localhost:8765 with auto-reconnection, heartbeat, and request/response matching.

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

export interface StellaWSMessage {
  id: string;
  endpoint: string;
  payload: any;
}

export interface StellaWSResponse {
  id: string;
  endpoint: string;
  ok: boolean;
  result?: any;
  reply?: any;
  error?: any;
  honesty?: any;
}

type StatusListener = (status: ConnectionStatus) => void;
type MessageListener = (message: StellaWSResponse) => void;

const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_BACKEND_WS_URL || 'ws://localhost:8765';
const RECONNECT_BASE_DELAY = 1500;
const MAX_RECONNECT_DELAY = 30000;
const HEARTBEAT_INTERVAL = 30000;
const HEARTBEAT_TIMEOUT = 10000;
const MAX_QUEUE_SIZE = 100;

class StellaWebSocketManager {
  private url: string;
  private socket: WebSocket | null = null;
  private status: ConnectionStatus = 'disconnected';
  private statusListeners = new Set<StatusListener>();
  private messageListeners = new Set<MessageListener>();
  private pendingRequests = new Map<string, { resolve: (value: any) => void; reject: (err: Error) => void; timer: NodeJS.Timeout }>();
  private sendQueue: StellaWSMessage[] = [];
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private heartbeatPongTimer: NodeJS.Timeout | null = null;
  private isConnectingManually = false;
  private readonly maxReconnectAttempts: number;

  constructor(url: string = DEFAULT_WS_URL, maxReconnectAttempts: number = -1) {
    this.url = url;
    this.maxReconnectAttempts = maxReconnectAttempts;
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  isConnected(): boolean {
    return this.status === 'connected';
  }

  onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  onMessage(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  private setStatus(newStatus: ConnectionStatus): void {
    if (this.status === newStatus) return;
    this.status = newStatus;
    this.statusListeners.forEach((listener) => {
      try { listener(newStatus); } catch { /* swallow */ }
    });
  }

  connect(): Promise<void> {
    if (this.status === 'connected' || this.status === 'connecting') {
      return Promise.resolve();
    }
    this.isConnectingManually = true;
    this.setStatus('connecting');
    this.reconnectAttempts = 0;
    return new Promise((resolve, reject) => {
      const attemptConnect = () => {
        try { this.socket = new WebSocket(this.url); } catch (err) { this.handleConnectionError(err as Error); reject(err); return; }
        const socket = this.socket!;
        socket.onopen = () => { this.reconnectAttempts = 0; this.setStatus('connected'); this.startHeartbeat(); this.flushSendQueue(); resolve(); };
        socket.onmessage = (event) => { this.handleIncomingMessage(event.data); };
        socket.onerror = (err) => { console.warn('[StellaWS] WebSocket error:', err); };
        socket.onclose = () => { this.stopHeartbeat(); this.socket = null; if (this.status === 'connected') { this.setStatus('reconnecting'); this.scheduleReconnect(); } else if (this.status === 'connecting') { this.setStatus('disconnected'); reject(new Error('WebSocket connection failed')); } else { this.setStatus('disconnected'); } };
      };
      attemptConnect();
    });
  }

  disconnect(): void {
    this.isConnectingManually = false;
    this.stopReconnectTimer();
    this.stopHeartbeat();
    if (this.socket) { try { this.socket.close(); } catch { /* ignore */ } this.socket = null; }
    this.pendingRequests.forEach(({ reject }) => { reject(new Error('WebSocket disconnected')); });
    this.pendingRequests.clear();
    this.setStatus('disconnected');
  }

  private scheduleReconnect(): void {
    this.stopReconnectTimer();
    if (this.maxReconnectAttempts >= 0 && this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[StellaWS] Max reconnection attempts reached');
      this.setStatus('disconnected');
      return;
    }
    this.reconnectAttempts++;
    const delay = Math.min(RECONNECT_BASE_DELAY * Math.pow(2, this.reconnectAttempts - 1), MAX_RECONNECT_DELAY);
    console.log(`[StellaWS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => { if (!this.isConnectingManually && this.status !== 'connected') { this.connect().catch(() => { }); } }, delay);
  }

  private stopReconnectTimer(): void { if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; } }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => { if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return; this.sendRaw({ id: 'hb-' + Date.now(), endpoint: 'backend.ping', payload: {} }); this.heartbeatPongTimer = setTimeout(() => { console.warn('[StellaWS] Heartbeat timeout — closing socket'); try { this.socket?.close(); } catch { /* ignore */ } }, HEARTBEAT_TIMEOUT); }, HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat(): void { if (this.heartbeatTimer) { clearInterval(this.heartbeatTimer); this.heartbeatTimer = null; } if (this.heartbeatPongTimer) { clearTimeout(this.heartbeatPongTimer); this.heartbeatPongTimer = null; } }

  send(message: StellaWSMessage): void { this.enqueue(message); }

  request(message: StellaWSMessage, timeoutMs: number = 30000): Promise<any> {
    return new Promise((resolve, reject) => { const timer = setTimeout(() => { this.pendingRequests.delete(message.id); reject(new Error(`Request timeout for endpoint: ${message.endpoint}`)); }, timeoutMs); this.pendingRequests.set(message.id, { resolve, reject, timer }); this.enqueue(message); });
  }

  private enqueue(message: StellaWSMessage): void {
    if (this.sendQueue.length >= MAX_QUEUE_SIZE) { this.sendQueue.shift(); }
    this.sendQueue.push(message);
    this.tryFlush();
  }

  private tryFlush(): void { if (this.status !== 'connected' || !this.socket || this.socket.readyState !== WebSocket.OPEN) return; this.flushSendQueue(); }

  private flushSendQueue(): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    while (this.sendQueue.length > 0) { const message = this.sendQueue.shift()!; try { this.socket.send(JSON.stringify(message)); } catch (err) { this.sendQueue.unshift(message); console.warn('[StellaWS] Failed to send queued message:', err); break; } }
  }

  private sendRaw(message: StellaWSMessage): void { if (this.socket && this.socket.readyState === WebSocket.OPEN) { try { this.socket.send(JSON.stringify(message)); } catch { /* ignore */ } } }

  private handleIncomingMessage(data: any): void {
    // Binary voice frames
    if (data instanceof ArrayBuffer || data instanceof Blob) {
      const voiceMsg = { id:'voice', endpoint:'voice.stream', ok:true, result:{ audio:data } };
      this.messageListeners.forEach((listener) => { try { listener(voiceMsg as StellaWSResponse); } catch {} });
      return;
    }
    try { const msg = JSON.parse(data) as StellaWSResponse; if (msg.id && msg.id.startsWith('hb-') && msg.endpoint === 'backend.ping') { if (this.heartbeatPongTimer) { clearTimeout(this.heartbeatPongTimer); this.heartbeatPongTimer = null; } return; } if (msg.id && this.pendingRequests.has(msg.id)) { const pending = this.pendingRequests.get(msg.id)!; clearTimeout(pending.timer); this.pendingRequests.delete(msg.id); if (!msg.ok) { pending.reject(new Error(msg.error?.message || `Backend error for endpoint ${msg.endpoint}`)); } else { pending.resolve(msg.result ?? msg.reply ?? msg); } return; } this.messageListeners.forEach((listener) => { try { listener(msg); } catch { /* swallow */ } }); } catch (err) { console.warn('[StellaWS] Failed to parse incoming message:', err); }
  }

  private handleConnectionError(err: Error): void {
    this.stopHeartbeat(); this.socket = null;
    this.pendingRequests.forEach(({ reject }) => { reject(new Error(`WebSocket connection error: ${err.message}`)); });
    this.pendingRequests.clear();
    if (this.isConnectingManually) { this.setStatus('disconnected'); } else { this.setStatus('reconnecting'); this.scheduleReconnect(); }
  }
}

export const stellaWS = new StellaWebSocketManager();

export function createWSMessage(endpoint: string, payload: any): StellaWSMessage {
  return { id: 'stella-' + Date.now() + '-' + Math.random().toString(36).slice(2, 9), endpoint, payload };
}