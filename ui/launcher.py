from ._imports import *
from .common import *

class LauncherControlPanel(QDialog):
    def __init__(self, *, startup_workspace: bool = False, on_open=None, on_close=None,
                 on_toggle_startup=None, on_hide_icon=None, on_restart=None, on_quit=None,
                 on_open_app=None,
                 on_show_icon=None,
                 on_open_dev=None,
                 parent=None):
        super().__init__(parent)
        self._on_open = on_open
        self._on_close = on_close
        self._on_toggle_startup = on_toggle_startup
        self._on_hide_icon = on_hide_icon
        self._on_restart = on_restart
        self._on_quit = on_quit
        self._on_open_app = on_open_app
        self._on_show_icon = on_show_icon
        self._on_open_dev = on_open_dev

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(15,15,20,235);
                border: 1px solid rgba(0,191,255,60);
                border-radius: 18px;
            }
        """)
        root.addWidget(frame)

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        title = QLabel("STELLA EVO CONTROL")
        title.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: {C.WHITE}; background: transparent; letter-spacing: 1px;")
        lay.addWidget(title)

        sub = QLabel("Desktop launcher controls")
        sub.setFont(QFont("Exo 2", 9))
        sub.setStyleSheet("color: C.TEXT; background: transparent;")
        lay.addWidget(sub)

        def mk_btn(text: str, *, checkable: bool = False, checked: bool = False) -> QPushButton:
            btn = QPushButton(text)
            btn.setCheckable(checkable)
            btn.setChecked(checked)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(36)
            btn.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton {
                    background: C.TEXT;
                    color: {C.WHITE};
                    border: 1px solid C.TEXT;
                    border-radius: 12px;
                    padding: 6px 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(0,191,255,0.10);
                    border: 1px solid rgba(0,191,255,0.45);
                }
                QPushButton:checked {
                    background: rgba(0,191,255,0.16);
                    border: 1px solid rgba(0,191,255,0.60);
                }
            """)
            return btn

        self._open_btn = mk_btn("Open Workspace")
        self._close_btn = mk_btn("Close Workspace")
        self._startup_btn = mk_btn("Show Workspace On Startup", checkable=True, checked=bool(startup_workspace))
        self._show_icon_btn = mk_btn("Show Floating Icon")
        self._hide_icon_btn = mk_btn("Hide Floating Icon")
        self._restart_btn = mk_btn("Restart Stella")
        self._quit_btn = mk_btn("Quit Stella")
        self._open_app_btn = mk_btn("Open App")
        self._open_dev_btn = mk_btn("Open Developer Mode")

        self._open_btn.clicked.connect(lambda: self._invoke(self._on_open))
        self._close_btn.clicked.connect(lambda: self._invoke(self._on_close))
        self._startup_btn.clicked.connect(lambda: self._invoke(self._on_toggle_startup, self._startup_btn.isChecked()))
        self._show_icon_btn.clicked.connect(lambda: self._invoke(self._on_show_icon))
        self._hide_icon_btn.clicked.connect(self._hide_icon_confirm)
        self._restart_btn.clicked.connect(lambda: self._invoke(self._on_restart))
        self._quit_btn.clicked.connect(lambda: self._invoke(self._on_quit))
        self._open_app_btn.clicked.connect(lambda: self._invoke(self._on_open_app))
        self._open_dev_btn.clicked.connect(lambda: self._invoke(self._on_open_dev))

        for btn in (
            self._open_app_btn, self._open_btn, self._close_btn, self._startup_btn,
            self._show_icon_btn, self._hide_icon_btn, self._open_dev_btn,
            self._restart_btn, self._quit_btn
        ):
            lay.addWidget(btn)

        self.adjustSize()

    def _invoke(self, fn, *args):
        if fn:
            try:
                fn(*args)
            except Exception:
                pass
        self.close()

    def _hide_icon_confirm(self):
        box = QDialog(self)
        box.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        box.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: rgba(15,15,20,240); border: 1px solid rgba(0,191,255,60); border-radius: 16px; }")
        lay.addWidget(frame)
        flay = QVBoxLayout(frame)
        flay.setContentsMargins(18, 16, 18, 16)
        flay.setSpacing(10)
        lbl = QLabel("Hide Stella icon?")
        lbl.setStyleSheet("color: {C.WHITE}; background: transparent; font: 700 11pt 'Segoe UI';")
        sub = QLabel("You can restore it from the system tray.")
        sub.setStyleSheet("color: C.TEXT; background: transparent;")
        flay.addWidget(lbl)
        flay.addWidget(sub)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        hide = QPushButton("Hide")
        for btn in (cancel, hide):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(34)
            btn.setStyleSheet("QPushButton { background: C.TEXT; color: {C.WHITE}; border: 1px solid C.TEXT; border-radius: 10px; } QPushButton:hover { border: 1px solid {C.ICE}; }")
        cancel.clicked.connect(box.reject)
        hide.clicked.connect(box.accept)
        row.addWidget(cancel)
        row.addWidget(hide)
        flay.addLayout(row)
        box.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        box.move(screen.center().x() - box.width() // 2, screen.center().y() - box.height() // 2)
        if box.exec():
            self._invoke(self._on_hide_icon)

    def set_startup_workspace(self, enabled: bool):
        self._startup_btn.setChecked(bool(enabled))

class StellaTelemetryWing(QFrame):
    """
    Stella Right Wing: Live Operations, Research Streams, and Sources.
    Auto-dismisses in 10 seconds unless pinned or hovered.
    Adapts dynamically to the active theme color (Amber Gold by default).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StellaTelemetryWing")
        self.setFixedWidth(310)
        self.setMinimumHeight(320)
        self.setMaximumHeight(520)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        self._pinned = False
        self._paused = False
        self._total_duration_ms = 10000
        self._remaining_ms = 10000
        self._sources_list = []
        self._theme_pri = "{C.PRI}"
        self._theme_rgb = (124, 110, 230)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)

        # Header Row: [⚡ OPERATIONS] + Tool Tag + Pin + Close
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._hud_tag = QLabel("⚡ [OPERATIONS]")
        self._hud_tag.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        header_row.addWidget(self._hud_tag)

        self._tool_tag = QLabel("TELEMETRY")
        self._tool_tag.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        header_row.addWidget(self._tool_tag)
        header_row.addStretch()

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setFixedSize(26, 26)
        self._pin_btn.setToolTip("Pin card (prevent auto-dismiss)")
        self._pin_btn.clicked.connect(self.toggle_pin)
        header_row.addWidget(self._pin_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setToolTip("Dismiss")
        self._close_btn.clicked.connect(self.dismiss)
        header_row.addWidget(self._close_btn)
        lay.addLayout(header_row)

        # Operation Title
        self._title_lbl = QLabel("LIVE TASK EXECUTION")
        self._title_lbl.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color: {C.WHITE};")
        self._title_lbl.setWordWrap(True)
        lay.addWidget(self._title_lbl)

        # Active Step Box
        self._step_box = QFrame()
        step_lay = QVBoxLayout(self._step_box)
        step_lay.setContentsMargins(12, 9, 12, 9)
        step_lay.setSpacing(4)

        step_hdr = QHBoxLayout()
        self._pulse_dot = QLabel("◉")
        self._pulse_dot.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        step_hdr.addWidget(self._pulse_dot)
        self._step_status_lbl = QLabel("ACTIVE STEP")
        self._step_status_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        step_hdr.addWidget(self._step_status_lbl)
        step_hdr.addStretch()
        step_lay.addLayout(step_hdr)

        self._step_text_lbl = QLabel("Initializing operation...")
        self._step_text_lbl.setFont(QFont("Exo 2", 9))
        self._step_text_lbl.setStyleSheet("color: {C.TEXT};")
        self._step_text_lbl.setWordWrap(True)
        step_lay.addWidget(self._step_text_lbl)
        lay.addWidget(self._step_box)

        # Sources / References List
        self._sources_hdr = QLabel("LIVE SOURCES & CHANNELS")
        self._sources_hdr.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        lay.addWidget(self._sources_hdr)

        self._sources_container = QWidget()
        self._sources_container.setStyleSheet("background: transparent;")
        self._sources_lay = QVBoxLayout(self._sources_container)
        self._sources_lay.setContentsMargins(0, 0, 0, 0)
        self._sources_lay.setSpacing(5)
        lay.addWidget(self._sources_container)

        lay.addStretch()

        # Bottom 10-Second Fuse
        fuse_row = QHBoxLayout()
        self._fuse_lbl = QLabel("10s")
        self._fuse_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        fuse_row.addWidget(self._fuse_lbl)
        self._fuse_bar = QProgressBar()
        self._fuse_bar.setRange(0, 100)
        self._fuse_bar.setValue(100)
        self._fuse_bar.setTextVisible(False)
        self._fuse_bar.setFixedHeight(4)
        fuse_row.addWidget(self._fuse_bar, stretch=1)
        lay.addLayout(fuse_row)

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)

        self._opacity_fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_fx)
        self._anim = QPropertyAnimation(self._opacity_fx, b"opacity", self)

        self.apply_theme()
        if hasattr(C, "register_listener"):
            C.register_listener(self.apply_theme)

        self.hide()

    def apply_theme(self):
        pri = getattr(C, "PRI", "{C.PRI}") or "{C.PRI}"
        try:
            r = int(pri[1:3], 16)
            g = int(pri[3:5], 16)
            b = int(pri[5:7], 16)
        except Exception:
            pri = "{C.PRI}"
            r, g, b = 124, 110, 230

        self._theme_pri = pri
        self._theme_rgb = (r, g, b)

        self.setStyleSheet(f"""
            QFrame#StellaTelemetryWing {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(10, 15, 24, 238),
                    stop:0.6 rgba(6, 10, 18, 222),
                    stop:1 rgba(3, 5, 12, 212));
                border: 1px solid rgba({r}, {g}, {b}, 0.45);
                border-radius: 18px;
            }}
            QLabel {{
                background: transparent;
            }}
            QPushButton {{
                background: rgba({r}, {g}, {b}, 0.10);
                border: 1px solid rgba({r}, {g}, {b}, 0.28);
                border-radius: 6px;
                color: {C.WHITE};
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background: rgba({r}, {g}, {b}, 0.26);
                border: 1px solid {pri};
                color: {pri};
            }}
        """)

        self._hud_tag.setStyleSheet(f"color: {pri}; letter-spacing: 1px; font-weight: bold;")
        self._tool_tag.setStyleSheet(f"""
            background: rgba({r}, {g}, {b}, 0.14);
            color: {pri};
            border: 1px solid rgba({r}, {g}, {b}, 0.38);
            border-radius: 9px;
            padding: 1px 7px;
            font-weight: bold;
        """)
        self._step_box.setStyleSheet(f"""
            background: rgba({r}, {g}, {b}, 0.07);
            border: 1px solid rgba({r}, {g}, {b}, 0.22);
            border-radius: 10px;
        """)
        self._pulse_dot.setStyleSheet(f"color: {pri}; font-weight: bold;")
        self._step_status_lbl.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.85); font-weight: bold;")
        self._sources_hdr.setStyleSheet("color: C.TEXT; letter-spacing: 0.5px; font-weight: bold;")
        self._fuse_lbl.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.75); font-weight: bold;")
        self._fuse_bar.setStyleSheet(f"""
            QProgressBar {{
                background: C.TEXT;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {pri};
                border-radius: 2px;
            }}
        """)
        if self._pinned:
            self._pin_btn.setStyleSheet(f"background: rgba({r}, {g}, {b}, 0.35); border: 1px solid {pri}; color: {pri};")
        else:
            self._pin_btn.setStyleSheet("")

    def enterEvent(self, event):
        super().enterEvent(event)
        self._paused = True

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._paused = False

    def toggle_pin(self):
        self._pinned = not self._pinned
        r, g, b = self._theme_rgb
        pri = self._theme_pri
        self._pin_btn.setStyleSheet(f"background: rgba({r}, {g}, {b}, 0.35); border: 1px solid {pri}; color: {pri};" if self._pinned else "")
        if self._pinned:
            self._fuse_lbl.setText("PINNED")
            self._fuse_bar.setValue(100)
        else:
            self._fuse_lbl.setText("10s")

    def show_operation(self, title: str, step: str, sources: list = None, tool: str = None):
        self.apply_theme()
        r, g, b = self._theme_rgb
        pri = self._theme_pri
        self._title_lbl.setText(title or "LIVE TASK EXECUTION")
        self._step_text_lbl.setText(step or "Running operation...")
        if tool:
            self._tool_tag.setText(str(tool).upper()[:14])

        # Clear and repopulate sources
        while self._sources_lay.count():
            item = self._sources_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sources = sources or []
        if not sources:
            default_item = QLabel("• System core processing data")
            default_item.setFont(QFont("Exo 2", 8))
            default_item.setStyleSheet("color: C.TEXT;")
            self._sources_lay.addWidget(default_item)
        else:
            for s in sources[:4]:
                s_str = str(s).strip()
                if s_str.startswith("http"):
                    import urllib.parse
                    domain = urllib.parse.urlparse(s_str).netloc or s_str[:25]
                    text = f"🌐 {domain}"
                else:
                    text = f"📄 {s_str[:32]}"
                pill = QLabel(text)
                pill.setFont(QFont("Exo 2", 8))
                pill.setStyleSheet(f"""
                    background: C.TEXT;
                    color: {C.TEXT};
                    border: 1px solid rgba({r}, {g}, {b}, 0.25);
                    border-radius: 6px;
                    padding: 3px 7px;
                """)
                self._sources_lay.addWidget(pill)

        self._remaining_ms = self._total_duration_ms
        self._paused = False
        if not self._pinned:
            self._timer.start()

        # Fade-in animation
        was_visible = self.isVisible()
        self.show()
        if not was_visible:
            sound_mgr.play_deploy_whoosh()
        else:
            sound_mgr.play_telemetry_chirp()
        self._anim.stop()
        try:
            self._anim.finished.disconnect()
        except Exception:
            pass
        self._anim.setDuration(250)
        self._anim.setStartValue(self._opacity_fx.opacity())
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _on_tick(self):
        if self._pinned or self._paused:
            return
        self._remaining_ms -= 100
        pct = max(0, int((self._remaining_ms / self._total_duration_ms) * 100))
        self._fuse_bar.setValue(pct)
        sec_left = max(0, int(math.ceil(self._remaining_ms / 1000.0)))
        self._fuse_lbl.setText(f"{sec_left}s")
        if self._remaining_ms <= 0:
            self._timer.stop()
            self.dismiss()

    def set_body(self, text: str):
        if hasattr(self, "_step_lbl") and text:
            self._step_lbl.setText(str(text))
            sound_mgr.play_telemetry_chirp()

    def dismiss(self):
        self._timer.stop()
        self._anim.stop()
        try:
            self._anim.finished.disconnect()
        except Exception:
            pass
        self._anim.setDuration(250)
        self._anim.setStartValue(self._opacity_fx.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self.hide)
        self._anim.start()

class StellaResultWing(QFrame):
    """
    Stella Left Wing: Final Results, Generated Deliverables (PDF/Word/Media/Code),
    Executive Summary Bullets, and Quick Action Buttons.
    Auto-dismisses in 10 seconds unless pinned or hovered.
    Adapts dynamically to the active theme color (Amber Gold by default).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StellaResultWing")
        self.setFixedWidth(310)
        self.setMinimumHeight(320)
        self.setMaximumHeight(540)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
        self._pinned = False
        self._paused = False
        self._total_duration_ms = 10000
        self._remaining_ms = 10000
        self._active_file_path = None
        self._theme_pri = "{C.PRI}"
        self._theme_rgb = (124, 110, 230)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)

        # Header: [✨ DELIVERABLE] + Status Badge + Pin + Close
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._hud_tag = QLabel("✨ [DELIVERABLE]")
        self._hud_tag.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        header_row.addWidget(self._hud_tag)

        self._status_badge = QLabel("COMPLETED")
        self._status_badge.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        header_row.addWidget(self._status_badge)
        header_row.addStretch()

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setFixedSize(26, 26)
        self._pin_btn.setToolTip("Pin card (prevent auto-dismiss)")
        self._pin_btn.clicked.connect(self.toggle_pin)
        header_row.addWidget(self._pin_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setToolTip("Dismiss")
        self._close_btn.clicked.connect(self.dismiss)
        header_row.addWidget(self._close_btn)
        lay.addLayout(header_row)

        # Title Label
        self._title_lbl = QLabel("MISSION RESULT")
        self._title_lbl.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color: {C.WHITE};")
        self._title_lbl.setWordWrap(True)
        lay.addWidget(self._title_lbl)

        # File Card Section (Visible when deliverable is a file)
        self._file_card = QFrame()
        file_lay = QHBoxLayout(self._file_card)
        file_lay.setContentsMargins(12, 8, 12, 8)
        file_lay.setSpacing(10)

        self._file_icon_lbl = QLabel("📄")
        self._file_icon_lbl.setFont(QFont("Exo 2", 16))
        file_lay.addWidget(self._file_icon_lbl)

        file_info_lay = QVBoxLayout()
        file_info_lay.setSpacing(2)
        self._file_name_lbl = QLabel("document.pdf")
        self._file_name_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        self._file_name_lbl.setStyleSheet("color: {C.WHITE};")
        self._file_name_lbl.setWordWrap(True)
        file_info_lay.addWidget(self._file_name_lbl)

        self._file_size_lbl = QLabel("Ready to open")
        self._file_size_lbl.setFont(QFont("Exo 2", 8))
        self._file_size_lbl.setStyleSheet("color: C.TEXT;")
        file_info_lay.addWidget(self._file_size_lbl)
        file_lay.addLayout(file_info_lay, stretch=1)

        self._btn_open_file = QPushButton("Open")
        self._btn_open_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_open_file.clicked.connect(self._on_open_file_clicked)
        file_lay.addWidget(self._btn_open_file)

        lay.addWidget(self._file_card)
        self._file_card.hide()

        # Summary / Bullets Scroll Area
        self._bullets_scroll = QScrollArea()
        self._bullets_scroll.setWidgetResizable(True)
        self._bullets_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._bullets_scroll.setStyleSheet("background: transparent; border: none;")
        self._bullets_container = QWidget()
        self._bullets_container.setStyleSheet("background: transparent;")
        self._bullets_lay = QVBoxLayout(self._bullets_container)
        self._bullets_lay.setContentsMargins(0, 0, 4, 0)
        self._bullets_lay.setSpacing(5)
        self._bullets_scroll.setWidget(self._bullets_container)
        lay.addWidget(self._bullets_scroll, stretch=1)

        # Actions Row: [Reveal in Folder] [Copy Result]
        self._actions_row = QHBoxLayout()
        self._actions_row.setSpacing(8)

        self._btn_explorer = QPushButton("📁 Reveal in Folder")
        self._btn_explorer.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_explorer.clicked.connect(self._on_reveal_clicked)
        self._actions_row.addWidget(self._btn_explorer)

        self._btn_copy = QPushButton("📋 Copy Result")
        self._btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copy.clicked.connect(self._on_copy_clicked)
        self._actions_row.addWidget(self._btn_copy)
        lay.addLayout(self._actions_row)

        # Bottom 10-Second Fuse
        fuse_row = QHBoxLayout()
        self._fuse_lbl = QLabel("10s")
        self._fuse_lbl.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        fuse_row.addWidget(self._fuse_lbl)
        self._fuse_bar = QProgressBar()
        self._fuse_bar.setRange(0, 100)
        self._fuse_bar.setValue(100)
        self._fuse_bar.setTextVisible(False)
        self._fuse_bar.setFixedHeight(4)
        fuse_row.addWidget(self._fuse_bar, stretch=1)
        lay.addLayout(fuse_row)

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)

        self._opacity_fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_fx)
        self._anim = QPropertyAnimation(self._opacity_fx, b"opacity", self)
        self._raw_result_text = ""

        self.apply_theme()
        if hasattr(C, "register_listener"):
            C.register_listener(self.apply_theme)

        self.hide()

    def apply_theme(self):
        pri = getattr(C, "PRI", "{C.PRI}") or "{C.PRI}"
        try:
            r = int(pri[1:3], 16)
            g = int(pri[3:5], 16)
            b = int(pri[5:7], 16)
        except Exception:
            pri = "{C.PRI}"
            r, g, b = 124, 110, 230

        self._theme_pri = pri
        self._theme_rgb = (r, g, b)

        self.setStyleSheet(f"""
            QFrame#StellaResultWing {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(14, 18, 26, 240),
                    stop:0.6 rgba(9, 13, 20, 225),
                    stop:1 rgba(4, 7, 12, 215));
                border: 1px solid rgba({r}, {g}, {b}, 0.45);
                border-radius: 18px;
            }}
            QLabel {{
                background: transparent;
            }}
            QPushButton {{
                background: rgba({r}, {g}, {b}, 0.10);
                border: 1px solid rgba({r}, {g}, {b}, 0.28);
                border-radius: 6px;
                color: {C.WHITE};
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background: rgba({r}, {g}, {b}, 0.26);
                border: 1px solid {pri};
                color: {pri};
            }}
        """)

        self._hud_tag.setStyleSheet(f"color: {pri}; letter-spacing: 1px; font-weight: bold;")
        self._status_badge.setStyleSheet(f"""
            background: rgba({r}, {g}, {b}, 0.15);
            color: {pri};
            border: 1px solid rgba({r}, {g}, {b}, 0.40);
            border-radius: 9px;
            padding: 1px 7px;
            font-weight: bold;
        """)
        self._file_card.setStyleSheet(f"""
            background: C.TEXT;
            border: 1px solid rgba({r}, {g}, {b}, 0.25);
            border-radius: 10px;
        """)
        self._fuse_lbl.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.75); font-weight: bold;")
        self._fuse_bar.setStyleSheet(f"""
            QProgressBar {{
                background: C.TEXT;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {pri};
                border-radius: 2px;
            }}
        """)
        if self._pinned:
            self._pin_btn.setStyleSheet(f"background: rgba({r}, {g}, {b}, 0.35); border: 1px solid {pri}; color: {pri};")
        else:
            self._pin_btn.setStyleSheet("")

    def enterEvent(self, event):
        super().enterEvent(event)
        self._paused = True

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._paused = False

    def toggle_pin(self):
        self._pinned = not self._pinned
        r, g, b = self._theme_rgb
        pri = self._theme_pri
        self._pin_btn.setStyleSheet(f"background: rgba({r}, {g}, {b}, 0.35); border: 1px solid {pri}; color: {pri};" if self._pinned else "")
        if self._pinned:
            self._fuse_lbl.setText("PINNED")
            self._fuse_bar.setValue(100)
        else:
            self._fuse_lbl.setText("10s")

    def show_deliverable(self, title: str, summary: str = "", bullets: list = None,
                         file_path: str = None, kind: str = "result", actions: list = None, data: dict = None):
        self.apply_theme()
        self._title_lbl.setText(title or "MISSION RESULT")
        self._active_file_path = file_path
        self._raw_result_text = summary or "\n".join(bullets or [])

        # File card handling
        if file_path and Path(file_path).exists():
            p = Path(file_path)
            self._file_name_lbl.setText(p.name)
            suf = p.suffix.lower()
            icon_map = {
                ".pdf": ("📄", "PDF Document"),
                ".docx": ("📝", "Word Document"),
                ".xlsx": ("📊", "Spreadsheet"),
                ".pptx": ("📈", "Slide Presentation"),
                ".mp4": ("🎬", "Video File"),
                ".py": ("💻", "Python Script"),
                ".png": ("🖼️", "Image"),
                ".jpg": ("🖼️", "Image"),
            }
            icon, ftype = icon_map.get(suf, ("📁", "File"))
            self._file_icon_lbl.setText(icon)
            try:
                sz_mb = p.stat().st_size / (1024 * 1024)
                if sz_mb >= 0.1:
                    self._file_size_lbl.setText(f"{ftype} • {sz_mb:.1f} MB")
                else:
                    sz_kb = p.stat().st_size / 1024
                    self._file_size_lbl.setText(f"{ftype} • {sz_kb:.0f} KB")
            except Exception:
                self._file_size_lbl.setText(ftype)
            self._file_card.show()
            self._btn_explorer.show()
        else:
            self._file_card.hide()
            self._btn_explorer.hide()

        # Clear and repopulate bullets
        while self._bullets_lay.count():
            item = self._bullets_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        bullets = bullets or []
        if not bullets and summary:
            for sent in summary.split(". "):
                clean_s = sent.strip()
                if clean_s and len(clean_s) > 10:
                    bullets.append(clean_s + ("." if not clean_s.endswith(".") else ""))

        for b in bullets[:6]:
            b_lbl = QLabel(f"• {b}")
            b_lbl.setFont(QFont("Exo 2", 9))
            b_lbl.setStyleSheet("color: {C.TEXT};")
            b_lbl.setWordWrap(True)
            self._bullets_lay.addWidget(b_lbl)

        self._remaining_ms = self._total_duration_ms
        self._paused = False
        if not self._pinned:
            self._timer.start()

        # Fade-in animation
        self.show()
        if kind == "deliverable" or file_path:
            sound_mgr.play_mission_complete()
        else:
            sound_mgr.play_deploy_whoosh()
        self._anim.stop()
        try:
            self._anim.finished.disconnect()
        except Exception:
            pass
        self._anim.setDuration(250)
        self._anim.setStartValue(self._opacity_fx.opacity())
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _on_tick(self):
        if self._pinned or self._paused:
            return
        self._remaining_ms -= 100
        pct = max(0, int((self._remaining_ms / self._total_duration_ms) * 100))
        self._fuse_bar.setValue(pct)
        sec_left = max(0, int(math.ceil(self._remaining_ms / 1000.0)))
        self._fuse_lbl.setText(f"{sec_left}s")
        if self._remaining_ms <= 0:
            self._timer.stop()
            self.dismiss()

    def dismiss(self):
        self._timer.stop()
        self._anim.stop()
        try:
            self._anim.finished.disconnect()
        except Exception:
            pass
        self._anim.setDuration(250)
        self._anim.setStartValue(self._opacity_fx.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self.hide)
        self._anim.start()

    def _on_open_file_clicked(self):
        if self._active_file_path:
            p = Path(self._active_file_path).resolve()
            if p.exists():
                try:
                    if sys.platform == "win32":
                        os.startfile(str(p))
                    else:
                        import subprocess
                        subprocess.Popen(["xdg-open", str(p)])
                except Exception as e:
                    print(f"[StellaResultWing] Open file error: {e}")

    def _on_reveal_clicked(self):
        if self._active_file_path:
            p = Path(self._active_file_path).resolve()
            try:
                import subprocess
                if sys.platform == "win32":
                    if p.exists():
                        subprocess.Popen(["explorer.exe", f"/select,{str(p)}"])
                    elif p.parent.exists():
                        subprocess.Popen(["explorer.exe", str(p.parent)])
                else:
                    subprocess.Popen(["xdg-open", str(p.parent)])
            except Exception as e:
                print(f"[StellaResultWing] Reveal error: {e}")

    def set_body(self, text: str):
        if hasattr(self, "_summary_lbl") and text:
            self._summary_lbl.setText(str(text))

    def _on_copy_clicked(self):
        if self._raw_result_text:
            try:
                import pyperclip
                pyperclip.copy(self._raw_result_text)
                self._btn_copy.setText("✓ Copied!")
                QTimer.singleShot(1500, lambda: self._btn_copy.setText("📋 Copy Result"))
            except Exception:
                pass

class SmallPanelCard(QFrame):
    def __init__(self, title: str, body: str, *, accent: str = C.WHITE, parent=None):
        super().__init__(parent)
        self.setObjectName("SmallPanelCard")
        self.setStyleSheet(
            f"""
            QFrame#SmallPanelCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(16, 18, 24, 230),
                    stop:1 rgba(9, 11, 15, 210));
                border: 1px solid C.TEXT;
                border-radius: 14px;
            }}
            """
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        t = QLabel(title.upper())
        t.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent; letter-spacing: 1px;")
        lay.addWidget(t)

        self._body_lbl = QLabel(body)
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._body_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
        lay.addWidget(self._body_lbl)

