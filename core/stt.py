"""core/stt.py — one speech-to-text entry point that degrades honestly.

Two tiers, chosen by what's actually available at runtime (never assumed):

  1. **Cloud** — Google STT via `speech_recognition`, used when the package is
     installed AND the internet is reachable. Best accuracy, open-ended.
  2. **Offline** — a wake-word / fixed-command matcher over energy-gated mic
     audio. No acoustic model required, so it works with zero pip deps. It
     recognises the wake phrase and a small set of known commands; anything
     else it reports as "unclear" so the UI can ask the user to type.

The mic capture, energy gating, and wake-word policy stay where they are
(`main.py` + `core/voice_gate.py` + `core/wakeword.py`). This module only turns
captured audio (or an already-transcribed hint) into text. Every path is
defensive: STT must never take Stella down — a failure just means "type
instead", which the UI surfaces.
"""

from __future__ import annotations

import re
from typing import Optional


def internet_available(timeout: float = 2.0) -> bool:
    """Cheap connectivity probe. False offline; never raises."""
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False


def _have_speech_recognition() -> bool:
    try:
        import speech_recognition  # noqa: F401
        return True
    except Exception:
        return False


def cloud_stt(pcm_bytes: bytes, sample_rate: int = 16000, sample_width: int = 2) -> Optional[str]:
    """Transcribe via Google STT. Returns text, or None on any failure."""
    if not _have_speech_recognition():
        return None
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        audio = sr.AudioData(pcm_bytes, sample_rate, sample_width)
        return r.recognize_google(audio)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Offline fallback: wake-word + a small fixed command vocabulary.
# --------------------------------------------------------------------------
def _norm(text: str) -> str:
    t = re.sub(r"[^a-z0-9\s]+", " ", (text or "").lower())
    return " ".join(t.split())


# Minimal offline command set. Keys are normalised phrases; values are the
# intents the agent already understands. Extend as needed — this is the only
# thing that works with no acoustic model and no network.
_OFFLINE_COMMANDS = {
    "hello": "hello",
    "hi stella": "hello",
    "hey stella": "hello",
    "what can you do": "capabilities",
    "help": "capabilities",
    "stop": "stop",
    "cancel": "stop",
    "go to sleep": "stop",
}


def match_offline_command(hint_text: str) -> Optional[str]:
    """Given any partial/hint text, return a matched offline intent or None.

    Used when there is no STT: the wake detector gives us a hint that *something*
    was said; this checks whether it maps to a known command so Stella can at
    least respond to a fixed set offline.
    """
    t = _norm(hint_text)
    if not t:
        return None
    for phrase, intent in _OFFLINE_COMMANDS.items():
        if phrase in t:
            return intent
    return None


def transcribe(pcm_bytes: Optional[bytes], *, hint_text: str = "",
               sample_rate: int = 16000, sample_width: int = 2,
               allow_cloud: bool = True) -> dict:
    """Unified entry point. Returns a dict describing the outcome:

        {"text": str|None, "engine": "cloud"|"offline"|"none", "intent": str|None}

    - Tries cloud STT first (when installed + online).
    - Falls back to the offline command matcher using `hint_text`.
    - Never raises.
    """
    # 1. Cloud, when possible.
    if allow_cloud and pcm_bytes and _have_speech_recognition() and internet_available():
        text = cloud_stt(pcm_bytes, sample_rate, sample_width)
        if text:
            return {"text": text, "engine": "cloud", "intent": None}

    # 2. Offline: best-effort fixed-command match from whatever hint we have.
    intent = match_offline_command(hint_text)
    if intent:
        return {"text": hint_text or intent, "engine": "offline", "intent": intent}

    # 3. Nothing we can do without a model — be honest.
    return {"text": None, "engine": "none", "intent": None}


def offline_notice() -> str:
    """User-facing message when voice input can't be transcribed offline."""
    return ("I can hear you, but offline speech-to-text needs a local model "
            "that isn't installed yet. Type your message and I'll answer right "
            "away — or connect to the internet and I'll listen normally.")
