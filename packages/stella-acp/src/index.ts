/**
 * @stella/acp - Agent Client Protocol implementation for Stella AI
 * 
 * ACP enables agent-to-agent and client-to-agent communication
 * across devices and processes.
 */

export { ACPClient } from './client';
export type {
  ACPEnvelope,
  ACPMessage,
  ACPMessageType,
  ACPHelloPayload,
  ACPExecutePayload,
  ACPResultPayload,
} from '@stella/types';
