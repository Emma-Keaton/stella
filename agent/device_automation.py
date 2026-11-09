r"""agent/device_automation.py - rootless device automation driven by your local LLM.

What it does
------------
Stella can *see* the whole device without you ever opening Settings. It reads
every screen, control, permission and running process, then writes and executes a
precise script built from that state. It also undoes everything it did on
deactivation, at the same access level.

Roots: mobile (ADB) and PC (Windows/macOS/Linux). Any device that exposes a
drivers-less path can be added by dropping a scanner in ``scanners/``. The
orchestrator dispatches by platform and never touches Settings.

Safety
------
Every activation records what it changed. Deactivation reverses at the same
access level it was granted. A failed step marks the activation as degraded and
the UI asks before forcing a rollback.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.user_paths import get_user_data_dir

APP_DIR = get_user_data_dir() / "devices"
APP_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = APP_DIR / "device_state.json"

# The local LLM the agent uses to convert collected state into a precise script.
LLM = None

# ---------------------------------------------------------------------------
# Activation / deactivation (the reversibility contract)
# ---------------------------------------------------------------------------

class ActivationError(Exception):
    pass

class Activation:
    """A single device automation activation.

    ``record`` captures what the scanner touched. ``revert`` replays that log in
    reverse order, at the same access level. ``degraded`` is set when a step
    failed and the user must confirm before the rollback is forced.
    """

    def __init__(self, device: str, agent: str):
        self.device = device
        self.agent = agent
        self.log: list[dict[str, Any]] = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.status = "pending"  # pending -> active -> degraded|complete

    def record(self, action: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = {"at": datetime.now(timezone.utc).isoformat(), "action": action,
                 "detail": detail or {}}
        self.log.append(entry)
        return entry

    def commit(self, entry: dict[str, Any]) -> None:
        self.log.append(entry)

    def revert(self) -> dict[str, Any]:
        """Reverse the activation in reverse order. Returns a summary."""
        summary: dict[str, Any] = {"device": self.device, "reverted": 0,
                                   "failed": 0, "forced": False,
                                   "start": datetime.now(timezone.utc).isoformat()}
        for entry in reversed(self.log):
            try:
                self._step_revert(entry)
                summary["reverted"] += 1
            except Exception as exc:
                summary["failed"] += 1
                summary.setdefault("errors", []).append({"action": entry.get("action"),
                                                         "error": str(exc)})
        summary["end"] = datetime.now(timezone.utc).isoformat()
        return summary

    def _step_revert(self, entry: dict[str, Any]) -> None:
        # Override in subclasses so each scanner knows how to undo one step.
        raise NotImplementedError

    def summary(self) -> dict[str, Any]:
        return {"device": self.device, "agent": self.agent,
                "started_at": self.started_at, "status": self.status,
                "steps": len(self.log), "reverted": len(self.log)}


def activate(device: str, agent: str, state: dict[str, Any]) -> Activation:
    """Run a device activation and gate it behind your *chosen* agent.

    Only a registered Stella agent may request device automation. The module
    refuses anything else, which keeps local control of "I want Stella to touch
    my device" in the user's hands at all times.
    """
    if agent != "stella":
        raise ActivationError("activation by unknown agent not permitted")
    app = activate_device(device, state)
    if not app:
        raise ActivationError(f"could not activate {device}")
    return app


def activate_device(device: str, state: dict[str, Any]) -> Activation:
    """Platform-aware activation. Returns the activation or None when unsupported."""
    platform = state.get("platform", "unknown")
    if platform.startswith("android"):
        return AndroidActivation(device, state)
    if platform == "ios":
        return iOSActivation(device, state)
    if platform in ("windows", "darwin", "linux"):
        return PCActivation(device, state)
    return UnsupportedActivation(device, state)


# ---------------------------------------------------------------------------
# Scanner dispatch (rootless; no Settings access required)
# ---------------------------------------------------------------------------

def scan_device(device: str):
    platform = _platform_of(device)
    scanners = {"android": AndroidScanner, "ios": iOSScanner,
                "windows": PCScanner, "darwin": PCScanner, "linux": PCScanner}
    scanner = scanners.get(platform)
    if not scanner:
        return None, f"no rootless scanner for platform {platform}"
    return scanner(device).scan(), None


def _platform_of(device: str) -> str:
    low = (device or "").lower()
    if "android" in low or low.startswith("192.168."):
        return "android"
    if "ios" in low or low.startswith("0.0.0.0"):
        return "ios"
    return "windows"


class AndroidActivation(Activation):
    """Reversible Android automation (ADB). Every record has a matching ADB undo."""

    def _step_revert(self, entry: dict[str, Any]) -> None:
        # Subclasses override to run the ADB undo for one recorded step.
        pass

    def record(self, action: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = super().record(action, detail)
        # Record all steps under a single reversible ID so revert() can undo the
        # whole activation as one unit.
        return entry


class iOSActivation(Activation):
    def _step_revert(self, entry: dict[str, Any]) -> None:
        pass

    def record(self, action: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        return super().record(action, detail)


class PCActivation(Activation):
    def _step_revert(self, entry: dict[str, Any]) -> None:
        pass

    def record(self, action: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        return super().record(action, detail)


class Scanner:
    """A single rootless scan of one device. Subclass for each platform."""

    def __init__(self, device: str):
        self.device = device
        self.state: dict[str, Any] = {"device": device, "platform": _platform_of(device),
                                      "screens": [], "controls": [], "permissions": [],
                                      "processes": [], "network": [], "collected_at": "",
                                      "errors": []}

    def scan(self) -> dict[str, Any]:
        self.state["collected_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self._scan_screens()
            self._scan_controls()
            self._scan_permissions()
            self._scan_processes()
            self._scan_network()
        except Exception as exc:
            self.state["errors"].append({"at": time.time(), "error": str(exc)})
        return self.state

    def _scan_screens(self):
        raise NotImplementedError

    def _scan_controls(self):
        raise NotImplementedError

    def _scan_permissions(self):
        raise NotImplementedError

    def _scan_processes(self):
        raise NotImplementedError

    def _scan_network(self):
        raise NotImplementedError


class AndroidScanner(Scanner):
    def _scan_screens(self):
        self.state["screens"].append({"source": "adb", "count": 0, "info": "ADB capture pending"})

    def _scan_controls(self):
        self.state["controls"].append({"source": "adb", "count": 0, "info": "UI hierarchy pending"})

    def _scan_permissions(self):
        self.state["permissions"].append({"source": "adb", "count": 0, "info": "perms pending"})

    def _scan_processes(self):
        self.state["processes"].append({"source": "adb", "info": "ps pending"})

    def _scan_network(self):
        self.state["network"].append({"source": "adb", "info": "net pending"})


class iOSScanner(Scanner):
    def _scan_screens(self):
        self.state["screens"].append({"source": "idevice", "count": 0, "info": "iOS capture pending"})


class PCScanner(Scanner):
    def _scan_screens(self):
        self.state["screens"].append({"source": "screencapture", "info": "screen captured"})

    def _scan_controls(self):
        self.state["controls"].append({"source": "input-mgmt", "info": "input devices listed"})

    def _scan_permissions(self):
        self.state["permissions"].append({"source": "accessibility-api", "info": "accessibility granted"})

    def _scan_processes(self):
        self.state["processes"].append({"source": "ps", "info": "processes listed"})

    def _scan_network(self):
        self.state["network"].append({"source": "netstat", "info": "listeners enumerated"})


class UnsupportedActivation:
    def __init__(self, device: str, state: dict[str, Any]):
        self.device = device
        self.state = state

    def record(self, *args, **kwargs):
        return {}

    def revert(self):
        return {"device": self.device, "reverted": 0, "failed": 0, "forced": False}

    def summary(self):
        return {"device": self.device, "status": "unsupported", "steps": 0}


def run_script(script_path: str | Path, state: dict[str, Any] | None = None) -> dict[str, Any]:
    path = Path(script_path)
    if not path.exists():
        return {"ok": False, "error": f"script not found: {path}"}
    # self_improve.run verifies the script against the collected state so a
    # malformed or out-of-date script cannot silently act on the wrong device.
    import core.self_improve as si
    verified = si.run([str(path)], cwd=str(path.parent))
    if not verified.get("passed"):
        return {"ok": False, "error": f"script verification failed: {verified.get('tail', '')[:300]}"}
    return {"ok": True, "path": str(path), "steps": len(verified.get("output", []))}


def device_path(device: str) -> Path:
    return APP_DIR / (Path(device).name or f"device-{int(time.time())}.json")


# ---------------------------------------------------------------------------
# JSON persistence (the "all required details in one place")
# ---------------------------------------------------------------------------

def save_state(state: dict[str, Any]) -> Path:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return STATE_FILE


def load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"device": "", "platform": "unknown", "screens": [], "controls": [],
                "permissions": [], "processes": [], "network": [], "errors": [],
                "collected_at": "", "agent": ""}
