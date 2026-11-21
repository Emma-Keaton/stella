import Database from 'better-sqlite3';
import { Agent, AgentCreateInput, AgentUpdateInput, ID } from '@stella/types';

export class AgentStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  create(input: AgentCreateInput): Agent {
    const id = crypto.randomUUID();
    const now = this.now();
    const agent: Agent = {
      id,
      ...input,
      status: 'idle',
      capabilities: input.capabilities ?? [],
      skills: input.skills ?? [],
      teamId: input.teamId,
      metadata: input.metadata ?? {},
      createdAt: now,
      updatedAt: now,
    };
    this.db.prepare(
      `INSERT INTO agents (id, name, description, system_prompt, model, provider, api_key_ref, temperature, max_tokens, top_p, status, capabilities, skills, team_id, metadata, created_at, updated_at)
       VALUES (@id, @name, @description, @system_prompt, @model, @provider, @api_key_ref, @temperature, @max_tokens, @top_p, @status, @capabilities, @skills, @team_id, @metadata, @created_at, @updated_at)`
    ).run({
      ...agent,
      capabilities: JSON.stringify(agent.capabilities),
      skills: JSON.stringify(agent.skills),
      metadata: JSON.stringify(agent.metadata),
    });
    return agent;
  }

  get(id: ID): Agent | null {
    const row = this.db.prepare('SELECT * FROM agents WHERE id = @id').get({ id }) as any;
    if (!row) return null;
    return this.toAgent(row);
  }

  list(): Agent[] {
    const rows = this.db.prepare('SELECT * FROM agents ORDER BY created_at DESC').all() as any[];
    return rows.map(row => this.toAgent(row));
  }

  update(id: ID, input: AgentUpdateInput): Agent | null {
    const existing = this.get(id);
    if (!existing) return null;
    const now = this.now();
    const updated: Agent = { ...existing, ...input, updatedAt: now };
    this.db.prepare(
      `UPDATE agents SET name=@name, description=@description, system_prompt=@system_prompt, model=@model, provider=@provider, api_key_ref=@api_key_ref, temperature=@temperature, max_tokens=@max_tokens, top_p=@top_p, status=@status, capabilities=@capabilities, skills=@skills, team_id=@team_id, metadata=@metadata, updated_at=@updated_at WHERE id=@id`
    ).run({
      ...updated,
      capabilities: JSON.stringify(updated.capabilities),
      skills: JSON.stringify(updated.skills),
      metadata: JSON.stringify(updated.metadata),
    });
    return updated;
  }

  delete(id: ID): boolean {
    const result = this.db.prepare('DELETE FROM agents WHERE id = @id').run({ id });
    return result.changes > 0;
  }

  private toAgent(row: any): Agent {
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      systemPrompt: row.system_prompt,
      model: row.model,
      provider: row.provider,
      apiKeyRef: row.api_key_ref,
      temperature: row.temperature,
      maxTokens: row.max_tokens,
      topP: row.top_p,
      status: row.status as Agent['status'],
      capabilities: JSON.parse(row.capabilities || '[]'),
      skills: JSON.parse(row.skills || '[]'),
      teamId: row.team_id,
      metadata: JSON.parse(row.metadata || '{}'),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
