import Database from 'better-sqlite3';
import { Team, TeamCreateInput, ID } from '@stella/types';

export class TeamStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  create(input: TeamCreateInput): Team {
    const id = crypto.randomUUID();
    const now = this.now();
    const team: Team = {
      id,
      ...input,
      memberIds: input.memberIds ?? [],
      settings: input.settings ?? {},
      metadata: {},
      createdAt: now,
      updatedAt: now,
    };
    this.db.prepare(
      `INSERT INTO teams (id, name, description, owner_id, member_ids, settings, metadata, created_at, updated_at)
       VALUES (@id, @name, @description, @owner_id, @member_ids, @settings, @metadata, @created_at, @updated_at)`
    ).run({
      ...team,
      memberIds: JSON.stringify(team.memberIds),
      settings: JSON.stringify(team.settings),
      metadata: JSON.stringify(team.metadata),
    });
    return team;
  }

  get(id: ID): Team | null {
    const row = this.db.prepare('SELECT * FROM teams WHERE id = @id').get({ id }) as any;
    if (!row) return null;
    return this.toTeam(row);
  }

  list(): Team[] {
    const rows = this.db.prepare('SELECT * FROM teams ORDER BY created_at DESC').all() as any[];
    return rows.map(row => this.toTeam(row));
  }

  private toTeam(row: any): Team {
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      ownerId: row.owner_id,
      memberIds: JSON.parse(row.member_ids || '[]'),
      settings: JSON.parse(row.settings || '{}'),
      metadata: JSON.parse(row.metadata || '{}'),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
