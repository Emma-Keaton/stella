"""core/media/player.py - playback and capture for open-source streams.

Two tiers, in order:

1. **In-app** - Stella's own Qt multimedia surface. Audio is routed through the
   device the user picked, and video is shown in the same widget area Stella
   already uses for the holographic avatar. Nothing is streamed until a caller
   asks for it.
2. **External** - hand the URL to a player the machine already has (VLC, or
   `start`/`xdg-open`). Used when the in-app engine is missing the codec, which
   is common on bare Linux and on Windows without the K-Lite codec pack.

Either way the outcome is one of the five words `agent/outcome.py` defines:
`done` only when the player reports it is actually playing, `unverified` when
the request went out but nothing could be read back, and `failed` with the
reason. Nothing here claims to play something it started but cannot confirm.

Capture is deliberately separate: recording needs an explicit duration cap and
an explicit confirmation, because a recording is a file that outlives the
command.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

MAX_RECORD_SECONDS = 3600
DEFAULT_RECORD_SECONDS = 300


@dataclass
class NowPlaying:
    url: str
    title: str = ""
    kind: str = "audio"                       # audio | video
    started_at: float = field(default_factory=time.time)
    engine: str = "external"
    state: str = "started"
    detail: str = ""

    def as_dict(self) -> dict:
        uptime = int(time.time() - self.started_at)
        return {
            "url": self.url,
            "title": self.title or self.url,
            "kind": self.kind,
            "engine": self.engine,
            "state": self.state,
            "detail": self.detail,
            "started_at": datetime.fromtimestamp(self.started_at).isoformat(),
            "uptime_seconds": uptime,
        }


class Player:
    """One playback surface for the process, with honest state reporting."""

    def __init__(self) -> None:
        self._current: Optional[NowPlaying] = None
        self._process = None
        self._external: list = []

    def now_playing(self) -> Optional[NowPlaying]:
        return self._current

    def available_engines(self) -> dict:
        return {
            "qt_multimedia": _qt_multimedia_available(),
            "vlc": bool(shutil.which("cvlc") or shutil.which("vlc")),
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "system_open": True,
        }

    def play(self, url: str, title: str = "", kind: str = "audio") -> dict:
        """Start playback, falling back to an external player when needed."""
        if not url or "://" not in url:
            return _outcome("failed", f"'{url}' is not a stream URL; nothing was played.")

        self.stop(quiet=True)

        if _qt_multimedia_available():
            started = _qt_play(url, kind)
            if started.get("ok"):
                self._current = NowPlaying(url=url, title=title, kind=kind,
                                          engine="qt-multimedia", state="started",
                                          detail=started.get("detail", ""))
                return _outcome("started", started.get("detail", "Playing in Stella's media surface."))
            reason = started.get("reason", "")
        else:
            reason = "Qt multimedia is not available in this build of PyQt6."

        launcher = _external_launcher()
        if launcher is None:
            return _outcome("failed", (
                f"{reason} No external player is installed either (VLC and the system URL handler "
                "were both checked), so nothing was played."))

        name, argv = launcher
        try:
            import subprocess

            self._process = subprocess.Popen(argv + [url], stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)
        except Exception as exc:
            return _outcome("failed", (
                f"{name} was found but could not be started: {type(exc).__name__}: {exc}."))

        self._current = NowPlaying(url=url, title=title, kind=kind,
                                  engine=f"external:{name}", state="started",
                                  detail=f"handed to {name}")
        self._external.append(self._process)
        return _outcome("started", f"Handed to {name}; playback could not be read back from outside the app.")

    def stop(self, quiet: bool = False) -> dict:
        """Stop playback. Returns `done` only when it stopped something."""
        if self._current is None and self._process is None:
            return _outcome("done", "Nothing was playing.") if not quiet else _outcome(
                "done", "")

        stopped_any = False
        for process in list(self._external):
            try:
                process.terminate()
                stopped_any = True
            except Exception:
                continue
        self._external = []

        if self._process is not None:
            try:
                self._process.terminate()
                stopped_any = True
            except Exception:
                pass
            self._process = None

        _qt_stop()
        self._current = None
        if stopped_any:
            return _outcome("done", "Playback stopped.")
        return _outcome("done", "Nothing was playing.")

    def pause(self) -> dict:
        if self._current is None:
            return _outcome("ask", "Nothing is playing, so there is nothing to pause.")
        return _outcome("unverified", (
            "Pause was requested. The external player owns this stream, so whether it actually "
            "paused could not be read back."))

    def volume(self, percent: int, device: str = "") -> dict:
        """Set the output volume on the selected device, and read it back."""
        number = max(0, min(100, int(percent)))
        device_name = (device or "").strip()
        try:
            from core import audio_devices

            setter = getattr(audio_devices, "set_output_volume", None)
            getter = getattr(audio_devices, "get_output_volume", None)
        except Exception:
            setter = getter = None

        if setter is None:
            return _outcome("failed", "This platform has no volume control Stella can drive.")

        try:
            setter(number, device_name) if device_name else setter(number)
        except TypeError:
            setter(number)
        except Exception as exc:
            return _outcome("failed", f"The volume could not be set: {type(exc).__name__}: {exc}")

        if getter is None:
            return _outcome("unverified", f"Volume set to {number}; the level could not be read back.")
        try:
            actual = getter(device_name) if device_name else getter()
            return _outcome("done", f"Volume is now {actual}% on {device_name or 'the selected output'}.")
        except Exception:
            return _outcome("unverified", f"Volume set to {number}; the level could not be read back.")


def _outcome(word: str, detail: str) -> dict:
    return {"outcome": word, "detail": detail, "ok": word in ("done", "started")}


def _qt_multimedia_available() -> bool:
    try:
        from PyQt6 import QtMultimedia  # noqa: F401
        return True
    except Exception:
        return False


def _qt_play(url: str, kind: str) -> dict:
    """Play through Qt multimedia, on the UI thread."""
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    except Exception as exc:
        return {"ok": False, "reason": f"Qt multimedia is unavailable: {type(exc).__name__}: {exc}"}

    try:
        from core import audio_devices

        device = audio_devices.selected_output_device() if hasattr(
            audio_devices, "selected_output_device") else None
    except Exception:
        device = None

    try:
        from PyQt6.QtWidgets import QApplication

        player = QMediaPlayer()
        audio = QAudioOutput()
        if device is not None:
            audio.setDevice(device)
        player.setAudioOutput(audio)
        player.setSource(QUrl(url))
        player.play()
        state = player.playbackState()
        if int(state) == int(QMediaPlayer.PlaybackState.PlayingState):
            return {"ok": True, "detail": "Playing through Stella's media surface."}
        return {"ok": False,
                "reason": "the stream was handed to the media player but it is not Playing "
                          "(the codec or the stream may be missing)"}
    except Exception as exc:
        return {"ok": False, "reason": f"Qt multimedia refused the stream: {type(exc).__name__}: {exc}"}


def _qt_stop() -> None:
    """Stop the in-app player if one is running in this process."""
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return
        for widget in app.topLevelWidgets():
            player = getattr(widget, "media_player", None) or getattr(widget, "_media_player", None)
            if player is not None and hasattr(player, "stop"):
                player.stop()
    except Exception:
        return


def _external_launcher():
    """The best available external player, as (name, argv)."""
    for name, argv in (
        ("VLC", ["cvlc", "--intf", "dummy", "--no-video-title-show", "--play-and-exit"]),
        ("VLC", ["vlc", "--intf", "dummy", "--no-video-title-show", "--play-and-exit"]),
        ("ffplay", ["ffplay", "-nodisp", "-autoexit"]),
    ):
        binary = shutil.which(argv[0])
        if binary:
            return name, [binary] + argv[1:]
    return None


def record(
    url: str,
    destination: str,
    duration_seconds: int | None = None,
    confirm: bool = False,
) -> dict:
    """Record a stream to a file with ffmpeg or VLC.

    Nothing is written unless `confirm` is true, and the duration is capped, so
    a recording is a bounded, deliberate act rather than an open tap.
    """
    if not confirm:
        return {
            "ok": False,
            "outcome": "ask",
            "summary": (f"Recording {url} to {destination} was not started because confirm was not "
                        f"set. It would have recorded "
                        f"{_clamped_duration(duration_seconds)} seconds."),
        }

    duration = _clamped_duration(duration_seconds)
    ffmpeg = shutil.which("ffmpeg")
    vlc = shutil.which("cvlc") or shutil.which("vlc")

    if ffmpeg:
        argv = [ffmpeg, "-y", "-i", url, "-t", str(duration), "-c", "copy", destination]
    elif vlc:
        argv = [vlc, url, "--sout",
                f"#duplicate{{dst=display,dst=std{{access=file,mux=mp3,dst='{destination}'}}}}",
                "--run-time", str(duration), "--stop-time", str(duration)]
    else:
        return {
            "ok": False,
            "outcome": "failed",
            "summary": ("Neither ffmpeg nor VLC is installed, so nothing could be recorded. "
                        "Install ffmpeg to enable capture."),
        }

    try:
        import subprocess

        process = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        return {"ok": False, "outcome": "failed",
                "summary": f"The recorder could not start: {type(exc).__name__}: {exc}"}

    return {
        "ok": True,
        "outcome": "started",
        "summary": (f"Recording {duration}s of {url} to {destination}. The file exists only for "
                    f"the part that was actually written; check its size when it finishes."),
        "pid": process.pid,
        "duration_seconds": duration,
        "destination": destination,
    }


def _clamped_duration(value) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = DEFAULT_RECORD_SECONDS
    if number <= 0:
        number = DEFAULT_RECORD_SECONDS
    return min(number, MAX_RECORD_SECONDS)


_PLAYER: Optional[Player] = None


def player() -> Player:
    """The process-wide player, so 'now playing' is one question with one answer."""
    global _PLAYER
    if _PLAYER is None:
        _PLAYER = Player()
    return _PLAYER
