from ._imports import *
from .common import *

# ---------------------------------------------------------------------------
# Stella Holographic Avatar — 3D-style hologram rendered with QPainter
# ---------------------------------------------------------------------------

class StellaHologramWidget(QWidget):
    """A holographic Stella avatar rendered entirely with QPainter (no external
    3D dependencies). Cycles through idle/listening/speaking/thinking states
    with pulsing rings, a face-like nucleus, and reactive waveform rings."""

    def __init__(self, parent=None, size: int = 200):
        super().__init__(parent)
        self.setObjectName("StellaHologram")
        self.setFixedSize(size, size)
        self._state = "idle"          # idle | listening | speaking | thinking | muted
        self._pulse_phase = 0.0
        self._caret_on = True
        self._mouth_open = False
        self._mouth_timer = QTimer(self)
        self._mouth_timer.timeout.connect(self._tick_mouth)
        self._mouth_timer.start(180)

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick_anim)
        self._anim.start(30)

        self._waveform_level = 0.0
        self._waveform_target = 0.0

    # ------------------------------------------------------------------ state
    def set_state(self, state: str):
        if state not in ("idle", "listening", "speaking", "thinking", "muted"):
            return
        self._state = state
        self.update()

    def set_audio_level(self, level: float):
        """0.0 .. 1.0 audio level from the mic / TTS output."""
        self._waveform_target = max(0.0, min(1.0, level))
        self.update()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2

        # Base glow (always present, dimmer when idle)
        base_col = self._state_color()
        p.setBrush(QBrush(QColor(base_col).darker(180)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - W * 0.42, cy - H * 0.42, W * 0.84, H * 0.84))

        # Outer pulse ring — breathes
        pulse = (math.sin(self._pulse_phase) + 1) / 2
        ring_r = W * (0.30 + 0.18 * pulse)
        ring_alpha = int(90 + 60 * pulse)
        ring_col = QColor(base_col)
        ring_col.setAlpha(ring_alpha)
        p.setBrush(Qt.BrushStyle.NoPen)
        p.setPen(QPen(ring_col, 2))
        p.drawEllipse(QRectF(cx - ring_r / 2, cy - ring_r / 2, ring_r, ring_r))

        # Middle scanline ring — rotates
        self._scan_angle = getattr(self, "_scan_angle", 0) + 2
        p.setPen(QPen(QColor(base_col).lighter(140), 2))
        p.drawArc(QRectF(cx - W * 0.28, cy - H * 0.28, W * 0.56, H * 0.56),
                  int(self._scan_angle * 16), int(120 * 16))

        # Inner core — nucleus face
        core_r = W * 0.22
        core_col = QColor(base_col).lighter(130)
        p.setBrush(QBrush(core_col))
        p.setPen(QPen(QColor(base_col), 2))
        p.drawEllipse(QRectF(cx - core_r / 2, cy - core_r / 2, core_r, core_r))

        # Nucleus "face" — eyes + mouth
        eye_r = max(2, core_r * 0.10)
        eye_y = cy - core_r * 0.18
        lx = cx - core_r * 0.24
        rx = cx + core_r * 0.24
        p.setBrush(QBrush(QColor(base_col).darker(220)))
        p.drawEllipse(QRectF(lx - eye_r / 2, eye_y - eye_r / 2, eye_r, eye_r))
        p.drawEllipse(QRectF(rx - eye_r / 2, eye_y - eye_r / 2, eye_r, eye_r))

        # Mouth — open when speaking, smile when idle
        mouth_w = core_r * 0.42 if self._mouth_open else core_r * 0.18
        mouth_h = core_r * 0.14 if self._mouth_open else core_r * 0.06
        p.setBrush(QBrush(QColor(base_col).darker(240)))
        p.drawRoundedRect(QRectF(cx - mouth_w / 2, cy + core_r * 0.12, mouth_w, mouth_h),
                          3, 3)

        # Audio waveform ring around core (listening/speaking)
        if self._state in ("listening", "speaking") and self._waveform_level > 0.05:
            wav_r = W * (0.34 + 0.06 * self._waveform_level)
            wav_col = QColor(base_col)
            wav_col.setAlpha(int(110 + 80 * self._waveform_level))
            p.setPen(QPen(wav_col, 2))
            p.setBrush(Qt.BrushStyle.NoPen)
            p.drawEllipse(QRectF(cx - wav_r / 2, cy - wav_r / 2, wav_r, wav_r))

        # Bottom status pill
        p.setBrush(QBrush(QColor(12, 14, 20, 220)))
        p.setPen(QPen(QColor(base_col), 1))
        pill_r = QRectF(cx - W * 0.30, H * 0.90, W * 0.60, H * 0.09)
        p.drawRoundedRect(pill_r, pill_r.height() / 2, pill_r.height() / 2)
        p.setPen(QPen(QColor(base_col), 1))
        p.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        p.drawText(pill_r, Qt.AlignmentFlag.AlignCenter, self._state.upper())

    def _state_color(self) -> str:
        if self._state == "listening":
            return C.PRI           # cyan-ish
        if self._state == "speaking":
            return C.SUCCESS       # green
        if self._state == "thinking":
            return C.ACC           # violet
        if self._state == "muted":
            return C.TEXT_DIM
        return C.TEXT_DIM          # idle — dim

    # ------------------------------------------------------------------ timers
    def _tick_anim(self):
        self._pulse_phase += 0.12
        if self._pulse_phase > math.pi * 2:
            self._pulse_phase -= math.pi * 2
        # Smoothly chase waveform target
        diff = self._waveform_target - self._waveform_level
        self._waveform_level += diff * 0.25
        if abs(diff) < 0.01:
            self._waveform_level = self._waveform_target
        self.update()

    def _tick_mouth(self):
        if self._state == "speaking":
            self._mouth_open = not self._mouth_open
        else:
            self._mouth_open = False
        self.update()

class MessageCard(QFrame):
    def __init__(self, role: str, name: str, text: str, stamp: str, parent=None):
        super().__init__(parent)
        self.setObjectName("MessageCard")
        accent_map = {
            "user": (C.BORDER_B, C.WHITE),
            "assistant": (C.PRI, C.PRI),
            "system": (C.ICE, C.ICE),
            "file": (C.GREEN, C.GREEN),
            "error": (C.EMBER, C.EMBER),
        }
        border_col, left_col = accent_map.get(role, accent_map["system"])
        self.setStyleSheet(
            f"""
            QFrame#MessageCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(13, 15, 20, 246),
                    stop:1 rgba(5, 6, 9, 238));
                border: 1px solid {border_col};
                border-left: 3px solid {left_col};
                border-radius: 12px;
            }}
            """
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(12)

        avatar = QLabel(name[:1].upper())
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))

        palette = {
            "user": ("#0D0F14", C.WHITE, C.BORDER_B),
            "assistant": ("#12090A", C.RED, C.PRI),
            "system": ("#101525", "#7CB7FF", C.ICE),
            "file": ("#0F1410", C.GREEN, C.GREEN),
            "error": ("#1A0F10", "#FFB074", C.EMBER),
        }
        bg, fg, border = palette.get(role, palette["system"])
        avatar.setStyleSheet(
            f"background: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 17px;"
        )

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(3)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")

        time_lbl = QLabel(stamp)
        time_lbl.setFont(QFont("Exo 2", 7))
        time_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        top.addWidget(name_lbl)
        top.addStretch()
        top.addWidget(time_lbl)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setFont(QFont("Exo 2", 9))
        text_color = {
            "user": C.TEXT,
            "assistant": C.WHITE,
            "system": C.TEXT_MED,
            "file": C.GREEN,
            "error": C.RED,
        }.get(role, C.TEXT)
        text_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")

        body.addLayout(top)
        body.addWidget(text_lbl)
        lay.addWidget(avatar)
        lay.addLayout(body)

class ChatBubble(QFrame):
    def __init__(self, role: str, name: str, text: str, stamp: str, attachments: list[dict] | None = None, parent=None, animate: bool = False, live: bool = False):
        super().__init__(parent)
        self._role = role
        self._full_text = text or ""
        self._typing_index = 0
        self._typing_timer: QTimer | None = None
        # Live token-stream state: a blinking caret while the LLM renders and
        # a breathing pulse dot beside Stella's name (core/hud_theme.PulseDot).
        self._live = bool(live)
        self._caret_on = True
        self._caret_timer: QTimer | None = None
        self._pulse = None
        self.setObjectName("ChatBubble")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(1)
        max_w = 340
        if parent and hasattr(parent, "viewport"):
            _vw = parent.viewport().width()
            max_w = max(200, int(_vw * _chat_measure(_vw)))
        self.setMaximumWidth(max_w)
        if role == "user":
            self.setMinimumWidth(120)

        bg_style = (
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(20, 16, 12, 0.45), stop:1 rgba(10, 8, 5, 0.60)); border: 1px solid rgba(124, 110, 230, 0.25); border-radius: 16px;"
            if role != "user"
            else "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(124, 110, 230, 0.22), stop:1 rgba(210, 140, 0, 0.32)); border: 1px solid rgba(124, 110, 230, 0.55); border-radius: 16px;"
        )
        self.setStyleSheet(f"QFrame#ChatBubble {{ {bg_style} }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(6)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)

        if role == "assistant":
            avatar = _framed_logo(24, 24, bg="rgba(12,14,20,245)", border="rgba(124, 110, 230,0.50)", radius=12, inset=4)
            head.addWidget(avatar)
            name_lbl = QLabel(name or "Stella")
            name_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
            name_lbl.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
            head.addWidget(name_lbl)
            if live:
                # Breathing live indicator while tokens stream in.
                try:
                    from core.hud_theme import PulseDot
                    self._pulse = PulseDot()
                    head.addWidget(self._pulse)
                except Exception:
                    self._pulse = None
        elif role != "user":
            name_lbl = QLabel(name)
            name_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
            name_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
            head.addWidget(name_lbl)
        elif role == "user":
            user_icon = QLabel("👤")
            user_icon.setFont(QFont("Exo 2", 9))
            user_icon.setStyleSheet(f"color: {C.PRI}; background: transparent;")
            head.addWidget(user_icon)
            name_lbl = QLabel(name or "You")
            name_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
            name_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
            head.addWidget(name_lbl)

        head.addStretch()

        time_lbl = QLabel(stamp)
        time_lbl.setFont(QFont("Exo 2", 7))
        time_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
        head.addWidget(time_lbl)

        outer.addLayout(head)

        self._browser = QLabel()
        self._browser.setTextFormat(Qt.TextFormat.RichText)
        self._browser.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self._browser.setOpenExternalLinks(True)
        self._browser.setWordWrap(True)
        self._browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._browser.setStyleSheet("QLabel { background: transparent; border: none; color: #F4F6F8; padding: 0; margin: 0; }")
        self._render_text(text or "")

        outer.addWidget(self._browser)

        # Action row (assistant bubbles): Copy / Read aloud / Retry
        if role == "assistant":
            actions = QHBoxLayout()
            actions.setContentsMargins(0, 4, 0, 0)
            actions.setSpacing(6)
            for label, tip in (("Copy", "Copy text"), ("Read aloud", "Read aloud"), ("Retry", "Retry")):
                btn = QPushButton(label)
                btn.setToolTip(tip)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("QPushButton { background: C.TEXT; color: C.TEXT; border: 1px solid C.TEXT; border-radius: 8px; padding: 2px 8px; font-size: 10px; } QPushButton:hover { background: C.TEXT; }")
                if label == "Copy":
                    btn.clicked.connect(lambda _=False, t=text: QApplication.clipboard().setText(t or ""))
                actions.addWidget(btn)
            actions.addStretch()
            outer.addLayout(actions)


        if attachments:
            for attachment in attachments:
                title = str(attachment.get("name") or attachment.get("title") or attachment.get("path") or "Attachment")
                subtitle = str(attachment.get("path") or attachment.get("description") or "")
                outer.addWidget(ArtifactCard(title, file_type=Path(title).suffix.lstrip(".").upper() or "File", status="Attached", path=subtitle or title))

        if animate and role == "assistant":
            self._start_typing_animation()

    def _render_text(self, text: str, final: bool = True):
        self._browser.setText(_markdown_to_html(text or "", self._role))

    def _start_typing_animation(self):
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(14)
        self._typing_timer.timeout.connect(self._tick_typing)
        self._typing_timer.start()

    def _tick_typing(self):
        self._typing_index = min(len(self._full_text), self._typing_index + 3)
        snippet = self._full_text[:self._typing_index]
        self._render_text(snippet, final=False)
        if self._typing_index >= len(self._full_text):
            try:
                self._typing_timer.stop()
            except Exception:
                pass
            self._render_text(self._full_text, final=True)

    # ---- live token streaming (LLM renders -> we render) -----------------
    def set_live(self, text: str):
        """Update the bubble while the model is still producing tokens.

        Renders the accumulated text with a blinking caret so it reads as a
        live terminal feed instead of a frozen block.
        """
        self._full_text = text or ""
        self._start_caret()
        self._caret_on = True
        self._render_live()

    def _start_caret(self):
        if self._caret_timer is None:
            self._caret_timer = QTimer(self)
            self._caret_timer.setInterval(480)
            self._caret_timer.timeout.connect(self._tick_caret)
            self._caret_timer.start()

    def _tick_caret(self):
        if not self._live:
            return
        self._caret_on = not self._caret_on
        self._render_live()

    def _render_live(self):
        caret = "▋" if self._caret_on else " "
        try:
            self._browser.setText(_markdown_to_html(self._full_text + caret, self._role))
        except Exception:
            self._browser.setText((self._full_text or "") + caret)

    def end_live(self):
        """Stop caret + pulse. The final text is rendered by the caller."""
        self._live = False
        for t in (self._caret_timer, self._typing_timer):
            if t is not None:
                try:
                    t.stop()
                except Exception:
                    pass
        self._caret_timer = None
        if self._pulse is not None:
            try:
                self._pulse._anim.stop()
                self._pulse.hide()
            except Exception:
                pass
        try:
            self._browser.setText(_markdown_to_html(self._full_text or "", self._role))
        except Exception:
            self._browser.setText(self._full_text or "")

class ConversationFeed(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(
            """
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                border: none;
                margin: 6px 0 6px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(124, 110, 230,0.45);
                border-radius: 4px;
                min-height: 24px;
            }
            """
        )
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(8)
        self._layout.addStretch(1) # Stretch at bottom pushes bubbles tightly to the top
        self.setWidget(self._content)
        self._empty_widget: QWidget | None = None
        self._message_count = 0
        # Live reply stream: one ephemeral bubble that grows as tokens arrive;
        # it is removed when the persisted reply lands through append_log.
        self._live_bubble = None
        self._live_text = ""

        # Holographic avatar - floating above the conversation
        self._holo = StellaHologramWidget(self._content, size=200)
        self._holo.set_state("idle")
        self._holo.move(0, 0)
        self._holo.hide()
        self._layout.addWidget(self._holo, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._layout.setStretch(0, 1)

    def show_hologram(self, show: bool = True):
        if show:
            self._holo.show()
        else:
            self._holo.hide()

    def set_holo_state(self, state: str):
        self._holo.set_state(state)

    def set_audio_level(self, level: float):
        self._holo.set_audio_level(level)

    def _ensure_empty_widget(self):
        if self._empty_widget is not None:
            return self._empty_widget
        frame = QFrame()
        frame.setStyleSheet(
            """
            QFrame {
                background: C.TEXT;
                border: 1px solid rgba(124, 110, 230,0.16);
                border-radius: 14px;
            }
            QPushButton {
                background: C.TEXT;
                color: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 12px;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230,0.08);
                border: 1px solid rgba(124, 110, 230,0.28);
            }
            """
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        title = QLabel("Try asking Stella")
        title.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: C.TEXT; background: transparent;")
        subtitle = QLabel("Create a presentation, analyze a screen, build a website, organize files, or run browser automation.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: C.TEXT; background: transparent;")
        lay.addWidget(title)
        lay.addWidget(subtitle)
        grid = QGridLayout()
        grid.setSpacing(8)
        self._empty_widget_buttons = []
        for idx, suggestion in enumerate([
            "Create Presentation",
            "Analyze Screen",
            "Build Website",
            "Organize Downloads",
            "Browser Automation",
        ]):
            btn = QPushButton(suggestion)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, s=suggestion: self._emit_empty_suggestion(s))
            self._empty_widget_buttons.append(btn)
            grid.addWidget(btn, idx // 2, idx % 2)
        lay.addLayout(grid)
        self._empty_widget = frame
        return frame

    def _emit_empty_suggestion(self, text: str):
        root = self.parentWidget()
        while root is not None and not hasattr(root, "command_submitted"):
            root = root.parentWidget()
        if root is not None and hasattr(root, "command_submitted"):
            root.command_submitted.emit(text)

    def clear_messages(self):
        self.end_live_reply()
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self._empty_widget:
                widget.deleteLater()
        if self._empty_widget is not None:
            self._empty_widget.hide()
        self._layout.addStretch(1)
        self._message_count = 0

    def add_message(self, role: str, name: str, text: str, stamp: str, attachments: list[dict] | None = None, animate: bool = False, event_type: str | None = None):
        vw = self.viewport().width()
        if hasattr(self, "_content") and self._content is not None and vw > 20:
            self._content.setFixedWidth(vw)
        if self._layout.count() and self._layout.itemAt(self._layout.count() - 1).spacerItem() is not None:
            self._layout.takeAt(self._layout.count() - 1)
        if role == "system":
            bubble = self._build_event_card(text, stamp, event_type=event_type)
            self._layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        elif role == "file":
            bubble = self._build_artifact_card(text, attachments=attachments, stamp=stamp)
            self._layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        elif role == "user":
            bubble = ChatBubble(role, name, text, stamp, attachments=attachments, parent=self, animate=animate)
            self._layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        else:
            bubble = ChatBubble(role, name, text, stamp, attachments=attachments, parent=self, animate=animate)
            self._layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        self._layout.addStretch(1)
        self._message_count += 1
        self._sync_empty_state()
        QTimer.singleShot(0, self.scroll_to_bottom)

    # ---- live token streaming -------------------------------------------
    def begin_live_reply(self):
        """Create the ephemeral assistant bubble for an in-flight reply."""
        if self._live_bubble is not None:
            return
        if self._layout.count() and self._layout.itemAt(self._layout.count() - 1).spacerItem() is not None:
            self._layout.takeAt(self._layout.count() - 1)
        vw = self.viewport().width()
        if hasattr(self, "_content") and self._content is not None and vw > 20:
            self._content.setFixedWidth(vw)
        bubble = ChatBubble("assistant", "Stella", "", "", parent=self, live=True)
        if vw > 20:
            bubble.setMaximumWidth(max(180, int(vw * _chat_measure(vw))))
        self._live_bubble = bubble
        self._live_text = ""
        self._layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._layout.addStretch(1)
        self._sync_empty_state()
        QTimer.singleShot(0, self.scroll_to_bottom)

    def append_live_reply(self, chunk: str):
        """Accumulate one model token/chunk into the live bubble."""
        if not chunk:
            return
        if self._live_bubble is None:
            self.begin_live_reply()
        if self._live_bubble is None:
            return
        self._live_text = (self._live_text or "") + chunk
        try:
            self._live_bubble.set_live(self._live_text)
        except Exception:
            pass
        QTimer.singleShot(0, self.scroll_to_bottom)

    def end_live_reply(self, final: str = ""):
        """Stream finished — retire the live bubble.

        The persisted reply then arrives through the normal log path within
        the same event-loop tick, so this swap is invisible in practice.
        """
        bubble = self._live_bubble
        if bubble is None:
            return
        self._live_bubble = None
        try:
            bubble.end_live()
        except Exception:
            pass
        idx = self._layout.indexOf(bubble)
        if idx != -1:
            self._layout.takeAt(idx)
        bubble.deleteLater()
        # Re-show the empty state only if no real message follows shortly.
        QTimer.singleShot(700, self._sync_empty_state)

    def _build_event_card(self, text: str, stamp: str, event_type: str | None = None) -> QWidget:
        low = (event_type or text or "").lower()
        title = "System Event"
        icon = "●"
        accent = "#7C6EE6"
        if "discord" in low and "connected" in low:
            title, icon, accent = "Discord Connected", "◉", "#5865F2"
        elif "presentation" in low:
            title, icon, accent = "Presentation Generated", "▣", "#FF7A45"
        elif "website" in low:
            title, icon, accent = "Website Created", "⌂", "#37FF5F"
        elif "spreadsheet" in low:
            title, icon, accent = "Spreadsheet Generated", "▦", "#6FD6FF"
        elif "browser" in low:
            title, icon, accent = "Browser Automation Completed", "↗", "#FFBF00"
        elif "organ" in low and "file" in low:
            title, icon, accent = "File Organization Completed", "🗂", "#37FF5F"
        elif "screen" in low and "analysis" in low:
            title, icon, accent = "Screen Analysis Completed", "◫", "#6FD6FF"
        return EventCard(title, text, stamp, icon=icon, accent=accent, parent=self)

    def _build_artifact_card(self, text: str, attachments: list[dict] | None = None, stamp: str = "") -> QWidget:
        attachment = (attachments or [{}])[0] if attachments else {}
        path = str(attachment.get("path") or attachment.get("file") or attachment.get("name") or "").strip()
        title = str(attachment.get("name") or attachment.get("title") or Path(path).name or "Generated File").strip()
        suffix = Path(path or title).suffix.lstrip(".").upper() or (str(attachment.get("type") or "FILE")).upper()
        status = "Ready"
        return ArtifactCard(title, file_type=suffix, status=status, path=path or title, parent=self)

    def scroll_to_bottom(self):
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def load_messages(self, messages: list[dict[str, Any]], max_display: int = 40):
        self.clear_messages()
        # Cap batch to recent messages to prevent UI thread freeze with large histories
        display_messages = messages[-max_display:] if len(messages) > max_display else messages
        for msg in display_messages:
            role = (msg.get("role") or "assistant").strip().lower()
            content = msg.get("content") or ""
            stamp = _fmt_time_stamp(msg.get("timestamp"))
            attachments = msg.get("attachments") or []
            name = {
                "user": "You",
                "assistant": "Stella",
                "system": "System",
                "file": "Files",
            }.get(role, "Stella")
            self.add_message(role, name, content, stamp, attachments=attachments, animate=False)
        self._sync_empty_state()
        QTimer.singleShot(0, self.scroll_to_bottom)

    def _sync_empty_state(self):
        if self._empty_widget is None:
            self._ensure_empty_widget()
        if self._message_count <= 0:
            if self._layout.indexOf(self._empty_widget) == -1:
                self._layout.insertWidget(0, self._empty_widget)
            self._empty_widget.show()
        else:
            if self._layout.indexOf(self._empty_widget) != -1:
                self._layout.removeWidget(self._empty_widget)
            self._empty_widget.hide()

    def has_messages(self) -> bool:
        return self._message_count > 0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vw = self.viewport().width()
        if hasattr(self, "_content") and self._content is not None and vw > 20:
            self._content.setFixedWidth(vw)
            for i in range(self._layout.count()):
                w = self._layout.itemAt(i).widget()
                if w and isinstance(w, ChatBubble):
                    max_w = max(180, int(vw * _chat_measure(vw)))
                    w.setMaximumWidth(max_w)
                elif w and hasattr(w, "_fit_to_content"):
                    w._fit_to_content()
        QTimer.singleShot(0, self.scroll_to_bottom)

class AttachmentCard(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("AttachmentCard")
        self.setStyleSheet("""
            QFrame#AttachmentCard {
                background: C.TEXT;
                border: 1px solid rgba(124, 110, 230,0.26);
                border-radius: 10px;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)
        icon = QLabel("⎙")
        icon.setFixedSize(26, 26)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("color: #7C6EE6; background: C.TEXT; border-radius: 13px; font-size: 14px;")
        lay.addWidget(icon)
        txt = QVBoxLayout()
        txt.setContentsMargins(0, 0, 0, 0)
        txt.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet("color: C.TEXT; background: transparent; font: 600 9pt 'Segoe UI';")
        s = QLabel(subtitle)
        s.setStyleSheet("color: C.TEXT; background: transparent; font: 8pt 'Segoe UI';")
        txt.addWidget(t)
        txt.addWidget(s)
        lay.addLayout(txt, 1)

class EventCard(QFrame):
    def __init__(self, title: str, detail: str, stamp: str, icon: str = "●", accent: str = "#7C6EE6", parent=None):
        super().__init__(parent)
        self.setObjectName("EventCard")
        self.setStyleSheet(
            f"""
            QFrame#EventCard {{
                background: C.TEXT;
                border: 1px solid rgba(124, 110, 230,0.15);
                border-radius: 12px;
            }}
            """
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 12, 6)
        lay.setSpacing(8)

        icon_lbl = QLabel(icon[:1])
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        icon_lbl.setStyleSheet(f"background: transparent; color: {accent};")
        lay.addWidget(icon_lbl)

        clean_detail = (detail or "").strip()
        if len(clean_detail) > 160:
            clean_detail = clean_detail[:157] + "..."
        full_text = f"{title}: {clean_detail}" if clean_detail and clean_detail != title else title
        title_lbl = QLabel(full_text)
        title_lbl.setFont(QFont("Exo 2", 9))
        title_lbl.setWordWrap(True)
        title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
        lay.addWidget(title_lbl, 1)
        
        stamp_lbl = QLabel(stamp)
        stamp_lbl.setFont(QFont("Exo 2", 7))
        stamp_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
        lay.addWidget(stamp_lbl)

class ArtifactCard(QFrame):
    def __init__(self, title: str, file_type: str = "File", status: str = "Generated", path: str = "", parent=None):
        super().__init__(parent)
        self._path = path.strip()
        self.setObjectName("ArtifactCard")
        self.setStyleSheet(
            """
            QFrame#ArtifactCard {
                background: rgba(11, 12, 16, 230);
                border: 1px solid rgba(124, 110, 230,0.22);
                border-radius: 12px;
            }
            QPushButton {
                background: C.TEXT;
                color: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230,0.08);
                border: 1px solid rgba(124, 110, 230,0.35);
            }
            QPushButton:disabled {
                color: C.TEXT;
            }
            """
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(10)
        badge = QLabel("↗")
        badge.setFixedSize(30, 30)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        badge.setStyleSheet("background: rgba(124, 110, 230,0.08); color: #7C6EE6; border: 1px solid rgba(124, 110, 230,0.24); border-radius: 15px;")
        head.addWidget(badge)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(2)
        name_lbl = QLabel(title or "Generated file")
        name_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
        type_lbl = QLabel(f"{file_type} • {status}")
        type_lbl.setFont(QFont("Exo 2", 8))
        type_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
        meta.addWidget(name_lbl)
        meta.addWidget(type_lbl)
        head.addLayout(meta, 1)
        lay.addLayout(head)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._open_btn = QPushButton("Open")
        self._reveal_btn = QPushButton("Reveal Folder")
        self._open_btn.clicked.connect(self._open_file)
        self._reveal_btn.clicked.connect(self._reveal_file)
        if not self._path or not Path(self._path).exists():
            self._open_btn.setEnabled(False)
            self._reveal_btn.setEnabled(False)
        btn_row.addWidget(self._open_btn)
        btn_row.addWidget(self._reveal_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

    def _open_file(self):
        if not self._path or not Path(self._path).exists():
            return
        try:
            os.startfile(self._path)
        except Exception:
            pass

    def _reveal_file(self):
        if not self._path or not Path(self._path).exists():
            return
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", "/select,", self._path])
            else:
                os.startfile(str(Path(self._path).parent))
        except Exception:
            pass

class TaskCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskCard")
        self._active = False
        self._workspace_locked = False
        self.setStyleSheet(
            f"""
            QFrame#TaskCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(16, 18, 24, 230),
                    stop:0.6 rgba(10, 12, 18, 210),
                    stop:1 rgba(5, 7, 11, 200));
                border: 1px solid C.TEXT;
                border-radius: 16px;
            }}
            QFrame#TaskCard:hover {{
                border: 1px solid rgba(124, 110, 230, 0.28);
            }}
            """
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        row = QHBoxLayout()
        self._title = QLabel("Task Workspace")
        self._title.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {C.PRI}; background: transparent;")

        self._pct = QLabel("0%")
        self._pct.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._pct.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self._title)
        row.addStretch()
        row.addWidget(self._pct)
        lay.addLayout(row)

        self._command_lbl = QLabel("Command: waiting for input")
        self._command_lbl.setWordWrap(True)
        self._command_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        self._command_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(self._command_lbl)

        self._plan_lbl = QLabel("Plan: Stella will generate a task plan after you send a command.")
        self._plan_lbl.setWordWrap(True)
        self._plan_lbl.setFont(QFont("Exo 2", 9))
        self._plan_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(self._plan_lbl)

        self._status_lbl = QLabel("Status: Idle")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        self._status_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(self._status_lbl)

        self._output_lbl = QLabel("Output: Ready to work.")
        self._output_lbl.setWordWrap(True)
        self._output_lbl.setFont(QFont("Exo 2", 9))
        self._output_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(self._output_lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        self._bar.setStyleSheet(
            f"""
            QProgressBar {{
                background: C.TEXT;
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {C.PRI};
                border-radius: 3px;
            }}
            """
        )
        lay.addWidget(self._bar)

        self._foot = QLabel("Working on it...")
        self._foot.setFont(QFont("Exo 2", 9))
        self._foot.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addWidget(self._foot)

    def set_task(self, title: str, desc: str, percent: int):
        if self._workspace_locked:
            return
        if self._active:
            self.update_workspace(title=title, status=desc, percent=percent)
            return
        self._title.setText(title)
        self._status_lbl.setText(desc)
        self._output_lbl.setText(desc)
        self._plan_lbl.setText("Plan: Stella will generate a task plan after you send a command.")
        self._command_lbl.setText("Command: waiting for input")
        self._pct.setText(f"{percent}%")
        self._bar.setValue(max(0, min(100, percent)))

    def _format_plan(self, plan: list[str] | str | None) -> str:
        if not plan:
            return "Plan: • Understand the request\n       • Execute the right tools\n       • Return the result"
        if isinstance(plan, str):
            text = plan.strip()
            return f"Plan: {text}" if text.lower().startswith("plan:") else f"Plan: {text}"
        items = [str(item).strip() for item in plan if str(item).strip()]
        if not items:
            return "Plan: • Understand the request\n       • Execute the right tools\n       • Return the result"
        return "Plan:\n" + "\n".join(f"• {item}" for item in items)

    def start_workspace(self, command: str, plan: list[str] | str | None = None, source: str = "local"):
        self._active = True
        self._workspace_locked = False
        self._title.setText("Task Workspace")
        self._command_lbl.setText(f"Command: {command or 'waiting for input'}")
        self._plan_lbl.setText(self._format_plan(plan))
        self._status_lbl.setText("Status: Planning task...")
        self._output_lbl.setText("Output: Waiting for execution.")
        self._pct.setText("8%")
        self._bar.setValue(8)
        self._foot.setText(f"Source: {source}")
        # self.show() intentionally removed to prevent flashing on quick/normal chats

    def update_workspace(self, *, title: str | None = None, command: str | None = None, plan: list[str] | str | None = None,
                         status: str | None = None, output: str | None = None, percent: int | None = None,
                         footer: str | None = None):
        if title:
            self._title.setText(title)
        if command:
            self._command_lbl.setText(f"Command: {command}")
        if plan is not None:
            self._plan_lbl.setText(self._format_plan(plan))
        if status:
            self._status_lbl.setText(f"Status: {status}" if not status.lower().startswith("status:") else status)
        if output:
            self._output_lbl.setText(f"Output: {output}" if not output.lower().startswith("output:") else output)
        if percent is not None:
            pct = max(0, min(100, int(percent)))
            self._pct.setText(f"{pct}%")
            self._bar.setValue(pct)
        self._foot.setText(footer)
        self._active = True
        self._workspace_locked = False
        if percent is not None and int(percent) > 10:
            self.show()

    def finish_workspace(self, result: str, status: str = "Task completed.", percent: int = 100):
        self._active = False
        self._workspace_locked = True
        self._title.setText("Task Complete")
        self._status_lbl.setText(f"Status: {status}")
        self._output_lbl.setText(f"Output: {result or 'Done.'}")
        self._pct.setText(f"{max(0, min(100, percent))}%")
        self._bar.setValue(max(0, min(100, percent)))
        self._foot.setText("Resetting workspace shortly...")
        self.show()
        QTimer.singleShot(5000, self.clear_workspace)

    def clear_workspace(self):
        self._active = False
        self._workspace_locked = False
        self._title.setText("Ready")
        self._command_lbl.setText("Command: waiting for input")
        self._plan_lbl.setText("Plan: Stella will generate a task plan after you send a command.")
        self._status_lbl.setText("Status: Idle")
        self._output_lbl.setText("Output: Ready to work.")
        self._pct.setText("0%")
        self._bar.setValue(0)
        self._foot.setText("Working on it...")
        self.hide()

class TaskDock(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskDock")
        self._collapsed = False
        self._expanded_w = 392
        self._collapsed_w = 44
        self.setFixedWidth(self._expanded_w)
        self.setStyleSheet(
            f"""
            QFrame#TaskDock {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(7, 8, 12, 250),
                    stop:1 rgba(3, 4, 6, 245));
                border-left: 1px solid rgba(124, 110, 230, 0.55);
            }}
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 10, 8, 10)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._title = QLabel("TASK WORKSPACE")
        try:
            from core.hud_theme import mono_font
            self._title.setFont(mono_font(13, True))
        except Exception:
            self._title.setFont(QFont("Exo 2", 14, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 2px;")
        header.addWidget(self._title)
        header.addStretch()

        self._toggle_btn = QPushButton(">")
        self._toggle_btn.setFixedSize(34, 34)
        self._toggle_btn.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(12,14,18,245); color: {C.WHITE}; border: 1px solid {C.BORDER_B}; border-radius: 8px; }}"
            f"QPushButton:hover {{ color: {C.PRI}; border: 1px solid {C.PRI}; }}"
        )
        self._toggle_btn.clicked.connect(self.toggle_collapsed)
        header.addWidget(self._toggle_btn)
        root.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.PRI_GHO}; margin: 2px 0;")
        root.addWidget(sep)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self._content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._task_card = TaskCard()
        lay.addWidget(self._task_card)

        self._mini_hint = QLabel("TASK")
        self._mini_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mini_hint.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        self._mini_hint.setStyleSheet(
            f"color: {C.PRI}; background: rgba(12,14,18,245); border: 1px solid {C.BORDER_B}; border-radius: 8px; padding: 10px 4px;"
        )
        self._mini_hint.setVisible(False)
        lay.addWidget(self._mini_hint)

        root.addWidget(self._content, stretch=1)
        self._apply_state()

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool):
        self._collapsed = bool(collapsed)
        self._apply_state()

    def is_collapsed(self) -> bool:
        return self._collapsed

    def _apply_state(self):
        self._content.setVisible(not self._collapsed)
        self._mini_hint.setVisible(self._collapsed)
        self._toggle_btn.setText(">" if self._collapsed else "<")
        self._toggle_btn.setToolTip("Open task workspace" if self._collapsed else "Collapse task workspace")
        self._title.setVisible(not self._collapsed)
        self.setFixedWidth(self._collapsed_w if self._collapsed else self._expanded_w)

    def start_workspace(self, command: str, plan: list[str] | str | None = None, source: str = "local"):
        self._task_card.start_workspace(command, plan, source)
        if self._collapsed:
            return

    def update_workspace(self, **kwargs):
        self._task_card.update_workspace(**kwargs)

    def finish_workspace(self, result: str, status: str = "Task completed.", percent: int = 100):
        self._task_card.finish_workspace(result, status, percent)

    def clear_workspace(self):
        self._task_card.clear_workspace()

class HistoryConversationItem(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, conversation_id: str, title: str, stamp: str, pinned: bool = False, parent=None):
        super().__init__(parent)
        self._conversation_id = conversation_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("HistoryConversationItem")
        self.setStyleSheet(
            """
            QFrame#HistoryConversationItem {
                background: C.TEXT;
                border: 1px solid rgba(124, 110, 230,0.18);
                border-radius: 10px;
            }
            QFrame#HistoryConversationItem:hover {
                background: rgba(124, 110, 230,0.07);
                border: 1px solid rgba(124, 110, 230,0.32);
            }
            """
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)

        icon = QLabel("B")
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background: rgba(124, 110, 230,0.10); color: #7C6EE6; border: 1px solid rgba(124, 110, 230,0.28); border-radius: 15px; font: 700 11pt 'Segoe UI';")
        lay.addWidget(icon)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(2)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        title_lbl = QLabel(title or "Conversation")
        title_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
        row.addWidget(title_lbl)
        if pinned:
            pin = QLabel("PIN")
            pin.setStyleSheet("color: #37FF5F; background: transparent; font: 700 7pt 'Courier New';")
            row.addWidget(pin)
        row.addStretch()
        stamp_lbl = QLabel(stamp)
        stamp_lbl.setFont(QFont("Exo 2", 7))
        stamp_lbl.setStyleSheet("color: C.TEXT; background: transparent;")
        row.addWidget(stamp_lbl)
        meta.addLayout(row)
        lay.addLayout(meta, 1)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._conversation_id)

