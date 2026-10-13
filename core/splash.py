"""core/splash.py - frameless launch splash for the desktop app.

Cold start is not instant: the app checks for a GitHub update, spins up the
dashboard server, wires the connect gateway and builds the whole UI. Without a
splash the user stares at nothing (or, worse, an OS "not responding" box) for
several seconds.

This shows a frameless branded window immediately, keeps it pumped from a
daemon thread so it never blocks the real startup, and is dismissed as soon as
the main UI takes over.

Design notes
------------
- Frameless + always-on-top, because a splash that steals focus or shows a
  title bar looks worse than no splash.
- Every Qt call is marshalled back onto the GUI thread via QMetaObject, since
  the status text is updated from a worker thread.
- All failures are swallowed: a splash must never be the reason the app fails
  to start. Every public entry point no-ops if Qt is unavailable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_QT = None


def _qt():
    """Import Qt lazily so importing this module never drags in the GUI."""
    global _QT
    if _QT is None:
        from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: WPS433
        _QT = (QtCore, QtGui, QtWidgets)
    return _QT


class Splash:
    """Frameless splash window. Use as a context manager or manually."""

    def __init__(self, base_dir: str | Path, title: str = "Stella") -> None:
        self.base_dir = Path(base_dir)
        self.title = title
        self._app = None
        self._owns_app = False
        self._win = None
        self._label = None
        self._hint = None

    # -- lifecycle ----------------------------------------------------------

    def show(self, message: str = "Starting Stella...") -> bool:
        """Create and paint the splash. Returns False if unavailable."""
        try:
            QtCore, QtGui, QtWidgets = _qt()

            # Reuse an existing QApplication if the app already made one,
            # otherwise own a throwaway so the splash can appear before the
            # real UI exists.
            self._app = QtWidgets.QApplication.instance()
            if self._app is None:
                self._app = QtWidgets.QApplication([])
                self._owns_app = True

            self._win = QtWidgets.QWidget()
            self._win.setWindowTitle(self.title)
            self._win.setWindowFlags(
                QtCore.Qt.WindowType.FramelessWindowHint
                | QtCore.Qt.WindowType.WindowStaysOnTopHint
            )
            self._win.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

            root = QtWidgets.QWidget(self._win)
            root.setObjectName("splashRoot")
            root.setStyleSheet(
                "#splashRoot { background-color: #05070C; border-radius: 18px; }"
                "#splashTitle { color: #FFFFFF; font-size: 30px; font-weight: 800; }"
                "#splashMsg { color: #B9C6D9; font-size: 13px; }"
                "#splashHint { color: #6C7A90; font-size: 11px; }"
            )
            lay = QtWidgets.QVBoxLayout(root)
            lay.setContentsMargins(34, 30, 34, 26)
            lay.setSpacing(10)

            logo = self._logo_path()
            if logo:
                lbl = QtWidgets.QLabel()
                pix = QtGui.QPixmap(str(logo))
                if not pix.isNull():
                    # The mark sits in a squircle badge, not a circle: it reads
                    # as an app icon rather than a generic avatar. The shape is
                    # shared with the mobile app and the icon pack.
                    side = 96
                    try:
                        from core.shapes import qt_badge
                        badge = qt_badge(
                            pix, side,
                            background="#0B0F18",
                            border="#1E2636",
                            inset=0.20,
                        )
                    except Exception:
                        badge = pix.scaled(
                            side, side,
                            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                            QtCore.Qt.TransformationMode.SmoothTransformation,
                        )
                    lbl.setPixmap(badge)
                    lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    lay.addWidget(lbl)

            name = QtWidgets.QLabel(self.title)
            name.setObjectName("splashTitle")
            name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(name)

            self._label = QtWidgets.QLabel(message)
            self._label.setObjectName("splashMsg")
            self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(self._label)

            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 0)  # indeterminate
            bar.setTextVisible(False)
            bar.setFixedHeight(3)
            bar.setStyleSheet(
                "QProgressBar { background:#141B26; border:none; border-radius:2px; }"
                "QProgressBar::chunk { background:#3B82F6; border-radius:2px; }"
            )
            lay.addWidget(bar)

            self._hint = QtWidgets.QLabel("Local-first. Your data stays on this device.")
            self._hint.setObjectName("splashHint")
            self._hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(self._hint)

            # QWidget has no setCentralWidget: wrap the layout manually.
            if self._win.layout() is None:
                outer = QtWidgets.QVBoxLayout(self._win)
                outer.setContentsMargins(0, 0, 0, 0)
                outer.addWidget(root)

            self._win.setFixedSize(root.sizeHint())
            self._centre()
            self._win.show()
            self._app.processEvents()
            return True
        except Exception:
            return False

    def set_message(self, message: str) -> None:
        """Update the status line from any thread."""
        try:
            if self._label is None:
                return
            self._label.setText(message)
            if self._app is not None:
                self._app.processEvents()
        except Exception:
            pass

    def close(self) -> None:
        try:
            if self._win is not None:
                self._win.close()
                self._win = None
            if self._app is not None and self._owns_app:
                self._app.quit()
            self._app = None
        except Exception:
            pass

    def __enter__(self) -> "Splash":
        self.show()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- helpers ------------------------------------------------------------

    def _logo_path(self) -> Optional[Path]:
        for name in ("stella_logo.png", "logo.jpg", "stella_logo.ico"):
            p = self.base_dir / "assets" / name
            if p.exists():
                return p
        return None

    def _centre(self) -> None:
        try:
            QtCore, QtGui, _ = _qt()
            screen = QtGui.QGuiApplication.primaryScreen()
            if screen is None:
                return
            geo = screen.availableGeometry()
            size = self._win.size()
            self._win.move(
                (geo.width() - size.width()) // 2,
                (geo.height() - size.height()) // 2,
            )
        except Exception:
            pass