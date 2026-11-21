/**
 * @stella/types - Task/Run types (Paperclip-inspired agent runs)
 */

import { Entity, ID, JSONValue, Timestamp } from './entity';

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
export type TaskPriority = 'low' | 'normal' | 'high' | 'critical';

export interface Task extends Entity {
  agentId: ID;
  teamId?: ID;
  skillId?: ID;
  title: string;
  description?: string;
  input: JSONValue;
  output?: JSONValue;
  status: TaskStatus;
  priority: TaskPriority;
  error?: string;
  startedAt?: Timestamp;
  completedAt?: Timestamp;
  artifactIds: ID[];
  metadata: Record<string, JSONValue>;
}

export interface TaskCreateInput {
  agentId: ID;
  teamId?: ID;
  skillId?: ID;
  title: string;
  description?: string;
  input: JSONValue;
  priority?: TaskPriority;
  metadata?: Record<string, JSONValue>;
}
