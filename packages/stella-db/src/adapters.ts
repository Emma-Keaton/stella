import Database from 'better-sqlite3';
import { Adapter, ID } from '@stella/types';

export class AdapterStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  create(input: any): Adapter {
    const id = crypto.randomUUID();
    const now = this.now();
    const adapter: Adapter = {
      id,
      ...input,
      models: input.models ?? [],
      capabilities: input.capabilities ?? [],
      config: input.config ?? {},
      isConnected: false,
      metadata: {},
      createdAt: now,
      updatedAt: now,
    };
    this.db.prepare(
      `INSERT INTO adapters (id, name, type, endpoint, api_key_ref, models, capabilities, config, is_connected, last_health_check, metadata, created_at, updated_at)
       VALUES (@id, @name, @type, @endpoint, @api_key_ref, @models, @capabilities, @config, @is_connected, @last_health_check, @metadata, @created_at, @updated_at)`
    ).run({
      ...adapter,
      models: JSON.stringify(adapter.models),
      capabilities: JSON.stringify(adapter.capabilities),
      config: JSON.stringify(adapter.config),
      is_connected: adapter.isConnected ? 1 : 0,
      metadata: JSON.stringify(adapter.metadata),
    });
    return adapter;
  }

  get(id: ID): Adapter | null {
    const row = this.db.prepare('SELECT * FROM adapters WHERE id = @id').get({ id }) as any;
    if (!row) return null;
    return this.toAdapter(row);
  }

  list(): Adapter[] {
    const rows = this.db.prepare('SELECT * FROM adapters ORDER BY created_at DESC').all() as any[];
    return rows.map(row => this.toAdapter(row));
  }

  private toAdapter(row: any): Adapter {
    return {
      id: row.id,
      name: row.name,
      type: row.type as Adapter['type'],
      endpoint: row.endpoint,
      apiKeyRef: row.api_key_ref,
      models: JSON.parse(row.models || '[]'),
      capabilities: JSON.parse(row.capabilities || '[]'),
      config: JSON.parse(row.config || '{}'),
      isConnected: Boolean(row.is_connected),
      lastHealthCheck: row.last_health_check,
      metadata: JSON.parse(row.metadata || '{}'),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
