export interface DeviceState {
  volume: number; // 0 - 100
  isMuted: boolean;
  brightness: number; // 0 - 100
  flashlight: boolean;
  wifi: boolean;
  bluetooth: boolean;
  dnd: boolean;
  batteryLevel: number; // 0 - 100
  isCharging: boolean;
  lowPowerMode: boolean;
  activeTimers: Array<{
    id: string;
    label: string;
    totalSeconds: number;
    remainingSeconds: number;
    isRunning: boolean;
  }>;
  reminders: Array<{
    id: string;
    title: string;
    time?: string;
    completed: boolean;
  }>;
  recentApps: string[];
}

export type AssistantTheme = 'void' | 'oled' | 'aurora' | 'solar' | 'light';

export interface AssistantSettings {
  isDefaultAssistant: boolean;
  startListeningOnOpen: boolean;
  attachScreenshotOnInvoke: boolean;
  wakeWordEnabled: boolean;
  wakeWordPhrase: string; // e.g. "hey stella"
  contextAwarenessEnabled: boolean; // Ask with Stella
  theme: AssistantTheme;
  animateBackground: boolean;
  voicePitch: number;
  voiceRate: number;
  autoSpeakResponse: boolean;
  autoRespondOnPause: boolean; // Automatically send prompt when user pauses speaking
  pauseThresholdMs: number; // Duration of pause before auto-responding (e.g. 1500ms)
  soundEffects: boolean;
  hapticFeedback: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  spokenText?: string;
  timestamp: string;
  deviceAction?: {
    type: string;
    description: string;
    status: 'success' | 'pending' | 'failed';
    data?: any;
  };
  screenAttachment?: string; // base64 or description
}

export interface Workspace {
  id: string;
  name: string;
  threads: Array<{
    id: string;
    title: string;
    updatedAt: string;
    isDeviceAssistantChat?: boolean;
  }>;
}

export interface ConnectedDevice {
  id: string;
  name: string;
  type: 'pc' | 'phone' | 'vault' | 'tablet' | 'server';
  role: 'heavy_compute' | 'confidential_vault' | 'voice_primary' | 'standby';
  ip: string;
  status: 'online' | 'busy' | 'syncing';
  battery?: number;
  cpuLoad?: number;
  memoryUsage?: string;
  isCurrentDevice?: boolean;
}

export interface DeviceHubState {
  roomCode: string;
  isHosting: boolean;
  devices: ConnectedDevice[];
  maxDevices: number;
}

export interface DeferredTask {
  id: string;
  title: string;
  taskType: 'heavy_compute' | 'confidential' | 'sensor_read' | 'voice_route';
  sourceDevice: string;
  targetDevice: string;
  status: 'routing' | 'processing' | 'completed' | 'failed';
  result?: string;
  timestamp: string;
}

export type ProviderType = 'gemini' | 'nvidia' | 'openrouter' | 'openai' | 'groq' | 'anthropic' | 'local_gguf';

export interface LocalGgufModel {
  fileName: string;
  fileSize: string;
  sizeBytes: number;
  architecture: string;
  quantization: string;
  contextLength: number;
  tensorCount: number;
  magicValidated: boolean;
  loadedAt: string;
  status: 'ready' | 'loading' | 'serving';
}

export interface ModelOption {
  id: string;
  name: string;
  provider: ProviderType;
  tier: string;
  description: string;
  contextWindow?: string;
  isAuthorized?: boolean;
}

export interface ProviderConfig {
  provider: ProviderType;
  apiKey: string;
  isKeyTested: boolean;
  authLevel?: string;
  selectedModel: string;
  availableModels: ModelOption[];
  localGguf?: LocalGgufModel;
}