/**
 * @stella/types - Device Types (Stella device mesh)
 */

import { Entity, ID, Timestamp } from './entity';

export type DeviceType = 'pc' | 'phone' | 'vault' | 'tablet' | 'server';
export type DeviceRole = 'heavy_compute' | 'confidential_vault' | 'voice_primary' | 'standby';
export type DeviceStatus = 'online' | 'busy' | 'syncing' | 'offline';

export interface Device extends Entity {
  name: string;
  type: DeviceType;
  role: DeviceRole;
  ip?: string;
  status: DeviceStatus;
  battery?: number;
  cpuLoad?: number;
  memoryUsage?: string;
  capabilities: string[];
  isCurrentDevice: boolean;
  linkedDevices: ID[];
}

export interface DeviceLink {
  id: ID;
  sourceDeviceId: ID;
  targetDeviceId: ID;
  createdAt: Timestamp;
  capabilities: string[];
  status: 'active' | 'inactive' | 'pending';
}
