/**
 * @stella/types - Team types (multi-agent collaboration)
 */

import { Entity, ID, JSONValue, Timestamp } from './entity';

export type TeamRole = 'owner' | 'admin' | 'member' | 'viewer';

export interface Team extends Entity {
  name: string;
  description?: string;
  ownerId: ID;
  memberIds: ID[];
  settings: Record<string, JSONValue>;
  metadata: Record<string, JSONValue>;
}

export interface TeamCreateInput {
  name: string;
  description?: string;
  ownerId: ID;
  memberIds?: ID[];
  settings?: Record<string, JSONValue>;
}

export interface TeamMember {
  id: ID;
  teamId: ID;
  agentId: ID;
  role: TeamRole;
  joinedAt: Timestamp;
}
