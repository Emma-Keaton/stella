/**
 * @stella/types - Health / Status types
 */

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface HealthComponent {
  status: HealthStatus;
  message?: string;
}

export interface HealthStatusResponse {
  status: HealthStatus;
  version: string;
  uptime: number;
  components: Record<string, HealthComponent>;
  timestamp: string;
}
