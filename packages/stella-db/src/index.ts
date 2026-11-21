/**
 * @stella/db - Database layer for Stella AI
 * Embedded SQLite database with migration support.
 */

import Database from 'better-sqlite3';
import { AgentStore } from './agents';
import { SkillStore } from './skills';
import { TaskStore } from './tasks';
import { ArtifactStore } from './artifacts';
import { TeamStore } from './teams';
import { AdapterStore } from './adapters';
import { DeviceStore } from './devices';
import { SettingsStore } from './settings';

export class StellaDB {
  public db: Database.Database;
  public agents: AgentStore;
  public skills: SkillStore;
  public tasks: TaskStore;
  public artifacts: ArtifactStore;
  public teams: TeamStore;
  public adapters: AdapterStore;
  public devices: DeviceStore;
  public settings: SettingsStore;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('foreign_keys = ON');
    this.initSchema();
    this.agents = new AgentStore(this.db);
    this.skills = new SkillStore(this.db);
    this.tasks = new TaskStore(this.db);
    this.artifacts = new ArtifactStore(this.db);
    this.teams = new TeamStore(this.db);
    this.adapters = new AdapterStore(this.db);
    this.devices = new DeviceStore(this.db);
    this.settings = new SettingsStore(this.db);
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        system_prompt TEXT,
        model TEXT NOT NULL,
        provider TEXT NOT NULL,
        api_key_ref TEXT,
        temperature REAL,
        max_tokens INTEGER,
        top_p REAL,
        status TEXT NOT NULL DEFAULT 'idle',
        capabilities TEXT NOT NULL DEFAULT '[]',
        skills TEXT NOT NULL DEFAULT '[]',
        team_id TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS skills (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        type TEXT NOT NULL DEFAULT 'builtin',
        status TEXT NOT NULL DEFAULT 'active',
        version TEXT NOT NULL DEFAULT '0.1.0',
        author TEXT,
        capabilities TEXT NOT NULL DEFAULT '[]',
        parameters TEXT NOT NULL DEFAULT '{}',
        return_schema TEXT,
        adapter_ref TEXT,
        entry_point TEXT,
        source_url TEXT,
        checksum TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        team_id TEXT,
        skill_id TEXT,
        title TEXT NOT NULL,
        description TEXT,
        input TEXT NOT NULL DEFAULT '{}',
        output TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        priority TEXT NOT NULL DEFAULT 'normal',
        error TEXT,
        started_at TEXT,
        completed_at TEXT,
        artifact_ids TEXT NOT NULL DEFAULT '[]',
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (agent_id) REFERENCES agents(id),
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (skill_id) REFERENCES skills(id)
      );

      CREATE TABLE IF NOT EXISTS artifacts (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        size INTEGER NOT NULL DEFAULT 0,
        url TEXT,
        content TEXT,
        checksum TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        FOREIGN KEY (agent_id) REFERENCES agents(id)
      );

      CREATE TABLE IF NOT EXISTS teams (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        owner_id TEXT NOT NULL,
        member_ids TEXT NOT NULL DEFAULT '[]',
        settings TEXT NOT NULL DEFAULT '{}',
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS adapters (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        endpoint TEXT,
        api_key_ref TEXT,
        models TEXT NOT NULL DEFAULT '[]',
        capabilities TEXT NOT NULL DEFAULT '[]',
        config TEXT NOT NULL DEFAULT '{}',
        is_connected INTEGER NOT NULL DEFAULT 0,
        last_health_check TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        role TEXT NOT NULL,
        ip TEXT,
        status TEXT NOT NULL DEFAULT 'offline',
        battery INTEGER,
        cpu_load REAL,
        memory_usage TEXT,
        capabilities TEXT NOT NULL DEFAULT '[]',
        is_current_device INTEGER NOT NULL DEFAULT 0,
        linked_devices TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        applied_at TEXT NOT NULL
      );
    `);
  }

  close(): void {
    this.db.close();
  }
}

export type ID = string;

