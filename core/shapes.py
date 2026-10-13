"""core/shapes.py - the squircle (superellipse) shape, defined once.

Why a shared module
-------------------
The logo badge appears on the desktop splash, in the desktop chat header, in
the mobile app, and as the app/launcher icon. If each surface rounds its own
corners we get four subtly different shapes, which is exactly the kind of
drift that makes a product feel unpolished.

So the shape is defined here, mathematically, and every surface consumes it:

* :func:`superellipse_points` - pure maths, no dependencies, unit-tested.
* :func:`svg_path` - an SVG ``d`` string, reused by the web UI (CSS/SVG) and
  converted to a VectorDrawable path for Android.
* :func:`qt_path` / :func:`qt_badge` - PyQt6 renderers for the desktop app.

A squircle is a superellipse ``|x/a|^n + |y/b|^n = 1``. At ``n = 2`` it is an
ellipse (a circle, when ``a == b``). At ``n -> infinity`` it is a rectangle.
``n = 4`` is the familiar "iOS icon" squircle: a rounded square that is
noticeably *not* a circle, which is the point.
"""

from __future__ import annotations

import math

# The canonical exponent. 4.0 matches the accepted app-icon squircle and reads
# as a rounded square rather than a circle.
DEFAULT_N = 4.0


def superellipse_points(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    n: float = DEFAULT_N,
    steps: int = 240,
) -> list[tuple[float, float]]:
    """Sample a superellipse centred at ``(cx, cy)``.

    ``rx``/``ry`` are the radii (half-width / half-height). ``steps`` controls
    smoothness; 240 is plenty for badges up to a few hundred pixels without a
    visible facet.
    """
    if n <= 0:
        raise ValueError("superellipse exponent must be positive")
    steps = max(8, int(steps))
    exponent = 2.0 / n
    pts: list[tuple[float, float]] = []
    for i in range(steps):
        t = 2.0 * math.pi * i / steps
        ct, st = math.cos(t), math.sin(t)
        x = cx + rx * math.copysign(abs(ct) ** exponent, ct)
        y = cy + ry * math.copysign(abs(st) ** exponent, st)
        pts.append((x, y))
    return pts


def svg_path(size: float, n: float = DEFAULT_N, pad: float = 0.0,
             steps: int = 240) -> str:
    """Return an SVG path ``d`` for a squircle inscribed in ``size`` x ``size``.

    ``pad`` insets the shape from the box edge, mirroring the padding most
    icon systems require. This string is what Android and the web reuse so the
    badge is pixel-identical to the desktop one.
    """
    half = (size - 2.0 * pad) / 2.0
    cx = cy = size / 2.0
    pts = superellipse_points(cx, cy, half, half, n=n, steps=steps)
    head = f"M {pts[0][0]:.3f} {pts[0][1]:.3f}"
    body = " ".join(f"L {x:.3f} {y:.3f}" for x, y in pts[1:])
    return f"{head} {body} Z"


def is_inside(x: float, y: float, size: float, n: float = DEFAULT_N,
              pad: float = 0.0) -> bool:
    """Point test against a squircle. Used by tests and by the mask fallback."""
    half = (size - 2.0 * pad) / 2.0
    cx = cy = size / 2.0
    if half <= 0:
        return False
    dx = abs(x - cx) / half
    dy = abs(y - cy) / half
    return (dx ** n + dy ** n) <= 1.0 + 1e-9


def qt_path(size: int, n: float = DEFAULT_N, pad: float = 0.0):
    """Build a ``QPainterPath`` squircle. Imported lazily to keep Qt optional."""
    from PyQt6.QtGui import QPainterPath
    from PyQt6.QtCore import QPointF

    path = QPainterPath()
    pts = superellipse_points(size / 2.0, size / 2.0,
                              (size - 2.0 * pad) / 2.0, (size - 2.0 * pad) / 2.0,
                              n=n)
    path.moveTo(QPointF(*pts[0]))
    for x, y in pts[1:]:
        path.lineTo(QPointF(x, y))
    path.closeSubpath()
    return path


def _qcolor(value):
    """Parse a CSS-style colour (``#rrggbb``, ``rgb()``, ``rgba()``) for Qt.

    ``QColor`` understands hex and SVG names but not CSS ``rgba(...)``, which
    the UI layer uses everywhere, so we translate before handing it over.
    """
    from PyQt6.QtGui import QColor

    if value is None:
        return QColor(0, 0, 0, 0)
    if isinstance(value, QColor):
        return value
    text = str(value).strip()
    low = text.lower()
    if low.startswith("rgba(") or low.startswith("rgb("):
        body = text[text.index("(") + 1: text.rindex(")")]
        parts = [p.strip() for p in body.replace("/", ",").split(",") if p.strip()]
        try:
            r, g, b = (int(round(float(parts[i]))) for i in range(3))
            a = 255
            if len(parts) >= 4:
                a = int(round(float(parts[3]) * 255)) if float(parts[3]) <= 1.0 else int(round(float(parts[3])))
            return QColor(r, g, b, max(0, min(255, a)))
        except (ValueError, IndexError):
            return QColor(0, 0, 0, 255)
    color = QColor(text)
    if not color.isValid():
        return QColor(0, 0, 0, 255)
    return color


def qt_badge(pixmap, size: int, n: float = DEFAULT_N, pad: float = 0.0,
             inset: float = 0.14, background=None, border=None,
             border_width: float = 1.0):
    """Render ``pixmap`` inside a squircle badge of ``size`` pixels.

    The badge fills its own squircle with ``background`` (defaulting to the
    app's near-black), optionally strokes a ``border``, and draws the logo
    centred with ``inset`` proportional padding - the mark never touches the
    badge edge, which is what makes it read as a proper icon tile.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush

    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    path = qt_path(size, n=n, pad=pad)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(_qcolor(background or "#05070C")))
    painter.drawPath(path)

    if border is not None:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_qcolor(border), border_width))
        painter.drawPath(path)

    if pixmap is not None and not pixmap.isNull():
        inner = max(1, int(size * (1.0 - 2.0 * inset)))
        logo = pixmap.scaled(
            inner, inner,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.setClipPath(path)
        painter.drawPixmap(
            int((size - logo.width()) / 2),
            int((size - logo.height()) / 2),
            logo,
        )

    painter.end()
    return out
