"""core/media/volume.py - per-device output volume, with a read-back.

Volume is the one system setting where "it should have worked" is not good
enough: a slider that moves the wrong device is worse than no slider. Three rules
come from that:

* the level is set on the *named* device, not on whatever the system calls the
  default
* the level is read back afterwards, and a mismatch is reported as `unverified`
  rather than rounded up to `done`
* Windows keeps not-present devices under the same friendly name as live ones, so
  the device is re-resolved by name after the change and its actual level reported

Supported backends: pycaw (Windows Core Audio), AppleScript (macOS),
PulseAudio/PipeWire `pactl` and `amixer` (Linux). Anything else is reported as
unavailable by name.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional

FAILED = "failed"
DONE = "done"
UNVERIFIED = "unverified"


def backend() -> str:
    """The volume backend available on this machine, by name."""
    if _pycaw_importable():
        return "windows-core-audio"
    import sys

    if sys.platform == "darwin":
        return "macos-applescript"
    if sys.platform.startswith("linux"):
        if shutil.which("pactl"):
            return "pulseaudio-pactl"
        if shutil.which("amixer"):
            return "alsa-amixer"
    return "none"


def _pycaw_importable() -> bool:
    """Whether pycaw can even be imported - checked before any COM call."""
    try:
        from pycaw.pycaw import AudioUtilities  # noqa: F401

        return True
    except Exception:
        return False


def set_volume(percent: int, device: str = "") -> dict:
    """Set the output volume, then read it back and report the difference."""
    level = max(0, min(100, int(percent)))
    backend_name = backend()

    if backend_name == "windows-core-audio":
        return _windows_set(level, device)
    if backend_name == "macos-applescript":
        return _macos_set(level)
    if backend_name == "pulseaudio-pactl":
        return _pactl_set(level, device)
    if backend_name == "alsa-amixer":
        return _amixer_set(level)

    return {"outcome": FAILED, "detail": (
        f"No volume backend is available on this machine (looked for: {backend_name}); "
        "the level was not changed.")}


def get_volume(device: str = "") -> Optional[int]:
    """The current output volume, or None when it cannot be read."""
    backend_name = backend()
    if backend_name == "windows-core-audio":
        return _windows_get(device)
    if backend_name == "macos-applescript":
        return _macos_get()
    if backend_name == "pulseaudio-pactl":
        return _pactl_get(device)
    if backend_name == "alsa-amixer":
        return _amixer_get()
    return None


# --------------------------------------------------------------------- Windows

def _pycaw_device(device_name: str):
    """pycaw's AudioDevice wrapper for a device by name, or the default one."""
    try:
        from comtypes import CoInitialize

        from pycaw.pycaw import AudioUtilities

        try:
            CoInitialize()
        except Exception:
            pass
    except Exception:
        return None

    try:
        if device_name:
            wanted = device_name.strip().lower()
            for candidate in AudioUtilities.GetAllDevices():
                name = str(getattr(candidate, "FriendlyName", "") or "").strip()
                # Core Audio calls a device "Speakers (2- High Definition Audio
                # Device)", so a bare "Speakers" matches the leading name.
                leading = name.split("(", 1)[0].strip().lower()
                if wanted in (name.lower(), leading):
                    return candidate
            return None
        return AudioUtilities.GetSpeakers()
    except Exception:
        return None


def _windows_device(device: str):
    return _pycaw_device(device)


def _windows_set(level: int, device: str) -> dict:
    device_object = _windows_device(device)
    if device_object is None:
        return {"outcome": FAILED, "detail": (
            f"No Core Audio device matched '{device or 'the default output'}'; the level was not changed.")}
    try:
        device_object.EndpointVolume.SetMasterVolumeLevelScalar(level / 100.0, None)
    except Exception as exc:
        return {"outcome": FAILED, "detail": (
            f"The device refused the change: {type(exc).__name__}: {exc}")}

    actual = _windows_get(device)
    if actual is None:
        return {"outcome": UNVERIFIED, "detail": (
            f"Volume was set to {level}% but could not be read back.")}
    if abs(actual - level) <= 2:
        return {"outcome": DONE, "detail": (
            f"Volume is {actual}% on {getattr(device_object, 'FriendlyName', device or 'the selected output')}.")}
    return {"outcome": UNVERIFIED, "detail": (
        f"Volume was set to {level}% but reads back as {actual}% on "
        f"{getattr(device_object, 'FriendlyName', device or 'the selected output')}.")}


def _windows_get(device: str) -> Optional[int]:
    device_object = _windows_device(device)
    if device_object is None:
        return None
    try:
        return int(round(device_object.EndpointVolume.GetMasterVolumeLevelScalar() * 100))
    except Exception:
        return None


# ----------------------------------------------------------------------- macOS

def _macos_set(level: int) -> dict:
    try:
        subprocess.run(["osascript", "-e", f"set volume output volume {level}"],
                       capture_output=True, timeout=5, check=True)
    except Exception as exc:
        return {"outcome": FAILED, "detail": (
            f"AppleScript could not set the volume: {type(exc).__name__}: {exc}")}
    actual = _macos_get()
    if actual is None:
        return {"outcome": UNVERIFIED, "detail": f"Volume was set to {level}% but could not be read back."}
    if abs(actual - level) <= 3:
        return {"outcome": DONE, "detail": f"Volume is {actual}%."}
    return {"outcome": UNVERIFIED, "detail": (
        f"Volume was set to {level}% but reads back as {actual}%.")}


def _macos_get() -> Optional[int]:
    try:
        result = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"],
                                capture_output=True, timeout=5, text=True, check=True)
        return int(result.stdout.strip())
    except Exception:
        return None


# ----------------------------------------------------------------- Linux pactl

def _pactl_set(level: int, device: str) -> dict:
    target = device or "@DEFAULT_SINK@"
    try:
        subprocess.run(["pactl", "set-sink-volume", target, f"{level}%"],
                       capture_output=True, timeout=5, check=True)
    except Exception as exc:
        return {"outcome": FAILED, "detail": (
            f"pactl could not set the volume on {target}: {type(exc).__name__}: {exc}")}
    actual = _pactl_get(device)
    if actual is None:
        return {"outcome": UNVERIFIED, "detail": f"Volume was set to {level}% but could not be read back."}
    if abs(actual - level) <= 3:
        return {"outcome": DONE, "detail": f"Volume is {actual}% on {target}."}
    return {"outcome": UNVERIFIED, "detail": (
        f"Volume was set to {level}% but reads back as {actual}% on {target}.")}


def _pactl_get(device: str) -> Optional[int]:
    target = device or "@DEFAULT_SINK@"
    try:
        result = subprocess.run(["pactl", "get-sink-volume", target],
                                capture_output=True, timeout=5, text=True, check=True)
        for token in result.stdout.split():
            if token.endswith("%"):
                return int(token.rstrip("%"))
        return None
    except Exception:
        return None


# ----------------------------------------------------------------- Linux amixer

def _amixer_set(level: int) -> dict:
    try:
        subprocess.run(["amixer", "set", "Master", f"{level}%"],
                       capture_output=True, timeout=5, check=True)
    except Exception as exc:
        return {"outcome": FAILED, "detail": (
            f"amixer could not set the volume: {type(exc).__name__}: {exc}")}
    actual = _amixer_get()
    if actual is None:
        return {"outcome": UNVERIFIED, "detail": f"Volume was set to {level}% but could not be read back."}
    return {"outcome": DONE, "detail": f"Volume is {actual}%."}


def _amixer_get() -> Optional[int]:
    try:
        result = subprocess.run(["amixer", "get", "Master"],
                                capture_output=True, timeout=5, text=True, check=True)
        for token in result.stdout.replace("[", " ").split():
            if token.endswith("%"):
                return int(token.rstrip("%"))
        return None
    except Exception:
        return None
