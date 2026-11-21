import Database from 'better-sqlite3';
import { Artifact, ID } from '@stella/types';

export class ArtifactStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  create(input: Omit<Artifact, 'id' | 'createdAt' | 'updatedAt'>): Artifact {
    const id = crypto.randomUUID();
    const now = this.now();
    const artifact: Artifact = { ...input, id, createdAt: now, updatedAt: now };
    this.db.prepare(
      `INSERT INTO artifacts (id, task_id, agent_id, name, type, mime_type, size, url, content, checksum, metadata, created_at, updated_at)
       VALUES (@id, @task_id, @agent_id, @name, @type, @mime_type, @size, @url, @content, @checksum, @metadata, @created_at, @updated_at)`
    ).run({
      ...artifact,
      metadata: JSON.stringify(artifact.metadata),
    });
    return artifact;
  }

  get(id: ID): Artifact | null {
    const row = this.db.prepare('SELECT * FROM artifacts WHERE id = @id').get({ id }) as any;
    if (!row) return null;
    return this.toArtifact(row);
  }

  listByTask(taskId: ID): Artifact[] {
    const rows = this.db
      .prepare('SELECT * FROM artifacts WHERE task_id = @task_id ORDER BY created_at DESC')
      .all({ task_id: taskId }) as any[];
    return rows.map(row => this.toArtifact(row));
  }

  private toArtifact(row: any): Artifact {
    return {
      id: row.id,
      taskId: row.task_id,
      agentId: row.agent_id,
      name: row.name,
      type: row.type as Artifact['type'],
      mimeType: row.mime_type,
      size: row.size,
      url: row.url,
      content: row.content,
      checksum: row.checksum,
      metadata: JSON.parse(row.metadata || '{}'),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
