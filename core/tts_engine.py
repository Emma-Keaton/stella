"""
core/tts_engine.py — Stella backend TTS engine.

Provides always-on text-to-speech for Stella using two wire protocols:

1. **Stella voice (primary)** — US English female voice built on Kokoro-82M.
   Runs locally via the kokoro Python package. Downloaded on first launch
   from HuggingFace and kept resident for the lifetime of the backend.
2. **Kokoro (secondary)** — Kokoro-82M default female voices
   (af_bella, af_sarah, alicia, etc.) as fallback.

Every failure falls back to edge-tts (Microsoft Edge online TTS) so Stella
never loses her voice.

Config (app_settings.json, "tts" group):
- provider: "kokoro" | "edge" | "auto"  (default "auto")
- voice_id: kokoro voice id (default "af_bella" = Stella voice)
- auto_download: bool (default True)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .user_paths import get_user_data_dir

# ── Where models and voices live on disk ──────────────────────────────────
MODELS_DIR = get_user_data_dir() / "tts_models"
KOKORO_MODEL_PATH = MODELS_DIR / "kokoro-v0_19.onnx"
VOICES_DIR = MODELS_DIR / "voices"
STELLA_VOICE_PATH = VOICES_DIR / "dala.pt"

# HuggingFace sources
KOKORO_MODEL_URL = (
    "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/kokoro-v0_19.onnx"
)
KOKORO_VOICES_URL = (
    "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices/{voice}.pt"
)

# Known Kokoro female voices (sorted, user-friendly)
KOKORO_FEMALE_VOICES = [
    ("af_bella", "Bella", "Warm, clear US English female"),
    ("af_sarah", "Sarah", "Professional US English female"),
    ("af_sky", "Sky", "Bright, youthful US English female"),
    ("af_aoede", "Aoede", "Expressive US English female"),
    ("af_nicole", "Nicole", "Soft, gentle US English female"),
    ("af_nova", "Nova", "Energetic US English female"),
    ("af_alloy", "Alloy", "Balanced US English female"),
    ("af_heart", "Heart", "Empathetic US English female"),
    ("alicia", "Alicia", "Classic US English female"),
    ("laura", "Laura", "Warm US English female"),
]

# TinyTTS voices - Stella is female only
TINYTTS_VOICES = [
    ("tiny_female", "Tiny Female", "TinyTTS 1.6M female voice, CPU edge"),
]

# Kyutai Pocket TTS top voices - female only
POCKET_VOICES = [
    ("pocket_alba_casual", "Alba Casual", "Kyutai Pocket TTS 1.9M casual female"),
    ("pocket_alba_clarity", "Alba Clarity", "Kyutai Pocket TTS 1.9M clear female"),
]

# Default voice: Stella voice (mapped to af_bella, the Kokoro female)
DEFAULT_VOICE_ID = "af_bella"
STELLA_VOICE_ID = "af_bella"

_LOCK = threading.Lock()
_ENGINE: Optional["TTSEngine"] = None


class TTSEngine:
    def __init__(self, provider: str = "auto", voice_id: str = DEFAULT_VOICE_ID):
        self.provider = provider
        self.voice_id = voice_id
        self._kokoro = None
        self._edge_tts = None
        self._tiny = None
        self._pocket = None
        self._initialized = False
        self._init_error: Optional[str] = None

    def _init(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        if self.provider in ("auto", "kokoro"):
            if _ensure_kokoro() and _ensure_models():
                try:
                    from kokoro import KPipeline
                    self._kokoro = KPipeline(lang_code="a")
                    print(f"[tts_engine] Kokoro-82M loaded (voice: {self.voice_id})")
                except Exception as exc:
                    self._init_error = str(exc)
                    print(f"[tts_engine] Kokoro init failed: {exc}")
                    self._kokoro = None
        if self.provider in ("auto", "edge"):
            try:
                import edge_tts  # noqa: F401
                self._edge_tts = True
                print("[tts_engine] edge-tts fallback available.")
            except ImportError:
                self._edge_tts = None
                print("[tts_engine] edge-tts not installed.")
        if self.provider in ("auto", "tiny"):
            if _ensure_tiny():
                try:
                    from tiny_tts import TinyTTS
                    self._tiny = TinyTTS()
                    print("[tts_engine] TinyTTS loaded")
                except Exception as exc:
                    print(f"[tts_engine] TinyTTS init failed: {exc}")
                    self._tiny = None
        if self.provider in ("auto", "pocket"):
            if _ensure_pocket():
                try:
                    from pocket_tts import TTSModel
                    self._pocket = TTSModel.load_model("kyutai/pocket-tts")
                    print("[tts_engine] Kyutai Pocket TTS loaded")
                except Exception as exc:
                    print(f"[tts_engine] Pocket TTS init failed: {exc}")
                    self._pocket = None

    def list_voices(self) -> list[dict[str, str]]:
        """Return the full list of selectable voices."""
        self._init()
        voices = []
        for vid, label, desc in KOKORO_FEMALE_VOICES:
            voices.append(
                {
                    "id": vid,
                    "name": label,
                    "provider": "kokoro",
                    "gender": "female",
                    "language": "en-US",
                    "description": desc,
                    "active": vid == self.voice_id,
                }
            )
        for vid, label, desc in TINYTTS_VOICES:
            voices.append(
                {
                    "id": vid,
                    "name": label,
                    "provider": "tiny",
                    "gender": "female" if "female" in vid else "male",
                    "language": "en-US",
                    "description": desc,
                    "active": vid == self.voice_id,
                }
            )
        for vid, label, desc in POCKET_VOICES:
            voices.append(
                {
                    "id": vid,
                    "name": label,
                    "provider": "pocket",
                    "gender": "female",
                    "language": "en-US",
                    "description": desc,
                    "active": vid == self.voice_id,
                }
            )
        if self._edge_tts:
            voices.append(
                {
                    "id": "edge-female",
                    "name": "Edge Female (Fallback)",
                    "provider": "edge",
                    "gender": "female",
                    "language": "en-US",
                    "description": "Microsoft Edge online TTS female voice",
                    "active": self.voice_id == "edge-female",
                }
            )
        return voices

    def set_voice(self, voice_id: str) -> bool:
        """Set the active TTS voice. Returns True if the voice is known."""
        known = {v[0] for v in KOKORO_FEMALE_VOICES} | {v[0] for v in TINYTTS_VOICES} | {v[0] for v in POCKET_VOICES} | {"edge-female"}
        if voice_id not in known:
            return False
        self.voice_id = voice_id
        if voice_id != "edge-female" and self._kokoro is None:
            self._initialized = False
            self._init()
        return True

    def speak(self, text: str, voice_id: Optional[str] = None) -> Optional[Path]:
        """
        Synthesize *text* to speech and return a Path to a WAV file.

        Returns None if synthesis fails completely.
        """
        self._init()
        voice = voice_id or self.voice_id
        text = (text or "").strip()
        if not text:
            return None

        # ── Primary: kokoro (Stella voice / Kokoro voices) ─────────────
        if self._kokoro is not None and voice != "edge-female":
            try:
                out_path = Path(tempfile.gettempdir()) / f"stella_tts_{int(time.time()*1000)}.wav"
                generator = self._kokoro(text, voice=voice)
                import numpy as np
                import soundfile as sf

                audio_segments = []
                for _, _, audio in generator:
                    audio_segments.append(audio)
                if audio_segments:
                    full_audio = np.concatenate(audio_segments)
                    sf.write(str(out_path), full_audio, 24000)
                    print(f"[tts_engine] Kokoro synthesized -> {out_path}")
                    return out_path
            except Exception as exc:
                print(f"[tts_engine] Kokoro speak failed: {exc}")

        # ── Fallback: edge-tts ─────────────────────────────────────────
        if self._edge_tts:
            try:
                import edge_tts
                import asyncio

                out_path = Path(tempfile.gettempdir()) / f"stella_tts_{int(time.time()*1000)}.mp3"

                async def _synth():
                    communicate = edge_tts.Communicate(
                        text, voice="en-US-AriaNeural"
                    )
                    await communicate.save(str(out_path))

                asyncio.run(_synth())
                print(f"[tts_engine] edge-tts synthesized -> {out_path}")
                return out_path
            except Exception as exc:
                print(f"[tts_engine] edge-tts speak failed: {exc}")

        # ── Last resort: system say / espeak ───────────────────────────
        try:
            out_path = Path(tempfile.gettempdir()) / f"stella_tts_{int(time.time()*1000)}.wav"
            if sys.platform == "win32":
                ps_cmd = (
                    f'Add-Type -AssemblyName System.Speech; '
                    f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                    f'$s.SetOutputToWaveFile("{out_path}"); '
                    f'$s.Speak("{text}"); $s.Dispose()'
                )
                subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    ["espeak", "-w", str(out_path), text],
                    check=True,
                    capture_output=True,
                )
            if out_path.exists():
                return out_path
        except Exception:
            pass

        print("[tts_engine] All TTS backends failed.")
        return None


def get_engine() -> TTSEngine:
    """Return the singleton TTS engine."""
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            _settings = _load_settings()
            _ENGINE = TTSEngine(
                provider=_settings.get("provider", "auto"),
                voice_id=_settings.get("voice_id", DEFAULT_VOICE_ID),
            )
        return _ENGINE


def _load_settings() -> dict[str, Any]:
    try:
        from memory import config_manager
        return config_manager.load_settings().get("tts", {})
    except Exception:
        return {}


def _save_settings(settings: dict[str, Any]) -> None:
    try:
        from memory import config_manager
        cfg = config_manager.load_settings()
        cfg["tts"] = settings
        config_manager.set_setting("tts", settings)
    except Exception:
        pass


# Backwards-compatible module-level helpers
def speak(text: str, voice_id: Optional[str] = None) -> Optional[Path]:
    return get_engine().speak(text, voice_id)


def list_voices() -> list[dict[str, str]]:
    return get_engine().list_voices()


def set_voice(voice_id: str) -> bool:
    return get_engine().set_voice(voice_id)

def _download(url: str, dest: Path) -> bool:
    """Download *url* to *dest*, returning True on success."""
    try:
        import urllib.request
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            return True
        print(f"[tts_engine] Downloading {url} -> {dest} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"[tts_engine] Download complete: {dest} ({dest.stat().st_size} bytes)")
        return True
    except Exception as exc:
        print(f"[tts_engine] Download failed ({url}): {exc}")
        return False

def _ensure_kokoro() -> bool:
    """Make sure kokoro-tts is importable. Install if missing."""
    try:
        import kokoro  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        print("[tts_engine] Installing kokoro-tts ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "kokoro", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
        )
        import kokoro  # noqa: F401
        print("[tts_engine] kokoro-tts installed.")
        return True
    except Exception as exc:
        print(f"[tts_engine] Could not install kokoro-tts: {exc}")
        return False

def _ensure_models() -> bool:
    """Download Kokoro-82M model and Stella voice if missing."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    if not KOKORO_MODEL_PATH.exists():
        ok = _download(KOKORO_MODEL_URL, KOKORO_MODEL_PATH) and ok
    if not STELLA_VOICE_PATH.exists():
        ok = _download(KOKORO_VOICES_URL.format(voice="af_bella"), STELLA_VOICE_PATH) and ok
    return ok
