"""
core/voice_clone.py — lightweight user-voice cloning for Stella.

Stella can speak for the user. Instead of shipping a handful of machine voices,
the user records a short sample of their own voice once, Stella extracts a
compact speaker embedding from it, and that embedding is fed back into the TTS
engine for calls, reminders, and everyday responses. The result is a voice
that sounds like the user, without the weight of a full personal voice model.

What this module provides
-------------------------
- A voice profile: record -> extract -> store a short WAV sample on-device,
  with no network involved.
- A compact speaker embedding (~64 floats) computed from the sample's spectral
  envelope.
- ``get_voice_condition``: the single entry point a TTS engine asks for the
  current clone state.
- Safe by design: every failure falls back to the normal machine voice, and
  voice cloning never breaks the app.

Config (app_settings.json, "voice_clone" group)
-----------------------------------------------
- enabled
- profile_path (default %LOCALAPPDATA%/StellaAI/user_profile.wav)
- sample_seconds (default 5)
- turndown_threshold (default 0.55)
"""

from __future__ import annotations

import json
import math
import wave
import array
from pathlib import Path

from .user_paths import get_user_data_dir

DEFAULT_PROFILE_NAME = "user_profile.wav"
DEFAULT_SAMPLE_SECONDS = 5
DEFAULT_TURNDOWN_THRESHOLD = 0.55

_SETTING_GROUP = "voice_clone"


def _user_profile_path() -> Path:
    """Where the user's voice sample is stored on disk."""
    return get_user_data_dir() / DEFAULT_PROFILE_NAME


def _settings() -> dict:
    try:
        from memory import config_manager
        return config_manager.load_settings()
    except Exception:
        return {}


def _save_settings(settings: dict) -> None:
    """Merge new voice_clone options into the stored config."""
    try:
        from memory import config_manager
        cfg = _settings()
        cfg.update(settings)
        config_manager.set_setting(_SETTING_GROUP, cfg)
    except Exception:
        pass


def record_voice_sample(path: str | Path | None = None,
                        seconds: float | None = None) -> str:
    """Record a short sample of the user's voice into a WAV file.

    Uses the device's default microphone, 48 kHz, mono, 16-bit. Returns the
    path recorded. Raises RuntimeError if no microphone is available.
    """
    import sounddevice as sd

    p = Path(path) if path else _user_profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    if seconds is None:
        seconds = float(_settings().get("sample_seconds", DEFAULT_SAMPLE_SECONDS))

    sr = 48000
    print(f"[voice_clone] Record {seconds}s of your voice -> {p} ...")
    try:
        data = sd.rec(int(seconds * sr), samplerate=sr, channels=1,
                      dtype="float32", blocking=True)
        sd.wait()
    except Exception as e:
        raise RuntimeError(f"Microphone unavailable for recording: {e}")

    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((data * 32767).clip(-32768, 32767)
                        .astype("int16").tobytes())
    return str(p)
