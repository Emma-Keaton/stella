# packages/contracts — Python side of IPC wire protocol types.
# Mirrors the TypeScript declarations so backend and frontend stay in sync.

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
from enum import Enum

IpcEndpoint = str

IPC_ENDPOINTS = {
    "backend_ping": "backend.ping",
    "backend_ready": "backend.ready",
    "backend_shutdown": "backend.shutdown",
    "config_read": "config.read",
    "config_write": "config.write",
    "config_provider_mode": "config.provider.mode",
    "config_provider_config": "config.provider.config",
    "provider_list": "provider.list",
    "provider_build": "provider.build",
    "provider_reset": "provider.reset",
    "agent_run": "agent.run",
    "agent_tool_declarations": "agent.tool.declarations",
    "agent_tool_call": "agent.tool.call",
    "agent_skill_list": "agent.skill.list",
    "agent_skill_load": "agent.skill.load",
    "action_list": "action.list",
    "action_run": "action.run",
    "plugin_list": "plugin.list",
    "plugin_run": "plugin.run",
    "plugin_toggle": "plugin.toggle",
    "memory_read": "memory.read",
    "memory_write": "memory.write",
    "memory_search": "memory.search",
    "session_start": "session.start",
    "session_summary": "session.summary",
    "event_log": "event.log",
    "event_state": "event.state",
    "event_audio_level": "event.audio.level",
    "event_visemes": "event.visemes",
    "event_wake": "event.wake",
    "event_error": "event.error",
}


@dataclass
class IpcRequest:
    id: str
    endpoint: IpcEndpoint
    payload: Any
    timestamp: float


@dataclass
class IpcResponse:
    id: str
    endpoint: IpcEndpoint
    ok: bool
    payload: Optional[Any] = None
    error: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class IpcEvent:
    endpoint: IpcEndpoint
    payload: Any
    timestamp: float = 0.0


@dataclass
class ToolDeclaration:
    name: str
    description: str
    parameters: Dict[str, Any]
    behavior: Optional[Literal["BLOCKING", "NON_BLOCKING"]] = None
    scheduling: Optional[Literal["WHEN_IDLE", "SILENT", "INTERRUPT"]] = None
    tier: Optional[Literal["core", "extra"]] = None
    brief: Optional[str] = None


@dataclass
class PluginDeclaration:
    name: str
    description: str
    parameters: Dict[str, Any]
    behavior: Optional[Literal["BLOCKING", "NON_BLOCKING"]] = None
    scheduling: Optional[Literal["WHEN_IDLE", "SILENT", "INTERRUPT"]] = None
    tier: Optional[Literal["core", "extra"]] = None
    brief: Optional[str] = None


@dataclass
class ProviderDeclaration:
    id: str
    kind: Literal["llm", "stt", "tts", "engine"]
    label: str
    hint: Optional[str] = None
    requires: List[str] = field(default_factory=list)
    needs: List[Dict[str, Any]] = field(default_factory=list)
    caps: Optional[Dict[str, Any]] = None


@dataclass
class ProviderConfig:
    mode: str = "gemini"
    providers: Dict[str, Any] = field(default_factory=dict)
    pipeline: Optional[Dict[str, Any]] = None
    enabledPlugins: Dict[str, bool] = field(default_factory=dict)


@dataclass
class BackendState:
    connected: bool = False
    providerMode: str = ""
    wakeWord: bool = False
    pushToTalk: bool = False
    audioLevel: float = 0.0
    speaking: bool = False
    listening: bool = False


@dataclass
class LogEvent:
    level: Literal["debug", "info", "warn", "error"] = "info"
    message: str = ""
    source: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class SkillDeclaration:
    slug: str
    name: str
    description: str
    category: str
    source: str
    version: str
    enabled: bool = True
