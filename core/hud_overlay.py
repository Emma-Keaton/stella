"""core/hud_overlay.py — lightweight always-on-top desktop HUD orb.

A minimal, cross-platform (tkinter, stdlib) transparent-ish status orb that
sits on top of the desktop as Stella's presence layer — the lightweight
counterpart to a full 3D avatar. Shows connection/agent state and pulses on
events. Optional: start with start(); never blocks headless servers.
"""
from __future__ import annotations

import threading
from typing import Optional

_tk = None
try:
    import tkinter as _tk
except Exception:
    _tk = None


class HudOverlay:
    def __init__(self, title: str = "Stella"):
        self.title = title
        self._root = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._status = "idle"
        self._canvas = None
        self._label = None

    def available(self) -> bool:
        return _tk is not None

    def set_status(self, status: str) -> None:
        self._status = status
        if self._label is not None:
            try:
                self._label.config(text=f"{self.title}: {status}")
            except Exception:
                pass

    def start(self) -> bool:
        if self._running or _tk is None:
            return self._running
        self._running = True

        def _run():
            try:
                self._root = _tk.Tk()
                self._root.overrideredirect(True)
                self._root.attributes("-topmost", True)
                self._root.attributes("-alpha", 0.85)
                w, h = 180, 56
                x = self._root.winfo_screenwidth() - w - 24
                y = self._root.winfo_screenheight() - h - 60
                self._root.geometry(f"{w}x{h}+{x}+{y}")
                self._canvas = _tk.Canvas(self._root, width=w, height=h,
                                          bg="#0b0f1a", highlightthickness=0)
                self._canvas.pack()
                self._canvas.create_oval(10, 12, 40, 42, fill="#39d0ff", outline="")
                self._label = _tk.Label(self._root, text=f"{self.title}: {self._status}",
                                        bg="#0b0f1a", fg="#e6f6ff", font=("Segoe UI", 10))
                self._label.place(x=48, y=18)
                self._root.mainloop()
            except Exception:
                pass
            finally:
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True, name="stella-hud")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        try:
            if self._root is not None:
                self._root.quit()
                self._root.destroy()
        except Exception:
            pass


hud = HudOverlay()
