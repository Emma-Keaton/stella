import Database from 'better-sqlite3';
import { Skill, SkillCreateInput, ID } from '@stella/types';

export class SkillStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  create(input: SkillCreateInput): Skill {
    const id = crypto.randomUUID();
    const now = this.now();
    const skill: Skill = {
      id,
      ...input,
      status: 'active',
      version: input.version ?? '0.1.0',
      capabilities: input.capabilities ?? [],
      parameters: input.parameters ?? { type: 'object', properties: {} },
      metadata: input.metadata ?? {},
      createdAt: now,
      updatedAt: now,
    };
    this.db.prepare(
      `INSERT INTO skills (id, name, description, type, status, version, author, capabilities, parameters, return_schema, adapter_ref, entry_point, source_url, checksum, metadata, created_at, updated_at)
       VALUES (@id, @name, @description, @type, @status, @version, @author, @capabilities, @parameters, @return_schema, @adapter_ref, @entry_point, @source_url, @checksum, @metadata, @created_at, @updated_at)`
    ).run({
      ...skill,
      capabilities: JSON.stringify(skill.capabilities),
      parameters: JSON.stringify(skill.parameters),
      return_schema: skill.returnSchema ? JSON.stringify(skill.returnSchema) : null,
      metadata: JSON.stringify(skill.metadata),
    });
    return skill;
  }

  get(id: ID): Skill | null {
    const row = this.db.prepare('SELECT * FROM skills WHERE id = @id').get({ id }) as any;
    if (!row) return null;
    return this.toSkill(row);
  }

  list(): Skill[] {
    const rows = this.db.prepare('SELECT * FROM skills ORDER BY created_at DESC').all() as any[];
    return rows.map(row => this.toSkill(row));
  }

  private toSkill(row: any): Skill {
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      type: row.type as Skill['type'],
      status: row.status as Skill['status'],
      version: row.version,
      author: row.author,
      capabilities: JSON.parse(row.capabilities || '[]'),
      parameters: JSON.parse(row.parameters || '{}'),
      returnSchema: row.return_schema ? JSON.parse(row.return_schema) : undefined,
      adapterRef: row.adapter_ref,
      entryPoint: row.entry_point,
      sourceUrl: row.source_url,
      checksum: row.checksum,
      metadata: JSON.parse(row.metadata || '{}'),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
