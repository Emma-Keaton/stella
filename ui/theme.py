from ._imports import *
from .common import *

def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c

def _logo_icon() -> QIcon:
    return QIcon(str(LOGO_ICO if LOGO_ICO.exists() else LOGO_FILE))

def _logo_pixmap(size: int) -> QPixmap:
    pix = QPixmap(str(LOGO_FILE))
    if pix.isNull():
        return QPixmap(size, size)
    return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

def _framed_logo(size: int, icon_size: int | None = None, *, bg: str = "rgba(18,18,18,240)",
                 border: str = None, radius: int | None = None, inset: int = 6) -> QLabel:
    # The mark always sits in the shared squircle badge, never a circle, so the
    # chat header, the splash and the mobile app all wear the same shape.
    # `radius` is accepted for call-site compatibility and deliberately ignored.
    border = border or C.BORDER_B
    frame = QLabel()
    frame.setFixedSize(size, size)
    frame.setStyleSheet("background: transparent; border: none;")
    frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
    try:
        from core.shapes import qt_badge
        badge = qt_badge(
            _logo_pixmap(size), size,
            background=bg,
            border=border,
            inset=max(0.0, min(0.4, inset / max(1, size))),
        )
        frame.setPixmap(badge)
    except Exception:
        frame.setPixmap(_logo_pixmap(icon_size or max(8, size - inset * 2)))
    return frame

def _icon_pixmap(kind: str, size: int = 18) -> QPixmap:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(qcol(C.WHITE), max(2.2, size * 0.14), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "attach":
        # More readable paperclip shape
        p.drawArc(QRectF(size*0.22, size*0.14, size*0.42, size*0.58), 35*16, 290*16)
        p.drawArc(QRectF(size*0.42, size*0.24, size*0.28, size*0.44), 35*16, 290*16)
        p.drawLine(QPointF(size*0.28, size*0.56), QPointF(size*0.38, size*0.66))
    elif kind == "mic":
        # Clearer microphone silhouette
        p.drawRoundedRect(QRectF(size*0.31, size*0.14, size*0.38, size*0.48), size*0.16, size*0.16)
        p.drawLine(QPointF(size*0.50, size*0.62), QPointF(size*0.50, size*0.83))
        p.drawLine(QPointF(size*0.36, size*0.83), QPointF(size*0.64, size*0.83))
        p.drawLine(QPointF(size*0.42, size*0.70), QPointF(size*0.58, size*0.70))
    elif kind == "send":
        p.drawLine(QPointF(size*0.20, size*0.50), QPointF(size*0.70, size*0.50))
        p.drawLine(QPointF(size*0.48, size*0.30), QPointF(size*0.70, size*0.50))
        p.drawLine(QPointF(size*0.48, size*0.70), QPointF(size*0.70, size*0.50))

    p.end()
    return px

def _attach_pulse_glow(widget: QWidget, *, color: str = C.WHITE, blur_min: float = 12.0,
                       blur_max: float = 28.0, alpha: int = 180, period_ms: int = 2400) -> None:
    # Intentionally disabled for performance. Kept as a no-op so existing calls
    # do not need to change across the UI.
    return

def _ease_out_expo(x: float) -> float:
    return 1.0 if x == 1.0 else 1.0 - math.pow(2.0, -10.0 * x)

def _ease_in_out_sine(x: float) -> float:
    return -(math.cos(math.pi * x) - 1.0) / 2.0

