import Database from 'better-sqlite3';
import { Task, TaskCreateInput, ID } from '@stella/types';

export class TaskStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  create(input: TaskCreateInput): Task {
    const id = crypto.randomUUID();
    const now = this.now();
    const task: Task = {
      id,
      ...input,
      status: 'pending',
      priority: input.priority ?? 'normal',
      artifactIds: [],
      metadata: input.metadata ?? {},
      createdAt: now,
      updatedAt: now,
    };
    this.db.prepare(
      `INSERT INTO tasks (id, agent_id, team_id, skill_id, title, description, input, output, status, priority, error, started_at, completed_at, artifact_ids, metadata, created_at, updated_at)
       VALUES (@id, @agent_id, @team_id, @skill_id, @title, @description, @input, @output, @status, @priority, @error, @started_at, @completed_at, @artifact_ids, @metadata, @created_at, @updated_at)`
    ).run({
      ...task,
      input: JSON.stringify(task.input),
      output: task.output ? JSON.stringify(task.output) : null,
      artifactIds: JSON.stringify(task.artifactIds),
      metadata: JSON.stringify(task.metadata),
    });
    return task;
  }

  get(id: ID): Task | null {
    const row = this.db.prepare('SELECT * FROM tasks WHERE id = @id').get({ id }) as any;
    if (!row) return null;
    return this.toTask(row);
  }

  list(): Task[] {
    const rows = this.db.prepare('SELECT * FROM tasks ORDER BY created_at DESC').all() as any[];
    return rows.map(row => this.toTask(row));
  }

  private toTask(row: any): Task {
    return {
      id: row.id,
      agentId: row.agent_id,
      teamId: row.team_id,
      skillId: row.skill_id,
      title: row.title,
      description: row.description,
      input: JSON.parse(row.input || '{}'),
      output: row.output ? JSON.parse(row.output) : undefined,
      status: row.status as Task['status'],
      priority: row.priority as Task['priority'],
      error: row.error,
      startedAt: row.started_at,
      completedAt: row.completed_at,
      artifactIds: JSON.parse(row.artifact_ids || '[]'),
      metadata: JSON.parse(row.metadata || '{}'),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
