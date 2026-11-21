import Database from 'better-sqlite3';

export class SettingsStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  get(key: string): string | null {
    const row = this.db.prepare('SELECT value FROM settings WHERE key = @key').get({ key }) as any;
    return row ? row.value : null;
  }

  set(key: string, value: string): void {
    const now = this.now();
    this.db.prepare(
      `INSERT INTO settings (key, value, updated_at) VALUES (@key, @value, @updated_at)
       ON CONFLICT(key) DO UPDATE SET value=@value, updated_at=@updated_at`
    ).run({ key, value, updatedAt: now });
  }

  delete(key: string): boolean {
    const result = this.db.prepare('DELETE FROM settings WHERE key = @key').run({ key });
    return result.changes > 0;
  }
}
