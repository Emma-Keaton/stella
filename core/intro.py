"""core/intro.py — Stella's startup self-introduction + onboarding.

On first launch Stella introduces herself and asks the user for two things
she then reuses forever: their **name** (to address them personally) and
their **voice** (which Piper TTS voice she speaks with). Both persist so the
flow runs once; later launches greet by name without re-asking.

UI-agnostic: it produces the lines to speak/print and does the persistence.
The caller (desktop Qt `runner()`, or the Android launch) decides how to
render them. Speaking routes through `actions.attention_monitor.speak_native`
(Piper TTS, offline-capable). Everything is defensive — a missing mic, voice
model, or TTS backend must never crash startup.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable, Optional

from core.identity import identity
from core.user_paths import get_user_data_dir


def _voice_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / ".venv" / "piper" / "voices"


def available_voices() -> list[str]:
    """Sorted list of installed Piper voice names (e.g. 'en_US-amy-medium')."""
    try:
        d = _voice_dir()
        if not d.exists():
            return []
        names = set()
        for p in d.iterdir():
            if p.suffix == ".onnx":
                names.add(p.stem)
        return sorted(names)
    except Exception:
        return []


def _settings_path() -> Path:
    return get_user_data_dir() / "config" / "app_settings.json"


def get_selected_voice() -> str:
    """The voice Stella currently speaks with (persisted, or a sane default)."""
    default = "en_US-lessac-medium"
    try:
        sp = _settings_path()
        if sp.exists():
            with open(sp, "r", encoding="utf-8-sig") as f:
                v = json.load(f).get("tts_voice")
                if v:
                    return v
    except Exception:
        pass
    voices = available_voices()
    if default in voices:
        return default
    return voices[0] if voices else default


def save_voice(voice: str) -> None:
    try:
        sp = _settings_path()
        sp.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if sp.exists():
            try:
                with open(sp, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["tts_voice"] = voice
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as exc:  # pragma: no cover
        print(f"[intro] save_voice failed: {exc}")


def owner_name() -> str:
    try:
        return (identity.get_owner_name() or "").strip()
    except Exception:
        return ""


def is_first_run() -> bool:
    """True when the user has never given their name."""
    return not owner_name()


def save_name(name: str) -> None:
    name = (name or "").strip()
    if not name:
        return
    try:
        identity.set_owner_name(name)
    except Exception as exc:  # pragma: no cover
        print(f"[intro] save_name failed: {exc}")


def preferred_name() -> str:
    """What Stella calls the user: their name, or a warm fallback."""
    n = owner_name()
    return n if n else "there"


def build_greeting(name: Optional[str] = None) -> str:
    """The self-introduction Stella speaks/shows on launch."""
    if name:
        return (
            f"Hey {name}, I'm Stella — your personal assistant, running right "
            f"here on this device. Good to see you again."
        )
    return (
        "Hey, I'm Stella — your personal assistant, running right here on "
        "this device. I'm offline-capable, so I keep working even without the "
        "internet."
    )


def build_intro_questions() -> str:
    """The onboarding ask shown only on first run."""
    voices = available_voices()
    voice_line = (
        "Pick a voice you'd like me to use: " + ", ".join(voices) + "."
        if voices else
        "I'll use my default voice for now — you can change it in Settings."
    )
    return (
        "Before we start, two quick things so I can make this yours:\n"
        "1. What should I call you?\n"
        f"2. {voice_line}"
    )


def speak(text: str, *, voice: Optional[str] = None, blocking: bool = False) -> None:
    """Speak `text` via Piper TTS. Never raises; never blocks the UI thread
    unless `blocking=True`."""
    text = (text or "").strip()
    if not text:
        return

    def _do():
        try:
            from actions import attention_monitor as am
            am.speak_native(text)
        except Exception as exc:  # pragma: no cover
            print(f"[intro] speak failed: {exc}")

    if blocking:
        _do()
    else:
        threading.Thread(target=_do, daemon=True).start()


def run_startup_intro(
    on_greeting: Optional[Callable[[str], None]] = None,
    on_questions: Optional[Callable[[str], None]] = None,
    speak_enabled: bool = True,
) -> dict:
    """Run the launch intro. Returns a small state dict the UI can read."""
    name = owner_name()
    greeting = build_greeting(name or None)
    result = {"first_run": is_first_run(), "greeting": greeting, "questions": ""}

    if on_greeting:
        try:
            on_greeting(greeting)
        except Exception:
            pass
    if speak_enabled:
        speak(greeting)

    if is_first_run():
        questions = build_intro_questions()
        result["questions"] = questions
        if on_questions:
            try:
                on_questions(questions)
            except Exception:
                pass

    return result


def complete_intro(name: str, voice: Optional[str] = None) -> str:
    """Persist the user's answers and return the personalised thank-you line."""
    save_name(name)
    if voice:
        save_voice(voice)
    thanks = f"Great — I'll call you {preferred_name()} from now on. Let's get started."
    speak(thanks)
    return thanks

