"""
core/hud_theme.py — Stella's design system: tokens, type, glass, motion.

Why this exists
---------------
The app grew one stylesheet at a time. This module is the single source of
truth for the *hyper-futuristic* layer: colour tokens taken straight from the
official Stella palette (class C in ui.py — "Atmospheric Functionalism"),
a type scale, spacing/radius rhythm, breakpoints for responsive layouts, an
application-level stylesheet, and a couple of reusable animated components.

Guiding principles (from the design-system research):
- One palette, semantic roles — never ad-hoc hex per screen.
- 4/8/12/16/24/32 spacing rhythm; 8/12/16/24 radii.
- Display voice = tracked-out uppercase for headers; body = Segoe UI;
  telemetry/HUD numerics = Consolas mono (ships with Windows, no download).
- Motion: micro-interactions 150-300 ms, state pulses loop softly, never
  block content.
- Responsive breakpoints: compact < 720 (phone-sized windows), medium < 1100,
  wide >= 1100 (desktop/ultrawide). Chat measure tightens on wide screens so
  long replies stay readable.

`install()` is called once from StellaUI and re-runs automatically when the
user changes theme (via the C palette listener), so it can never go stale
against the colour engine.
"""

from __future__ import annotations

from PyQt6.QtCore import (QEasingCurve, QPropertyAnimation, QRectF, Qt,
                           pyqtProperty)
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QFrame, QWidget

# ---------------------------------------------------------------------------
# Colour tokens — mirror class C (ui.py) so both stay in lockstep.
# ---------------------------------------------------------------------------
VOID = "#0C0D14"        # primary dark background
PANEL = "#161826"       # cards / containers
PANEL2 = "#10121b"      # sunken panels
IRIS = "#7C6EE6"        # brand / action
IRIS_DIM = "#5a4fc4"
MINT = "#38E2B8"        # success / live
EMBER = "#FF8A5B"       # accent / focus
ALABASTER = "#F4F3EF"   # primary text
SLATE = "#86899F"       # secondary text


def rgba(hex_color: str, alpha: float) -> str:
    """#RRGGBB + alpha -> 'rgba(r, g, b, a)' for QSS."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# ---------------------------------------------------------------------------
# Spacing / radius / breakpoints / type
# ---------------------------------------------------------------------------
SPACING = {"2xs": 4, "xs": 8, "sm": 12, "md": 16, "lg": 24, "xl": 32}
RADII = {"sm": 8, "md": 12, "lg": 16, "xl": 24}
BREAKPOINTS = {"compact": 720, "medium": 1100}
TYPE = {"display": "Segoe UI", "body": "Segoe UI", "mono": "Consolas"}


def breakpoint(width_px: int) -> str:
    if width_px < BREAKPOINTS["compact"]:
        return "compact"
    if width_px < BREAKPOINTS["medium"]:
        return "medium"
    return "wide"


def measure_ratio(width_px: int) -> float:
    """Max share of the viewport a chat bubble may occupy.

    Phones get almost the full width; ultrawide gets a tighter measure so
    lines stay readable instead of stretching edge to edge.
    """
    return {"compact": 0.94, "medium": 0.84, "wide": 0.70}[breakpoint(width_px)]


def mono_font(size: int = 10, bold: bool = False):
    """Consolas QFont helper for telemetry/HUD numerics."""
    from PyQt6.QtGui import QFont
    f = QFont(TYPE["mono"], size)
    f.setBold(bold)
    return f


# ---------------------------------------------------------------------------
# Application stylesheet — the ambient, futuristic layer.
# ---------------------------------------------------------------------------
def build_stylesheet() -> str:
    focus = rgba(IRIS, 0.55)
    return f"""
    /* ---- Stella HUD ambient layer (core/hud_theme.py) ---- */
    QWidget {{
        font-family: "{TYPE['body']}";
    }}
    QPushButton {{
        min-height: 26px;
        border-radius: {RADII['sm']}px;
    }}
    QPushButton:hover {{
        border-color: {rgba(IRIS, 0.45)};
    }}
    QPushButton:focus {{
        border: 1px solid {focus};
        outline: none;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background: {rgba(PANEL, 0.55)};
        border: 1px solid {rgba(IRIS, 0.22)};
        border-radius: {RADII['md']}px;
        padding: 6px 10px;
        selection-background-color: {rgba(IRIS, 0.40)};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {rgba(IRIS, 0.65)};
    }}
    QToolTip {{
        background: {PANEL};
        color: {ALABASTER};
        border: 1px solid {rgba(IRIS, 0.45)};
        border-radius: {RADII['sm']}px;
        padding: 6px 8px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {rgba(IRIS, 0.45)};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {rgba(IRIS, 0.75)};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px; background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent; height: 8px; margin: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {rgba(IRIS, 0.45)}; border-radius: 4px; min-width: 24px;
    }}
    """


_installed = {"on": False}


def install(app: QApplication | None = None) -> bool:
    """Install (or refresh) the HUD stylesheet. Safe to call repeatedly."""
    try:
        application = app or QApplication.instance()
        if application is None:
            return False
        application.setStyleSheet(build_stylesheet())
        if not _installed["on"]:
            _installed["on"] = True
            try:
                from ui import C
                C.register_listener(lambda: install())
            except Exception:
                pass
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
class PulseDot(QWidget):
    """A tiny live-status dot that breathes (opacity 0.35 -> 1.0).

    Used next to the streaming bubble's name and anywhere a "system is
    thinking" signal helps. Pure paint + QPropertyAnimation; ~0 CPU.
    """

    def __init__(self, color: str = MINT, diameter: int = 7, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._opacity = 1.0
        self.setFixedSize(diameter, diameter)
        anim = QPropertyAnimation(self, b"pulset", self)
        anim.setDuration(850)
        anim.setStartValue(0.35)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.setLoopCount(-1)
        self._anim = anim
        anim.start()

    def get_pulse(self) -> float:
        return self._opacity

    def set_pulse(self, v: float) -> None:
        self._opacity = float(v)
        self.update()

    pulset = pyqtProperty(float, get_pulse, set_pulse)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        c.setAlphaF(self._opacity)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(QRectF(0, 0, self.width(), self.height()))


class NeonDivider(QFrame):
    """A 1px horizontal rule that fades IRIS -> transparent (HUD separator)."""

    def __init__(self, accent: str = IRIS, parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)
        self.setFixedHeight(1)

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        c = QColor(self._accent)
        grad.setColorAt(0.0, c)
        c.setAlpha(120)
        grad.setColorAt(0.6, c)
        c.setAlpha(0)
        grad.setColorAt(1.0, c)
        p.setPen(QPen(grad, 1.0))
        p.drawLine(0, 0, self.width(), 0)
