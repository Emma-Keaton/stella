"""Stella voice gate — mic live when voice-activated AND user NOT typing.

Policy (user requirement): voice input stays active while voice-activated,
unless the user starts typing. Typing pauses mic capture; clearing the input
(and a short idle window) resumes it.

Thread-safe; safe to call from Qt slots and audio callbacks.
"""
from __future__ import annotations

import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal

_lock = threading.Lock()
_typing: bool = False
_last_type_ts: float = 0.0
_voice_activated: bool = True
IDLE_RESUME_SEC = 2.0


class VoiceGateSignals(QObject):
    """Signals emitted when voice state changes so the UI can react."""
    voice_activated_changed = pyqtSignal(bool)   # True = voice on, False = off
    mic_allowed_changed = pyqtSignal(bool)       # True = mic can capture, False = muted
    audio_level = pyqtSignal(float)              # 0.0 .. 1.0 audio level


_voice_signals = VoiceGateSignals()


def voice_signals() -> VoiceGateSignals:
    return _voice_signals


def set_voice_activated(on: bool) -> None:
    global _voice_activated
    with _lock:
        new_val = bool(on)
        if new_val == _voice_activated:
            return
        _voice_activated = new_val
    _voice_signals.voice_activated_changed.emit(new_val)
    _voice_signals.mic_allowed_changed.emit(mic_allowed())


def is_voice_activated() -> bool:
    with _lock:
        return _voice_activated


def set_typing(active: bool) -> None:
    """Called from UI whenever chat-input text presence changes."""
    global _typing, _last_type_ts
    with _lock:
        new_val = bool(active)
        if new_val == _typing and not new_val:
            return
        _typing = new_val
        if active:
            _last_type_ts = time.time()
    _voice_signals.mic_allowed_changed.emit(mic_allowed())


def is_typing() -> bool:
    with _lock:
        return _typing


def mic_allowed() -> bool:
    """True only when voice is on AND user is not actively typing.

    If text was cleared, allow a short idle window before resuming so a
    just-sent message doesn't instantly re-trigger the mic.
    """
    with _lock:
        if not _voice_activated or _typing:
            return False
        if _last_type_ts and (time.time() - _last_type_ts) < IDLE_RESUME_SEC:
            return False
        return True


def set_audio_level(level: float) -> None:
    """Emit audio level (0.0 .. 1.0) for waveform visualization."""
    _voice_signals.audio_level.emit(max(0.0, min(1.0, level)))
