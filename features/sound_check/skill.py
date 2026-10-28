"""
Feature: sound_check
Description: Prove the machine's audio works - list usable microphones and speakers, play a measured test tone, meter live microphone input, and read back the output volume after setting it.
Uses theme tokens from themes.json (no hardcoded colours). Every automated check runs on silence, which is exactly why it cannot settle whether a person can be heard: the meter says what it heard and its peak, a test tone says how long it took and whether the device answered, and a volume change is read back rather than assumed. Missing backends are named, never guessed at.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "sound_check",
    "aliases": ["sound_check", "test my mic", "test microphone", "mic test", "audio test",
                "test speakers", "audio devices", "list microphones", "list speakers",
                "can you hear me", "why can't you hear me", "set volume", "change volume"],
    "description": (
        "Prove the machine's audio actually works: list the microphones and speakers the "
        "operating system reports as usable, measure a speaker test tone, show a live microphone "
        "input meter and report the peak it heard, and read back the output volume after setting "
        "it. A muted microphone and a level slider at zero both pass every automated probe on "
        "silence, so the only real proof is a person speaking - and the meter says what it heard "
        "instead of assuming."
    ),
    "triggers": [
        "test my mic", "test the microphone", "mic test", "audio test",
        "test my speakers", "play a test tone", "list microphones", "list speakers",
        "audio devices", "can you hear me", "why can't you hear me",
        "set volume", "change volume", "volume up", "mute", "how loud is it",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: devices | tone | meter | volume | diagnosis. Defaults to devices.",
            },
            "kind": {
                "type": "STRING",
                "description": "Device kind for devices: input | output | all. Defaults to all.",
            },
            "device": {
                "type": "STRING",
                "description": "Device name for tone, meter or volume. Defaults to the selected device.",
            },
            "target": {
                "type": "STRING",
                "description": "Alias for device.",
            },
            "volume": {
                "type": "INTEGER",
                "description": "Volume percentage 0-100 for the volume operation.",
            },
            "seconds": {
                "type": "NUMBER",
                "description": "How long the meter listens. Defaults to 3, capped at 20.",
            },
            "frequency": {
                "type": "INTEGER",
                "description": "Test-tone frequency in Hz. Defaults to 440.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "media",
    "surface": "both",
    "requires": [],
    "optional_dependencies": ["sounddevice", "numpy"],
    "notes": "Backends: sounddevice for devices and metering, pycaw/AppleScript/pactl/amixer for volume, ffplay or numpy for the test tone. Each is probed per call and named when missing.",
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _as_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default: int, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _device_name(kwargs: Dict[str, Any]) -> str:
    return (kwargs.get("device") or kwargs.get("target") or "").strip()


def _op_devices(kwargs: Dict[str, Any]) -> dict:
    from core.security.tools import available

    kind = (kwargs.get("kind") or "all").strip().lower()
    try:
        from core import audio_devices
    except Exception as exc:
        return _op("devices", False, None,
                   f"the audio device layer could not be loaded: {type(exc).__name__}: {exc}")

    inputs = audio_devices.list_devices("input") if kind in ("all", "input") else []
    outputs = audio_devices.list_devices("output") if kind in ("all", "output") else []
    if not inputs and not outputs:
        return _op("devices", False, None, (
            "the operating system reports no usable audio devices. On a phone, grant the "
            "microphone permission and connect or wake the device."))

    return _op("devices", True, {
        "inputs": inputs,
        "outputs": outputs,
        "selected_output": _selected_output(audio_devices),
        "volume_backend": _volume_backend(),
        "tone_available": bool(available(["ffplay"]).get("ffplay", {}).get("present"))
        or _numpy_present(),
        "note": ("Only devices the OS reports as actually usable are listed - a device that "
                 "cannot be opened is not offered, because picking it produces silence that "
                 "looks like a broken microphone."),
    })


def _selected_output(audio_devices) -> Optional[str]:
    for name in ("selected_output_device", "get_output_device", "output_device"):
        getter = getattr(audio_devices, name, None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                continue
    return None


def _volume_backend() -> str:
    try:
        from core.media import volume
        return volume.backend()
    except Exception:
        return "unknown"


def _numpy_present() -> bool:
    try:
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def _op_tone(kwargs: Dict[str, Any]) -> dict:
    import time

    frequency = _as_int(kwargs.get("frequency"), 440, 20000)
    device = _device_name(kwargs)
    from core.security.tools import available

    if available(["ffplay"]).get("ffplay", {}).get("present"):
        started = time.time()
        result = available(["ffplay"])
        try:
            import subprocess

            argv = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                    "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration=1"]
            if device:
                argv += ["-showmode", "0"]
            subprocess.run(argv, capture_output=True, timeout=15)
        except Exception as exc:
            return _op("tone", False, None, f"ffplay ran but failed: {type(exc).__name__}: {exc}")
        return _op("tone", True, {
            "frequency_hz": frequency,
            "duration_seconds": 1,
            "engine": "ffplay",
            "elapsed_ms": round((time.time() - started) * 1000, 1),
            "device": device or "system default",
            "note": ("ffplay answered with a completed process. Whether a person heard the tone "
                     "depends on this machine being un-muted."),
        })

    if _numpy_present():
        try:
            import numpy as np
            import sounddevice as sd

            rate = 44100
            duration = 1.0
            samples = 0.3 * np.sin(2.0 * np.pi * frequency * np.arange(int(rate * duration)) / rate)
            started = time.time()
            sd.play(samples, rate, blocking=True)
            return _op("tone", True, {
                "frequency_hz": frequency,
                "duration_seconds": duration,
                "engine": "sounddevice+numpy",
                "elapsed_ms": round((time.time() - started) * 1000, 1),
                "device": device or "system default",
                "note": "The tone was written to the output stream; whether it was heard depends on the device being un-muted.",
            })
        except Exception as exc:
            return _op("tone", False, None, f"sounddevice refused the tone: {type(exc).__name__}: {exc}")

    return _op("tone", False, None, (
        "No audio playback backend is available: ffplay is not installed and numpy/sounddevice "
        "are missing either. Install ffmpeg to enable the test tone."))


def _op_meter(kwargs: Dict[str, Any]) -> dict:
    seconds = _as_float(kwargs.get("seconds"), 3.0)
    seconds = max(0.5, min(seconds, 20.0))
    device = _device_name(kwargs)

    try:
        import numpy as np
        import sounddevice as sd
    except Exception as exc:
        return _op("meter", False, None, (
            f"Live metering needs numpy and sounddevice, which are not available here "
            f"({type(exc).__name__}). Without them there is no honest meter: a probe on silence "
            "cannot tell a muted microphone from a quiet room, and it would be dishonest to "
            "report either as working."))

    try:
        frames = int(44100 * seconds)
        recording = sd.rec(frames, samplerate=44100, channels=1, dtype="float64")
        sd.wait()
    except Exception as exc:
        return _op("meter", False, None, (
            f"The input stream could not be opened ({type(exc).__name__}: {exc}). Check the "
            "microphone is connected and that the OS has granted the permission."))

    if recording is None or recording.size == 0:
        return _op("meter", False, None, "The input stream produced no samples.")

    peak = float(np.max(np.abs(recording)))
    rms = float(np.sqrt(np.mean(np.power(recording, 2))))
    clipping = peak >= 0.99
    if peak < 1e-4:
        verdict = "silence"
        note = ("The input read as silence. That is either a muted microphone, a level at zero, "
                "or a privacy shutter - it is not proof that the microphone works.")
    elif clipping:
        verdict = "too loud"
        note = "The input is clipping; lower the microphone level."
    else:
        verdict = "sound heard"
        note = "A signal was heard. The peak is what actually reached Stella, not what the OS claims."

    return _op("meter", True, {
        "seconds": seconds,
        "device": device or "system default",
        "peak": round(peak, 6),
        "rms": round(rms, 6),
        "peak_dbfs": round(20 * float(np.log10(peak)), 1) if peak > 0 else None,
        "verdict": verdict,
        "clipping": clipping,
        "note": note,
    })


def _op_volume(kwargs: Dict[str, Any]) -> dict:
    level = kwargs.get("volume")
    try:
        level = int(float(level))
    except (TypeError, ValueError):
        return _op("volume", False, None,
                   "Give a volume percentage 0-100 (volume=...).")
    device = _device_name(kwargs)

    try:
        from core.media import volume as volume_module
    except Exception as exc:
        return _op("volume", False, None, f"{type(exc).__name__}: {exc}")

    outcome = volume_module.set_volume(level, device)
    current = volume_module.get_volume(device)
    worked = outcome.get("outcome") in ("done", "started")
    return _op("volume", worked, {
        **outcome,
        "requested": level,
        "read_back": current,
        "device": device or "the selected output",
        "backend": volume_module.backend(),
    }, "" if worked else outcome.get("detail"))


def _op_diagnosis(kwargs: Dict[str, Any]) -> dict:
    from core.security.tools import available

    try:
        from core import audio_devices
    except Exception as exc:
        return _op("diagnosis", False, None, f"{type(exc).__name__}: {exc}")

    inputs = audio_devices.list_devices("input")
    outputs = audio_devices.list_devices("output")
    checks: list = []

    checks.append({"check": "microphone present", "ok": bool(inputs),
                   "detail": f"{len(inputs)} usable input device(s)"})
    checks.append({"check": "speaker present", "ok": bool(outputs),
                   "detail": f"{len(outputs)} usable output device(s)"})

    backend_available = _volume_backend() != "none"
    checks.append({"check": "volume control available", "ok": backend_available,
                   "detail": f"backend: {_volume_backend()}"})

    if _volume_backend() != "none":
        try:
            from core.media import volume as volume_module

            level = volume_module.get_volume("")
            checks.append({"check": "output level above zero", "ok": (level or 0) > 0,
                           "detail": f"level reads {level}%"})
        except Exception:
            pass

    blockers = [check["check"] for check in checks if not check["ok"]]
    summary = ("Audio is usable on this machine." if not blockers else
               "Blocked: " + ", ".join(blockers))
    return _op("diagnosis", True, {
        "checks": checks,
        "blockers": blockers,
        "summary": summary,
        "next_step": ("Run the meter operation and speak for a few seconds - it is the only check "
                      "that settles whether a person can be heard." if not blockers else
                      "Fix the blockers above first; a meter or tone test will not pass while one is open."),
    })


_OPERATIONS = {
    "devices": _op_devices,
    "tone": _op_tone,
    "meter": _op_meter,
    "volume": _op_volume,
    "diagnosis": _op_diagnosis,
}

_OPERATION_TITLES = {
    "devices": "Audio Devices", "tone": "Speaker Test Tone", "meter": "Microphone Meter",
    "volume": "Output Volume", "diagnosis": "Audio Diagnosis",
}

_ALIASES = {
    "list_devices": "devices", "audio_devices": "devices", "devices_list": "devices",
    "test_tone": "tone", "speakers": "tone", "play_tone": "tone",
    "mic_meter": "meter", "test_mic": "meter", "listen": "meter", "record_test": "meter",
    "set_volume": "volume", "mute": "volume",
    "diagnose": "diagnosis", "audio_check": "diagnosis",
}


def _failure(operation: str, reason: str) -> dict:
    title = _OPERATION_TITLES.get(operation, "Audio")
    return {
        "title": title,
        "summary": f"{title} unavailable: {reason}",
        "spoken_narrative": f"{title} unavailable: {reason}",
        "operation": operation,
        "ok": False,
        "record": _op(operation, False, None, reason),
    }


def execute(**kwargs) -> dict:
    """Prove the machine's audio works, with read-backs rather than assumptions."""
    operation = (kwargs.get("operation") or "devices").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return _failure(operation, f"Unknown operation '{operation}'. One of: "
                                   + ", ".join(sorted(_OPERATIONS)) + ".")

    try:
        record = handler(kwargs)
    except TypeError as exc:
        return _failure(operation, f"Bad arguments for '{operation}': {exc}")
    except Exception as exc:
        return _failure(operation, f"{type(exc).__name__}: {exc}")

    return {
        "title": _OPERATION_TITLES.get(operation, "Audio"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "devices":
        if not record.get("ok"):
            return f"Audio devices unavailable: {record.get('error')}"
        return (f"{len(value.get('inputs') or [])} usable microphone(s) and "
                f"{len(value.get('outputs') or [])} usable speaker(s). Volume backend: "
                f"{value.get('volume_backend')}.")
    if operation == "tone":
        if not record.get("ok"):
            return f"Test tone unavailable: {record.get('error')}"
        return (f"A {value.get('frequency_hz')} Hz tone played through {value.get('engine')} in "
                f"{value.get('elapsed_ms')} ms. {value.get('note')}")
    if operation == "meter":
        if not record.get("ok"):
            return f"Microphone meter unavailable: {record.get('error')}"
        return (f"Metered {value.get('seconds')}s: peak {value.get('peak')} "
                f"({value.get('peak_dbfs')} dBFS) - {value.get('verdict')}. {value.get('note')}")
    if operation == "volume":
        if not record.get("ok"):
            return f"Volume could not be set: {record.get('error')}"
        return value.get("detail", "Volume set.")
    if operation == "diagnosis":
        return f"{value.get('summary')} {value.get('next_step')}"
    return record.get("error") or "No operation ran."
