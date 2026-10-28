from ._imports import *
from .common import *

class BackgroundWidget(QWidget):
    _state_sig = pyqtSignal(str)
    _audio_sig = pyqtSignal(float)

    def __init__(self, image_path: Path | str | None = None, parent=None):
        super().__init__(parent)
        self._state_sig.connect(self._do_set_ai_state)
        self._audio_sig.connect(self._do_set_audio_level)
        self._last_audio_js_time = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        self.setMouseTracking(True)
        self._fallback_pixmap: QPixmap | None = None
        if image_path:
            try:
                path = Path(image_path)
                if path.exists():
                    self._fallback_pixmap = QPixmap(str(path))
            except Exception:
                self._fallback_pixmap = None
        self._web_view = None

        if WEB_ENGINE_AVAILABLE:
            self._init_web_engine()

    def _init_web_engine(self):
        if self._web_view is not None:
            return
        try:
            html_path = BASE_DIR / "assets" / "web_background" / "index.html"
            if not html_path.exists():
                return
            self._web_view = QWebEngineView(self)
            st = self._web_view.settings()
            try:
                st.setAttribute(st.WebAttribute.WebGLEnabled, True)
                st.setAttribute(st.WebAttribute.JavascriptEnabled, True)
                st.setAttribute(st.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                st.setAttribute(st.WebAttribute.LocalContentCanAccessFileUrls, True)
                st.setAttribute(st.WebAttribute.Accelerated2dCanvasEnabled, True)
                st.setAttribute(st.WebAttribute.ScrollAnimatorEnabled, False)
            except Exception:
                pass

            self._web_view.setStyleSheet("background: C.BG;")
            self._web_view.page().setBackgroundColor(QColor("C.BG"))
            self._web_view.loadFinished.connect(self._on_web_loaded)

            file_url = QUrl.fromLocalFile(str(html_path.resolve()))
            self._web_view.load(file_url)

            w = max(self.width(), 800)
            h = max(self.height(), 600)
            self._web_view.setGeometry(0, 0, w, h)
            self._web_view.lower()
            self._web_view.show()
        except Exception as e:
            print(f"[BackgroundWidget] Init web engine error: {e}")
            self._web_view = None

    def _on_web_loaded(self, ok: bool):
        if ok and self._web_view:
            if self.width() > 0 and self.height() > 0:
                self._web_view.setGeometry(self.rect())
                self._web_view.lower()
            st = getattr(self, "_last_state", "IDLE") or "IDLE"
            self._do_set_ai_state(st)
        elif not ok:
            print("[BackgroundWidget] Background WebEngine failed to load, retrying in 250ms...")
            html_path = BASE_DIR / "assets" / "web_background" / "index.html"
            if html_path.exists() and self._web_view:
                QTimer.singleShot(250, lambda: self._web_view.load(QUrl.fromLocalFile(str(html_path.resolve()))))

    def _load_background(self) -> None:
        pass

    def _apply_theme_to_html(self, html_content: str) -> str:
        import colorsys
        import re
        
        try:
            r = int(C.PRI[1:3], 16)
            g = int(C.PRI[3:5], 16)
            b = int(C.PRI[5:7], 16)
            target_h, _, _ = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        except:
            return html_content
            
        def map_hex(match):
            old_hex = match.group(0)
            prefix = old_hex[:2]
            h_str = old_hex[2:]
            if len(h_str) != 6: return old_hex
            try:
                or_r, or_g, or_b = int(h_str[:2], 16), int(h_str[2:4], 16), int(h_str[4:], 16)
                _, or_l, or_s = colorsys.rgb_to_hls(or_r/255.0, or_g/255.0, or_b/255.0)
                n_r, n_g, n_b = colorsys.hls_to_rgb(target_h, or_l, or_s)
                return f"{prefix}{int(n_r*255):02x}{int(n_g*255):02x}{int(n_b*255):02x}"
            except:
                return old_hex
                
        gold_hexes = [r"0xffbe1a", r"0xaa8010", r"0x040302", r"0x553f05", r"0xffea80", r"0xfff2a3", r"0xffe680", r"0xd4af37", r"0x3b2e0c"]
        for gh in gold_hexes:
            html_content = re.sub(gh, map_hex, html_content, flags=re.IGNORECASE)
            
        return html_content

    def set_ai_state(self, state: str) -> None:
        try:
            self._state_sig.emit(str(state or "IDLE"))
        except Exception:
            pass

    def _do_set_ai_state(self, state: str) -> None:
        if self._web_view:
            try:
                st = (state or "IDLE").strip().replace("'", "\\'")
                page = self._web_view.page()
                if page:
                    page.runJavaScript(f"if(window.setStellaState) window.setStellaState('{st}');")
            except Exception:
                pass

    def set_audio_level(self, level: float) -> None:
        try:
            self._audio_sig.emit(float(level))
        except Exception:
            pass

    def _do_set_audio_level(self, level: float) -> None:
        now = time.monotonic()
        if (now - self._last_audio_js_time) < 0.016:  # Ultra-smooth 60 FPS WebEngine bridge
            return
        self._last_audio_js_time = now
        if self._web_view:
            try:
                lv = max(0.0, min(1.0, float(level)))
                page = self._web_view.page()
                if page:
                    page.runJavaScript(f"if(window.setAudioLevel) window.setAudioLevel({lv:.3f});")
            except Exception:
                pass

    def set_pointer_norm(self, nx: float, ny: float) -> None:
        if self._web_view:
            try:
                page = self._web_view.page()
                if page:
                    page.runJavaScript(f"if(window.setPointerNorm) window.setPointerNorm({nx:.4f}, {ny:.4f});")
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        if self._web_view is None and WEB_ENGINE_AVAILABLE:
            self._init_web_engine()
        elif self._web_view and self.width() > 0 and self.height() > 0:
            self._web_view.setGeometry(self.rect())
            self._web_view.lower()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._web_view is None and WEB_ENGINE_AVAILABLE:
            self._init_web_engine()
        elif self._web_view and self.width() > 0 and self.height() > 0:
            self._web_view.setGeometry(self.rect())
            self._web_view.lower()

    def paintEvent(self, event):
        if not self._web_view:
            painter = QPainter(self)
            rect = self.rect()
            if self._fallback_pixmap and not self._fallback_pixmap.isNull():
                painter.fillRect(rect, QColor(0, 0, 0))
                scaled = self._fallback_pixmap.scaled(
                    rect.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = rect.x() + (rect.width() - scaled.width()) // 2
                y = rect.y() + (rect.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            else:
                painter.fillRect(rect, QColor(0, 0, 0))
            painter.end()
            return
        super().paintEvent(event)

class RemoteKeyOverlay(QWidget):
    closed = pyqtSignal()

    def __init__(self, url: str, key: str, auto: str, manual: str, parent=None):
        super().__init__(parent)
        self._on_new_key = None
        self._manual_url = manual or url
        self._auto_login_url = auto or url
        self._expiry = time.time() + 600

        # modern glassmorphism panel
        frame = QFrame(self)
        frame.setObjectName("RemoteOverlayMainFrame")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(16)
        
        try:
            self.setFixedSize(560, 680)
            frame.setFixedSize(self.size())
        except Exception:
            self.setFixedSize(520, 640)
            frame.setFixedSize(self.size())
            
        frame.setStyleSheet(f"""
            QFrame#RemoteOverlayMainFrame {{
                background: rgba(10, 12, 18, 250);
                border: 1px solid C.TEXT;
                border-radius: 24px;
            }}
        """)
        
        # elegant shadow
        try:
            glow = QGraphicsDropShadowEffect(self)
            glow.setBlurRadius(60)
            glow.setColor(QColor(0, 0, 0, 180))
            glow.setOffset(0, 12)
            frame.setGraphicsEffect(glow)
        except Exception:
            pass

        title = QLabel("Mobile Connect")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Exo 2", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        lay.addWidget(title)

        subtitle = QLabel("Scan the QR code with your phone to remotely control Stella.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setFont(QFont("Exo 2", 9))
        subtitle.setStyleSheet(f"color: {C.TEXT_DIM}; border: none; margin-bottom: 10px;")
        lay.addWidget(subtitle)

        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setFixedSize(240, 240)
        self._qr_label.setStyleSheet("background: white; border-radius: 12px; padding: 12px; border: none;")
        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(self._qr_label)
        qr_row.addStretch()
        lay.addLayout(qr_row)

        manual_hint = QLabel("Manual address")
        manual_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        manual_hint.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        manual_hint.setStyleSheet(f"color: {C.TEXT_DIM}; border: none; margin-top: 10px;")
        lay.addWidget(manual_hint)

        self._url_lbl = QLabel(self._manual_url)
        self._url_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._url_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._url_lbl.setFont(QFont("Consolas", 10))
        self._url_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: C.TEXT; border: 1px solid C.TEXT; border-radius: 8px; padding: 6px;")
        lay.addWidget(self._url_lbl)

        self._key_lbl = QLabel(key)
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._key_lbl.setFont(QFont("Consolas", 36, QFont.Weight.Black))
        self._key_lbl.setStyleSheet(f"""
            color: #7C6EE6;
            background: rgba(124, 110, 230, 0.05);
            border: 1px solid rgba(124, 110, 230, 0.2);
            border-radius: 16px;
            padding: 18px;
            letter-spacing: 14px;
            font-weight: 900;
            margin-top: 12px;
            margin-bottom: 8px;
        """)
        lay.addWidget(self._key_lbl)

        self._timer_lbl = QLabel("")
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer_lbl.setFont(QFont("Exo 2", 8))
        self._timer_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; border: none;")
        lay.addWidget(self._timer_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)
        
        self._new_btn = QPushButton("New Key")
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.setFixedHeight(40)
        self._new_btn.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._new_btn.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 12px;
            }}
            QPushButton:hover {{ 
                background: rgba(124, 110, 230, 0.08); 
                border: 1px solid rgba(124, 110, 230, 0.3);
                color: #7C6EE6;
            }}
        """)
        self._new_btn.clicked.connect(self._refresh_key)
        btn_row.addWidget(self._new_btn)

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedHeight(40)
        close_btn.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 12px;
            }}
            QPushButton:hover {{ 
                background: rgba(255, 60, 60, 0.08); 
                border: 1px solid rgba(255, 60, 60, 0.3);
                color: #FF6B6B;
            }}
        """)
        close_btn.clicked.connect(self._do_close)
        btn_row.addWidget(close_btn)
        
        lay.addLayout(btn_row)

        self._ctimer = QTimer(self)
        self._ctimer.timeout.connect(self._tick)
        self._ctimer.start(1000)
        self._update_qr(self._auto_login_url)
        self._tick()

        self.adjustSize()
        try:
            self.setFixedSize(max(360, self.width()), max(360, self.height()))
        except Exception:
            self.setFixedSize(420, 520)

    def set_new_key_callback(self, fn) -> None:
        self._on_new_key = fn

    def _update_qr(self, url: str) -> None:
        if not url:
            self._qr_label.setText("NO URL")
            return
        try:
            import qrcode
            from io import BytesIO
            qr = qrcode.QRCode(box_size=5, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            pix = QPixmap()
            pix.loadFromData(buf.getvalue())
            self._qr_label.setPixmap(pix.scaled(172, 172, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except ImportError:
            self._qr_label.setText("Install\nqrcode[pil]")
            self._qr_label.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
            self._qr_label.setStyleSheet("color: #111; background: white; border-radius: 12px; padding: 6px;")
        except Exception:
            self._qr_label.setText("QR failed")

    def _tick(self):
        remaining = max(0, int(self._expiry - time.time()))
        mins, secs = divmod(remaining, 60)
        self._timer_lbl.setText(f"Key expires in {mins:02d}:{secs:02d}")
        if remaining <= 0:
            self._do_close()

    def mark_connected(self) -> None:
        self._ctimer.stop()
        self._key_lbl.setText("CONNECTED")
        self._key_lbl.setStyleSheet(f"""
            color: {C.GREEN};
            background: rgba(55,255,95,20);
            border: 1px solid rgba(55,255,95,150);
            border-radius: 10px;
            padding: 8px;
            letter-spacing: 4px;
        """)
        self._qr_label.setText("OK")
        self._qr_label.setFont(QFont("Orbitron", 34, QFont.Weight.Black))
        self._qr_label.setStyleSheet("color: #37FF5F; background: #041006; border-radius: 12px;")
        self._timer_lbl.setText("Phone connected. Stella remote is ready.")

    def _refresh_key(self):
        if not self._on_new_key:
            return
        result = self._on_new_key()
        if not result:
            return
        url = result[0]
        key = result[1]
        auto = result[2] if len(result) >= 3 else url
        manual = result[3] if len(result) >= 4 else url
        self._manual_url = manual or url
        self._auto_login_url = auto or url
        self._url_lbl.setText(self._manual_url)
        self._key_lbl.setText(key)
        self._key_lbl.setStyleSheet(f"""
            color: {C.WHITE};
            background: rgba(124, 110, 230,28);
            border: 1px solid {C.PRI};
            border-radius: 10px;
            padding: 8px;
            letter-spacing: 9px;
        """)
        self._update_qr(self._auto_login_url)
        self._expiry = time.time() + 600
        self._ctimer.start(1000)
        self._tick()

    def _do_close(self):
        self._ctimer.stop()
        self.hide()
        self.closed.emit()

class DailyBriefingOverlay(QWidget):
    closed = pyqtSignal()

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        import datetime

        if isinstance(data, str):
            self._data = {
                "greeting": "Daily Briefing",
                "timestamp": datetime.datetime.now().strftime("%A, %B %d • %I:%M %p"),
                "spoken_narrative": data,
                "weather": {"status": "info", "temp_c": "--", "condition": "Atmospheric data", "city": "Local"},
                "calendar": {"count": 0, "events": []},
                "gmail": {"count": 0, "senders": []},
                "instagram": {"count": 0, "senders": []},
                "headlines": [],
            }
        elif isinstance(data, dict):
            self._data = data
        else:
            self._data = {}

        self._remaining_secs = 30
        self.setFixedSize(720, 540)

        # Glassmorphism container
        self._frame = QFrame(self)
        self._frame.setObjectName("BriefingOverlayMainFrame")
        self._frame.setFixedSize(self.size())
        self._frame.setStyleSheet(f"""
            QFrame#BriefingOverlayMainFrame {{
                background: rgba(10, 12, 18, 250);
                border: 1px solid rgba(124, 110, 230, 0.4);
                border-radius: 20px;
            }}
        """)

        try:
            glow = QGraphicsDropShadowEffect(self)
            glow.setBlurRadius(50)
            glow.setColor(QColor(0, 0, 0, 220))
            glow.setOffset(0, 10)
            self._frame.setGraphicsEffect(glow)
        except Exception:
            pass

        main_lay = QVBoxLayout(self._frame)
        main_lay.setContentsMargins(24, 20, 24, 20)
        main_lay.setSpacing(14)

        # Header Row
        hdr_lay = QHBoxLayout()
        hdr_lay.setSpacing(12)

        hdr_info = QVBoxLayout()
        hdr_info.setSpacing(2)

        title_lbl = QLabel("⚡ STELLA INTELLIGENCE // UNIFIED MORNING BRIEFING")
        title_lbl.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {C.PRI}; letter-spacing: 1.5px; background: transparent; border: none;")
        hdr_info.addWidget(title_lbl)

        ts_str = self._data.get("timestamp") or datetime.datetime.now().strftime("%A, %B %d • %I:%M %p")
        ts_lbl = QLabel(ts_str)
        ts_lbl.setFont(QFont("Exo 2", 9))
        ts_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        hdr_info.addWidget(ts_lbl)

        hdr_lay.addLayout(hdr_info)
        hdr_lay.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.TEXT_DIM};
                border: 1px solid C.TEXT;
                border-radius: 16px;
            }}
            QPushButton:hover {{
                background: rgba(255, 60, 60, 0.2);
                border: 1px solid rgba(255, 60, 60, 0.5);
                color: #FF5555;
            }}
        """)
        close_btn.clicked.connect(self._do_close)
        hdr_lay.addWidget(close_btn)

        main_lay.addLayout(hdr_lay)

        # 2x2 Bento Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. Weather Card
        grid.addWidget(self._build_weather_card(), 0, 0)
        # 2. Calendar Card
        grid.addWidget(self._build_calendar_card(), 0, 1)
        # 3. Gmail Card
        grid.addWidget(self._build_gmail_card(), 1, 0)
        # 4. Instagram Card
        grid.addWidget(self._build_instagram_card(), 1, 1)

        main_lay.addLayout(grid)

        # Spoken Narrative Box
        narrative_frame = QFrame()
        narrative_frame.setStyleSheet("""
            QFrame {
                background: C.BG;
                border: 1px solid C.TEXT;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        narr_lay = QVBoxLayout(narrative_frame)
        narr_lay.setContentsMargins(12, 10, 12, 10)
        narr_lay.setSpacing(4)

        narr_tag = QLabel("🎙 EXECUTIVE SUMMARY")
        narr_tag.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        narr_tag.setStyleSheet(f"color: {C.PRI}; letter-spacing: 1px; background: transparent; border: none;")
        narr_lay.addWidget(narr_tag)

        narrative_text = self._data.get("spoken_narrative") or "No briefing narrative generated."
        narr_lbl = QLabel(narrative_text)
        narr_lbl.setWordWrap(True)
        narr_lbl.setFont(QFont("Exo 2", 9))
        narr_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none; line-height: 1.4;")
        narr_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        narr_lay.addWidget(narr_lbl)

        main_lay.addWidget(narrative_frame)

        # Bottom Bar: Auto-dismiss countdown + action button
        bot_lay = QHBoxLayout()
        bot_lay.setSpacing(12)

        self._countdown_lbl = QLabel(f"Auto-dismissing in {self._remaining_secs}s")
        self._countdown_lbl.setFont(QFont("Exo 2", 8))
        self._countdown_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        bot_lay.addWidget(self._countdown_lbl)

        bot_lay.addStretch()

        dismiss_btn = QPushButton("DISMISS")
        dismiss_btn.setFixedSize(100, 30)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss_btn.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(124, 110, 230, 0.12);
                color: {C.PRI};
                border: 1px solid rgba(124, 110, 230, 0.35);
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.25);
                border: 1px solid {C.PRI};
            }}
        """)
        dismiss_btn.clicked.connect(self._do_close)
        bot_lay.addWidget(dismiss_btn)

        main_lay.addLayout(bot_lay)

        # Auto-hide timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _create_bento_box(self) -> QFrame:
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background: C.TEXT;
                border: 1px solid rgba(124, 110, 230, 0.18);
                border-radius: 12px;
            }
        """)
        return box

    def _build_weather_card(self) -> QFrame:
        box = self._create_bento_box()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)

        w = self._data.get("weather") or {}
        tag = QLabel("🌤  ATMOSPHERE & WEATHER")
        tag.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        tag.setStyleSheet(f"color: {C.PRI}; letter-spacing: 1px; background: transparent; border: none;")
        lay.addWidget(tag)

        temp = w.get("temp_c")
        temp_str = f"{temp}°C" if temp is not None else "--°C"
        cond = w.get("condition") or "Clear"
        city = w.get("city") or "Local Station"

        val_row = QHBoxLayout()
        val_lbl = QLabel(temp_str)
        val_lbl.setFont(QFont("Exo 2", 20, QFont.Weight.Bold))
        val_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
        val_row.addWidget(val_lbl)

        cond_lbl = QLabel(f"{cond}\n{city}")
        cond_lbl.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        cond_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        cond_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_row.addWidget(cond_lbl)
        lay.addLayout(val_row)

        hum = w.get("humidity", "--")
        wind = w.get("wind_kmph", "--")
        meta_lbl = QLabel(f"Humidity: {hum}% • Wind: {wind} km/h")
        meta_lbl.setFont(QFont("Exo 2", 8))
        meta_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        lay.addWidget(meta_lbl)
        return box

    def _build_calendar_card(self) -> QFrame:
        box = self._create_bento_box()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)

        cal = self._data.get("calendar") or {}
        tag = QLabel("📅  TODAY'S AGENDA")
        tag.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        tag.setStyleSheet(f"color: {C.PRI}; letter-spacing: 1px; background: transparent; border: none;")
        lay.addWidget(tag)

        count = cal.get("count", 0)
        events = cal.get("events", [])

        if count > 0:
            val_lbl = QLabel(f"{count} Event{'s' if count > 1 else ''}")
            val_lbl.setFont(QFont("Exo 2", 20, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
            lay.addWidget(val_lbl)

            evt_summary = events[0] if len(events) == 1 else f"{events[0]} (+{len(events)-1} more)"
            sub_lbl = QLabel(evt_summary[:38] + ("..." if len(evt_summary) > 38 else ""))
            sub_lbl.setFont(QFont("Exo 2", 8))
            sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
            lay.addWidget(sub_lbl)
        else:
            val_lbl = QLabel("Clear Schedule")
            val_lbl.setFont(QFont("Exo 2", 18, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
            lay.addWidget(val_lbl)

            sub_lbl = QLabel("No events booked today")
            sub_lbl.setFont(QFont("Exo 2", 8))
            sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
            lay.addWidget(sub_lbl)

        meta_lbl = QLabel("Google Calendar Active")
        meta_lbl.setFont(QFont("Exo 2", 8))
        meta_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        lay.addWidget(meta_lbl)
        return box

    def _build_gmail_card(self) -> QFrame:
        box = self._create_bento_box()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)

        gm = self._data.get("gmail") or {}
        tag = QLabel("✉  GMAIL COMMUNICATIONS")
        tag.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        tag.setStyleSheet(f"color: {C.PRI}; letter-spacing: 1px; background: transparent; border: none;")
        lay.addWidget(tag)

        count = gm.get("count", 0)
        senders = gm.get("senders", [])

        if count > 0:
            val_lbl = QLabel(f"{count} Unread")
            val_lbl.setFont(QFont("Exo 2", 20, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
            lay.addWidget(val_lbl)

            if senders:
                s_str = f"From: {', '.join(senders[:2])}"
                if len(senders) > 2:
                    s_str += f" +{len(senders)-2}"
            else:
                s_str = "Unread messages awaiting review"
            sub_lbl = QLabel(s_str[:38] + ("..." if len(s_str) > 38 else ""))
            sub_lbl.setFont(QFont("Exo 2", 8))
            sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
            lay.addWidget(sub_lbl)
        else:
            val_lbl = QLabel("Inbox Zero")
            val_lbl.setFont(QFont("Exo 2", 18, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
            lay.addWidget(val_lbl)

            sub_lbl = QLabel("All communications caught up")
            sub_lbl.setFont(QFont("Exo 2", 8))
            sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
            lay.addWidget(sub_lbl)

        meta_lbl = QLabel("Google Workspace Connected")
        meta_lbl.setFont(QFont("Exo 2", 8))
        meta_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        lay.addWidget(meta_lbl)
        return box

    def _build_instagram_card(self) -> QFrame:
        box = self._create_bento_box()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)

        ig = self._data.get("instagram") or {}
        tag = QLabel("📸  INSTAGRAM INTEL")
        tag.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        tag.setStyleSheet(f"color: {C.PRI}; letter-spacing: 1px; background: transparent; border: none;")
        lay.addWidget(tag)

        count = ig.get("count", 0)
        senders = ig.get("senders", [])

        if count > 0:
            val_lbl = QLabel(f"{count} New DM{'s' if count > 1 else ''}")
            val_lbl.setFont(QFont("Exo 2", 20, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
            lay.addWidget(val_lbl)

            if senders:
                s_str = f"From: {', '.join(['@' + s for s in senders[:2]])}"
                if len(senders) > 2:
                    s_str += f" +{len(senders)-2}"
            else:
                s_str = "Direct messages awaiting review"
            sub_lbl = QLabel(s_str[:38] + ("..." if len(s_str) > 38 else ""))
            sub_lbl.setFont(QFont("Exo 2", 8))
            sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
            lay.addWidget(sub_lbl)
        else:
            val_lbl = QLabel("0 Direct Messages")
            val_lbl.setFont(QFont("Exo 2", 18, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {C.TEXT}; background: transparent; border: none;")
            lay.addWidget(val_lbl)

            sub_lbl = QLabel("No pending notifications")
            sub_lbl.setFont(QFont("Exo 2", 8))
            sub_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
            lay.addWidget(sub_lbl)

        meta_lbl = QLabel("Instagram Browser Engine Ready")
        meta_lbl.setFont(QFont("Exo 2", 8))
        meta_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        lay.addWidget(meta_lbl)
        return box

    def _tick(self):
        self._remaining_secs -= 1
        if self._remaining_secs <= 0:
            self._do_close()
        else:
            self._countdown_lbl.setText(f"Auto-dismissing in {self._remaining_secs}s")

    def _do_close(self):
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        self.hide()
        self.closed.emit()

class ConfirmationOverlay(QWidget):
    """Physical confirmation gate for irreversible actions (shutdown, restart, wifi toggles)."""
    answered = pyqtSignal(bool)
    closed   = pyqtSignal()
    _OW = 440

    def __init__(self, title: str, detail: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ConfirmationOverlay {{
                background: rgba(18, 10, 4, 250);
                border: 2px solid {C.ACC};
                border-radius: 12px;
            }}
        """)
        self.setFixedWidth(self._OW)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)

        hdr = QLabel("⚠  PHYSICAL CONFIRMATION REQUIRED")
        hdr.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.ACC}; background: transparent; letter-spacing: 0.5px;")
        lay.addWidget(hdr)

        ttl = QLabel(title)
        ttl.setWordWrap(True)
        ttl.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        ttl.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        lay.addWidget(ttl)

        if detail:
            dtl = QLabel(detail)
            dtl.setWordWrap(True)
            dtl.setFont(QFont("Exo 2", 9))
            dtl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            lay.addWidget(dtl)

        self._remaining_secs = 90
        self._countdown_lbl = QLabel(f"Confirmation auto-cancels in {self._remaining_secs}s")
        self._countdown_lbl.setFont(QFont("Exo 2", 8))
        self._countdown_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addWidget(self._countdown_lbl)

        row = QHBoxLayout()
        row.setSpacing(10)

        yes = QPushButton("CONFIRM")
        yes.setFixedHeight(36)
        yes.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        yes.setCursor(Qt.CursorShape.PointingHandCursor)
        yes.setStyleSheet(f"""
            QPushButton {{
                background: rgba(124, 110, 230, 0.15);
                color: {C.ACC};
                border: 1.5px solid {C.ACC};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.35);
                color: {C.WHITE};
            }}
        """)
        yes.clicked.connect(self._on_confirm)
        row.addWidget(yes)

        no = QPushButton("CANCEL")
        no.setFixedHeight(36)
        no.setFont(QFont("Exo 2", 9))
        no.setCursor(Qt.CursorShape.PointingHandCursor)
        no.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.TEXT_MED};
                border: 1px solid {C.BORDER};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                color: {C.TEXT};
                border-color: {C.BORDER_B};
                background: C.TEXT;
            }}
        """)
        no.clicked.connect(self._on_cancel)
        row.addWidget(no)
        lay.addLayout(row)

        no.setDefault(True)
        no.setFocus()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._remaining_secs -= 1
        if self._remaining_secs <= 0:
            self._on_cancel()
        else:
            self._countdown_lbl.setText(f"Confirmation auto-cancels in {self._remaining_secs}s")

    def _on_confirm(self):
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        self.hide()
        self.answered.emit(True)
        self.closed.emit()

    def _on_cancel(self):
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        self.hide()
        self.answered.emit(False)
        self.closed.emit()

class MemoryInspectorOverlay(QWidget):
    """HUD overlay inspecting long-term stored facts, with instant search and manual deletion."""
    closed = pyqtSignal()
    _OW = 560

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            MemoryInspectorOverlay {{
                background: rgba(8, 10, 15, 250);
                border: 1.5px solid {C.BORDER_B};
                border-radius: 12px;
            }}
        """)
        self.setFixedWidth(self._OW)

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(24, 20, 24, 20)
        self._lay.setSpacing(10)
        self._filter_query = ""
        self._rebuild()

    def _rebuild(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                while sub.count():
                    si = sub.takeAt(0)
                    sw = si.widget()
                    if sw is not None:
                        sw.hide()
                        sw.deleteLater()
                sub.deleteLater()

        from memory.memory_manager import all_entries_for_ui

        hdr = QLabel("🧠  WHAT STELLA REMEMBERS")
        hdr.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 0.5px;")
        self._lay.addWidget(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        self._lay.addWidget(sep)

        rows = all_entries_for_ui()
        if self._filter_query:
            q = self._filter_query.lower()
            rows = [r for r in rows if q in r.get("key", "").lower() or q in r.get("value", "").lower() or q in r.get("category", "").lower()]

        cap = QLabel(
            f"{len(rows)} stored memory entries. Stored locally in memory/long_term.json. "
            f"Stella recalls these during relevant conversations."
        )
        cap.setWordWrap(True)
        cap.setFont(QFont("Exo 2", 8))
        cap.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._lay.addWidget(cap)

        s_row = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("Filter memories (e.g. coffee, name, work, python)...")
        search_input.setText(self._filter_query)
        search_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(20, 24, 32, 220);
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        search_input.textChanged.connect(self._on_search_changed)
        s_row.addWidget(search_input)
        self._lay.addLayout(s_row)

        if not rows:
            empty = QLabel("No matching memories found.")
            empty.setFont(QFont("Exo 2", 10))
            empty.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; padding: 20px 0;")
            self._lay.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFixedHeight(min(380, 42 * len(rows) + 20))
            scroll.setStyleSheet(
                f"QScrollArea {{ border: 1px solid {C.BORDER}; border-radius: 6px; "
                f"background: rgba(12, 15, 20, 180); }}"
            )
            inner = QWidget()
            inner.setStyleSheet("background: transparent;")
            ilay = QVBoxLayout(inner)
            ilay.setContentsMargins(8, 8, 8, 8)
            ilay.setSpacing(6)

            for r in rows:
                line = QHBoxLayout()
                line.setSpacing(8)

                txt = QLabel(f"<b>{r['key'].replace('_', ' ')}</b>: <span style='color:{C.TEXT_MED}'>{r['value']}</span>")
                txt.setWordWrap(True)
                txt.setFont(QFont("Exo 2", 9))
                txt.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
                line.addWidget(txt, 1)

                meta = QLabel(f"{r['category'][:4].upper()} · {r.get('updated') or '—'}")
                meta.setFont(QFont("Exo 2", 8))
                meta.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
                line.addWidget(meta)

                rm = QPushButton("✕")
                rm.setFixedSize(22, 22)
                rm.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
                rm.setCursor(Qt.CursorShape.PointingHandCursor)
                rm.setToolTip("Forget this fact")
                rm.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER};
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        color: {C.RED};
                        border-color: {C.RED};
                        background: rgba(255, 59, 48, 0.15);
                    }}
                """)
                rm.clicked.connect(lambda _=False, c=r["category"], k=r["key"]: self._forget(c, k))
                line.addWidget(rm)

                holder = QWidget()
                holder.setLayout(line)
                ilay.addWidget(holder)

            ilay.addStretch()
            scroll.setWidget(inner)
            self._lay.addWidget(scroll)

        close = QPushButton("CLOSE")
        close.setFixedHeight(34)
        close.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.TEXT_MED};
                border: 1px solid {C.BORDER};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                color: {C.WHITE};
                border-color: {C.BORDER_B};
                background: rgba(124, 110, 230, 0.15);
            }}
        """)
        close.clicked.connect(self._do_close)
        self._lay.addWidget(close)

        self.adjustSize()
        p = self.parentWidget()
        if p is not None:
            self.move(max(16, (p.width() - self.width()) // 2), max(16, (p.height() - self.height()) // 2))

    def _on_search_changed(self, text: str):
        self._filter_query = text.strip()
        self._rebuild()

    def _forget(self, category: str, key: str):
        from memory.memory_manager import forget
        forget(key, category)
        QTimer.singleShot(0, self._rebuild)

    def _do_close(self):
        self.hide()
        self.closed.emit()

class SetupOverlay(QWidget):
    done = pyqtSignal(str, str, str)

    def __init__(self, parent=None, defaults: dict | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        self._defaults = defaults or {}
        self._detected = {"darwin": "mac", "windows": "windows"}.get(_OS.lower(), "linux")
        self._sel_os = self._defaults.get("os_system", self._detected)

        self._stack = QStackedWidget(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._stack)

        self._build_stage1()
        self._build_stage_identity()
        self._build_stage_owner()
        self._build_stage_behavior()
        self._build_stage_shared()
        self._build_stage2()
        self._build_stage3()
        self._build_stage4()

        self._stack.setCurrentIndex(0)
        QTimer.singleShot(1000, self._start_stage1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Heavy dark overlay to completely hide dashboard UI and make a full faded background
        painter.fillRect(self.rect(), QColor(3, 5, 8, 245))

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # Add a subtle gold vignette ring over the full faded background
        ring_grad = QRadialGradient(cx, cy, 320.0)
        ring_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        ring_grad.setColorAt(0.7, QColor(0, 0, 0, 0))
        ring_grad.setColorAt(0.85, QColor(124, 110, 230, 12))
        ring_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(ring_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 320.0, 320.0)

    def _call_js(self, func_call):
        try:
            p = self.parentWidget()
            while p is not None:
                if hasattr(p, '_background'):
                    p._background.page().runJavaScript(func_call)
                    return
                p = p.parentWidget()
        except Exception:
            pass

    # ── STAGE 1: System Check ──────────────────────────────────────
    def _build_stage1(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        # Push text to the bottom half (below reactor)
        lay.addStretch(3)

        self._s1_container = QFrame()
        self._s1_container.setStyleSheet("""
            QFrame {
                background: rgba(5, 8, 12, 180);
                border: 1px solid rgba(124, 110, 230, 0.08);
                border-radius: 16px;
            }
        """)
        self._s1_container.setFixedWidth(420)
        clay = QVBoxLayout(self._s1_container)
        clay.setContentsMargins(30, 24, 30, 24)
        clay.setSpacing(0)

        self._s1_lbl = QLabel("")
        self._s1_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._s1_lbl.setFont(QFont("Consolas", 12))
        self._s1_lbl.setStyleSheet("color: rgba(124, 110, 230, 0.9); background: transparent; border: none;")
        self._s1_lbl.setWordWrap(True)
        clay.addWidget(self._s1_lbl)

        lay.addWidget(self._s1_container, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(1)
        self._stack.addWidget(page)

    def _start_stage1(self):
        self._s1_lines = [
            ("Scanning local configuration...", "#7C6EE6", False),
            ("✓  " + self._detected.capitalize() + " detected", "#37FF5F", False),
            ("✓  GPU acceleration enabled", "#37FF5F", False),
            ("✓  Network online", "#37FF5F", False),
            ("Looking for AI provider...", "#7C6EE6", False),
            ("✕  No provider configured", "#FF3B30", True),
            ("", "", False),
            ("One final step is required\nbefore I can think.", "C.TEXT", True),
        ]
        self._s1_idx = 0
        self._s1_text_parts = []
        self._s1_timer = QTimer(self)
        self._s1_timer.timeout.connect(self._s1_tick)
        self._s1_timer.start(900)
        self._s1_tick()

    def _s1_tick(self):
        if self._s1_idx < len(self._s1_lines):
            line_text, color, is_special = self._s1_lines[self._s1_idx]

            if line_text == "":
                self._s1_idx += 1
                return

            if is_special and "✕" in line_text:
                self._call_js("if(window.losePower) window.losePower();")
            elif is_special and "final step" in line_text:
                self._call_js("if(window.triggerPulse) window.triggerPulse();")

            size = "14px" if is_special and "final" in line_text else "12px"
            weight = "bold" if is_special else "normal"
            spacing = "margin-top: 16px;" if is_special and "final" in line_text else "margin-top: 4px;"

            self._s1_text_parts.append(
                f'<div style="color:{color}; font-size:{size}; font-weight:{weight}; font-family:Consolas; {spacing}">{line_text}</div>'
            )
            self._s1_lbl.setText("".join(self._s1_text_parts))

            self._s1_idx += 1
        else:
            self._s1_timer.stop()
            QTimer.singleShot(2500, self._finish_stage1)

    # ── STAGE 2: Provider Selection ────────────────────────────────

    # ── STAGE 1.1: Assistant Identity ────────────────────────────────
    def _build_stage_identity(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(2)

        title = QLabel("DEFINE YOUR ASSISTANT")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: C.TEXT; background: transparent; letter-spacing: 2px;")
        lay.addWidget(title)
        
        sub = QLabel("Every assistant needs an identity.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Exo 2", 10))
        sub.setStyleSheet("color: C.TEXT; background: transparent;")
        lay.addWidget(sub)
        lay.addSpacing(20)

        form_lay = QGridLayout()
        form_lay.setSpacing(16)
        
        lbl_ast = QLabel("Assistant Name")
        lbl_ast.setStyleSheet("color: #FFAA30;")
        self._inp_ast = QLineEdit(identity.get_assistant_name())
        self._inp_ast.setStyleSheet("background: C.TEXT; color: #fff; padding: 6px; border-radius: 4px;")
        form_lay.addWidget(lbl_ast, 0, 0)
        form_lay.addWidget(self._inp_ast, 0, 1)

        lbl_app = QLabel("Application Name")
        lbl_app.setStyleSheet("color: #FFAA30;")
        self._inp_app = QLineEdit(identity.get_application_name())
        self._inp_app.setStyleSheet("background: C.TEXT; color: #fff; padding: 6px; border-radius: 4px;")
        form_lay.addWidget(lbl_app, 1, 0)
        form_lay.addWidget(self._inp_app, 1, 1)

        container = QWidget()
        container.setFixedWidth(400)
        container.setLayout(form_lay)
        lay.addWidget(container, 0, Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("CONTINUE →")
        btn.setFixedSize(160, 40)
        btn.setStyleSheet("background: rgba(255, 170, 48, 0.2); color: #FFAA30; border: 1px solid #FFAA30; border-radius: 20px;")
        btn.clicked.connect(self._save_identity_and_next)
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        lay.addStretch(2)
        self._stack.addWidget(page)

    def _save_identity_and_next(self):
        identity.set_assistant_name(self._inp_ast.text().strip() or "Stella")
        identity.set_application_name(self._inp_app.text().strip() or "Stella")
        self._stack.setCurrentIndex(2)

    # ── STAGE 1.2: Owner Profile ────────────────────────────────
    def _build_stage_owner(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(2)

        title = QLabel("WHO AM I ASSISTING?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: C.TEXT; background: transparent; letter-spacing: 2px;")
        lay.addWidget(title)
        
        sub = QLabel("Tell me a little about yourself so I can work better with you.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Exo 2", 10))
        sub.setStyleSheet("color: C.TEXT; background: transparent;")
        lay.addWidget(sub)
        lay.addSpacing(20)

        form_lay = QGridLayout()
        form_lay.setSpacing(16)
        
        lbl_own = QLabel("Your Name")
        lbl_own.setStyleSheet("color: #FFAA30;")
        self._inp_own = QLineEdit(identity.get_owner_name())
        self._inp_own.setStyleSheet("background: C.TEXT; color: #fff; padding: 6px; border-radius: 4px;")
        form_lay.addWidget(lbl_own, 0, 0)
        form_lay.addWidget(self._inp_own, 0, 1)

        lbl_role = QLabel("Your Role")
        lbl_role.setStyleSheet("color: #FFAA30;")
        self._inp_role = QLineEdit(identity.get_owner_role())
        self._inp_role.setPlaceholderText("e.g. Student, Developer")
        self._inp_role.setStyleSheet("background: C.TEXT; color: #fff; padding: 6px; border-radius: 4px;")
        form_lay.addWidget(lbl_role, 1, 0)
        form_lay.addWidget(self._inp_role, 1, 1)

        container = QWidget()
        container.setFixedWidth(400)
        container.setLayout(form_lay)
        lay.addWidget(container, 0, Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("CONTINUE →")
        btn.setFixedSize(160, 40)
        btn.setStyleSheet("background: rgba(255, 170, 48, 0.2); color: #FFAA30; border: 1px solid #FFAA30; border-radius: 20px;")
        btn.clicked.connect(self._save_owner_and_next)
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        lay.addStretch(2)
        self._stack.addWidget(page)

    def _save_owner_and_next(self):
        identity.set_owner_name(self._inp_own.text().strip())
        identity.set_owner_role(self._inp_role.text().strip())
        self._stack.setCurrentIndex(3)

    # ── STAGE 1.3: Behavior ────────────────────────────────
    def _build_stage_behavior(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(2)

        title = QLabel("HOW SHOULD I ASSIST YOU?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: C.TEXT; background: transparent; letter-spacing: 2px;")
        lay.addWidget(title)
        lay.addSpacing(20)

        self._combo_mode = QComboBox()
        self._combo_mode.addItems(["professional", "casual", "technical", "minimal", "proactive"])
        self._combo_mode.setCurrentText(identity.get_behavior_mode())
        self._combo_mode.setStyleSheet("background: C.TEXT; color: #fff; padding: 6px; border-radius: 4px;")
        self._combo_mode.setFixedWidth(300)
        lay.addWidget(self._combo_mode, 0, Qt.AlignmentFlag.AlignCenter)
        
        sub = QLabel("Custom Instructions (Optional)")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #FFAA30; margin-top: 10px;")
        lay.addWidget(sub)
        
        self._inp_custom = QTextEdit(identity.get_custom_instructions())
        self._inp_custom.setFixedSize(400, 80)
        self._inp_custom.setStyleSheet("background: C.TEXT; color: #fff; padding: 6px; border-radius: 4px;")
        lay.addWidget(self._inp_custom, 0, Qt.AlignmentFlag.AlignCenter)

        lay.addSpacing(20)
        btn = QPushButton("CONTINUE →")
        btn.setFixedSize(160, 40)
        btn.setStyleSheet("background: rgba(255, 170, 48, 0.2); color: #FFAA30; border: 1px solid #FFAA30; border-radius: 20px;")
        btn.clicked.connect(self._save_behavior_and_next)
        lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        lay.addStretch(2)
        self._stack.addWidget(page)

    def _save_behavior_and_next(self):
        identity.set_behavior_mode(self._combo_mode.currentText())
        identity.set_custom_instructions(self._inp_custom.toPlainText().strip())
        self._stack.setCurrentIndex(4)

    # ── STAGE 1.4: Shared Computer ────────────────────────────────
    def _build_stage_shared(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(2)

        title = QLabel("WHO USES THIS COMPUTER?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: C.TEXT; background: transparent; letter-spacing: 2px;")
        lay.addWidget(title)
        lay.addSpacing(20)
        
        btn_personal = QPushButton("THIS IS MY PERSONAL COMPUTER")
        btn_personal.setFixedSize(300, 50)
        btn_personal.setStyleSheet("background: rgba(255, 170, 48, 0.1); color: #FFAA30; border: 1px solid #FFAA30; border-radius: 8px;")
        btn_personal.clicked.connect(lambda: self._save_shared_and_next(False))
        lay.addWidget(btn_personal, 0, Qt.AlignmentFlag.AlignCenter)
        
        lay.addSpacing(10)
        
        btn_shared = QPushButton("THIS IS A SHARED COMPUTER")
        btn_shared.setFixedSize(300, 50)
        btn_shared.setStyleSheet("background: C.TEXT; color: #fff; border: 1px solid C.TEXT; border-radius: 8px;")
        btn_shared.clicked.connect(lambda: self._save_shared_and_next(True))
        lay.addWidget(btn_shared, 0, Qt.AlignmentFlag.AlignCenter)
        
        lay.addStretch(2)
        self._stack.addWidget(page)
        
    def _save_shared_and_next(self, shared: bool):
        identity.set_shared_computer(shared)
        self._stack.setCurrentIndex(5)


    def _finish_stage1(self):
        if not identity.is_setup_complete():
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(5)

    def _build_stage2(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addStretch(3)

        title = QLabel("SELECT PRIMARY INTELLIGENCE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: C.TEXT; background: transparent; border: none; letter-spacing: 4px;")
        lay.addWidget(title)
        lay.addSpacing(24)

        cards_lay = QHBoxLayout()
        cards_lay.setSpacing(20)
        cards_lay.addStretch()

        # ── Gemini Card ──
        gem_card = QFrame()
        gem_card.setFixedSize(260, 160)
        gem_card.setStyleSheet("""
            QFrame {
                background: rgba(124, 110, 230, 0.06);
                border: 1px solid rgba(124, 110, 230, 0.25);
                border-radius: 16px;
            }
            QFrame:hover {
                background: rgba(124, 110, 230, 0.12);
                border: 1px solid rgba(124, 110, 230, 0.5);
            }
        """)
        gem_card.setCursor(Qt.CursorShape.PointingHandCursor)
        glay = QVBoxLayout(gem_card)
        glay.setContentsMargins(22, 18, 22, 18)
        glay.setSpacing(4)

        gt = QLabel("Google Gemini")
        gt.setFont(QFont("Exo 2", 15, QFont.Weight.Bold))
        gt.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
        glay.addWidget(gt)

        gs = QLabel("★★★★★  Recommended")
        gs.setFont(QFont("Exo 2", 9))
        gs.setStyleSheet("color: rgba(124, 110, 230,0.7); background: transparent; border: none;")
        glay.addWidget(gs)

        gd = QLabel("Primary Intelligence")
        gd.setFont(QFont("Exo 2", 9))
        gd.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        glay.addWidget(gd)

        glay.addStretch()

        gc = QLabel("Connect →")
        gc.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        gc.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
        glay.addWidget(gc)

        # Make the whole card clickable via a transparent button overlay
        gem_btn = QPushButton(gem_card)
        gem_btn.setGeometry(0, 0, 260, 160)
        gem_btn.setStyleSheet("background: transparent; border: none;")
        gem_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gem_btn.clicked.connect(self._goto_stage3)

        cards_lay.addWidget(gem_card)

        # ── OpenRouter Card ──
        or_card = QFrame()
        or_card.setFixedSize(260, 160)
        or_card.setStyleSheet("""
            QFrame {
                background: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 16px;
            }
            QFrame:hover {
                background: C.TEXT;
                border: 1px solid C.TEXT;
            }
        """)
        or_card.setCursor(Qt.CursorShape.PointingHandCursor)
        olay = QVBoxLayout(or_card)
        olay.setContentsMargins(22, 18, 22, 18)
        olay.setSpacing(4)

        ot = QLabel("OpenRouter")
        ot.setFont(QFont("Exo 2", 15, QFont.Weight.Bold))
        ot.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        olay.addWidget(ot)

        od = QLabel("Multiple Models")
        od.setFont(QFont("Exo 2", 9))
        od.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        olay.addWidget(od)

        od2 = QLabel("Optional · Secondary")
        od2.setFont(QFont("Exo 2", 9))
        od2.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        olay.addWidget(od2)

        olay.addStretch()

        oc = QLabel("Configure Later →")
        oc.setFont(QFont("Exo 2", 11))
        oc.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        olay.addWidget(oc)

        cards_lay.addWidget(or_card)
        cards_lay.addStretch()

        lay.addLayout(cards_lay)
        lay.addStretch(1)
        self._stack.addWidget(page)

    def _goto_stage3(self):
        self._call_js("if(window.triggerPulse) window.triggerPulse();")
        self._stack.setCurrentIndex(6)

    # ── STAGE 3 & 4: API Input + Auth ──────────────────────────────
    def _build_stage3(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addStretch(3)

        self._s3_box = QFrame()
        self._s3_box.setFixedSize(480, 260)
        self._s3_box.setStyleSheet("""
            QFrame {
                background: rgba(8, 10, 16, 220);
                border: 1px solid rgba(124, 110, 230, 0.2);
                border-radius: 20px;
            }
        """)
        blay = QVBoxLayout(self._s3_box)
        blay.setContentsMargins(32, 28, 32, 28)
        blay.setSpacing(6)

        self._s3_title = QLabel("Google Gemini")
        self._s3_title.setFont(QFont("Exo 2", 18, QFont.Weight.Bold))
        self._s3_title.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
        blay.addWidget(self._s3_title)

        self._s3_sub = QLabel("Paste your Neural Key")
        self._s3_sub.setFont(QFont("Exo 2", 10))
        self._s3_sub.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        blay.addWidget(self._s3_sub)

        blay.addSpacing(16)

        # Input row
        input_row = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("Paste API key here...")
        self._key_input.setFont(QFont("Consolas", 12))
        self._key_input.setFixedHeight(48)
        self._key_input.setStyleSheet("""
            QLineEdit {
                background: rgba(124, 110, 230, 0.04);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.25);
                border-radius: 12px;
                padding: 0 16px;
                letter-spacing: 1px;
                selection-background-color: rgba(124, 110, 230, 0.3);
            }
            QLineEdit:focus {
                border: 1px solid rgba(124, 110, 230, 0.6);
                background: rgba(124, 110, 230, 0.06);
            }
        """)
        self._key_input.setText((self._defaults.get("gemini_api_key") or "").strip())
        self._key_input.textChanged.connect(self._on_key_changed)
        input_row.addWidget(self._key_input)

        toggle_pw = QPushButton("👁")
        toggle_pw.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_pw.setFixedSize(36, 48)
        toggle_pw.setStyleSheet("QPushButton { background: transparent; border: none; color: C.TEXT; font-size: 16px; } QPushButton:hover { color: #7C6EE6; }")
        def _toggle():
            if self._key_input.echoMode() == QLineEdit.EchoMode.Password:
                self._key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            else:
                self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        toggle_pw.clicked.connect(_toggle)
        input_row.addWidget(toggle_pw)
        blay.addLayout(input_row)

        # Status + link row
        status_row = QHBoxLayout()
        self._s3_status = QLabel("")
        self._s3_status.setFont(QFont("Consolas", 10))
        self._s3_status.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
        status_row.addWidget(self._s3_status)

        status_row.addStretch()

        hint = QLabel("<a href='https://aistudio.google.com/app/apikey' style='color: rgba(124, 110, 230,0.5); text-decoration: none; font-size: 10px;'>Get API Key →</a>")
        hint.setOpenExternalLinks(True)
        hint.setStyleSheet("background: transparent; border: none;")
        status_row.addWidget(hint)
        blay.addLayout(status_row)

        blay.addStretch()

        lay.addWidget(self._s3_box, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(1)

        # Intro page (hidden initially, will replace s3_box)
        self._intro_widget = QWidget(page)
        self._intro_widget.hide()
        intro_lay = QVBoxLayout(self._intro_widget)
        intro_lay.setContentsMargins(0, 0, 0, 0)
        intro_lay.setSpacing(12)

        self._intro_lines = []
        for txt in ["Identity confirmed.", "Hello.", "I'm Stella.", "Ready whenever you are."]:
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if txt == "I'm Stella.":
                lbl.setFont(QFont("Exo 2", 24, QFont.Weight.Bold))
                lbl.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
            else:
                lbl.setFont(QFont("Exo 2", 14))
                lbl.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
            lbl.hide()
            intro_lay.addWidget(lbl)
            self._intro_lines.append(lbl)

        intro_lay.addSpacing(20)

        self._launch_btn = QPushButton("Launch Stella →")
        self._launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._launch_btn.setFixedSize(220, 48)
        self._launch_btn.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        self._launch_btn.setStyleSheet("""
            QPushButton {
                background: rgba(124, 110, 230, 0.1);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.4);
                border-radius: 24px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230, 0.25);
                border: 1px solid #7C6EE6;
            }
        """)
        self._launch_btn.hide()
        self._launch_btn.clicked.connect(self._start_ignition)
        intro_lay.addWidget(self._launch_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self._stack.addWidget(page)

    def _on_key_changed(self, text):
        if len(text) > 10 and not hasattr(self, "_authenticating"):
            self._authenticating = True
            self._key_input.setReadOnly(True)
            self._s3_sub.setText("Authenticating...")
            self._s3_sub.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
            self._auth_step = 0
            self._auth_timer = QTimer(self)
            self._auth_timer.timeout.connect(self._auth_tick)
            self._auth_timer.start(250)

    def _auth_tick(self):
        bars = [
            "█░░░░░░░░░░░░░░",
            "████░░░░░░░░░░░",
            "████████░░░░░░░",
            "███████████░░░░",
            "███████████████",
        ]
        if self._auth_step < len(bars):
            self._s3_status.setText(bars[self._auth_step])
            if self._auth_step % 2 == 0:
                self._call_js("if(window.triggerPulse) window.triggerPulse();")
            self._auth_step += 1
        else:
            self._auth_timer.stop()
            self._s3_status.setText("✓ Identity Verified")
            self._s3_status.setStyleSheet("color: #37FF5F; background: transparent; border: none;")
            self._s3_title.setText("✓ Google Gemini")
            self._s3_title.setStyleSheet("color: #37FF5F; background: transparent; border: none;")
            self._s3_sub.setText("Gemini 2.5 Pro  ·  Ready")
            self._s3_sub.setStyleSheet("color: rgba(55,255,95,0.6); background: transparent; border: none;")
            self._key_input.setStyleSheet("""
                QLineEdit {
                    background: rgba(55, 255, 95, 0.04);
                    color: #37FF5F;
                    border: 1px solid rgba(55, 255, 95, 0.3);
                    border-radius: 12px;
                    padding: 0 16px;
                }
            """)
            self._s3_box.setStyleSheet("""
                QFrame {
                    background: rgba(8, 10, 16, 220);
                    border: 1px solid rgba(55, 255, 95, 0.2);
                    border-radius: 20px;
                }
            """)
            QTimer.singleShot(1800, self._show_or_prompt)


    def _show_or_prompt(self):
        """After Gemini verified, ask if user wants to add OpenRouter too."""
        self._s3_box.hide()
        page = self._stack.widget(6)
        lay = page.layout()

        self._or_prompt_widget = QFrame()
        self._or_prompt_widget.setFixedSize(460, 200)
        self._or_prompt_widget.setStyleSheet("""
            QFrame {
                background: rgba(8, 10, 16, 220);
                border: 1px solid rgba(124, 110, 230, 0.15);
                border-radius: 20px;
            }
        """)
        prom_lay = QVBoxLayout(self._or_prompt_widget)
        prom_lay.setContentsMargins(32, 28, 32, 24)
        prom_lay.setSpacing(8)

        q_title = QLabel("Secondary Intelligence")
        q_title.setFont(QFont("Exo 2", 16, QFont.Weight.Bold))
        q_title.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        prom_lay.addWidget(q_title)

        q_sub = QLabel("Would you like to configure OpenRouter as well?\nThis is optional and can be done later in Settings.")
        q_sub.setFont(QFont("Exo 2", 10))
        q_sub.setWordWrap(True)
        q_sub.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        prom_lay.addWidget(q_sub)

        prom_lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        skip_btn = QPushButton("Skip")
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.setFixedHeight(42)
        skip_btn.setFont(QFont("Exo 2", 11))
        skip_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 12px;
                padding: 0 24px;
            }
            QPushButton:hover {
                color: C.TEXT;
                border: 1px solid C.TEXT;
            }
        """)
        skip_btn.clicked.connect(self._skip_or)
        btn_row.addWidget(skip_btn)

        yes_btn = QPushButton("Configure OpenRouter")
        yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        yes_btn.setFixedHeight(42)
        yes_btn.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        yes_btn.setStyleSheet("""
            QPushButton {
                background: rgba(124, 110, 230, 0.1);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.35);
                border-radius: 12px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230, 0.2);
                border: 1px solid rgba(124, 110, 230, 0.6);
            }
        """)
        yes_btn.clicked.connect(self._show_or_input)
        btn_row.addWidget(yes_btn)

        prom_lay.addLayout(btn_row)

        lay.insertWidget(lay.count() - 1, self._or_prompt_widget, 0, Qt.AlignmentFlag.AlignCenter)

    def _skip_or(self):
        """User chose to skip OpenRouter, go to color selection."""
        self._or_key_value = ""
        self._or_prompt_widget.hide()
        self._show_color_stage()

    def _show_or_input(self):
        """User wants to add OpenRouter."""
        self._or_prompt_widget.hide()
        page = self._stack.widget(6)
        lay = page.layout()

        self._or_box = QFrame()
        self._or_box.setFixedSize(480, 230)
        self._or_box.setStyleSheet("""
            QFrame {
                background: rgba(8, 10, 16, 220);
                border: 1px solid rgba(124, 110, 230, 0.2);
                border-radius: 20px;
            }
        """)
        or_blay = QVBoxLayout(self._or_box)
        or_blay.setContentsMargins(32, 28, 32, 28)
        or_blay.setSpacing(6)

        or_title = QLabel("OpenRouter")
        or_title.setFont(QFont("Exo 2", 18, QFont.Weight.Bold))
        or_title.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        or_blay.addWidget(or_title)

        or_sub = QLabel("Paste your OpenRouter API Key")
        or_sub.setFont(QFont("Exo 2", 10))
        or_sub.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        or_blay.addWidget(or_sub)

        or_blay.addSpacing(12)

        self._or_input = QLineEdit()
        self._or_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_input.setPlaceholderText("sk-or-************************")
        self._or_input.setFont(QFont("Consolas", 12))
        self._or_input.setFixedHeight(48)
        self._or_input.setStyleSheet("""
            QLineEdit {
                background: C.TEXT;
                color: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 12px;
                padding: 0 16px;
                letter-spacing: 1px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(124, 110, 230, 0.5);
            }
        """)
        self._or_input.setText((self._defaults.get("openrouter_api_key") or "").strip())
        or_blay.addWidget(self._or_input)

        or_blay.addStretch()

        or_btn_row = QHBoxLayout()
        or_skip = QPushButton("Skip")
        or_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        or_skip.setFixedHeight(42)
        or_skip.setFont(QFont("Exo 2", 11))
        or_skip.setStyleSheet("""
            QPushButton { background: transparent; color: C.TEXT; border: none; }
            QPushButton:hover { color: C.TEXT; }
        """)
        or_skip.clicked.connect(self._skip_or)
        or_btn_row.addWidget(or_skip)

        or_save = QPushButton("Save & Continue")
        or_save.setCursor(Qt.CursorShape.PointingHandCursor)
        or_save.setFixedHeight(42)
        or_save.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        or_save.setStyleSheet("""
            QPushButton {
                background: rgba(124, 110, 230, 0.1);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.35);
                border-radius: 12px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230, 0.2);
                border: 1px solid rgba(124, 110, 230, 0.6);
            }
        """)
        or_save.clicked.connect(self._save_or_key)
        or_btn_row.addWidget(or_save)

        or_blay.addLayout(or_btn_row)

        lay.insertWidget(lay.count() - 1, self._or_box, 0, Qt.AlignmentFlag.AlignCenter)

    def _save_or_key(self):
        self._or_key_value = self._or_input.text().strip()
        self._or_box.hide()
        self._show_color_stage()

    def _show_color_stage(self):
        """Show color selection."""
        page = self._stack.widget(6)
        lay = page.layout()

        self._color_box = QFrame()
        self._color_box.setFixedSize(480, 230)
        self._color_box.setStyleSheet("""
            QFrame {
                background: rgba(8, 10, 16, 220);
                border: 1px solid rgba(124, 110, 230, 0.2);
                border-radius: 20px;
            }
        """)
        c_blay = QVBoxLayout(self._color_box)
        c_blay.setContentsMargins(32, 28, 32, 28)
        c_blay.setSpacing(6)

        c_title = QLabel("CHOOSE AESTHETIC")
        c_title.setFont(QFont("Exo 2", 16, QFont.Weight.Bold))
        c_title.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        c_blay.addWidget(c_title)

        c_sub = QLabel("Select your preferred neural color palette.")
        c_sub.setFont(QFont("Exo 2", 10))
        c_sub.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
        c_blay.addWidget(c_sub)

        c_blay.addSpacing(12)
        
        self._setup_color_btn = QPushButton("Pick Custom Color")
        self._setup_color_btn.setFixedHeight(48)
        self._setup_color_btn.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        self._setup_color_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI};
                color: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 12px;
            }}
        """)
        # Accent color picker removed - theme fixed to default
        c_blay.addWidget(self._setup_color_btn)

        c_blay.addStretch()

        c_btn_row = QHBoxLayout()
        c_btn_row.addStretch()
        c_continue = QPushButton("Continue →")
        c_continue.setCursor(Qt.CursorShape.PointingHandCursor)
        c_continue.setFixedHeight(42)
        c_continue.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        c_continue.setStyleSheet("""
            QPushButton {
                background: rgba(124, 110, 230, 0.1);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.35);
                border-radius: 12px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230, 0.2);
                border: 1px solid rgba(124, 110, 230, 0.6);
            }
        """)
        c_continue.clicked.connect(self._finish_color_stage)
        c_btn_row.addWidget(c_continue)
        
        c_blay.addLayout(c_btn_row)

        lay.insertWidget(lay.count() - 1, self._color_box, 0, Qt.AlignmentFlag.AlignCenter)
        
    def _finish_color_stage(self):
        self._color_box.hide()
        self._show_intro_final()

    def _show_intro_final(self):
        """Show the Stella intro sequence."""
        page = self._stack.widget(6)
        lay = page.layout()
        self._intro_widget.setParent(None)
        lay.insertWidget(lay.count() - 1, self._intro_widget, 0, Qt.AlignmentFlag.AlignCenter)
        self._intro_widget.show()
        self._intro_reveal_idx = 0
        self._intro_timer = QTimer(self)
        self._intro_timer.timeout.connect(self._intro_tick)
        self._intro_timer.start(600)

    def _show_intro(self):
        self._s3_box.hide()
        page = self._stack.widget(6)
        lay = page.layout()
        self._intro_widget.setParent(None)
        lay.insertWidget(lay.count() - 1, self._intro_widget, 0, Qt.AlignmentFlag.AlignCenter)
        self._intro_widget.show()
        self._intro_reveal_idx = 0
        self._intro_timer = QTimer(self)
        self._intro_timer.timeout.connect(self._intro_tick)
        self._intro_timer.start(600)

    def _intro_tick(self):
        if self._intro_reveal_idx < len(self._intro_lines):
            self._intro_lines[self._intro_reveal_idx].show()
            if self._intro_reveal_idx == 2:
                self._call_js("if(window.triggerPulse) window.triggerPulse();")
            self._intro_reveal_idx += 1
        else:
            self._intro_timer.stop()
            self._launch_btn.show()

    # ── STAGE 6: Neural Link Ignition ──────────────────────────────
    def _build_stage4(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addStretch(3)

        self._s4_container = QFrame()
        self._s4_container.setFixedWidth(360)
        self._s4_container.setStyleSheet("""
            QFrame {
                background: rgba(5, 8, 12, 180);
                border: 1px solid rgba(124, 110, 230, 0.12);
                border-radius: 16px;
            }
        """)
        c4lay = QVBoxLayout(self._s4_container)
        c4lay.setContentsMargins(30, 24, 30, 24)
        c4lay.setSpacing(8)

        self._s4_title = QLabel("ESTABLISHING NEURAL LINK")
        self._s4_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._s4_title.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._s4_title.setStyleSheet("color: rgba(124, 110, 230,0.7); background: transparent; border: none; letter-spacing: 3px;")
        c4lay.addWidget(self._s4_title)
        c4lay.addSpacing(12)

        self._module_labels = {}
        for mod in ["MEMORY", "VOICE", "VISION", "AUTOMATION", "REASONING"]:
            row = QHBoxLayout()
            name_lbl = QLabel(mod)
            name_lbl.setFont(QFont("Consolas", 11))
            name_lbl.setStyleSheet("color: C.TEXT; background: transparent; border: none;")
            name_lbl.setFixedWidth(130)
            row.addWidget(name_lbl)

            bar_lbl = QLabel("░░░░░░░░░░")
            bar_lbl.setFont(QFont("Consolas", 11))
            bar_lbl.setStyleSheet("color: rgba(124, 110, 230,0.15); background: transparent; border: none;")
            row.addWidget(bar_lbl)
            row.addStretch()

            c4lay.addLayout(row)
            self._module_labels[mod] = (name_lbl, bar_lbl)

        lay.addWidget(self._s4_container, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(1)
        self._stack.addWidget(page)

    def _start_ignition(self):
        self._stack.setCurrentIndex(7)
        self._call_js("if(window.setReactorSpeed) window.setReactorSpeed(5.0);")

        self._ignite_step = 0
        self._module_order = ["MEMORY", "VOICE", "VISION", "AUTOMATION", "REASONING"]
        self._ignite_timer = QTimer(self)
        self._ignite_timer.timeout.connect(self._ignite_tick)
        self._ignite_timer.start(600)

    def _ignite_tick(self):
        if self._ignite_step < len(self._module_order):
            mod = self._module_order[self._ignite_step]
            name_lbl, bar_lbl = self._module_labels[mod]
            name_lbl.setStyleSheet("color: #7C6EE6; background: transparent; border: none; font-weight: bold;")
            bar_lbl.setText("██████████")
            bar_lbl.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
            self._call_js(f"if(window.setReactorSpeed) window.setReactorSpeed({5.0 + self._ignite_step * 4});")
            self._call_js("if(window.triggerPulse) window.triggerPulse();")
            self._ignite_step += 1
        else:
            self._ignite_timer.stop()
            self._s4_title.setText("NEURAL LINK ESTABLISHED")
            self._s4_title.setStyleSheet("color: #37FF5F; background: transparent; border: none; letter-spacing: 3px; font-weight: bold;")
            self._s4_container.setStyleSheet("""
                QFrame {
                    background: rgba(5, 8, 12, 180);
                    border: 1px solid rgba(55, 255, 95, 0.2);
                    border-radius: 16px;
                }
            """)
            for mod in self._module_order:
                n, b = self._module_labels[mod]
                n.setStyleSheet("color: #37FF5F; background: transparent; border: none; font-weight: bold;")
                b.setStyleSheet("color: #37FF5F; background: transparent; border: none;")
            self._call_js("if(window.dissolveReactor) window.dissolveReactor();")
            QTimer.singleShot(1200, lambda: self.done.emit(self._key_input.text().strip(), getattr(self, "_or_key_value", ""), self._sel_os))

class CommandBar(QWidget):
    submitted = pyqtSignal(str)
    attach_clicked = pyqtSignal()
    mic_clicked = pyqtSignal()
    developer_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("CommandBar")
        self.setFixedSize(580, 48)
        self.setStyleSheet("background: transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(0)

        frame = QFrame()
        frame.setObjectName("CommandBarFrame")
        frame.setStyleSheet(f"""
            QFrame#CommandBarFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(6, 6, 10, 252),
                    stop:0.3 rgba(12, 11, 16, 252),
                    stop:0.7 rgba(12, 11, 16, 252),
                    stop:1 rgba(6, 6, 10, 252));
                border: 1px solid rgba(124, 110, 230, 0.22);
                border-radius: 20px;
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(6)

        # Stella mini logo
        logo_frame = QFrame()
        logo_frame.setFixedSize(32, 32)
        logo_frame.setStyleSheet("""
            QFrame {
                background: rgba(124, 110, 230, 0.06);
                border: 1px solid rgba(124, 110, 230, 0.25);
                border-radius: 16px;
            }
        """)
        logo_lay = QVBoxLayout(logo_frame)
        logo_lay.setContentsMargins(0, 0, 0, 0)
        logo_lbl = QLabel("\u092C\u094D\u0930")  # ब्र (short Hindi)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setFont(QFont("Nirmala UI", 9, QFont.Weight.Bold))
        logo_lbl.setStyleSheet("color: #7C6EE6; background: transparent; border: none;")
        logo_lay.addWidget(logo_lbl)
        lay.addWidget(logo_frame)

        # Input field
        self._input = QLineEdit()
        self._input.setPlaceholderText("Tell Stella what to do...")
        self._input.setFont(QFont("Exo 2", 9))
        self._input.setMinimumHeight(40)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: C.TEXT;
                color: {C.TEXT};
                border: 1px solid C.TEXT;
                border-radius: 16px;
                padding: 4px 14px;
                selection-background-color: rgba(124, 110, 230, 0.25);
            }}
            QLineEdit:focus {{
                border: 1px solid rgba(124, 110, 230, 0.45);
                background: rgba(124, 110, 230, 0.03);
            }}
        """)
        self._input.returnPressed.connect(self._submit)
        self._input.textChanged.connect(lambda t: voice_gate.set_typing(bool((t or "").strip())))
        lay.addWidget(self._input, stretch=1)

        # Action buttons container
        btn_style_ghost = f"""
            QPushButton {{
                background: C.TEXT;
                color: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.12);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.4);
            }}
        """

        attach = QPushButton()
        attach.setFixedSize(28, 28)
        attach.setCursor(Qt.CursorShape.PointingHandCursor)
        attach.setToolTip("Attach file")
        attach.setIcon(QIcon(_icon_pixmap("attach", 13)))
        attach.setIconSize(QSize(13, 13))
        attach.setStyleSheet(btn_style_ghost)
        attach.clicked.connect(self.attach_clicked.emit)
        lay.addWidget(attach)

        mic = QPushButton()
        mic.setFixedSize(28, 28)
        mic.setCursor(Qt.CursorShape.PointingHandCursor)
        mic.setToolTip("Voice input")
        mic.setIcon(QIcon(_icon_pixmap("mic", 13)))
        mic.setIconSize(QSize(13, 13))
        mic.setStyleSheet(btn_style_ghost)
        mic.clicked.connect(self.mic_clicked.emit)
        lay.addWidget(mic)

        dev = QPushButton("DEV")
        dev.setFixedSize(40, 28)
        dev.setCursor(Qt.CursorShape.PointingHandCursor)
        dev.setToolTip("Developer mode")
        dev.setStyleSheet(f"""
            QPushButton {{
                background: rgba(124, 110, 230, 0.06);
                color: rgba(124, 110, 230, 0.7);
                border: 1px solid rgba(124, 110, 230, 0.25);
                border-radius: 14px;
                font: 700 8px 'Segoe UI';
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.15);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.5);
            }}
        """)
        dev.clicked.connect(self.developer_clicked.emit)
        lay.addWidget(dev)

        # Send button — golden accent
        send = QPushButton()
        send.setFixedSize(32, 32)
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setToolTip("Send")
        send.setIcon(QIcon(_icon_pixmap("send", 14)))
        send.setIconSize(QSize(14, 14))
        send.setStyleSheet(f"""
            QPushButton {{
                background: rgba(124, 110, 230, 0.12);
                color: #7C6EE6;
                border: 1px solid rgba(124, 110, 230, 0.35);
                border-radius: 19px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.25);
                border: 1px solid #7C6EE6;
            }}
        """)
        send.clicked.connect(self._submit)
        lay.addWidget(send)

        root.addWidget(frame)

    def show_near(self, anchor: QWidget):
        screen = QApplication.primaryScreen().availableGeometry()
        geo = anchor.geometry()
        x = geo.center().x() - (self.width() // 2)
        y = geo.bottom() + 14
        x = max(screen.left() + 12, min(x, screen.right() - self.width() - 12))
        y = max(screen.top() + 12, min(y, screen.bottom() - self.height() - 12))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._input.setFocus()
        self._input.selectAll()

    def hideEvent(self, event):
        super().hideEvent(event)

    def _submit(self):
        txt = self._input.text().strip()
        if not txt:
            return
        self._input.clear()
        self.submitted.emit(txt)
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    def set_audio_level(self, level: float):
        pass

    def set_state(self, state: str):
        pass

class DeveloperModeDialog(QDialog):
    def __init__(self, parent=None, settings: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Developer Mode")
        self.setMinimumWidth(420)
        self.setStyleSheet(f"""
            QDialog {{ background: rgba(8,10,14,235); color: {C.WHITE}; border: 1px solid {C.BORDER_B}; }}
            QLabel {{ color: {C.TEXT}; }}
            QLineEdit {{
                background: rgba(16,16,16,240);
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 10px;
                padding: 8px 10px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
            QPushButton {{
                background: rgba(18,18,18,240);
                color: {C.WHITE};
                border: 1px solid {C.BORDER_B};
                border-radius: 10px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{ background: rgba(28,28,28,245); border: 1px solid {C.PRI}; }}
            QCheckBox {{ color: {C.TEXT}; }}
        """)

        self._settings = dict(settings or {})
        self._enabled = bool(self._settings.get("developer_mode_enabled", False))
        fallback_workspace = str(Path(__file__).resolve().parent)
        self._workspace = str(self._settings.get("developer_mode_workspace", "") or fallback_workspace)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Developer Co-pilot")
        title.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI};")
        root.addWidget(title)

        desc = QLabel("Pick a workspace folder Stella should use when building websites or other workspace-based tasks.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C.TEXT_DIM};")
        root.addWidget(desc)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self._workspace_edit = QLineEdit(self._workspace)
        self._workspace_edit.setPlaceholderText("Select a folder...")
        self._workspace_edit.setReadOnly(True)
        folder_row.addWidget(self._workspace_edit, stretch=1)

        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse)
        root.addLayout(folder_row)

        self._enabled_box = QCheckBox("Turn developer mode on")
        self._enabled_box.setChecked(self._enabled)
        root.addWidget(self._enabled_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.clicked.connect(self._save_and_close)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select developer workspace", self._workspace or str(BASE_DIR))
        if path:
            self._workspace_edit.setText(path)

    def _save_and_close(self):
        self._settings["developer_mode_enabled"] = bool(self._enabled_box.isChecked())
        self._settings["developer_mode_workspace"] = self._workspace_edit.text().strip()
        self.accept()

    def get_settings(self) -> dict:
        return dict(self._settings)

class ScanningOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self._text = "SCANNING SCREEN"
        self._sub = "Analyzing display..."
        self._result_text = ""
        
        self._time = 0.0
        self._dt = 0.016
        self._fade_out_opacity = 1.0
        self._is_finishing = False
        self._finish_time = 0.0
        
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(16)

        self._particles = []
        self._boxes = [] 
        self._context_lines = []
        
        self.GOLD = QColor("#7C6EE6")

    def set_message(self, text: str, sub: str | None = None):
        self._text = (text or "SCANNING SCREEN").upper()
        if sub is not None:
            self._sub = sub
        self.update()

    def show_fullscreen(self, text: str = "SCANNING SCREEN", sub: str = "Analyzing display..."):
        self.set_message(text, sub)
        self._time = 0.0
        self._fade_out_opacity = 1.0
        self._is_finishing = False
        self._finish_time = 0.0
        
        screen = QApplication.primaryScreen()
        geo = screen.geometry() if screen else QRectF(0, 0, 1920, 1080).toRect()
        self.setGeometry(geo)
        
        # Capture screen for OpenCV
        if screen:
            pixmap = screen.grabWindow(0)
            self._generate_layout(pixmap)
        else:
            self._generate_layout(None)
        
        self.show()
        self.raise_()
        self.setFocus()

    def hide_overlay(self):
        if not self._is_finishing:
            self._is_finishing = True
            self._finish_time = self._time
            
            self._result_text = "Workspace Recognized\\nVisual Studio Code · Browser · Terminal"

    def force_hide(self):
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.force_hide()
        else:
            super().keyPressEvent(event)

    def _generate_layout(self, pixmap):
        random.seed(42)
        w, h = self.width(), self.height()
        
        # Particles
        self._particles = []
        for _ in range(120):
            self._particles.append({
                'x': random.uniform(0, w),
                'y': random.uniform(0, h),
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(-1, 1),
                'life': random.uniform(0, math.pi * 2)
            })
            
        self._boxes = []
        self._context_lines = []
        
        if pixmap is not None:
            try:
                # Convert QPixmap to CV2
                qimg = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
                width = qimg.width()
                height = qimg.height()
                ptr = qimg.constBits()
                ptr.setsize(height * width * 3)
                arr = np.array(ptr).reshape(height, width, 3)
                
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                
                kernel = np.ones((5,5), np.uint8)
                dilated = cv2.dilate(edges, kernel, iterations=1)
                
                contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Sort contours by area
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                
                # Take top 30 elements to avoid crowding
                for cnt in contours[:30]:
                    x, y, cw, ch = cv2.boundingRect(cnt)
                    area = cw * ch
                    if area < 150: continue # Skip tiny noise
                    
                    category = "UNKNOWN"
                    start_time = 1.0
                    label = "UI Element"
                    
                    if cw > 400 and ch > 300:
                        category = "WINDOW"
                        start_time = 2.5
                        label = random.choice(["Dashboard Panel", "Task Workspace", "Editor Window"])
                    elif cw > 80 and ch < 40:
                        category = "OCR"
                        start_time = 0.5 + random.uniform(0, 0.5)
                        label = random.choice(["System Online", "Settings", "Microphone", "User Profile"])
                    elif cw < 60 and ch < 60:
                        category = "ICON"
                        start_time = 1.5 + random.uniform(0, 0.5)
                        label = "Icon Node"
                    elif 1.2 < (cw/ch) < 4.0 and ch < 80:
                        category = "BUTTON"
                        start_time = 1.0 + random.uniform(0, 0.5)
                        label = "Action Button"
                    else:
                        continue # Skip weird shapes
                        
                    self._boxes.append({
                        'x': x, 'y': y, 'w': cw, 'h': ch,
                        'category': category,
                        'label': label,
                        'conf': random.randint(67, 98) if category != "WINDOW" else random.randint(95, 99),
                        'start_time': start_time,
                        'has_product': (category == "WINDOW" and random.random() > 0.8)
                    })
                    
            except Exception as e:
                print(f"[ScanningOverlay] CV2 Error: {e}")
                
        # Fallback if no boxes found or CV failed
        if len(self._boxes) == 0:
            for _ in range(5):
                self._boxes.append({
                    'x': random.uniform(w*0.2, w*0.8),
                    'y': random.uniform(h*0.2, h*0.8),
                    'w': random.uniform(100, 300),
                    'h': random.uniform(30, 60),
                    'category': "OCR",
                    'label': "Fallback Element",
                    'conf': 85,
                    'start_time': random.uniform(0.5, 1.5),
                    'has_product': False
                })

        # Generate Context Lines between nearest neighbors (Phase 5)
        for i, b1 in enumerate(self._boxes):
            if i >= 15: break
            for j, b2 in enumerate(self._boxes):
                if i != j and j < 15:
                    dist = math.hypot(b1['x'] - b2['x'], b1['y'] - b2['y'])
                    if dist < 400 and random.random() > 0.7:
                        self._context_lines.append((i, j))
                        break # max 1 connection per node

    def _tick(self):
        self._time += self._dt
        if self._is_finishing:
            dt_finish = self._time - self._finish_time
            if dt_finish > 1.5: 
                self._fade_out_opacity = max(0.0, 1.0 - (dt_finish - 1.5) * 2.0)
                if self._fade_out_opacity <= 0.0:
                    self.hide()
                    return
        if self.isVisible():
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._fade_out_opacity)
        
        W, H = self.width(), self.height()
        p.fillRect(self.rect(), QColor(5, 5, 5, 210))
        
        phase1_progress = min(1.0, self._time / 1.5)
        phase6_progress = min(1.0, max(0.0, (self._time - 4.5) / 1.5))
        
        self._draw_particles(p, W, H, phase6_progress)
        self._draw_scan_waves(p, W, H, phase1_progress)
        
        if self._time > 0.5 and not self._is_finishing:
            self._draw_all_boxes(p)
            
        if self._time > 3.5 and not self._is_finishing:
            self._draw_context_lines(p)
            
        if self._time > 4.5 and not self._is_finishing:
            self._draw_neural_net(p, W, H, phase6_progress)
            
        self._draw_center_status(p, W, H)

    def _draw_particles(self, p, W, H, converge_progress):
        cx, cy = W / 2, H / 2
        p.setPen(Qt.PenStyle.NoPen)
        for part in self._particles:
            part['x'] += part['vx']
            part['y'] += part['vy']
            part['life'] += 0.05
            if part['x'] < 0: part['x'] = W
            if part['x'] > W: part['x'] = 0
            if part['y'] < 0: part['y'] = H
            if part['y'] > H: part['y'] = 0
            
            x, y = part['x'], part['y']
            if converge_progress > 0:
                e = _ease_in_out_sine(converge_progress)
                x = x + (cx - x) * e * 0.8
                y = y + (cy - y) * e * 0.8
                
            alpha = int(100 + math.sin(part['life']) * 50)
            p.setBrush(QColor(124, 110, 230, alpha))
            size = 1.5 + math.sin(part['life']) * 1.0
            p.drawEllipse(QRectF(x - size, y - size, size * 2, size * 2))
            
    def _draw_scan_waves(self, p, W, H, progress):
        if progress >= 1.0 or self._is_finishing: return
        e = _ease_out_expo(progress)
        y = e * H
        grad = QLinearGradient(0, y - 50, 0, y + 50)
        grad.setColorAt(0.0, QColor(124, 110, 230, 0))
        grad.setColorAt(0.5, QColor(124, 110, 230, 150))
        grad.setColorAt(1.0, QColor(124, 110, 230, 0))
        p.fillRect(QRectF(0, y - 50, W, 100), grad)
        x = e * W
        grad2 = QLinearGradient(x - 50, 0, x + 50, 0)
        grad2.setColorAt(0.0, QColor(124, 110, 230, 0))
        grad2.setColorAt(0.5, QColor(124, 110, 230, 150))
        grad2.setColorAt(1.0, QColor(124, 110, 230, 0))
        p.fillRect(QRectF(x - 50, 0, 100, H), grad2)
        
    def _draw_all_boxes(self, p):
        p.setBrush(Qt.BrushStyle.NoBrush)
        for box in self._boxes:
            dt = self._time - box['start_time']
            if dt < 0: continue
            
            out_dt = self._time - 4.5
            alpha_mult = max(0.0, 1.0 - out_dt) if out_dt > 0 else 1.0
            if alpha_mult <= 0: continue
            
            prog = min(1.0, dt / 0.8)
            e = _ease_out_expo(prog)
            
            x, y, w, h = box['x'], box['y'], box['w'], box['h']
            cat = box['category']
            
            alpha = int(255 * alpha_mult)
            
            # Styles based on category
            if cat == "OCR":
                br = (w / 4) * e
                p.setPen(QPen(QColor(124, 110, 230, int(150 * alpha_mult)), 1))
                if prog < 0.5:
                    p.drawLine(QPointF(x, y), QPointF(x + br, y))
                    p.drawLine(QPointF(x, y), QPointF(x, y + br))
                    p.drawLine(QPointF(x + w, y), QPointF(x + w - br, y))
                    p.drawLine(QPointF(x + w, y), QPointF(x + w, y + br))
                    p.drawLine(QPointF(x, y + h), QPointF(x + br, y + h))
                    p.drawLine(QPointF(x, y + h), QPointF(x, y + h - br))
                    p.drawLine(QPointF(x + w, y + h), QPointF(x + w - br, y + h))
                    p.drawLine(QPointF(x + w, y + h), QPointF(x + w, y + h - br))
                else:
                    p.drawRect(QRectF(x, y, w, h))
                    
            elif cat == "WINDOW":
                br = 30 * e
                p.setPen(QPen(QColor(124, 110, 230, int(200 * alpha_mult)), 2))
                p.drawLine(QPointF(x, y), QPointF(x + br, y))
                p.drawLine(QPointF(x, y), QPointF(x, y + br))
                p.drawLine(QPointF(x + w, y), QPointF(x + w - br, y))
                p.drawLine(QPointF(x + w, y), QPointF(x + w, y + br))
                p.drawLine(QPointF(x, y + h), QPointF(x + br, y + h))
                p.drawLine(QPointF(x, y + h), QPointF(x, y + h - br))
                p.drawLine(QPointF(x + w, y + h), QPointF(x + w - br, y + h))
                p.drawLine(QPointF(x + w, y + h), QPointF(x + w, y + h - br))
                
            elif cat == "BUTTON":
                p.setPen(QPen(QColor(124, 110, 230, int(100 * e * alpha_mult)), 1))
                p.setBrush(QColor(124, 110, 230, int(20 * e * alpha_mult)))
                p.drawRoundedRect(QRectF(x, y, w, h), 6, 6)
                p.setBrush(Qt.BrushStyle.NoBrush)
                
            elif cat == "ICON":
                p.setPen(QPen(QColor(124, 110, 230, int(200 * e * alpha_mult)), 1))
                p.drawEllipse(QRectF(x + w/2 - 4*e, y + h/2 - 4*e, 8*e, 8*e))
                
            if dt > 0.8:
                text_prog = min(1.0, (dt - 0.8) / 0.5)
                te = _ease_out_expo(text_prog)
                
                conf = box['conf']
                label = box['label']
                if conf < 75: label = f"Possible {label}"
                
                p.setFont(QFont("Inter", 8, QFont.Weight.Bold))
                p.setPen(QColor(124, 110, 230, int(255 * te * alpha_mult)))
                ly = y - 6 + (1.0 - te) * 10
                p.drawText(QRectF(x, ly - 10, 200, 12), Qt.AlignmentFlag.AlignLeft, f"{label} {conf}%")

            if box['has_product'] and dt > 2.0:
                card_prog = min(1.0, (dt - 2.0) / 0.5)
                ce = _ease_out_expo(card_prog)
                
                cx, cy = x + w + 20, y + 20
                cw, ch = 220, 90
                
                p.setPen(QPen(QColor(124, 110, 230, int(150 * ce * alpha_mult)), 1, Qt.PenStyle.DashLine))
                p.drawLine(QPointF(x + w, y + 40), QPointF(cx, cy + ch/2))
                
                p.setPen(QPen(QColor(124, 110, 230, int(100 * ce * alpha_mult)), 1))
                p.setBrush(QColor(10, 10, 5, int(220 * ce * alpha_mult)))
                p.drawRoundedRect(QRectF(cx, cy, cw, ch), 6, 6)
                p.setBrush(Qt.BrushStyle.NoBrush)
                
                if card_prog > 0.8:
                    p.setPen(QColor(255, 255, 255, int(255 * alpha_mult)))
                    p.setFont(QFont("Inter", 10, QFont.Weight.Bold))
                    p.drawText(QRectF(cx + 12, cy + 10, cw, 20), Qt.AlignmentFlag.AlignLeft, "Detected Interface")
                    
                    p.setPen(QColor(124, 110, 230, int(255 * alpha_mult)))
                    p.setFont(QFont("Inter", 8))
                    p.drawText(QRectF(cx + 12, cy + 32, cw, 20), Qt.AlignmentFlag.AlignLeft, f"{label} Verified")

    def _draw_context_lines(self, p):
        dt = self._time - 3.5
        out_dt = self._time - 4.5
        alpha_mult = max(0.0, 1.0 - out_dt) if out_dt > 0 else 1.0
        if alpha_mult <= 0: return
        prog = min(1.0, dt / 1.0)
        p.setPen(QPen(QColor(124, 110, 230, int(100 * prog * alpha_mult)), 1, Qt.PenStyle.DotLine))
        for i, j in self._context_lines:
            b1 = self._boxes[i]
            b2 = self._boxes[j]
            c1x, c1y = b1['x'] + b1['w']/2, b1['y'] + b1['h']/2
            c2x, c2y = b2['x'] + b2['w']/2, b2['y'] + b2['h']/2
            path = QPainterPath()
            path.moveTo(c1x, c1y)
            path.cubicTo(c1x + 100, c1y, c2x - 100, c2y, c2x, c2y)
            p.drawPath(path)

    def _draw_neural_net(self, p, W, H, progress):
        cx, cy = W / 2, H / 2
        e = _ease_out_expo(progress)
        r = 80 * e
        grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        grad.setColorAt(0.0, QColor(124, 110, 230, 150))
        grad.setColorAt(1.0, QColor(124, 110, 230, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawEllipse(QRectF(cx - r*1.5, cy - r*1.5, r*3, r*3))
        p.setPen(QPen(QColor(124, 110, 230, int(200 * e)), 1))
        num_nodes = 8
        time_rot = self._time * 0.5
        nodes = []
        for i in range(num_nodes):
            angle = (i / num_nodes) * math.pi * 2 + time_rot
            orbit_r = 120 + math.sin(self._time * 2 + i) * 20
            nx = cx + math.cos(angle) * orbit_r * e
            ny = cy + math.sin(angle) * orbit_r * e
            nodes.append((nx, ny))
            p.setBrush(QColor(124, 110, 230, 255))
            p.drawEllipse(QRectF(nx - 3, ny - 3, 6, 6))
        for i in range(num_nodes):
            n1 = nodes[i]
            n2 = nodes[(i+1)%num_nodes]
            n3 = nodes[(i+3)%num_nodes]
            p.drawLine(QPointF(*n1), QPointF(*n2))
            p.drawLine(QPointF(*n1), QPointF(*n3))
            p.drawLine(QPointF(cx, cy), QPointF(*n1))

    def _draw_center_status(self, p, W, H):
        cx, cy = W / 2, H / 2
        if self._is_finishing:
            dt = self._time - self._finish_time
            prog = min(1.0, dt / 0.5)
            e = _ease_out_expo(prog)
            pw, ph = 400, 120
            p.setPen(QPen(QColor(124, 110, 230, int(150 * e)), 1))
            p.setBrush(QColor(10, 10, 5, int(230 * e)))
            p.drawRoundedRect(QRectF(cx - pw/2, cy - ph/2, pw, ph), 8, 8)
            if prog > 0.8:
                p.setPen(QColor(255, 255, 255, 255))
                p.setFont(QFont("Inter", 14, QFont.Weight.Bold))
                lines = self._result_text.split("\\n")
                if len(lines) > 0:
                    p.drawText(QRectF(cx - pw/2, cy - 20, pw, 24), Qt.AlignmentFlag.AlignCenter, lines[0])
                if len(lines) > 1:
                    p.setPen(QColor(124, 110, 230, 255))
                    p.setFont(QFont("Inter", 10))
                    p.drawText(QRectF(cx - pw/2, cy + 10, pw, 20), Qt.AlignmentFlag.AlignCenter, lines[1])
        else:
            status = "INITIALIZING..."
            if self._time > 1.0: status = "SCANNING OCR..."
            if self._time > 2.5: status = "RECOGNIZING OBJECTS..."
            if self._time > 3.5: status = "ANALYZING CONTEXT..."
            if self._time > 4.5:
                cycle = int(self._time * 2) % 4
                dots = "." * cycle
                status = f"THINKING{dots}"
            p.setPen(QColor(255, 255, 255, 255))
            p.setFont(QFont("Inter", 12, QFont.Weight.Bold))
            p.drawText(QRectF(0, cy + 160, W, 20), Qt.AlignmentFlag.AlignCenter, status)

class BootSequenceOverlay(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setWindowOpacity(1.0)

        self._boot_finished = False
        self._time = 0.0
        self._dt = 0.016
        self._total_duration = 3.6

        # Particles & Effects State
        self._particles = []
        self._impact_sparks = []
        self._played_whoosh = False
        self._played_impact = False

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)

    def _init_particles(self, w: float, h: float):
        self._particles = []
        for _ in range(280):
            self._particles.append({
                'x': random.uniform(0, w),
                'y': random.uniform(0, h),
                'vx': random.uniform(-0.65, 0.65),
                'vy': random.uniform(-0.65, 0.65),
                'size': random.uniform(1.4, 4.0),
                'base_alpha': random.uniform(0.65, 1.0),
                'twinkle_speed': random.uniform(2.5, 6.5),
                'twinkle_phase': random.uniform(0, math.pi * 2),
                'converge_delay': random.uniform(0.0, 0.25),
                'orig_x': 0.0,
                'orig_y': 0.0,
            })

    def start(self, device_name: str = "", greeting_name: str = ""):
        self._boot_finished = False
        screen = QApplication.primaryScreen()
        geo = screen.geometry() if screen else QRectF(0, 0, 1920, 1080).toRect()
        self.setGeometry(geo)
        self._init_particles(float(geo.width()), float(geo.height()))
        self._time = 0.0
        self._played_whoosh = False
        self._played_impact = False
        self.show()
        self.raise_()
        self.activateWindow()
        self._tmr.start(16)

    def add_step(self, text: str):
        pass

    def set_step_status(self, text: str, status: str):
        pass

    def set_progress(self, percent: int, tip: str | None = None):
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._tmr.stop()
            self._boot_finished = True
            self.hide()
            self.close()
            self.finished.emit()

    def _tick(self):
        self._time += self._dt
        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        # Phase 1 (0.0 to 1.1s): particles drift across full screen
        if self._time < 1.1:
            for p in self._particles:
                p['x'] += p['vx']
                p['y'] += p['vy']
                if p['x'] < 0: p['x'] = w
                elif p['x'] > w: p['x'] = 0
                if p['y'] < 0: p['y'] = h
                elif p['y'] > h: p['y'] = 0

        # Phase 2 (1.1s to 1.8s): burst & convergence towards center
        elif 1.1 <= self._time < 1.8:
            if not self._played_whoosh:
                self._played_whoosh = True
                try:
                    from sound_manager import SoundManager
                    SoundManager.instance().play_deploy_whoosh()
                except Exception:
                    pass
                for p in self._particles:
                    p['orig_x'] = p['x']
                    p['orig_y'] = p['y']

            burst_t = (self._time - 1.1) / 0.7
            for p in self._particles:
                local_t = max(0.0, min(1.0, (burst_t - p['converge_delay']) / (1.0 - p['converge_delay'] + 0.001)))
                ease = math.pow(local_t, 3.2)
                p['x'] = p['orig_x'] + (cx - p['orig_x']) * ease
                p['y'] = p['orig_y'] + (cy - 30.0 - p['orig_y']) * ease

        # Phase 4 (2.5s to 3.2s): AI - EVO entrance with impact
        if self._time >= 2.5 and not self._played_impact:
            self._played_impact = True
            try:
                from sound_manager import SoundManager
                SoundManager.instance().play_mission_complete()
            except Exception:
                pass
            self._impact_sparks = []
            for _ in range(70):
                angle = random.uniform(0, math.pi * 2)
                spd = random.uniform(6.0, 24.0)
                self._impact_sparks.append({
                    'x': cx,
                    'y': cy + 55.0,
                    'vx': math.cos(angle) * spd,
                    'vy': math.sin(angle) * spd * 0.65,
                    'alpha': 1.0,
                    'size': random.uniform(2.0, 4.5),
                    'color': random.choice(['C.ACC', 'C.TEXT', '#7DD3FC', '#38BDF8'])
                })

        if self._impact_sparks:
            for s in self._impact_sparks:
                s['x'] += s['vx']
                s['y'] += s['vy']
                s['vx'] *= 0.92
                s['vy'] *= 0.92
                s['alpha'] *= 0.92

        self.update()

        if self._time >= self._total_duration:
            self._tmr.stop()
            self._boot_finished = True
            self.hide()
            self.close()
            self.finished.emit()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            # Minimal DWM compositing fill (alpha=1 ensures DWM layered composition without visible darkening)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

            w = float(self.width())
            h = float(self.height())
            cx = w / 2.0
            cy = h / 2.0

            # DO NOT DRAW BACKGROUND FILL: Purely transparent!

            # Transition out alpha (Phase 5: 3.2s to 3.6s)
            global_alpha = 1.0
            if self._time >= 3.2:
                exit_t = min(1.0, (self._time - 3.2) / 0.4)
                global_alpha = max(0.0, 1.0 - exit_t)

            # Camera Shake calculation during impact (2.5s to 3.0s)
            shake_x, shake_y = 0.0, 0.0
            if 2.5 <= self._time < 3.0:
                shake_dt = self._time - 2.5
                decay = max(0.0, 1.0 - (shake_dt / 0.45))
                shake_x = math.sin(shake_dt * 65.0) * 16.0 * decay
                shake_y = math.cos(shake_dt * 52.0) * 10.0 * decay

            painter.translate(shake_x, shake_y)

            # -------------------------------------------------------------
            # 1. DRAW PARTICLES
            # -------------------------------------------------------------
            if self._time < 1.8:
                for p in self._particles:
                    p_alpha = p['base_alpha']
                    if self._time < 0.6:
                        p_alpha *= (self._time / 0.6)
                    twinkle = 0.75 + 0.25 * math.sin(self._time * p['twinkle_speed'] + p['twinkle_phase'])
                    final_alpha = int(255 * p_alpha * twinkle * global_alpha)

                    if final_alpha <= 0:
                        continue

                    if p['size'] > 2.5:
                        glow_pen = QColor(255, 255, 255, int(final_alpha * 0.25))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(glow_pen)
                        painter.drawEllipse(QPointF(p['x'], p['y']), p['size'] * 2.2, p['size'] * 2.2)

                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(255, 255, 255, final_alpha))
                    painter.drawEllipse(QPointF(p['x'], p['y']), p['size'], p['size'])

            # -------------------------------------------------------------
            # 2. DRAW CENTER CONVERGENCE FLASH & SHOCKWAVE
            # -------------------------------------------------------------
            if 1.4 <= self._time < 1.9:
                flash_t = (self._time - 1.4) / 0.5
                flash_rad = 12.0 + math.sin(flash_t * math.pi) * 80.0
                flash_alpha = int(255 * math.sin(flash_t * math.pi) * global_alpha)
                if flash_alpha > 0:
                    grad = QRadialGradient(cx, cy - 30.0, flash_rad)
                    grad.setColorAt(0.0, QColor(255, 255, 255, flash_alpha))
                    grad.setColorAt(0.3, QColor(0, 240, 255, int(flash_alpha * 0.7)))
                    grad.setColorAt(1.0, QColor(0, 240, 255, 0))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(grad))
                    painter.drawEllipse(QPointF(cx, cy - 30.0), flash_rad, flash_rad)

            # Impact Shockwave at 2.5s
            if self._time >= 2.5:
                sw_prog = min(1.0, (self._time - 2.5) / 0.6)
                sw_rad = sw_prog * 480.0
                sw_alpha = int(255 * (1.0 - sw_prog) * global_alpha)
                if sw_alpha > 0:
                    sw_pen = QPen(QColor(0, 240, 255, sw_alpha), 3.0)
                    painter.setPen(sw_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPointF(cx, cy + 55.0), sw_rad, sw_rad * 0.6)

            # Impact Sparks
            if self._impact_sparks:
                painter.setPen(Qt.PenStyle.NoPen)
                for s in self._impact_sparks:
                    s_alpha = int(255 * s['alpha'] * global_alpha)
                    if s_alpha <= 0: continue
                    col = QColor(s['color'])
                    col.setAlpha(s_alpha)
                    painter.setBrush(col)
                    painter.drawEllipse(QPointF(s['x'], s['y']), s['size'], s['size'])

            # -------------------------------------------------------------
            # 3. DRAW "STELLA" TEXT & TYPOGRAPHY EFFECT
            # -------------------------------------------------------------
            if self._time >= 1.35:
                text_t = min(1.0, (self._time - 1.35) / 0.45)
                text_alpha = int(255 * text_t * global_alpha)

                spacing_prog = min(1.0, (self._time - 1.35) / 1.5)
                letter_spacing = 10.0 + (spacing_prog * 14.0)

                font_stella = QFont("Orbitron", 56, QFont.Weight.Black)
                font_stella.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
                painter.setFont(font_stella)

                rect_stella = QRectF(cx - 500, cy - 85, 1000, 90)

                # Outer text cyan glow
                glow_col = QColor(0, 240, 255, int(text_alpha * 0.45))
                painter.setPen(glow_col)
                for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)]:
                    painter.drawText(rect_stella.translated(ox, oy), Qt.AlignmentFlag.AlignCenter, "STELLA")

                # Core white text with dynamic shimmer
                if 1.8 <= self._time < 2.5:
                    shim_t = (self._time - 1.8) / 0.7
                    sweep_x = cx - 350 + (shim_t * 700)
                    grad = QLinearGradient(sweep_x - 120, cy, sweep_x + 120, cy)
                    grad.setColorAt(0.0, QColor(255, 255, 255, int(text_alpha * 0.75)))
                    grad.setColorAt(0.5, QColor(0, 240, 255, text_alpha))
                    grad.setColorAt(0.7, QColor(255, 255, 255, text_alpha))
                    grad.setColorAt(1.0, QColor(255, 255, 255, int(text_alpha * 0.75)))
                    painter.setPen(QPen(QBrush(grad), 1))
                else:
                    painter.setPen(QColor(255, 255, 255, text_alpha))

                painter.drawText(rect_stella, Qt.AlignmentFlag.AlignCenter, "STELLA")

            # -------------------------------------------------------------
            # 4. DRAW "AI - EVO" WITH MAXIMUM IMPACT (>= 2.5s)
            # -------------------------------------------------------------
            if self._time >= 2.5:
                evo_dt = self._time - 2.5
                evo_alpha = int(255 * min(1.0, evo_dt / 0.08) * global_alpha)

                slam_scale = 1.0
                if evo_dt < 0.18:
                    slam_t = evo_dt / 0.18
                    slam_scale = 1.5 - (0.5 * math.sin(slam_t * math.pi * 0.5))

                painter.save()
                painter.translate(cx, cy + 50.0)
                painter.scale(slam_scale, slam_scale)

                badge_w = 260.0
                badge_h = 44.0
                badge_rect = QRectF(-badge_w / 2.0, -badge_h / 2.0, badge_w, badge_h)

                painter.setPen(QPen(QColor(0, 240, 255, int(evo_alpha * 0.8)), 1.5))
                painter.setBrush(QColor(0, 20, 35, int(evo_alpha * 0.55)))
                painter.drawRoundedRect(badge_rect, 22.0, 22.0)

                font_sub = QFont("Exo 2", 18, QFont.Weight.Bold)
                font_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
                painter.setFont(font_sub)

                painter.setPen(QColor(220, 230, 245, evo_alpha))
                painter.drawText(QRectF(-badge_w / 2.0, -badge_h / 2.0, 125, badge_h), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "AI - ")

                font_evo = QFont("Orbitron", 20, QFont.Weight.Black)
                font_evo.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5.0)
                painter.setFont(font_evo)

                evo_glow = QColor(0, 240, 255, int(evo_alpha * 0.6))
                painter.setPen(evo_glow)
                for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    painter.drawText(QRectF(-badge_w / 2.0 + 130, -badge_h / 2.0, 115, badge_h).translated(ox, oy), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "EVO")

                painter.setPen(QColor(0, 240, 255, evo_alpha))
                painter.drawText(QRectF(-badge_w / 2.0 + 130, -badge_h / 2.0, 115, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "EVO")

                painter.restore()

            painter.end()
        except Exception as e:
            import traceback
            traceback.print_exc()

class IncomingAlertDialog(QDialog):
    decision = pyqtSignal(str)

    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        self._event = event or {}
        self._kind = (self._event.get("kind") or "message").strip().lower()
        self._app = (self._event.get("app") or "App").strip()
        self._title = (self._event.get("title") or "").strip()
        self._preview = (self._event.get("preview") or "").strip()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("IncomingAlertDialog")
        self.setMinimumWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        frame = QFrame()
        frame.setObjectName("IncomingAlertFrame")
        frame.setStyleSheet(f"""
            QFrame#IncomingAlertFrame {{
                background: rgba(8, 8, 8, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 16px;
            }}
        """)
        root.addWidget(frame)

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        heading = QLabel("Incoming Call" if self._kind == "call" else "Incoming Message")
        heading.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
        heading.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(heading)

        app_lbl = QLabel(f"From {self._app}")
        app_lbl.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        app_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(app_lbl)

        body = self._preview or self._title or "A notification was detected."
        body_lbl = QLabel(body)
        body_lbl.setWordWrap(True)
        body_lbl.setFont(QFont("Exo 2", 10))
        body_lbl.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(body_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        def _btn(text: str, *, primary: bool = False, danger: bool = False) -> QPushButton:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
            fg = C.WHITE
            border = C.BORDER_B if primary else C.BORDER
            bg = "C.TEXT" if primary else "rgba(14,14,14,235)"
            if danger:
                border = C.RED
                bg = "rgba(60,10,10,235)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: {fg};
                    border: 1px solid {border};
                    border-radius: 11px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background: C.TEXT;
                    border: 1px solid {C.WHITE};
                }}
            """)
            return btn

        if self._kind == "call":
            self._accept_btn = _btn("Pick up", primary=True)
            self._ignore_btn = _btn("Ignore")
            self._cut_btn = _btn("Cut call", danger=True)
            self._x_btn = _btn("X")
            self._accept_btn.clicked.connect(lambda: self._choose("accept"))
            self._ignore_btn.clicked.connect(lambda: self._choose("ignore"))
            self._cut_btn.clicked.connect(lambda: self._choose("cut"))
            self._x_btn.clicked.connect(lambda: self._choose("noop"))
            for btn in (self._accept_btn, self._ignore_btn, self._cut_btn, self._x_btn):
                btn_row.addWidget(btn)
        else:
            self._hear_btn = _btn("Hear it", primary=True)
            self._reply_btn = _btn("Reply")
            self._ignore_btn = _btn("Ignore")
            self._x_btn = _btn("X")
            self._hear_btn.clicked.connect(lambda: self._choose("hear"))
            self._reply_btn.clicked.connect(lambda: self._choose("reply"))
            self._ignore_btn.clicked.connect(lambda: self._choose("ignore"))
            self._x_btn.clicked.connect(lambda: self._choose("noop"))
            btn_row.addWidget(self._hear_btn)
            btn_row.addWidget(self._reply_btn)
            btn_row.addWidget(self._ignore_btn)
            btn_row.addWidget(self._x_btn)

        lay.addLayout(btn_row)

    def _choose(self, decision: str):
        self.decision.emit(decision)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._choose("ignore")
            return
        super().keyPressEvent(event)

class MeetingOverlay(QWidget):
    stop_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self._expanded_height = 142
        self._collapsed_height = 58
        self._collapsed = False
        self.setFixedHeight(self._expanded_height)
        self.setStyleSheet("background: transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 5, 5, 232);
                border: 1px solid {C.BORDER_B};
                border-radius: 18px;
            }}
        """)
        root.addWidget(frame)

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)

        self._badge = QLabel("MEETING MODE")
        self._badge.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._badge.setStyleSheet(
            f"color: {C.WHITE}; background: C.TEXT; border: 1px solid {C.BORDER_B}; border-radius: 10px; padding: 4px 10px;"
        )
        top.addWidget(self._badge)

        self._title = QLabel("Watching the meeting")
        self._title.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        top.addWidget(self._title)
        top.addStretch()

        self._min_btn = QPushButton("-")
        self._min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._min_btn.setFixedSize(28, 28)
        self._min_btn.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._min_btn.setToolTip("Minimize meeting bar")
        self._min_btn.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid {C.BORDER_B};
                border-radius: 9px;
            }}
            QPushButton:hover {{
                background: C.TEXT;
                border: 1px solid {C.WHITE};
            }}
        """)
        self._min_btn.clicked.connect(self._toggle_collapsed)
        top.addWidget(self._min_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setFixedHeight(28)
        self._stop_btn.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid {C.BORDER_B};
                border-radius: 9px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: C.TEXT;
                border: 1px solid {C.WHITE};
            }}
        """)
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        top.addWidget(self._stop_btn)

        self._close_btn = QPushButton("x")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._close_btn.setToolTip("Close meeting bar")
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid {C.BORDER_B};
                border-radius: 9px;
            }}
            QPushButton:hover {{
                background: C.TEXT;
                border: 1px solid {C.WHITE};
            }}
        """)
        self._close_btn.clicked.connect(self.close_requested.emit)
        top.addWidget(self._close_btn)
        lay.addLayout(top)

        self._summary = QLabel("Waiting for a meeting to start...")
        self._summary.setWordWrap(True)
        self._summary.setFont(QFont("Exo 2", 10))
        self._summary.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        lay.addWidget(self._summary)

        self._speech = QLabel("They said: nothing yet.")
        self._speech.setWordWrap(True)
        self._speech.setFont(QFont("Exo 2", 10))
        self._speech.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(self._speech)

        self._answer = QLabel("Stella will show the live answer here.")
        self._answer.setWordWrap(True)
        self._answer.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._answer.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        lay.addWidget(self._answer)

        self._apply_collapsed_state(False)

    def set_content(self, title: str, summary: str, answer: str, active: bool = True, speech: str = ""):
        self._title.setText(title or "Watching the meeting")
        self._summary.setText(summary or "Watching the meeting screen.")
        self._speech.setText(f"They said: {speech or 'nothing yet.'}")
        self._answer.setText(answer or "No question detected yet.")
        self._badge.setText("MEETING LIVE" if active else "MEETING MODE")

    def _apply_collapsed_state(self, collapsed: bool):
        self._collapsed = bool(collapsed)
        for widget in (self._summary, self._speech, self._answer):
            widget.setVisible(not self._collapsed)
        self._min_btn.setText("?" if self._collapsed else "-")
        self._min_btn.setToolTip("Restore meeting bar" if self._collapsed else "Minimize meeting bar")
        self.setFixedHeight(self._collapsed_height if self._collapsed else self._expanded_height)

    def set_collapsed(self, collapsed: bool):
        self._apply_collapsed_state(collapsed)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def _toggle_collapsed(self):
        self.minimize_requested.emit()

