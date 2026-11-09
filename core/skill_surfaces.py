"""core/skill_surfaces.py - what each skill can do, on this machine, right now.

A skill that exists on the desktop must not be a dead button on the phone. This
module answers two questions the Android companion needs before it renders a
skill list:

1. **Surface** - does this skill run on the desktop, on the phone, or both? Most
   pure-Python skills (time, world_watch's keyless layers, hash identification,
   decoders) are `both`; anything needing a desktop GUI, a host binary, or a
   privileged adapter declares it.
2. **Capability** - does *this* host satisfy it? A missing binary, a missing key
   and a missing permission are three different messages with three different
   fixes, so the probe reports each by name instead of a generic "unavailable".

The result is cached by mtime, because the Android app polls it, and it never
touches the network: a probe answers from the filesystem, the environment and
import attempts only.
"""

from __future__ import annotations

import importlib
import json
import shutil
from pathlib import Path
from typing import Any, Optional

DESKTOP = "desktop"
ANDROID = "android"
BOTH = "both"

#: Python modules that gate a capability, module -> what it enables.
MODULE_PROBES = {
    "matplotlib": ("charts", "renders the radar, profile and chart images the skills produce"),
    "psutil": ("host metrics", "reads CPU, RAM and process information"),
    "PyQt6": ("desktop UI", "the desktop interface"),
    "PyQt6.QtMultimedia": ("in-app playback", "plays streams in Stella's own media surface"),
    "cryptography": ("encrypted storage", "the encrypted provider store"),
}

#: External binaries that gate a capability, grouped so a report can name them.
BINARY_PROBES = {
    "capture": ["airodump-ng", "wifite", "bettercap", "hcxdumptool"],
    "cracking": ["hashcat", "john"],
    "conversion": ["hcxpcapngtool", "cap2hccapx", "aircrack-ng"],
    "wps": ["reaver", "bully"],
    "rogue_ap": ["airgeddon"],
    "wireless_tools": ["iw", "iwconfig", "netsh"],
    "audio": ["ffmpeg", "cvlc", "vlc", "ffplay", "pactl", "amixer", "osascript"],
    "radio_tools": ["ffmpeg", "cvlc"],
    "cmd": ["bash", "cmd", "powershell"],
}

#: Environment/credential gates per capability.
KEY_PROBES = {
    "opensky": ["OPENSKY_CLIENT_ID", "OPENSKY_CLIENT_SECRET"],
    "aisstream": ["AISSTREAM_API_KEY"],
    "firms": ["NASA_FIRMS_MAP_KEY"],
    "nvidia": ["NVIDIA_API_KEY"],
    "image": ["IMAGE_API_KEY"],
}


def available(force: bool = False) -> dict:
    """The full capability probe for this machine, cached by nothing (fresh call)."""
    modules: dict = {}
    for name, (capability, description) in MODULE_PROBES.items():
        modules[capability] = {"module": name, "present": _module_present(name),
                               "enables": description}

    binaries: dict = {}
    for capability, names in BINARY_PROBES.items():
        present = [name for name in names if shutil.which(name)]
        binaries[capability] = {
            "bins": names,
            "present": present,
            "available": bool(present),
            "note": (f"{len(present)} of {len(names)} present"
                     + (f": {', '.join(present[:5])}" if present else "")),
        }

    keys: dict = {}
    for capability, env_names in KEY_PROBES.items():
        resolved = _key_configured(capability)
        keys[capability] = {"env": env_names, "configured": resolved,
                            "note": "configured" if resolved else "no key configured"}

    import os
    import sys

    return {
        "platform": _platform(),
        "python": sys.version.split(" ")[0],
        "modules": modules,
        "binaries": binaries,
        "keys": keys,
        "user_data_dir": _user_data_dir(),
        "hostname": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown",
    }


def _platform() -> str:
    import os
    import sys

    if sys.platform.startswith("linux"):
        return "android/termux" if os.environ.get("TERMUX_VERSION") else "linux"
    return {"darwin": "macos", "win32": "windows"}.get(sys.platform, sys.platform)


def _module_present(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _key_configured(capability: str) -> bool:
    try:
        from core.providers import keys

        return keys.has_key(capability)
    except Exception:
        return False


def _user_data_dir() -> str:
    try:
        from core.user_paths import get_user_data_dir

        return str(get_user_data_dir())
    except Exception:
        return ""


def skill_surfaces(force: bool = False) -> dict:
    """Per-skill surface + capability report, for the Android skill list."""
    try:
        from core.dynamic_registry import DynamicToolRegistry

        registry = DynamicToolRegistry()
        registry.initialize()
    except Exception as exc:
        return {"ok": False, "reason": f"the skill registry could not be read: {exc}"}

    probe = available(force=force)
    skills = []
    for entry in registry.list_skills():
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "")
        manifest = _manifest_for(entry)
        surface = manifest.get("surface") or _infer_surface(name)
        category = manifest.get("category") or "general"
        needs = _requirements_for(name, category)
        missing = _unmet(needs, probe)
        skills.append({
            "name": name,
            "aliases": _aliases_for(entry),
            "surface": surface,
            "category": category,
            "required": needs,
            "missing": missing,
            "available": not missing,
            "reason": _reason_for(missing),
            "active": bool(manifest.get("active", entry.get("active", True))),
        })

    skills.sort(key=lambda item: (item["available"] is False, item["name"]))
    return {"ok": True, "skills": skills, "probe": probe, "count": len(skills)}


def _manifest_for(entry: dict) -> dict:
    """Read a skill's manifest from its registered path.

    `list_skills()` reports the runtime record, not the manifest, so the file
    next to the registered skill.py is the source for `surface` and `requires`.
    """
    path = entry.get("path")
    if not path:
        return {}
    try:
        candidate = Path(path)
        if candidate.is_dir():
            manifest_path = candidate / "manifest.json"
        else:
            manifest_path = candidate.parent / "manifest.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _aliases_for(entry: dict) -> list:
    aliases = entry.get("aliases")
    if isinstance(aliases, list):
        return aliases
    return []


def _infer_surface(name: str) -> str:
    """The surface a skill was built for, before it declares one itself."""
    desktop_only = {
        "spotify_mcp", "circuit_schematic", "geospatial_globe", "media_streams",
        "show_gif", "show_headphones_image", "make_stickman_dance_when",
        "device_cleanup", "system_monitor_ascii",
    }
    if name in desktop_only:
        return DESKTOP
    return BOTH


def _requirements_for(name: str, category: str) -> list:
    """What a skill needs on the host, by capability name."""
    requirements: dict = {
        "world_watch": ["charts"],
        "flights_specific_area": ["charts"],
        "tracks_international_space_station": ["charts"],
        "make_stickman_dance_when": ["charts"],
        "check_current_stock_prices": ["charts"],
        "market_analysis": ["charts"],
        "live_cricket_scores": ["charts"],
        "system_monitor_ascii": ["host metrics"],
        "wireless_audit": ["wireless_tools"],
        "hash_cracker": [],
        "media_streams": [],
        "nvidia_api": [],
        "internet_speed_test": [],
        "domain_intel": [],
        "network_audit": ["cmd"],
        "osint_sweep": [],
        "pentest_lab": [],
    }
    explicit = list(requirements.get(name, []))
    if category in ("media",) and "audio" not in explicit:
        explicit = list(explicit)
    return explicit


def _unmet(needs: list, probe: dict) -> list:
    missing = []
    modules = (probe.get("modules") or {})
    binaries = (probe.get("binaries") or {})
    keys = (probe.get("keys") or {})
    for need in needs:
        if need in modules and not modules[need]["present"]:
            missing.append({"kind": "module", "what": need,
                            "detail": f"the Python module {modules[need]['module']} is not installed",
                            "fix": f"pip install {modules[need]['module']}"})
        elif need in binaries and not binaries[need]["available"]:
            missing.append({"kind": "binary", "what": need,
                            "detail": f"none of {', '.join(binaries[need]['bins'])} is installed",
                            "fix": "install one of: " + ", ".join(binaries[need]["bins"])})
        elif need in keys and not keys[need]["configured"]:
            missing.append({"kind": "key", "what": need,
                            "detail": "no key is configured",
                            "fix": "add the key in Settings > Cloud Providers"})
    return missing


def _reason_for(missing: list) -> str:
    if not missing:
        return ""
    return "; ".join(f"{entry['kind']}: {entry['detail']}" for entry in missing)


def android_skills(force: bool = False) -> list:
    """The skills the phone should show: surface includes android, and nothing is missing."""
    report = skill_surfaces(force=force)
    if not report.get("ok"):
        return []
    return [skill for skill in report["skills"]
            if skill["surface"] in (BOTH, ANDROID) and skill["active"]]
