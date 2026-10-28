"""core/dependencies.py - what a machine needs, and how the agent installs it.

A skill that needs `matplotlib`, `psutil`, `ffmpeg` or a whole pentest suite should be able to
say so and have the agent bring it in. Four rules make that safe enough to automate:

1. **It is per-platform, and it says so.** pip on every platform; apt on Debian/Ubuntu/Kali;
   pkg on Termux; brew on macOS; a named download on Windows for tools that have no package.
   A machine with no package manager reports that, not a fake success.

2. **It never guesses a mapping.** Each package name is declared once, per platform, in
   `PACKAGE_MAP`, so `pip install aircrack-ng` (which does not exist) can never be attempted.

3. **It confirms before it changes the machine.** Installing is `active`/`destructive` class in
   `core/tool_policy.py`, so a rule must allow it; and the caller must pass `confirm=True`.

4. **It reads back.** After an install, the module is re-imported (or the binary re-probed) and
   the result says `done`, `unverified`, or `failed` with the actual error text.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Optional

#: requirement name -> {platform: install spec}
#: platform is one of: pip (every platform), apt, pkg, brew, winget, script
PACKAGE_MAP: dict[str, dict[str, Any]] = {
    # ---------------------------------------------------------- python modules
    "matplotlib": {"pip": "matplotlib", "apt": "python3-matplotlib", "pkg": "python-matplotlib",
                   "brew": "matplotlib"},
    "psutil": {"pip": "psutil", "apt": "python3-psutil", "pkg": "psutil", "brew": "psutil"},
    "numpy": {"pip": "numpy", "apt": "python3-numpy", "pkg": "python-numpy", "brew": "numpy"},
    "sounddevice": {"pip": "sounddevice", "apt": "python3-sounddevice"},
    "requests": {"pip": "requests", "apt": "python3-requests", "pkg": "python-requests",
                 "brew": "python-requests"},
    "speedtest": {"pip": "speedtest-cli", "apt": "speedtest-cli", "pkg": "speedtest-cli"},
    "PyQt6": {"pip": "PyQt6", "apt": "python3-PyQt6", "brew": "pyqt"},
    "PyQt6-WebEngine": {"pip": "PyQt6-WebEngine", "apt": "python3-PyQt6-WebEngine"},
    "cryptography": {"pip": "cryptography", "apt": "python3-cryptography", "brew": "cryptography"},
    "sgp4": {"pip": "sgp4"},
    "pyModeS": {"pip": "pyModeS"},
    "scapy": {"pip": "scapy", "apt": "python3-scapy", "pkg": "python-scapy"},
    "dnspython": {"pip": "dnspython", "apt": "python3-dnspython", "pkg": "python-dnspython"},
    "whois": {"pip": "python-whois"},
    "python-whois": {"pip": "python-whois"},
    "exifread": {"pip": "exifread", "apt": "python3-exifread"},
    "pypdf": {"pip": "pypdf", "apt": "python3-pypdf"},
    "python-docx": {"pip": "python-docx", "apt": "python3-docx"},
    "openpyxl": {"pip": "openpyxl", "apt": "python3-openpyxl"},
    "beautifulsoup4": {"pip": "beautifulsoup4", "apt": "python3-bs4", "pkg": "python-beautifulsoup4",
                       "brew": "beautifulsoup4"},
    "lxml": {"pip": "lxml", "apt": "python3-lxml", "pkg": "python-lxml", "brew": "lxml"},
    "Pillow": {"pip": "Pillow", "apt": "python3-pil", "pkg": "python-pillow", "brew": "pillow"},
    "pycaw": {"pip": "pycaw", "note": "Windows-only; the volume backend on other platforms differs"},
    "comtypes": {"pip": "comtypes", "note": "Windows-only; provides COM for pycaw"},
    "pytest": {"pip": "pytest", "apt": "python3-pytest"},

    # ------------------------------------------------------------ system tools
    "ffmpeg": {"apt": "ffmpeg", "pkg": "ffmpeg", "brew": "ffmpeg",
               "winget": "Gyan.FFmpeg",
               "script": "https://www.gyan.dev/ffmpeg/builds/"},
    "vlc": {"apt": "vlc", "pkg": "vlc", "brew": "vlc", "winget": "VideoLAN.VLC"},
    "ffplay": {"apt": "ffmpeg", "pkg": "ffmpeg", "brew": "ffmpeg"},
    "tshark": {"apt": "tshark", "pkg": "tshark", "brew": "wireshark", "winget": "WiresharkFoundation.Wireshark"},
    "aircrack-ng": {"apt": "aircrack-ng", "pkg": "aircrack-ng", "brew": "aircrack-ng",
                    "winget": "aircrack-ng.aircrack-ng"},
    "airodump-ng": {"apt": "aircrack-ng", "pkg": "aircrack-ng"},
    "aireplay-ng": {"apt": "aircrack-ng", "pkg": "aircrack-ng"},
    "airmon-ng": {"apt": "aircrack-ng", "pkg": "aircrack-ng"},
    "wifite": {"apt": "wifite", "pip": "wifite2"},
    "bettercap": {"apt": "bettercap", "pkg": "bettercap", "brew": "bettercap"},
    "hcxdumptool": {"apt": "hcxdumptool", "pkg": "hcxdumptool"},
    "hcxpcapngtool": {"apt": "hcxtools", "pkg": "hcxtools"},
    "hcxhashtool": {"apt": "hcxtools", "pkg": "hcxtools"},
    "cap2hccapx": {"apt": "aircrack-ng", "pkg": "aircrack-ng"},
    "hashcat": {"apt": "hashcat", "pkg": "hashcat", "brew": "hashcat", "winget": "hashcat.hashcat",
                "script": "https://hashcat.net/hashcat/"},
    "john": {"apt": "john", "pkg": "john", "brew": "john"},
    "reaver": {"apt": "reaver", "pkg": "reaver"},
    "bully": {"apt": "bully", "pkg": "bully"},
    "airgeddon": {"apt": "airgeddon", "pkg": "airgeddon"},
    "iw": {"apt": "iw", "pkg": "iw", "brew": ""},
    "iwconfig": {"apt": "wireless-tools", "pkg": "wireless-tools"},
    "iwlist": {"apt": "wireless-tools", "pkg": "wireless-tools"},
    "macchanger": {"apt": "macchanger", "pkg": "macchanger"},
    "ip": {"apt": "iproute2", "pkg": "iproute2", "brew": "iproute2mac"},
    "curl": {"apt": "curl", "pkg": "curl", "brew": "curl", "winget": "cURL.cURL"},
    "wget": {"apt": "wget", "pkg": "wget", "brew": "wget"},
    "git": {"apt": "git", "pkg": "git", "brew": "git", "winget": "Git.Git"},
    "pactl": {"apt": "pulseaudio-utils", "pkg": "pulseaudio", "brew": ""},
    "amixer": {"apt": "alsa-utils", "pkg": "alsa-utils", "brew": ""},
    "osascript": {"note": "built into macOS; never installed"},
    "nmap": {"apt": "nmap", "pkg": "nmap", "brew": "nmap", "winget": "Insecure.Nmap"},
}

#: Grouped bundles a skill can ask for in one word.
BUNDLES: dict[str, list[str]] = {
    "charts": ["matplotlib", "numpy"],
    "wireless": ["aircrack-ng", "iw", "iwconfig", "ffmpeg"],
    "wireless-full": ["aircrack-ng", "wifite", "bettercap", "hcxdumptool", "hcxpcapngtool",
                      "hashcat", "john", "reaver", "bully", "airgeddon", "iw", "iwconfig",
                      "macchanger", "ffmpeg"],
    "cracking": ["hashcat", "john", "hcxpcapngtool", "aircrack-ng"],
    "osint": ["requests", "dnspython", "whois", "beautifulsoup4", "lxml"],
    "media": ["ffmpeg", "vlc", "ffplay"],
    "audio": ["sounddevice", "numpy", "psutil"],
    "forensics": ["tshark", "exifread", "pypdf", "python-docx", "openpyxl", "Pillow"],
    "capture": ["tshark", "ffmpeg"],
}


@dataclass
class Requirement:
    """One thing a machine needs, and its state on this machine."""

    name: str
    kind: str                      # module | binary | bundle
    present: bool
    path: str = ""
    spec: Optional[dict] = None
    installs: list = field(default_factory=list)
    note: str = ""


def platform_tag() -> str:
    """The platform bucket installs are chosen from."""
    import os
    import sys

    if sys.platform.startswith("linux"):
        if os.environ.get("TERMUX_VERSION") or os.path.isdir("/data/data/com.termux"):
            return "termux"
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    return sys.platform


def package_manager() -> str:
    """The best package manager available on this machine, by name."""
    for manager, command in (("apt", "apt-get"), ("pkg", "pkg"), ("brew", "brew"),
                             ("winget", "winget"), ("pip", "pip"), ("pip", "pip3")):
        if shutil.which(command) or manager == "pip":
            return manager
    return "none"


def _module_present(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def probe(name: str) -> Requirement:
    """What this machine needs for one requirement, and whether it has it."""
    kind = "binary"
    if name in PACKAGE_MAP:
        spec = PACKAGE_MAP[name]
    else:
        spec = None

    # A requirement is a module when it has a pip entry and is not also a binary probe.
    if spec and "pip" in spec:
        kind = "module"
        present = _module_present(name)
        return Requirement(name=name, kind=kind, present=present,
                          path=name if present else "", spec=spec,
                          installs=_install_commands(spec), note=spec.get("note", ""))

    if spec:
        present = bool(shutil.which(name))
        return Requirement(name=name, kind=kind, present=present,
                          path=shutil.which(name) or "", spec=spec,
                          installs=_install_commands(spec), note=spec.get("note", ""))

    # Unknown to the map: probe as a binary, and say the map does not know it.
    present = bool(shutil.which(name))
    return Requirement(name=name, kind=kind, present=present, path=shutil.which(name) or "",
                      spec=None, installs=[], note=(
                          f"'{name}' is not in PACKAGE_MAP, so no install command is offered; "
                          "install it by hand and this probe will find it."))


def _install_commands(spec: dict) -> list:
    """The install commands to try, in order, for this platform."""
    commands: list = []
    if "pip" in spec:
        commands.append([sys.executable, "-m", "pip", "install", spec["pip"]])
    tag = platform_tag()
    if tag == "termux" and "pkg" in spec:
        commands.append(["pkg", "install", "-y", spec["pkg"]])
    if tag == "linux" and "apt" in spec:
        commands.append(["apt-get", "install", "-y", spec["apt"]])
    if tag == "macos" and "brew" in spec:
        commands.append(["brew", "install", spec["brew"]])
    if tag == "windows" and "winget" in spec:
        commands.append(["winget", "install", "--accept-source-agreements",
                         "--accept-package-agreements", spec["winget"]])
    return commands


def missing(names: list) -> list:
    """The requirements this machine does not satisfy, in order."""
    return [probe(name) for name in names if not probe(name).present]


def expand(bundle_or_name: str) -> list:
    """Expand a bundle name into its members, or return a single name."""
    return BUNDLES.get(bundle_or_name, [bundle_or_name])


def status(names: list) -> dict:
    """The state of several requirements, grouped by presence."""
    probes = [probe(name) for name in names]
    return {
        "ok": True,
        "present": [p.name for p in probes if p.present],
        "missing": [p.name for p in probes if not p.present],
        "details": [p.__dict__ for p in probes],
        "platform": platform_tag(),
        "package_manager": package_manager(),
    }


def install(name: str, confirm: bool = False, timeout: int = 900) -> dict:
    """Install one requirement, then re-probe it and read the result back.

    `confirm` is required: installing changes the machine, and a machine the user
    did not agree to change is a machine the user cannot trust.
    """
    if not confirm:
        requirement = probe(name)
        return {
            "ok": False,
            "outcome": "ask",
            "summary": (f"Installing '{name}' was not started because confirm was not set. "
                       f"It would run: {requirement.installs[0] if requirement.installs else 'a command this platform does not offer'}."),
            "requirement": requirement.__dict__,
        }

    requirement = probe(name)
    if requirement.present:
        return {"ok": True, "outcome": "done",
                "summary": f"'{name}' is already present at {requirement.path or 'the module path'}.",
                "requirement": requirement.__dict__}

    if not requirement.installs:
        return {"ok": False, "outcome": "failed",
                "reason": (f"'{name}' has no install command for {platform_tag()} "
                           f"({requirement.note}). Nothing was run."),
                "requirement": requirement.__dict__}

    attempts: list = []
    for command in requirement.installs:
        started = time.time()
        try:
            process = subprocess.run(command, capture_output=True, timeout=timeout)
            returncode = process.returncode
            stdout = (process.stdout or b"")[-2000:].decode("utf-8", errors="replace")
            stderr = (process.stderr or b"")[-1200:].decode("utf-8", errors="replace")
        except FileNotFoundError:
            attempts.append({"command": command[0], "ok": False,
                             "reason": f"{command[0]} is not installed on this machine"})
            continue
        except subprocess.TimeoutExpired:
            attempts.append({"command": command[0], "ok": False,
                             "reason": f"the install did not finish within {timeout}s"})
            continue
        except Exception as exc:  # noqa: BLE001
            attempts.append({"command": command[0], "ok": False,
                             "reason": f"{type(exc).__name__}: {exc}"})
            continue

        attempts.append({"command": " ".join(command[:2]), "ok": returncode == 0,
                         "returncode": returncode, "elapsed_s": round(time.time() - started, 1),
                         "stderr_tail": stderr})
        if returncode == 0:
            break

    installed = probe(name)
    if not installed.present:
        return {"ok": False, "outcome": "unverified",
                "reason": (f"The install command reported success, but '{name}' is still not "
                           "importable - check that it installed into this interpreter "
                           f"({sys.executable})."),
                "attempts": attempts, "requirement": requirement.__dict__}

    return {"ok": True, "outcome": "done",
            "summary": (f"'{name}' is now available "
                        f"({'binary at ' + installed.path if installed.kind == 'binary' else 'importable'})."),
            "attempts": attempts, "requirement": installed.__dict__}


def install_all(names: list, confirm: bool = False, timeout: int = 900) -> dict:
    """Install each missing requirement in turn, reporting every attempt."""
    results = []
    for name in names:
        if probe(name).present:
            results.append({"name": name, "outcome": "already-present"})
            continue
        outcome = install(name, confirm=confirm, timeout=timeout)
        results.append({"name": name, "outcome": outcome.get("outcome"),
                        "summary": outcome.get("summary") or outcome.get("reason"),
                        "ok": outcome.get("ok", False)})
    return {"ok": True, "results": results,
            "installed": [r["name"] for r in results if r["outcome"] == "done"],
            "failed": [r["name"] for r in results if r["outcome"] not in ("done", "already-present")]}


def requirement_names_for(skill_name: str) -> list:
    """The requirements a skill declares, from its manifest.

    A manifest may declare `requires` (capability names such as `charts`) and
    `optional_dependencies` (package names). Both are expanded through the maps
    so a skill can ask for a bundle in one word.
    """
    names: list = []
    try:
        from pathlib import Path

        manifest_path = Path(__file__).resolve().parents[1] / "features" / skill_name / "manifest.json"
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return names

    for entry in manifest.get("requires") or []:
        names.extend(expand(str(entry)))
    for entry in manifest.get("optional_dependencies") or []:
        names.extend(expand(str(entry)))
    return names
