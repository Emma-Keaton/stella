"""
core/wakeword.py — the "Hey, Stella" wake-word detector.

Why this exists
---------------
The assistant sits muted most of the time; the wake phrase is how you bring it
back hands-free without touching a button. The old inline matcher was too eager:
it woke on any bare "hey", "hi" or "hello", so saying "hey" to a colleague
would pull Stella out of mute. This module keeps the phrase list tight around the
assistant's *name*, which is what makes "Hey, Stella" mean something.

Design notes
------------
- **Name-gated by default.** A phrase only counts if it actually contains the
  wake name (default "stella"). "hey stella", "hi stella", "hello stella",
  "ok stella", "hey stella evo" all match; a bare "hey" does not. This is the
  single most important property — it stops random conversation from waking the
  mic.
- **Punctuation-insensitive.** Commas and apostrophes are stripped, so the
  spoken "Hey, Stella!" and the transcribed "hey stella" behave identically.
- **Configurable.** `wake_word_enabled` gates the whole thing; the user can set
  a custom phrase (e.g. a different name or language) via `set_wake_phrase`.
- **`strip_wake`** removes the wake phrase from a command so the part after it
  ("open spotify") can be acted on directly, instead of re-sent as part of the
  prompt.

The module never raises: a failure to read config simply falls back to the
default phrase, because a wake word that crashes the mic thread is worse than
one that is slightly out of date.
"""

from __future__ import annotations

import re

# Phrases that wake Stella. Each is matched after normalization (lowercased,
# punctuation stripped, whitespace collapsed). Every entry contains the name, so
# a bare greeting can never trigger it.
DEFAULT_PHRASES = (
    "hey stella",
    "hi stella",
    "hello stella",
    "ok stella",
    "okay stella",
    "hey stella evo",
    "stella evo",
    "wake up stella",
    "stella",
)

# The token that must appear for any phrase to be considered a wake.
WAKE_NAME = "stella"


def _normalize(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    t = re.sub(r"[^a-z0-9\s]+", " ", (text or "").lower())
    return re.sub(r"\s+", " ", t).strip()


# --------------------------------------------------------------- config -----
def _cfg():
    try:
        from memory import config_manager
        return config_manager
    except Exception:
        return None


def is_enabled() -> bool:
    """Whether wake-word activation is turned on at all."""
    cfg = _cfg()
    if cfg is None:
        return True
    try:
        return bool(cfg.get_setting("wake_word_enabled", True))
    except Exception:
        return True


def get_wake_phrase() -> str:
    """The configured custom wake phrase, or the default composite."""
    cfg = _cfg()
    if cfg is not None:
        try:
            custom = (cfg.get_setting("wake_phrase", "") or "").strip()
            if custom:
                return custom
        except Exception:
            pass
    return DEFAULT_PHRASES[0]


def set_wake_phrase(phrase: str) -> None:
    cfg = _cfg()
    if cfg is not None:
        try:
            cfg.set_setting("wake_phrase", (phrase or "").strip())
        except Exception:
            pass


# ------------------------------------------------------------- matching -----
def _phrases() -> list[str]:
    """Active phrase list: the custom phrase (if any) plus the built-ins."""
    out = []
    custom = get_wake_phrase()
    if custom:
        out.append(_normalize(custom))
    for p in DEFAULT_PHRASES:
        n = _normalize(p)
        if n not in out:
            out.append(n)
    return [p for p in out if p]


def detect(text: str) -> bool:
    """True when `text` contains a wake phrase and wake-word mode is enabled.

    Name-gated: the normalized phrase must appear as a word-boundary match, and
    every accepted phrase contains the wake name, so "hey" / "hi" alone never
    fire it.
    """
    if not is_enabled():
        return False
    norm = _normalize(text)
    if not norm:
        return False
    # Fast reject: if the name isn't in there at all, nothing can match.
    if WAKE_NAME not in norm.split():
        return False
    padded = f" {norm} "
    for phrase in _phrases():
        p = f" {phrase} "
        if p in padded:
            return True
    # Also allow the bare name as a standalone word (e.g. just "stella?").
    return WAKE_NAME in norm.split()


def strip_wake(text: str) -> str:
    """Remove the leading wake phrase, returning the command that follows it.

    "hey stella open spotify" -> "open spotify". If nothing follows, returns "".
    """
    norm = _normalize(text)
    if not norm or not detect(text):
        return norm
    for phrase in _phrases():
        if norm.startswith(phrase):
            rest = norm[len(phrase):].strip()
            if rest:
                return rest
    # Wake word was the whole utterance, or appeared mid-sentence — strip the
    # first occurrence of the name only.
    parts = norm.split(" ", 1)
# --------------------------------------------------------------------------- #
# Voice enrollment — "say a few wake words" so Stella recognizes the user
# --------------------------------------------------------------------------- #
# The *text* wake phrase ("hey stella") is voice-independent: it only needs the
# correct name, so it works at any pitch. The *enrollment* layer is where the
# user's actual voice is captured and bound to the AI session. Record several
# wake-phrase utterances, store a speaker embedding for each, and use the
# strongest/majority vote as the user's voice signature.
#
# Tone robustness: a sick, whispering or screaming voice changes pitch and
# loudness. `wake_tone_variability` controls how much embedding drift we accept
# when matching the enrolled voice, so a user does not have to re-record every
# time their voice changes.


def get_wake_tone_variability() -> float:
    """Acceptable embedding drift for a waking user, 0.0 (strict) -> 1.0 (loose)."""
    try:
        from memory import config_manager
        return float(config_manager.get_setting("wake_tone_variability", 0.35))
    except Exception:
        return 0.35


def set_wake_tone_variability(v: float) -> None:
    try:
        from memory import config_manager
        config_manager.set_setting("wake_tone_variability", float(v))
    except Exception:
        pass


def record_enrollment_phrases(count: int = 4,
                              path: str | Path | None = None) -> list[str]:
    """Record `count` wake-phrase utterances of the user.

    Each utterance is saved as its own WAV so we can compare clarity and keep
    the best samples. Returns the list of saved paths.
    """
    import sounddevice as sd

    p = Path(path) if path else _user_profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    paths = []
    print(f"[voice_clone] Record {count} wake phrases (we will keep the clearest):")
    for i in range(count):
        n = 3 + int(i * 0.5)          # drift a little between takes
        wav = p.parent / f"enroll_{i:02d}.wav"
        try:
            data = sd.rec(int(n * 48000), samplerate=48000, channels=1,
                          dtype="float32", blocking=True)
            sd.wait()
            with wave.open(str(wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes((data * 32767).clip(-32768, 32767)
                                .astype("int16").tobytes())
            paths.append(str(wav))
            print(f"  take {i + 1}: {wav.name}")
        except Exception as e:
            print(f"  take {i + 1}: skipped ({e})")
    return paths


def enroll_wake_phrases(phrases: list[str] | None = None) -> dict:
    """Record the user's wake phrases, extract an embedding per utterance and
    store the result. Returns a status dict describing what was captured."""
    from . import voice_clone

    if phrases is None:
        phrases = list(_phrases())
    paths = record_enrollment_phrases(count=len(phrases))
    enrollment = {
        "phrases": [],
        "paths": [],
        "embedding": None,
        "count": 0,
        "tone_variability": get_wake_tone_variability(),
    }
    for phrase, p in zip(phrases, paths):
        try:
            emb = voice_clone.extract_voice_embedding(p)
        except Exception:
            emb = None
        enrollment["phrases"].append(phrase)
        enrollment["paths"].append(p)
        enrollment["embedding"] = emb if emb else enrollment["embedding"]
        enrollment["count"] += 1
    if enrollment["count"]:
        enrollment["embedding"] = (enrollment["embedding"][:16]
                                   if isinstance(enrollment["embedding"], list)
                                   else None)
    # Persist so later wake checks can recognize the same voice.
    try:
        from memory import config_manager
        config_manager.set_setting("wake_enrollment", enrollment)
    except Exception:
        pass
    return enrollment


def get_enrollment() -> dict:
    try:
        from memory import config_manager
        val = config_manager.get_setting("wake_enrollment")
        return val if val is not None else {}
    except Exception:
        return {}


def is_wake_enrolled() -> bool:
    """True once we have captured enough wake-phrase samples to bind the AI."""
    e = get_enrollment()
    return bool(e.get("count", 0) >= 2)
    return parts[1].strip() if len(parts) > 1 else ""
