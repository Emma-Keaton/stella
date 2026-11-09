// IPC wire protocol types — frozen boundary between Electron main and Python backend
// Follows OpenBot's packages/contracts pattern: no Electron/Node/SolidJS dependency here.

export const IPC_ENDPOINTS = {
  // Backend lifecycle
  backend_ping: "backend.ping",
  backend_ready: "backend.ready",
  backend_shutdown: "backend.shutdown",

  // Configuration
  config_read: "config.read",
  config_write: "config.write",
  config_provider_mode: "config.provider.mode",
  config_provider_config: "config.provider.config",

  // Provider management
  provider_list: "provider.list",
  provider_build: "provider.build",
  provider_reset: "provider.reset",

  // Agent / tools
  agent_run: "agent.run",
  agent_tool_declarations: "agent.tool.declarations",
  agent_tool_call: "agent.tool.call",
  agent_skill_list: "agent.skill.list",
  agent_skill_load: "agent.skill.load",

  // Actions / plugins
  action_list: "action.list",
  action_run: "action.run",
  plugin_list: "plugin.list",
  plugin_run: "plugin.run",
  plugin_toggle: "plugin.toggle",

  // Memory
  memory_read: "memory.read",
  memory_write: "memory.write",
  memory_search: "memory.search",

  // Session
  session_start: "session.start",
  session_summary: "session.summary",

  // Events (backend -> frontend)
  event_log: "event.log",
  event_state: "event.state",
  event_audio_level: "event.audio.level",
  event_visemes: "event.visemes",
  event_wake: "event.wake",
  event_error: "event.error",
} as const;

export type IpcEndpoint = (typeof IPC_ENDPOINTS)[keyof typeof IPC_ENDPOINTS];

export interface IpcRequest<T = unknown> {
  id: string;
  endpoint: IpcEndpoint;
  payload: T;
  timestamp: number;
}

export interface IpcResponse<T = unknown> {
  id: string;
  endpoint: IpcEndpoint;
  ok: boolean;
  payload?: T;
  error?: string;
  timestamp: number;
}

export interface IpcEvent<T = unknown> {
  endpoint: IpcEndpoint;
  payload: T;
  timestamp: number;
}

// Tool declaration (matches Mark-LVI TOOL dict shape)
export interface ToolDeclaration {
  name: string;
  description: string;
  parameters: {
    type: "OBJECT";
    properties: Record<string, unknown>;
    required?: string[];
  };
  behavior?: "BLOCKING" | "NON_BLOCKING";
  scheduling?: "WHEN_IDLE" | "SILENT" | "INTERRUPT";
  tier?: "core" | "extra";
  brief?: string;
}

// Plugin declaration (matches Mark-LVI PLUGIN dict shape)
export interface PluginDeclaration {
  name: string;
  description: string;
  parameters: {
    type: "OBJECT";
    properties: Record<string, unknown>;
    required?: string[];
  };
  behavior?: "BLOCKING" | "NON_BLOCKING";
  scheduling?: "WHEN_IDLE" | "SILENT" | "INTERRUPT";
  tier?: "core" | "extra";
  brief?: string;
}

// Provider declaration
export interface ProviderDeclaration {
  id: string;
  kind: "llm" | "stt" | "tts" | "engine";
  label: string;
  hint?: string;
  requires?: string[];
  needs?: Array<{
    key: string;
    label: string;
    type: "string" | "boolean" | "number" | "secret";
    secret?: boolean;
  }>;
  caps?: {
    vision?: boolean;
    tools?: boolean;
    max_tools?: number;
    audio?: boolean;
  };
}

// Provider configuration state
export interface ProviderConfig {
  mode: "gemini" | "pipeline" | "local";
  providers: Record<string, unknown>;
  pipeline?: {
    stt?: string;
    llm?: string;
    tts?: string;
    sidecar?: string;
  };
  enabledPlugins: Record<string, boolean>;
}

// Backend state event
export interface BackendState {
  connected: boolean;
  providerMode: string;
  wakeWord: boolean;
  pushToTalk: boolean;
  audioLevel: number;
  speaking: boolean;
  listening: boolean;
}

// Log event
export interface LogEvent {
  level: "debug" | "info" | "warn" | "error";
  message: string;
  source?: string;
  timestamp: number;
}

// Skill declaration (OpenBot SKILL.md pattern)
export interface SkillDeclaration {
  slug: string;
  name: string;
  description: string;
  category: string;
  source: string;
  version: string;
  enabled: boolean;
}
