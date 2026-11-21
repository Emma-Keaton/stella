import Database from 'better-sqlite3';
import { Device, ID } from '@stella/types';

export class DeviceStore {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  private now(): string {
    return new Date().toISOString();
  }

  create(input: any): Device {
    const id = crypto.randomUUID();
    const now = this.now();
    const device: Device = {
      id,
      ...input,
      status: 'offline',
      capabilities: input.capabilities ?? [],
      isCurrentDevice: false,
      linkedDevices: [],
      createdAt: now,
      updatedAt: now,
    };
    this.db.prepare(
      `INSERT INTO devices (id, name, type, role, ip, status, battery, cpu_load, memory_usage, capabilities, is_current_device, linked_devices, created_at, updated_at)
       VALUES (@id, @name, @type, @role, @ip, @status, @battery, @cpu_load, @memory_usage, @capabilities, @is_current_device, @linked_devices, @created_at, @updated_at)`
    ).run({
      ...device,
      capabilities: JSON.stringify(device.capabilities),
      isCurrentDevice: device.isCurrentDevice ? 1 : 0,
      linkedDevices: JSON.stringify(device.linkedDevices),
    });
    return device;
  }

  get(id: ID): Device | null {
    const row = this.db.prepare('SELECT * FROM devices WHERE id = @id').get({ id }) as any;
    if (!row) return null;
    return this.toDevice(row);
  }

  list(): Device[] {
    const rows = this.db.prepare('SELECT * FROM devices ORDER BY created_at DESC').all() as any[];
    return rows.map(row => this.toDevice(row));
  }

  private toDevice(row: any): Device {
    return {
      id: row.id,
      name: row.name,
      type: row.type as Device['type'],
      role: row.role as Device['role'],
      ip: row.ip,
      status: row.status as Device['status'],
      battery: row.battery,
      cpuLoad: row.cpu_load,
      memoryUsage: row.memory_usage,
      capabilities: JSON.parse(row.capabilities || '[]'),
      isCurrentDevice: Boolean(row.is_current_device),
      linkedDevices: JSON.parse(row.linked_devices || '[]'),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
