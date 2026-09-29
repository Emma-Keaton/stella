"""
Clipboard Sentry for Brahma AI.
Monitors the Windows clipboard for actionable technical content:
- Tracebacks / Exceptions
- JSON structures
- URLs or SQL queries
- Code snippets
Notifies Brahma so it can offer quick contextual assistance.
"""

import time
import threading
import json
import re
from typing import Optional, Callable


def classify_clipboard_content(text: str) -> Optional[str]:
    """Classify technical content in clipboard text."""
    if not text:
        return None
    text = text.strip()
    if len(text) < 15:
        return None

    # Check for python / node / java traceback
    if "Traceback (most recent call last):" in text or ("Exception:" in text and "\n" in text) or ("Error:" in text and "\n" in text):
        return "error_traceback"

    # Check for JSON
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            json.loads(text)
            return "json_data"
        except Exception:
            pass

    # Check for SQL queries
    if re.search(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+", text, re.IGNORECASE):
        return "sql_query"

    # Check for code blocks
    if any(keyword in text for keyword in ["def ", "class ", "function ", "import ", "const ", "let ", "var "]) and "\n" in text:
        return "code_snippet"

    return None


class ClipboardSentry:
    def __init__(self, callback: Optional[Callable[[str, str], None]] = None):
        self._callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_clip = ""
        self._qt_connected = False

    def start(self):
        if self._running:
            return
        self._running = True

        # Check if Qt application is available on current thread or main thread
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None and threading.current_thread() is threading.main_thread():
                app.clipboard().dataChanged.connect(self._on_qt_clipboard_changed)
                self._qt_connected = True
                return
        except Exception:
            pass

        # Otherwise, spawn worker thread with COM safety
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ClipboardSentry")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._qt_connected:
            try:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app is not None:
                    app.clipboard().dataChanged.disconnect(self._on_qt_clipboard_changed)
            except Exception:
                pass
            self._qt_connected = False

    def _on_qt_clipboard_changed(self):
        if not self._running:
            return
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                return
            clip = app.clipboard()
            text = (clip.text() or "").strip()
            if text and text != self._last_clip:
                self._last_clip = text
                category = classify_clipboard_content(text)
                if category and self._callback:
                    self._callback(category, text)
        except Exception:
            pass

    def _classify_content(self, text: str) -> Optional[str]:
        return classify_clipboard_content(text)

    def _monitor_loop(self):
        # Initialize COM on this thread if Windows to prevent access violations
        try:
            import ctypes
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass

        try:
            import pyperclip
            try:
                self._last_clip = (pyperclip.paste() or "").strip()
            except Exception:
                self._last_clip = ""

            while self._running:
                time.sleep(2.0)
                try:
                    current = (pyperclip.paste() or "").strip()
                    if current and current != self._last_clip:
                        self._last_clip = current
                        category = classify_clipboard_content(current)
                        if category and self._callback:
                            self._callback(category, current)
                except Exception:
                    pass
        finally:
            try:
                import ctypes
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass
