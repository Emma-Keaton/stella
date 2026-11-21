/**
 * @stella/types - ACP (Agent Client Protocol) types
 */

import { ID, JSONValue, Timestamp } from './entity';

export type ACPMessageType =
  | 'hello'
  | 'pair_request'
  | 'pair_approved'
  | 'authenticate'
  | 'device_online'
  | 'device_offline'
  | 'capabilities'
  | 'execute'
  | 'result'
  | 'event'
  | 'error'
  | 'ping'
  | 'pong'
  | 'chat_message'
  | 'handoff'
  | 'device_link'
  | 'device_status'
  | 'device_host'
  | 'device_join'
  | 'device_relay'
  | 'device_peers'
  | 'device_handoffs_pull'
  | 'device_command';

export interface ACPEnvelope {
  type: ACPMessageType;
  request_id: string;
  timestamp: string;
  payload: Record<string, JSONValue>;
}

export interface ACPMessage {
  id: ID;
  type: ACPMessageType;
  payload: Record<string, JSONValue>;
  timestamp: Timestamp;
  fromAgent?: ID;
  toAgent?: ID;
  correlationId?: ID;
}

export interface ACPHelloPayload {
  device_id: string;
  device_name: string;
  platform: string;
  capabilities: string[];
}

export interface ACPExecutePayload {
  action: string;
  parameters: Record<string, JSONValue>;
  goal?: string;
  context?: Record<string, JSONValue>;
}

export interface ACPResultPayload {
  success: boolean;
  action?: string;
  result?: any;
  error?: string;
  handedOffTo?: string;
  from_device?: string;
}
