/**
 * @stella/types - Artifact types (outputs from agent runs)
 */

import { Entity, ID, JSONValue, Timestamp } from './entity';

export type ArtifactType = 'text' | 'code' | 'image' | 'audio' | 'video' | 'file' | 'json' | 'url';

export interface Artifact extends Entity {
  taskId: ID;
  agentId: ID;
  name: string;
  type: ArtifactType;
  mimeType: string;
  size: number;
  url?: string;
  content?: string;
  checksum?: string;
  metadata: Record<string, JSONValue>;
}
