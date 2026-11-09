import { NextResponse } from 'next/server';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

// Resolve repo root: <repo>/frontend/app/api/stella/device/link/route.ts
// -> 7 levels up = repo root
const REPO_ROOT = join(__dirname, '../../../..');
const CONFIG_DIR = join(REPO_ROOT, 'config');
const DEVICES_FILE = join(CONFIG_DIR, 'devices.json');

// Canonical device entry shape
interface DeviceEntry {
  id: string;
  name: string;
  type: 'phone' | 'pc' | 'tablet' | 'vault' | 'server';
  role: 'heavy_compute' | 'confidential_vault' | 'voice_primary' | 'standby';
  ip: string;
  status: 'online' | 'busy' | 'syncing' | 'offline';
  battery?: number;
  cpuLoad?: number;
  memoryUsage?: string;
  isCurrentDevice?: boolean;
  connected_at?: string;
  last_seen?: string;
  linked_by?: string;
  platform?: string;
  capabilities?: string[];
}

function ensureConfigDir() {
  if (!existsSync(CONFIG_DIR)) {
    mkdirSync(CONFIG_DIR, { recursive: true });
  }
}

function readDevices(): DeviceEntry[] {
  ensureConfigDir();
  if (!existsSync(DEVICES_FILE)) {
    return [];
  }
  try {
    const raw = readFileSync(DEVICES_FILE, 'utf-8');
    const data = JSON.parse(raw);
    if (Array.isArray(data)) {
      return data as DeviceEntry[];
    }
    return [];
  } catch {
    return [];
  }
}

function writeDevices(devices: DeviceEntry[]): void {
  ensureConfigDir();
  writeFileSync(DEVICES_FILE, JSON.stringify(devices, null, 2), 'utf-8');
}

/** GET — Return all linked devices from backend config. */
export async function GET() {
  const devices = readDevices();
  const linkedCount = devices.filter((d) => d.status === 'online').length;
  return NextResponse.json({
    devices,
    linkedCount,
    totalCount: devices.length,
  });
}

/** POST — Create or update a device link. */
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { device } = body as { device?: Partial<DeviceEntry> };

    if (!device || !device.id) {
      return NextResponse.json(
        { error: 'Invalid request: device with id is required' },
        { status: 400 },
      );
    }

    const devices = readDevices();
    const existingIndex = devices.findIndex((d) => d.id === device.id);

    const now = new Date().toISOString();
    const entry: DeviceEntry = {
      id: device.id,
      name: device.name || 'Unknown Device',
      type: (device.type as DeviceEntry['type']) || 'pc',
      role: (device.role as DeviceEntry['role']) || 'standby',
      ip: device.ip || '0.0.0.0',
      status: (device.status as DeviceEntry['status']) || 'online',
      battery: device.battery,
      cpuLoad: device.cpuLoad,
      memoryUsage: device.memoryUsage,
      isCurrentDevice: device.isCurrentDevice || false,
      connected_at: existingIndex >= 0 ? devices[existingIndex].connected_at : now,
      last_seen: now,
      linked_by: device.linked_by,
      platform: device.platform || 'desktop',
      capabilities: device.capabilities || [],
    };

    if (existingIndex >= 0) {
      devices[existingIndex] = entry;
    } else {
      devices.push(entry);
    }

    writeDevices(devices);
    return NextResponse.json({ ok: true, device: entry, devices });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || 'Failed to save device link' },
      { status: 500 },
    );
  }
}

/** DELETE — Remove a device link by id. */
export async function DELETE(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json(
        { error: 'Device id is required' },
        { status: 400 },
      );
    }

    const devices = readDevices();
    const filtered = devices.filter((d) => d.id !== id);
    writeDevices(filtered);
    return NextResponse.json({ ok: true, devices: filtered });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || 'Failed to remove device link' },
      { status: 500 },
    );
  }
}
