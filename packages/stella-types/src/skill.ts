/**
 * @stella/types - Skill types (Paperclip-inspired skill system)
 */

import { Entity, ID, JSONValue, Timestamp } from './entity';

export type SkillType = 'builtin' | 'mcp' | 'python' | 'typescript' | 'acp';
export type SkillStatus = 'active' | 'inactive' | 'error' | 'loading';

export interface Skill extends Entity {
  name: string;
  description?: string;
  type: SkillType;
  status: SkillStatus;
  version: string;
  author?: string;
  capabilities: string[];
  parameters: JSONSchema;
  returnSchema?: JSONSchema;
  adapterRef?: string;
  entryPoint?: string;
  sourceUrl?: string;
  checksum?: string;
  metadata: Record<string, JSONValue>;
}

export interface SkillCreateInput {
  name: string;
  description?: string;
  type: SkillType;
  version?: string;
  author?: string;
  capabilities?: string[];
  parameters?: JSONSchema;
  returnSchema?: JSONSchema;
  adapterRef?: string;
  entryPoint?: string;
  sourceUrl?: string;
  metadata?: Record<string, JSONValue>;
}

export interface JSONSchema {
  type: string;
  properties?: Record<string, JSONSchemaProperty>;
  required?: string[];
  additionalProperties?: boolean;
  description?: string;
  enum?: string[];
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  items?: JSONSchema;
}

export interface JSONSchemaProperty {
  type: string;
  description?: string;
  enum?: string[];
  minimum?: number;
  maximum?: number;
  items?: JSONSchema;
}
