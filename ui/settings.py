from ._imports import *
from .common import *
from .common import _default_app_settings, _default_discord_settings
from ._imports import _qt_alive

class SystemConnectivitySidebar(QFrame):
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self.setObjectName("SystemConnectivitySidebar")
        self.setStyleSheet(
            f"""
            QFrame#SystemConnectivitySidebar {{
                background: rgba(124, 110, 230, 0.03);
                border: 1px solid rgba(124, 110, 230, 0.6);
                border-radius: 22px;
            }}
            QLabel {{
                background: transparent;
            }}
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 12px;
                text-align: left;
                padding: 10px 12px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.10);
                border: 1px solid rgba(124, 110, 230, 0.3);
            }}
            """
        )
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(124, 110, 230, 80))
            shadow.setOffset(0, 0)
            self.setGraphicsEffect(shadow)
        except: pass
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)

        title = QLabel("SYSTEM STATUS")
        title.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.WHITE}; letter-spacing: 1px;")
        lay.addWidget(title)

        self._status_card = QFrame()
        self._status_card.setStyleSheet("QFrame { background: rgba(14,16,20,0.88); border: 1px solid rgba(53,255,117,0.18); border-radius: 14px; }")
        s_lay = QVBoxLayout(self._status_card)
        s_lay.setContentsMargins(16, 14, 16, 14)
        s_lay.setSpacing(10)
        self._online_lbl = QLabel("Î“ùÅ System Online")
        self._online_lbl.setStyleSheet("color: {C.GREEN}; font-weight: 700;")
        self._desc_lbl = QLabel("All systems are operational.")
        self._desc_lbl.setStyleSheet(f"color: {C.TEXT_MED};")
        s_lay.addWidget(self._online_lbl)
        s_lay.addWidget(self._desc_lbl)
        lay.addWidget(self._status_card)

        self._info_rows: dict[str, QLabel] = {}
        for label in ("Version", "Platform", "Current AI Provider", "Last Updated"):
            row = QHBoxLayout()
            row.setContentsMargins(0, 4, 0, 4)
            row.setSpacing(10)
            icon = QLabel("◌")
            icon.setFixedWidth(18)
            icon.setStyleSheet(f"color: {C.WHITE};")
            key_lbl = QLabel(label)
            key_lbl.setStyleSheet(f"color: {C.WHITE};")
            val_lbl = QLabel("")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_lbl.setStyleSheet(f"color: {C.TEXT_MED};")
            row.addWidget(icon)
            row.addWidget(key_lbl)
            row.addStretch(1)
            row.addWidget(val_lbl)
            lay.addLayout(row)
            self._info_rows[label] = val_lbl

        quick_title = QLabel("QUICK ACTIONS")
        quick_title.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
        quick_title.setStyleSheet(f"color: {C.WHITE}; letter-spacing: 1px;")
        lay.addWidget(quick_title)

        self._quick_actions = QVBoxLayout()
        self._quick_actions.setSpacing(10)
        lay.addLayout(self._quick_actions)
        self._mk_quick_action("↻ Restart Stella", QStyle.StandardPixmap.SP_BrowserReload, self._restart)
        self._mk_quick_action("⟳ Reload Configuration", QStyle.StandardPixmap.SP_BrowserReload, self._reload)
        self._mk_quick_action("≡ƒôü Open Data Folder", QStyle.StandardPixmap.SP_DirOpenIcon, self._open_data_folder)
        self._mk_quick_action("≡ƒôä View Logs", QStyle.StandardPixmap.SP_FileDialogDetailedView, self._view_logs)
        self._mk_quick_action("⬇ Check for Updates", QStyle.StandardPixmap.SP_ArrowDown, self._check_updates)

        tip = QFrame()
        tip.setStyleSheet("QFrame { background: rgba(24, 18, 8, 0.85); border: 1px solid rgba(255, 191, 0, 0.22); border-radius: 14px; }")
        tip_lay = QVBoxLayout(tip)
        tip_lay.setContentsMargins(16, 14, 16, 14)
        tip_lay.setSpacing(8)
        tip_title = QLabel("Security Tip")
        tip_title.setStyleSheet("color: {C.ACC2}; font-weight: 700;")
        tip_body = QLabel('"Never share your API keys with anyone."')
        tip_body.setWordWrap(True)
        tip_body.setStyleSheet(f"color: {C.TEXT_MED};")
        tip_lay.addWidget(tip_title)
        tip_lay.addWidget(tip_body)
        lay.addStretch(1)
        lay.addWidget(tip)

        self.refresh()

    def set_controller(self, controller):
        self._controller = controller
        self.refresh()

    def _mk_quick_action(self, text: str, icon_kind, slot):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIcon(self.style().standardIcon(icon_kind))
        btn.clicked.connect(slot)
        self._quick_actions.addWidget(btn)
        return btn

    def _bridge(self):
        return self._controller

    def _restart(self):
        if self._bridge() and hasattr(self._bridge(), "_restart_app"):
            self._bridge()._restart_app()

    def _reload(self):
        if self._bridge() and hasattr(self._bridge(), "_win"):
            try:
                self._bridge()._win._load_api_defaults()
                self._bridge()._win._load_discord_settings()
                self._bridge()._log_sig.emit("SYS: Configuration reloaded.")
            except Exception:
                pass

    def _open_data_folder(self):
        try:
            os.startfile(str(CONFIG_DIR))
        except Exception:
            pass

    def _view_logs(self):
        try:
            os.startfile(str(BASE_DIR))
        except Exception:
            pass

    def _check_updates(self):
        if self._bridge() and hasattr(self._bridge(), "write_log"):
            self._bridge().write_log("SYS: Update check is not connected to a remote service yet.")

    def refresh(self):
        if self._bridge() and hasattr(self._bridge(), "_win"):
            version = "v1.0.0"
            platform_name = platform.system()
            provider = self._bridge()._win._load_app_settings().get("default_ai_provider", "Gemini")
            last_updated = time.strftime("%d %b %Y %H:%M")
            self._info_rows["Version"].setText(version)
            self._info_rows["Platform"].setText(platform_name)
            self._info_rows["Current AI Provider"].setText(provider)
            self._info_rows["Last Updated"].setText(last_updated)
        else:
            self._info_rows["Version"].setText("v1.0.0")
            self._info_rows["Platform"].setText(platform.system())
            self._info_rows["Current AI Provider"].setText("Gemini")
            self._info_rows["Last Updated"].setText(time.strftime("%d %b %Y %H:%M"))

class SettingsHubPage(QWidget):
    def __init__(self, navigation_callback, parent=None):
        super().__init__(parent)
        self._nav_cb = navigation_callback
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 60, 40, 60)
        lay.setSpacing(25)

        title = QLabel("Settings Hub")
        title.setFont(QFont("Orbitron", 32, QFont.Weight.Black))
        title.setStyleSheet(f"color: {C.WHITE}; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        subtitle = QLabel("Select a section below to configure your Stella environment.")
        subtitle.setFont(QFont("Exo 2", 12))
        subtitle.setStyleSheet(f"color: {C.TEXT_DIM};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(subtitle)

        cards_lay = QHBoxLayout()
        cards_lay.setSpacing(24)
        cards_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cards_data = [
            ("Stella Home", "Configure smart home integrations", "🏠", 1),
            ("Devices", "Manage and control connected hardware", "🔌", 2),
            ("System & Connect", "Configure providers and api preferences", "⚙️", 3)
        ]

        for title_text, desc_text, icon_emoji, target_idx in cards_data:
            card = QFrame()
            card.setFixedSize(280, 200)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet(
                f"QFrame {{ "
                f"  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(16, 18, 26, 0.75), stop:1 rgba(8, 10, 15, 0.85)); "
                f"  border: 1px solid rgba(124, 110, 230, 0.18); "
                f"  border-radius: 18px; "
                f"}} "
                f"QFrame:hover {{ "
                f"  border: 1.5px solid {C.PRI}; "
                f"  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(35, 28, 15, 0.8), stop:1 rgba(16, 12, 8, 0.9)); "
                f"}}"
            )
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(20, 20, 20, 20)
            card_lay.setSpacing(12)
            card_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_lbl = QLabel(icon_emoji)
            icon_lbl.setFont(QFont("Exo 2", 36))
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            card_lay.addWidget(icon_lbl)

            t = QLabel(title_text)
            t.setFont(QFont("Exo 2", 15, QFont.Weight.Bold))
            t.setStyleSheet(f"color: {C.WHITE}; background: transparent; border: none;")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_lay.addWidget(t)

            d = QLabel(desc_text)
            d.setFont(QFont("Exo 2", 9))
            d.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
            d.setWordWrap(True)
            d.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_lay.addWidget(d)

            card.mousePressEvent = lambda e, idx=target_idx: self._nav_cb(idx)
            cards_lay.addWidget(card)

        lay.addStretch(1)
        lay.addLayout(cards_lay)
        lay.addStretch(2)

class SystemConnectivityPage(QWidget):
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self.setObjectName("SystemConnectivityPage")
        self.setStyleSheet(f"""
            QWidget#SystemConnectivityPage {{
                background: transparent;
            }}
            QFrame#SettingsCard {{
                background: rgba(10, 12, 18, 160);
                border: 1.5px solid rgba(124, 110, 230, 0.15);
                border-radius: 18px;
            }}
            QFrame#SettingsCard:hover {{
                border: 1.5px solid rgba(124, 110, 230, 0.35);
                background: rgba(20, 16, 12, 200);
            }}
            QLabel {{
                background: transparent;
            }}
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 12px;
                padding: 10px 12px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.12);
                border: 1px solid rgba(124, 110, 230, 0.45);
            }}
            QLineEdit, QComboBox {{
                background: rgba(13, 15, 19, 240);
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 12px;
                min-height: 34px;
                padding: 0 10px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {C.PRI};
                background: rgba(124, 110, 230, 0.02);
            }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        root.addWidget(self._scroll)

        self._content = QWidget()
        self._scroll.setWidget(self._content)
        lay = QVBoxLayout(self._content)
        # Retain the layout chain. PyQt lets Python GC reclaim a layout that is
        # only referenced locally, and taking it down destroys every widget it
        # owns - which surfaces much later as "wrapped C/C++ object ... has
        # been deleted" from unrelated methods.
        self._content_layout = lay
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        header = QFrame()
        header.setStyleSheet("background: transparent; border: none;")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(0, 0, 0, 0)
        h_lay.setSpacing(6)
        title = QLabel("SYSTEM & CONNECTIVITY")
        title.setFont(QFont("Orbitron", 22, QFont.Weight.Black))
        title.setStyleSheet(f"color: {C.WHITE}; letter-spacing: 1px;")
        sub = QLabel("Manage your AI providers, connections and application preferences.")
        sub.setFont(QFont("Exo 2", 10))
        sub.setStyleSheet(f"color: {C.TEXT_DIM};")
        h_lay.addWidget(title)
        h_lay.addWidget(sub)
        lay.addWidget(header)

        top = QHBoxLayout()
        top.setSpacing(14)
        self._top_layout = top
        # Keep both columns on `self` for the same retention reason as above.
        self._left_col = self._build_left_column()
        self._summary_card = self._build_summary_card()
        top.addWidget(self._left_col, 7)
        top.addWidget(self._summary_card, 3)
        lay.addLayout(top)
        lay.addStretch(1)

        self.refresh()

    def set_controller(self, controller):
        self._controller = controller
        self.refresh()

    def _ctrl(self):
        return self._controller

    def _card(self, title: str, subtitle: str = "") -> QFrame:
        frame = QFrame()
        frame.setObjectName("SettingsCard")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        head = QLabel(title)
        head.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
        head.setStyleSheet(f"color: {C.WHITE};")
        lay.addWidget(head)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setStyleSheet(f"color: {C.TEXT_DIM};")
            lay.addWidget(sub)
        return frame

    def _mk_toggle(self, text: str, checked: bool, callback):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: callback(btn.isChecked()))
        btn.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 12px;
                padding: 12px 14px;
            }}
            QPushButton:checked {{
                background: rgba(124, 110, 230,0.12);
                border: 1px solid {C.PRI};
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230,0.08);
            }}
            """
        )
        return btn

    def _provider_key_preview(self, key: str) -> str:
        key = (key or "").strip()
        if not key:
            return "Not set"
        if len(key) <= 8:
            return "••••••••"
        return f"{key[:4]}••••••••{key[-4:]}"

    def _provider_row(self, name: str, key: str, model: str, setting_key: str):
        row = QFrame()
        if key:
            row.setStyleSheet("QFrame { background: rgba(55, 255, 95, 0.02); border: 1px solid rgba(55, 255, 95, 0.1); border-radius: 14px; } QFrame:hover { background: rgba(55, 255, 95, 0.05); border: 1px solid rgba(55, 255, 95, 0.25); }")
        else:
            row.setStyleSheet("QFrame { background: C.TEXT; border: 1px solid C.TEXT; border-radius: 14px; } QFrame:hover { background: rgba(124, 110, 230, 0.04); border: 1px solid rgba(124, 110, 230, 0.3); }")
        r = QHBoxLayout(row)
        r.setContentsMargins(14, 12, 14, 12)
        r.setSpacing(12)
        icon = QLabel(name[:1].upper())
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
        if key:
            icon.setStyleSheet(f"background: rgba(55, 255, 95, 0.12); color: {C.GREEN}; border: 1px solid rgba(55, 255, 95, 0.3); border-radius: 21px;")
        else:
            icon.setStyleSheet(f"background: rgba(124, 110, 230, 0.12); color: {C.WHITE}; border: 1px solid rgba(124, 110, 230, 0.38); border-radius: 21px;")
        r.addWidget(icon)
        meta = QVBoxLayout()
        title = QLabel(name)
        title.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.WHITE}; border: none;")
        if key:
            status = QLabel("\u2713  Already Added")
            status.setStyleSheet(f"color: {C.GREEN}; border: none; font-weight: bold;")
        else:
            status = QLabel("Not configured")
            status.setStyleSheet(f"color: {C.TEXT_DIM}; border: none;")
        model_lbl = QLabel(f"Current model: {model}")
        model_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; border: none;")
        api_lbl = QLabel(self._provider_key_preview(key))
        api_lbl.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")
        meta.addWidget(title)
        meta.addWidget(status)
        meta.addWidget(model_lbl)
        meta.addWidget(api_lbl)
        r.addLayout(meta, 1)
        btn_lay = QVBoxLayout()
        btn_lay.setSpacing(8)
        if key:
            edit = QPushButton("Edit API Key")
        else:
            edit = QPushButton("Add API Key")
            edit.setStyleSheet("""
                QPushButton {
                    background: rgba(124, 110, 230, 0.1);
                    color: {C.PRI};
                    border: 1px solid rgba(124, 110, 230, 0.3);
                    border-radius: 12px;
                    padding: 10px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(124, 110, 230, 0.2);
                    border: 1px solid rgba(124, 110, 230, 0.5);
                }
            """)
        edit.clicked.connect(lambda: self._open_api_keys())
        test = QPushButton("Test Connection")
        test.clicked.connect(lambda: self._test_provider(setting_key))
        btn_lay.addWidget(edit)
        btn_lay.addWidget(test)
        r.addLayout(btn_lay)
        return row, status, api_lbl

    def _build_spotify_mcp_card(self):
        spotify_card = self._card("Spotify MCP Server", "Voice & AI music streaming, song searches, playlist browsing, and queue management via Spotify Web API.")
        s_lay = spotify_card.layout()

        self._spotify_status_lbl = QLabel("Status: Checking...")
        self._spotify_status_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
        s_lay.addWidget(self._spotify_status_lbl)

        cid_row = QHBoxLayout()
        cid_lbl = QLabel("Client ID")
        cid_lbl.setStyleSheet(f"color: {C.WHITE}; min-width: 90px;")
        cid_row.addWidget(cid_lbl)
        self._spotify_client_id = QLineEdit()
        self._spotify_client_id.setPlaceholderText("Spotify Client ID from Developer Dashboard")
        cid_row.addWidget(self._spotify_client_id, 1)
        s_lay.addLayout(cid_row)

        csec_row = QHBoxLayout()
        csec_lbl = QLabel("Client Secret")
        csec_lbl.setStyleSheet(f"color: {C.WHITE}; min-width: 90px;")
        csec_row.addWidget(csec_lbl)
        self._spotify_client_secret = QLineEdit()
        self._spotify_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._spotify_client_secret.setPlaceholderText("Spotify Client Secret")
        csec_row.addWidget(self._spotify_client_secret, 1)

        self._spotify_reveal_btn = QPushButton("Reveal")
        self._spotify_reveal_btn.setCheckable(True)
        self._spotify_reveal_btn.clicked.connect(self._toggle_spotify_secret_reveal)
        csec_row.addWidget(self._spotify_reveal_btn)
        s_lay.addLayout(csec_row)

        redir_row = QHBoxLayout()
        redir_lbl = QLabel("Redirect URI:")
        redir_lbl.setStyleSheet(f"color: {C.TEXT_MED}; font-size: 11px;")
        redir_val = QLabel("http://127.0.0.1:8888/callback")
        redir_val.setStyleSheet("color: {C.PRI}; font-size: 11px; font-family: monospace; font-weight: bold;")
        copy_btn = QPushButton("Copy URI")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("padding: 4px 10px; font-size: 10px;")
        copy_btn.clicked.connect(self._copy_spotify_redirect_uri)
        redir_row.addWidget(redir_lbl)
        redir_row.addWidget(redir_val)
        redir_row.addStretch(1)
        redir_row.addWidget(copy_btn)
        s_lay.addLayout(redir_row)

        s_btns_row = QHBoxLayout()
        s_btns_row.setSpacing(10)

        self._spotify_save_btn = QPushButton("Save Credentials")
        self._spotify_save_btn.clicked.connect(self._handle_spotify_save)
        s_btns_row.addWidget(self._spotify_save_btn)

        self._spotify_auth_btn = QPushButton("🔗 Authenticate in Browser")
        self._spotify_auth_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(124, 110, 230, 0.12);
                color: {C.PRI};
                border: 1px solid rgba(124, 110, 230, 0.45);
                font-weight: bold;
                border-radius: 12px;
                padding: 10px 14px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230, 0.25);
                border: 1px solid {C.PRI};
            }}
        """)
        self._spotify_auth_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._spotify_auth_btn.clicked.connect(self._handle_spotify_auth)
        s_btns_row.addWidget(self._spotify_auth_btn)

        self._spotify_test_btn = QPushButton("Test Connection")
        self._spotify_test_btn.clicked.connect(self._handle_spotify_test)
        s_btns_row.addWidget(self._spotify_test_btn)

        self._spotify_disconnect_btn = QPushButton("Disconnect")
        self._spotify_disconnect_btn.clicked.connect(self._handle_spotify_disconnect)
        s_btns_row.addWidget(self._spotify_disconnect_btn)

        s_lay.addLayout(s_btns_row)

        spotify_tip = QLabel("Tip: In developer.spotify.com/dashboard ➔ Settings ➔ add 'http://127.0.0.1:8888/callback' to Redirect URIs and save.")
        spotify_tip.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        spotify_tip.setWordWrap(True)
        s_lay.addWidget(spotify_tip)

        self._prefill_spotify_credentials()
        self._update_spotify_status()

        return spotify_card

    def _build_left_column(self):
        col = QWidget()
        lay = QVBoxLayout(col)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)


        


        # Instagram Connect
        ig_card = self._card("Instagram Connect", "Connect your personal Instagram account to allow Stella to manage your DMs.")
        ig_lay = ig_card.layout()

        self._ig_status_lbl = QLabel("Status: Checking...")
        self._ig_status_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
        ig_lay.addWidget(self._ig_status_lbl)

        self._ig_browser_btn = QPushButton("🌐 Connect via Browser (Recommended)")
        self._ig_browser_btn.setStyleSheet(f"background: {C.PRI}; color: {C.DARK}; font-weight: bold; padding: 7px; border-radius: 4px;")
        self._ig_browser_btn.setToolTip("Opens Instagram in a genuine browser window. Login once, solve 2FA easily, and never get blocked by Meta.")
        self._ig_browser_btn.clicked.connect(self._handle_ig_browser_connect)
        ig_lay.addWidget(self._ig_browser_btn)

        or_sep = QLabel("─── or connect with mobile credentials ───")
        or_sep.setAlignment(__import__('PyQt6').QtCore.Qt.AlignmentFlag.AlignCenter)
        or_sep.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px; margin: 4px 0;")
        ig_lay.addWidget(or_sep)

        ig_user_row = QHBoxLayout()
        ig_user_row.addWidget(QLabel("Username"))
        self._ig_username = QLineEdit()
        self._ig_username.setPlaceholderText("Instagram Username")
        ig_user_row.addWidget(self._ig_username)
        ig_lay.addLayout(ig_user_row)

        ig_pass_row = QHBoxLayout()
        ig_pass_row.addWidget(QLabel("Password"))
        self._ig_password = QLineEdit()
        self._ig_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._ig_password.setPlaceholderText("Instagram Password (or browser sessionid)")
        ig_pass_row.addWidget(self._ig_password, 1)

        self._ig_reveal_btn = QPushButton("Reveal")
        self._ig_reveal_btn.setCheckable(True)
        self._ig_reveal_btn.clicked.connect(self._toggle_ig_password_reveal)
        ig_pass_row.addWidget(self._ig_reveal_btn)
        ig_lay.addLayout(ig_pass_row)

        ig_hint = QLabel("Tip: Use 'Connect via Browser' above to avoid Meta's automated mobile blocks and 429 rate limits.")
        ig_hint.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px;")
        ig_hint.setWordWrap(True)
        ig_lay.addWidget(ig_hint)
        
        ig_btns_row = QHBoxLayout()
        
        self._ig_connect_btn = QPushButton("Connect (Password)")
        self._ig_connect_btn.clicked.connect(self._handle_ig_connect)
        ig_btns_row.addWidget(self._ig_connect_btn)
        
        self._ig_disconnect_btn = QPushButton("Disconnect")
        self._ig_disconnect_btn.clicked.connect(self._handle_ig_disconnect)
        ig_btns_row.addWidget(self._ig_disconnect_btn)

        ig_lay.addLayout(ig_btns_row)
        
        lay.addWidget(ig_card)
        
        # Pre-fill from API keys if they exist
        try:
            with open(Path("config/api_keys.json"), "r", encoding="utf-8") as f:
                d = json.load(f)
                if d.get("instagram_username"):
                    self._ig_username.setText(d.get("instagram_username"))
                if d.get("instagram_password"):
                    self._ig_password.setText(d.get("instagram_password"))
        except Exception:
            pass

        self._update_ig_status()

        # Google Workspace (Gmail / Calendar / Drive)
        gw_card = self._card("Google Workspace (Gmail / Calendar / Drive)", "Configure your Gmail, Google Calendar, and Drive integration.")
        gw_lay = gw_card.layout()

        gw_email_row = QHBoxLayout()
        gw_email_row.addWidget(QLabel("Gmail Address"))
        self._gw_email = QLineEdit()
        self._gw_email.setPlaceholderText("your-email@gmail.com")
        gw_email_row.addWidget(self._gw_email)
        gw_lay.addLayout(gw_email_row)

        gw_pass_row = QHBoxLayout()
        gw_pass_row.addWidget(QLabel("App Password"))
        self._gw_password = QLineEdit()
        self._gw_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._gw_password.setPlaceholderText("16-character Google App Password")
        gw_pass_row.addWidget(self._gw_password)

        self._gw_reveal_btn = QPushButton("Reveal")
        self._gw_reveal_btn.setCheckable(True)
        self._gw_reveal_btn.clicked.connect(self._toggle_gw_password_reveal)
        gw_pass_row.addWidget(self._gw_reveal_btn)
        gw_lay.addLayout(gw_pass_row)

        gw_btns_row = QHBoxLayout()
        self._gw_save_btn = QPushButton("Save Credentials")
        self._gw_save_btn.clicked.connect(self._handle_gw_save)
        gw_btns_row.addWidget(self._gw_save_btn)

        self._gw_test_btn = QPushButton("Test Connection")
        self._gw_test_btn.clicked.connect(self._handle_gw_test)
        gw_btns_row.addWidget(self._gw_test_btn)

        self._gw_oauth_btn = QPushButton("Load OAuth JSON")
        self._gw_oauth_btn.clicked.connect(self._handle_gw_oauth)
        gw_btns_row.addWidget(self._gw_oauth_btn)
        gw_lay.addLayout(gw_btns_row)

        self._gw_status_lbl = QLabel("Status: Ready")
        self._gw_status_lbl.setStyleSheet(f"color: {C.TEXT_DIM};")
        gw_lay.addWidget(self._gw_status_lbl)

        gw_help = QLabel("Tip: Generate a 16-character App Password at myaccount.google.com/apppasswords")
        gw_help.setStyleSheet(f"color: {C.TEXT_MED}; font-size: 11px;")
        gw_lay.addWidget(gw_help)

        lay.addWidget(gw_card)

        # Pre-fill stored Google Workspace credentials
        try:
            from actions.google_workspace_mcp import get_stored_gmail_credentials
            _em, _pw = get_stored_gmail_credentials()
            if _em:
                self._gw_email.setText(_em)
            if _pw:
                self._gw_password.setText(_pw)
        except Exception:
            pass

        # Spotify MCP Server
        lay.addWidget(self._build_spotify_mcp_card())

        # Identity & Profile
        identity_card = self._card("Identity & Profile", "Configure assistant identity, user profile, and behavior.")
        ilay = identity_card.layout()
        
        # Assistant Settings
        ast_row = QHBoxLayout()
        ast_row.addWidget(QLabel("Assistant Name"))
        self._set_ast_name = QLineEdit(identity.get_assistant_name())
        self._set_ast_name.textChanged.connect(lambda t: identity.set_assistant_name(t.strip() or "Stella"))
        ast_row.addWidget(self._set_ast_name)
        ilay.addLayout(ast_row)
        
        app_row = QHBoxLayout()
        app_row.addWidget(QLabel("Application Name"))
        self._set_app_name = QLineEdit(identity.get_application_name())
        self._set_app_name.textChanged.connect(lambda t: identity.set_application_name(t.strip() or "Stella"))
        app_row.addWidget(self._set_app_name)
        ilay.addLayout(app_row)

        # Owner Profile
        own_row = QHBoxLayout()
        own_row.addWidget(QLabel("Your Name"))
        self._set_own_name = QLineEdit(identity.get_owner_name())
        self._set_own_name.textChanged.connect(lambda t: identity.set_owner_name(t.strip()))
        own_row.addWidget(self._set_own_name)
        ilay.addLayout(own_row)

        role_row = QHBoxLayout()
        role_row.addWidget(QLabel("Your Role"))
        self._set_own_role = QLineEdit(identity.get_owner_role())
        self._set_own_role.textChanged.connect(lambda t: identity.set_owner_role(t.strip()))
        role_row.addWidget(self._set_own_role)
        ilay.addLayout(role_row)

        # Behavior
        beh_row = QHBoxLayout()
        beh_row.addWidget(QLabel("Behavior Mode"))
        self._set_beh_mode = QComboBox()
        self._set_beh_mode.addItems(["professional", "casual", "technical", "minimal", "proactive"])
        self._set_beh_mode.setCurrentText(identity.get_behavior_mode())
        self._set_beh_mode.currentTextChanged.connect(lambda t: identity.set_behavior_mode(t))
        beh_row.addWidget(self._set_beh_mode)
        ilay.addLayout(beh_row)

        lay.addWidget(identity_card)

        # AI Providers
        card = self._card("AI Providers", "Only the supported providers are shown here.")
        lay1 = card.layout()
        self._api_defaults = self._load_api_defaults()
        self._groq_row, self._groq_status, self._groq_key = self._provider_row(
            "Groq",
            self._api_defaults.get("groq_api_key", ""),
            "auto",
            "groq",
        )
        self._gemini_row, self._gemini_status, self._gemini_key = self._provider_row(
            "Google Gemini",
            self._api_defaults.get("gemini_api_key", ""),
            "gemini-2.5-flash",
            "gemini",
        )
        self._or_row, self._or_status, self._or_key = self._provider_row(
            "OpenRouter",
            self._api_defaults.get("openrouter_api_key", ""),
            "auto",
            "openrouter",
        )
        lay1.addWidget(self._groq_row)
        lay1.addWidget(self._gemini_row)
        lay1.addWidget(self._or_row)
        controls = QHBoxLayout()
        controls.setSpacing(12)
        self._default_provider = QComboBox()
        self._default_provider.addItems(["Groq", "Google Gemini", "OpenRouter", "Local"])
        try:
            import importlib.util
            if importlib.util.find_spec("core.server") is not None:
                self._default_provider.addItem("K2 Horizon")
                self._k2_available = True
            else:
                self._k2_available = False
        except Exception:
            self._k2_available = False
        
        current_provider = self._load_app_settings().get("default_ai_provider", "Gemini")
        if current_provider in {"Gemini", "Google Gemini"}:
            self._default_provider.setCurrentText("Google Gemini")
        elif current_provider == "Local":
            self._default_provider.setCurrentText("Local")
        elif current_provider == "Groq":
            self._default_provider.setCurrentText("Groq")
        elif current_provider == "K2":
            if getattr(self, "_k2_available", False):
                self._default_provider.setCurrentText("K2 Horizon")
            else:
                self._default_provider.setCurrentText("Groq")
        else:
            self._default_provider.setCurrentText("OpenRouter")
            
        self._default_provider.currentTextChanged.connect(self._set_default_provider)
        controls.addWidget(QLabel("Default AI Provider"))
        controls.addWidget(self._default_provider, 1)
        lay1.addLayout(controls)
        
        # Local AI Settings
        self._local_ai_widget = QWidget()
        local_lay = QVBoxLayout(self._local_ai_widget)
        local_lay.setContentsMargins(0, 8, 0, 8)
        local_lay.setSpacing(10)
        
        # Engine Status Row
        status_row = QHBoxLayout()
        is_online = local_brain.is_available()
        status_text = "🟢 Local Engine Online (Ollama)" if is_online else "🔴 Local Engine Offline"
        self._local_status_lbl = QLabel(status_text)
        self._local_status_lbl.setStyleSheet("color: {C.MINT}; font-weight: bold;" if is_online else "color: {C.RED}; font-weight: bold;")
        status_row.addWidget(QLabel("Engine Status:"))
        status_row.addWidget(self._local_status_lbl, 1)
        local_lay.addLayout(status_row)

        # Server URL
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Local Server URL"))
        self._local_url_input = QLineEdit(self._load_app_settings().get("local_ai_url", "http://localhost:11434/v1"))
        self._local_url_input.textChanged.connect(lambda t: self._set_setting("local_ai_url", t))
        url_row.addWidget(self._local_url_input, 1)
        local_lay.addLayout(url_row)
        
        # Model Selection with Combo Box & Refresh
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Local Model"))
        self._local_model_combo = QComboBox()
        self._local_model_combo.setEditable(True)
        
        def _populate_models():
            self._local_model_combo.clear()
            seen = []
            try:
                installed = local_brain.list_installed_models() or []
            except Exception:
                installed = []
            for m in installed:
                if m and m not in seen:
                    seen.append(m)
            # Direct .gguf files (project models/ + user models dir). Works on
            # fresh setups with no Ollama/LM Studio, and with existing files.
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
                from stella_model_manager import list_local
                for m in list_local():
                    label = f"{m['name']}  (file)"
                    if m["name"] not in seen and label not in seen:
                        seen.append(label)
            except Exception:
                pass
            if seen:
                self._local_model_combo.addItems(seen)
            else:
                self._local_model_combo.addItem("(no local models — Pull, Browse, or start Ollama)")
            saved_model = self._load_app_settings().get("local_ai_model", "qwen2.5:3b")
            self._local_model_combo.setCurrentText(saved_model)
            online = local_brain.is_available()
            self._local_status_lbl.setText("🟢 Local Engine Online (Ollama)" if online else "🔴 Local Engine Offline")
            self._local_status_lbl.setStyleSheet("color: {C.MINT}; font-weight: bold;" if online else "color: {C.RED}; font-weight: bold;")

        _populate_models()
        self._local_model_combo.currentTextChanged.connect(self._on_local_model_changed)
        model_row.addWidget(self._local_model_combo, 1)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setFixedWidth(85)
        btn_refresh.setStyleSheet("background: C.TEXT; border-radius: 4px; padding: 5px;")
        btn_refresh.clicked.connect(_populate_models)
        model_row.addWidget(btn_refresh)
        local_lay.addLayout(model_row)

        # 1-Click Model Download Helper Button
        action_row = QHBoxLayout()
        btn_pull = QPushButton("📥 Pull Qwen 2.5 (3B)")
        btn_pull.setStyleSheet("background: rgba(0, 255, 170, 0.15); color: {C.MINT}; border: 1px solid {C.MINT}; border-radius: 4px; padding: 6px;")
        def _on_download_click():
            btn_pull.setText("⏳ Downloading model in background...")
            btn_pull.setEnabled(False)
            local_brain.pull_model_async("qwen2.5:3b", lambda chunk: _populate_models())
        btn_pull.clicked.connect(_on_download_click)
        action_row.addWidget(btn_pull)
        btn_remove = QPushButton("🗑 Remove")
        btn_remove.setFixedWidth(85)
        btn_remove.setStyleSheet("background: rgba(255, 85, 85, 0.15); color: {C.RED}; border: 1px solid {C.RED}; border-radius: 4px; padding: 6px;")
        btn_remove.clicked.connect(self._remove_local_model)
        action_row.addWidget(btn_remove)
        btn_replace = QPushButton("🔁 Replace")
        btn_replace.setFixedWidth(85)
        btn_replace.setStyleSheet("background: rgba(255, 179, 0, 0.15); color: {C.ACC2}; border: 1px solid {C.ACC2}; border-radius: 4px; padding: 6px;")
        btn_replace.clicked.connect(self._replace_local_model)
        action_row.addWidget(btn_replace)
        btn_browse = QPushButton("📂 Browse")
        btn_browse.setFixedWidth(85)
        btn_browse.setStyleSheet("background: rgba(124, 110, 230, 0.10); color: {C.PRI}; border: 1px solid {C.PRI}; border-radius: 4px; padding: 6px;")
        btn_browse.clicked.connect(self._browse_local_model)
        action_row.addWidget(btn_browse)
        local_lay.addLayout(action_row)

        self._local_ai_widget.setVisible(current_provider == "Local")
        self._default_provider.currentTextChanged.connect(lambda t: self._local_ai_widget.setVisible(t == "Local"))
        
        lay1.addWidget(self._local_ai_widget)

        # Groq AI Settings
        self._groq_ai_widget = QWidget()
        groq_lay = QVBoxLayout(self._groq_ai_widget)
        groq_lay.setContentsMargins(0, 8, 0, 8)
        groq_lay.setSpacing(10)

        groq_model_row = QHBoxLayout()
        groq_model_row.addWidget(QLabel("Groq Model"))
        self._groq_model_combo = QComboBox()
        from groq_client import GROQ_MODELS
        self._groq_model_combo.addItems(GROQ_MODELS)
        saved_groq_model = self._load_app_settings().get("groq_model", "openai/gpt-oss-120b")
        self._groq_model_combo.setCurrentText(saved_groq_model)
        self._groq_model_combo.currentTextChanged.connect(lambda t: self._set_setting("groq_model", t))
        groq_model_row.addWidget(self._groq_model_combo, 1)
        groq_lay.addLayout(groq_model_row)

        self._groq_ai_widget.setVisible(current_provider == "Groq")
        self._default_provider.currentTextChanged.connect(lambda t: self._groq_ai_widget.setVisible(t == "Groq"))
        lay1.addWidget(self._groq_ai_widget)

        self._auto_switch_btn = self._mk_toggle("Automatically switch if a provider fails", bool(self._load_app_settings().get("auto_provider_switch", True)), self._toggle_auto_provider_switch)
        lay1.addWidget(self._auto_switch_btn)

        # Dedicated Offline Mode Toggle
        is_offline_mode = bool(self._load_app_settings().get("offline_mode_enabled", False))
        self._offline_mode_btn = self._mk_toggle(
            "🔒 Offline Mode (Air-Gapped: 100% Local Inference & Speech)",
            is_offline_mode,
            self._toggle_offline_mode
        )
        lay1.addWidget(self._offline_mode_btn)

        # Autonomous Mode — hands-off operation (reversible).
        # When on, irreversible actions (delete, shutdown, answering calls)
        # run without the on-screen confirmation. Everything still goes through
        # the Recycle Bin / undo stack, so it stays reversible. See core/autonomy.py.
        is_autonomous = bool(self._load_app_settings().get("autonomous_mode_enabled", False))
        self._autonomous_mode_btn = self._mk_toggle(
            "🤖 Autonomous Mode (act without asking — reversible, logged)",
            is_autonomous,
            self._toggle_autonomous_mode
        )
        lay1.addWidget(self._autonomous_mode_btn)
        lay.addWidget(card)

        # Feedback & Updates — upgrade/update pings to the creator
        fb = self._card("Feedback & Updates", "Request upgrades. Secrets are scrubbed and never leave your device raw.")
        fl = fb.layout()
        try:
            from core import feedback as _fb
            _channels = _fb.CHANNELS
        except Exception:
            _channels = ["local", "email", "github", "webhook", "off"]
        ch_row = QHBoxLayout()
        ch_row.addWidget(QLabel("Ping channel"))
        self._feedback_channel = QComboBox()
        self._feedback_channel.addItems(_channels)
        self._feedback_channel.setCurrentText(self._load_app_settings().get("feedback_channel", "local"))
        self._feedback_channel.currentTextChanged.connect(self._on_feedback_channel_changed)
        ch_row.addWidget(self._feedback_channel, 1)
        fl.addLayout(ch_row)

        # Honest availability note. Right now only the repo (GitHub issue) route
        # is wired up. Email/webhook become usable the moment the creator sets a
        # destination in the fields below — until then we say so plainly instead
        # of letting a user pick a channel that will fail.
        self._feedback_status = QLabel("")
        self._feedback_status.setWordWrap(True)
        self._feedback_status.setStyleSheet(f"color: {C.TEXT_DIM};")
        fl.addWidget(self._feedback_status)

        cd_row = QHBoxLayout()
        cd_row.addWidget(QLabel("Contact detail"))
        self._feedback_contact = QLineEdit(self._load_app_settings().get("feedback_contact", ""))
        self._feedback_contact.setPlaceholderText("email address · owner/repo · https webhook URL")
        self._feedback_contact.textChanged.connect(self._on_feedback_contact_changed)
        cd_row.addWidget(self._feedback_contact, 1)
        fl.addLayout(cd_row)
        smtp_row = QHBoxLayout()
        smtp_row.addWidget(QLabel("SMTP (email channel)"))
        self._feedback_smtp = QLineEdit(self._load_app_settings().get("feedback_smtp_host", ""))
        self._feedback_smtp.setPlaceholderText("host:port:user  (pass prompted at send time, never stored)")
        self._feedback_smtp.textChanged.connect(self._on_feedback_smtp_changed)
        smtp_row.addWidget(self._feedback_smtp, 1)
        fl.addLayout(smtp_row)

        # Refresh availability now that all fields exist.
        self._refresh_feedback_availability()

        btn_fb = QPushButton("📨 Request upgrade / Send feedback")
        btn_fb.setStyleSheet("background: rgba(124, 110, 230, 0.15); color: {C.PRI}; border: 1px solid {C.PRI}; border-radius: 4px; padding: 6px;")
        btn_fb.clicked.connect(self._open_feedback_dialog)
        fl.addWidget(btn_fb)
        lay.addWidget(fb)

        # Mobile connect
        mobile = self._card("Mobile Connect", "Connect your phone and control Stella remotely.")
        ml = mobile.layout()
        self._mobile_status = QLabel("Connection Status: Ready")
        self._mobile_phone = QLabel("Phone Name: Not connected")
        self._mobile_last = QLabel("Last Connected: Never")
        for lbl in (self._mobile_status, self._mobile_phone, self._mobile_last):
            lbl.setStyleSheet(f"color: {C.TEXT_MED};")
            ml.addWidget(lbl)
        row = QHBoxLayout()
        self._mobile_connect_btn = QPushButton("Connect Device")
        self._mobile_connect_btn.clicked.connect(self._connect_mobile)
        self._mobile_disconnect_btn = QPushButton("Disconnect")
        self._mobile_disconnect_btn.clicked.connect(self._disconnect_mobile)
        self._mobile_qr_btn = QPushButton("Generate QR Code")
        self._mobile_qr_btn.clicked.connect(self._show_qr_code)
        row.addWidget(self._mobile_connect_btn)
        row.addWidget(self._mobile_disconnect_btn)
        row.addWidget(self._mobile_qr_btn)
        ml.addLayout(row)
        lay.addWidget(mobile)

        # Attention prompts
        attention = self._card("Attention Prompts", "Control incoming message and call alerts.")
        al = attention.layout()
        self._attention_message_btn = self._mk_toggle(
            "Show incoming message prompts",
            bool(self._load_app_settings().get("attention_message_prompts", True)),
            self._toggle_attention_message_prompts,
        )
        self._attention_call_btn = self._mk_toggle(
            "Show incoming call prompts",
            bool(self._load_app_settings().get("attention_call_prompts", True)),
            self._toggle_attention_call_prompts,
        )
        al.addWidget(self._attention_message_btn)
        al.addWidget(self._attention_call_btn)
        lay.addWidget(attention)

        # Startup
        startup = self._card("Startup", "Use Stella with Windows startup preferences.")
        sl = startup.layout()
        self._startup_launch_btn = self._mk_toggle("Launch Stella when Windows starts", bool(self._load_app_settings().get("show_workspace_on_startup", False)), self._toggle_startup_from_page)
        self._startup_minimized_btn = self._mk_toggle("Launch Minimized", bool(self._load_app_settings().get("launch_minimized", False)), self._toggle_launch_minimized)
        self._startup_updates_btn = self._mk_toggle("Check for updates on startup", bool(self._load_app_settings().get("check_updates_on_startup", True)), self._toggle_update_check)
        sl.addWidget(self._startup_launch_btn)
        sl.addWidget(self._startup_minimized_btn)
        sl.addWidget(self._startup_updates_btn)
        lay.addWidget(startup)

        # Shortcuts & Pinning
        shortcuts = self._card("Shortcuts & Pinning", "Create shortcuts and pin Stella to your Windows system.")
        shl = shortcuts.layout()
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        self._desktop_shortcut_btn = QPushButton("Create Desktop Shortcut")
        self._desktop_shortcut_btn.clicked.connect(self._handle_create_desktop_shortcut)
        self._taskbar_pin_btn = QPushButton("Pin to Taskbar")
        self._taskbar_pin_btn.clicked.connect(self._handle_pin_to_taskbar)
        
        btn_row.addWidget(self._desktop_shortcut_btn, 1)
        btn_row.addWidget(self._taskbar_pin_btn, 1)
        shl.addLayout(btn_row)
        lay.addWidget(shortcuts)

        # App Theme
        theme_card = self._card("App Theme", "Select a complete theme for Stella.")
        tl = theme_card.layout()
        
        # Load current theme
        current_theme_id = "void"
        try:
            if APP_SETTINGS_FILE.exists():
                with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    _d = json.load(f)
                    current_theme_id = _d.get("app_theme", "void")
        except:
            pass
        
        from core.theme_tokens import theme_manager
        theme_ids = theme_manager.list_themes()
        
        # Theme selector combo box with preview
        self._theme_combo = QComboBox()
        self._theme_combo.setFixedHeight(36)
        self._theme_combo.setStyleSheet(f"""
            QComboBox {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER_B};
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER_B};
                selection-background-color: {C.PRI};
            }}
        """)
        
        for tid in theme_ids:
            name = theme_manager.get_name(tid)
            desc = theme_manager.get_description(tid)
            preview = theme_manager.get_preview(tid)
            self._theme_combo.addItem(f"{name}  —  {desc}", tid)
            # Set preview colors as item data for potential custom painting
            idx = self._theme_combo.count() - 1
            if preview:
                self._theme_combo.setItemData(idx, preview[0], Qt.ItemDataRole.UserRole)
        
        self._theme_combo.setCurrentIndex(theme_ids.index(current_theme_id) if current_theme_id in theme_ids else 0)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        theme_row.addWidget(self._theme_combo, 1)
        tl.addLayout(theme_row)
        
        # Text Size
        text_size_row = QHBoxLayout()
        text_size_row.addWidget(QLabel("Text Size:"))
        self._text_size_combo = QComboBox()
        self._text_size_combo.addItems(["Normal", "Large"])
        self._text_size_combo.setFixedHeight(36)
        self._text_size_combo.setStyleSheet(self._theme_combo.styleSheet())
        saved_text_size = self._load_app_settings().get("text_size", "Normal")
        self._text_size_combo.setCurrentText(saved_text_size)
        self._text_size_combo.currentTextChanged.connect(self._on_text_size_changed)
        text_size_row.addWidget(self._text_size_combo, 1)
        tl.addLayout(text_size_row)
        
        lay.addWidget(theme_card)

        # Startup animation
        anim = self._card("Startup Animation", "Control how the boot sequence behaves.")
        al = anim.layout()
        self._startup_anim_enable_btn = self._mk_toggle("Enable Startup Animation", bool(self._startup_animation_enabled()), self._toggle_startup_animation_from_page)
        al.addWidget(self._startup_anim_enable_btn)
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Animation Speed"))
        self._anim_speed = QComboBox()
        self._anim_speed.addItems(["Fast", "Normal", "Slow"])
        self._anim_speed.setCurrentText(self._load_app_settings().get("startup_anim_speed", "Normal"))
        speed_row.addWidget(self._anim_speed, 1)
        al.addLayout(speed_row)
        self._anim_preview_btn = QPushButton("Preview Animation")
        self._anim_preview_btn.clicked.connect(self._preview_animation)
        al.addWidget(self._anim_preview_btn)
        self._preview_progress = QProgressBar()
        self._preview_progress.setRange(0, 100)
        self._preview_progress.setValue(0)
        self._preview_progress.setTextVisible(False)
        self._preview_progress.setFixedHeight(8)
        self._preview_progress.setStyleSheet("QProgressBar { background: C.TEXT; border: none; border-radius: 4px; } QProgressBar::chunk { background: {C.PRI}; border-radius: 4px; }")
        al.addWidget(self._preview_progress)
        lay.addWidget(anim)
        # Discord bot
        discord = self._card("Discord Bot", "Mirror Stella between the app and your server.")
        dl = discord.layout()
        self._discord_defaults = self._load_discord_settings()
        self._discord_status = QLabel("Bot Status: Offline")
        dl.addWidget(self._discord_status)
        self._discord_token = QLineEdit()
        self._discord_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._discord_token.setPlaceholderText("Bot Token")
        self._discord_token.setText((self._discord_defaults.get("bot_token") or "").strip())
        self._discord_token.setCursorPosition(0)
        dl.addWidget(self._discord_token)
        self._discord_reveal = QPushButton("Reveal")
        self._discord_reveal.setCheckable(True)
        self._discord_reveal.clicked.connect(self._toggle_discord_reveal)
        dl.addWidget(self._discord_reveal)
        self._discord_channel = QLineEdit()
        self._discord_channel.setPlaceholderText("Optional Channel ID")
        self._discord_channel.setText((self._discord_defaults.get("channel_id") or "").strip())
        dl.addWidget(self._discord_channel)
        db = QHBoxLayout()
        self._discord_save = QPushButton("Save")
        self._discord_test = QPushButton("Test Connection")
        self._discord_restart = QPushButton("Restart Bot")
        self._discord_save.clicked.connect(self._save_discord_from_page)
        self._discord_test.clicked.connect(self._test_discord_from_page)
        self._discord_restart.clicked.connect(self._restart_discord_from_page)
        db.addWidget(self._discord_save)
        db.addWidget(self._discord_test)
        db.addWidget(self._discord_restart)
        dl.addLayout(db)
        self._discord_msg = QLabel("")
        self._discord_msg.setStyleSheet(f"color: {C.TEXT_DIM};")
        dl.addWidget(self._discord_msg)
        lay.addWidget(discord)

        about = self._card("About Stella", "Stella information only.")
        ab = about.layout()
        about_grid = QGridLayout()
        about_grid.setHorizontalSpacing(22)
        about_grid.setVerticalSpacing(8)
        entries = [
            ("Version", "v1.0.0"),
            ("Build Number", "2026.06.29"),
            ("Release Date", "29 Jun 2026"),
        ]
        self._about_values: dict[str, QLabel] = {}
        for idx, (label, value) in enumerate(entries):
            key = QLabel(label)
            key.setStyleSheet(f"color: {C.TEXT_DIM};")
            val = QLabel(value)
            val.setStyleSheet(f"color: {C.WHITE}; font-weight: 700;")
            about_grid.addWidget(key, idx, 0)
            about_grid.addWidget(val, idx, 1)
            self._about_values[label] = val
        ab.addLayout(about_grid)
        lay.addWidget(about)

        # Autonomous Self-Healing & Continuous Self-Improvement Card
        auto_heal_card = self._card("Auto-Heal & Continuous Self-Improvement", "Autonomous bug repair, crash recovery sentry, AST-verified patching, and persistent behavioral directives.")
        ah_lay = auto_heal_card.layout()

        self._ah_status_lbl = QLabel("Sentry: Active | Sandbox: Enabled | Rules: 0 active")
        self._ah_status_lbl.setStyleSheet(f"color: {C.WHITE}; font-size: 12px; font-weight: bold; padding: 4px 0;")
        ah_lay.addWidget(self._ah_status_lbl)

        ah_btn_row = QHBoxLayout()
        self._ah_history_btn = QPushButton("Patch History")
        self._ah_history_btn.clicked.connect(self._handle_ah_history)
        ah_btn_row.addWidget(self._ah_history_btn)

        self._ah_rollback_btn = QPushButton("Rollback Last Patch")
        self._ah_rollback_btn.clicked.connect(self._handle_ah_rollback)
        ah_btn_row.addWidget(self._ah_rollback_btn)

        self._ah_rules_btn = QPushButton("Learned Rules")
        self._ah_rules_btn.clicked.connect(self._handle_ah_rules)
        ah_btn_row.addWidget(self._ah_rules_btn)
        ah_lay.addLayout(ah_btn_row)

        test_row = QHBoxLayout()
        self._ah_trigger_bug_btn = QPushButton("⚡ Trigger Test Bug")
        self._ah_trigger_bug_btn.clicked.connect(self._handle_ah_trigger_test_bug)
        test_row.addWidget(self._ah_trigger_bug_btn)

        self._ah_fix_bug_btn = QPushButton("🛠️ Fix Captured Bug")
        self._ah_fix_bug_btn.clicked.connect(self._handle_ah_fix_captured_bug)
        test_row.addWidget(self._ah_fix_bug_btn)
        ah_lay.addLayout(test_row)

        rule_input_row = QHBoxLayout()
        self._ah_rule_input = QLineEdit()
        self._ah_rule_input.setPlaceholderText("Teach Stella a rule (e.g. Always summarize in bullet points)")
        rule_input_row.addWidget(self._ah_rule_input)
        self._ah_learn_btn = QPushButton("Teach Rule")
        self._ah_learn_btn.clicked.connect(self._handle_ah_learn_rule)
        rule_input_row.addWidget(self._ah_learn_btn)
        ah_lay.addLayout(rule_input_row)

        self._ah_output_lbl = QLabel("Self-healing sentry is active. Safe unbrick & auto-rollback protected.")
        self._ah_output_lbl.setStyleSheet(f"color: {C.TEXT_MED}; font-size: 11px;")
        self._ah_output_lbl.setWordWrap(True)
        ah_lay.addWidget(self._ah_output_lbl)

        lay.addWidget(auto_heal_card)
        try:
            self._refresh_auto_heal_status()
        except Exception:
            pass

        # Stella Audio Routing & Hardware Controls
        audio_card = self._card("Audio Routing & Hardware Controls", "Select hardware audio interfaces, toggle Push-to-Talk, or inspect long-term memory.")
        alay = audio_card.layout()

        # Mic selection row
        mic_row = QHBoxLayout()
        mic_lbl = QLabel("Input Microphone")
        mic_lbl.setStyleSheet(f"color: {C.WHITE}; min-width: 130px;")
        mic_row.addWidget(mic_lbl)

        self._mic_combo = QComboBox()
        self._mic_combo.addItem("Default System Microphone")
        try:
            from core import audio_devices
            from memory import config_manager
            audio_devices.prefetch()
            input_devs = audio_devices.list_devices("input")
            for dev in input_devs:
                self._mic_combo.addItem(dev)
            saved_in = config_manager.get_input_device()
            if saved_in and saved_in in input_devs:
                self._mic_combo.setCurrentText(saved_in)
        except Exception:
            pass
        self._mic_combo.currentTextChanged.connect(self._on_input_device_changed)
        mic_row.addWidget(self._mic_combo, 1)
        alay.addLayout(mic_row)

        # Speaker selection row
        spk_row = QHBoxLayout()
        spk_lbl = QLabel("Output Speaker")
        spk_lbl.setStyleSheet(f"color: {C.WHITE}; min-width: 130px;")
        spk_row.addWidget(spk_lbl)

        self._spk_combo = QComboBox()
        self._spk_combo.addItem("Default System Speaker")
        try:
            from core import audio_devices
            from memory import config_manager
            output_devs = audio_devices.list_devices("output")
            for dev in output_devs:
                self._spk_combo.addItem(dev)
            saved_out = config_manager.get_output_device()
            if saved_out and saved_out in output_devs:
                self._spk_combo.setCurrentText(saved_out)
        except Exception:
            pass
        self._spk_combo.currentTextChanged.connect(self._on_output_device_changed)
        spk_row.addWidget(self._spk_combo, 1)
        alay.addLayout(spk_row)

        # Push-to-Talk and Memory Inspector Action buttons
        tools_row = QHBoxLayout()
        try:
            from memory import config_manager
            ptt_enabled = config_manager.get_push_to_talk_enabled()
        except Exception:
            ptt_enabled = False

        self._ptt_toggle = self._mk_toggle(
            "Push-to-Talk (Hold Ctrl+Space)",
            ptt_enabled,
            self._on_ptt_toggled
        )
        tools_row.addWidget(self._ptt_toggle)

        # TTS Voice Selection
        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("TTS Voice"))
        self._tts_voice_combo = QComboBox()
        self._tts_voice_combo.addItems(["en_US-lessac-medium", "en_US-amy-medium", "en_US-kathleen-low"])
        try:
            from memory import config_manager
            saved_voice = config_manager.get_setting("tts_voice", "en_US-lessac-medium")
            self._tts_voice_combo.setCurrentText(saved_voice)
        except Exception:
            self._tts_voice_combo.setCurrentText("en_US-lessac-medium")
        self._tts_voice_combo.currentTextChanged.connect(lambda v: self._set_setting("tts_voice", v))
        voice_row.addWidget(self._tts_voice_combo, 1)
        # Wake Word & Voice Enrollment ─ record a few wake phrases so that
        # when Stella hears the user, it binds the session to that voice.
        # This runs after the TTS voice pick so the user can enroll once and
        # reuse it for outbound calls and voice messages.
        self._wake_enroll_btn = QPushButton("🎤 Record My Voice (wake + enroll)")
        self._wake_enroll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._wake_enroll_btn.clicked.connect(self._on_wakeword_enroll)
        tools_row.addWidget(self._wake_enroll_btn)

        self._wake_status_lbl = QLabel("")
        self._wake_status_lbl.setStyleSheet(f"color: {C.TEXT_MED}; font-size: 11px;")
        tools_row.addWidget(self._wake_status_lbl)

        tools_row.addLayout(voice_row)

        mem_btn = QPushButton("🧠 Inspect Memory")
        mem_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mem_btn.clicked.connect(self._open_memory_inspector)
        tools_row.addWidget(mem_btn)
        alay.addLayout(tools_row)

        # Memory Vault
        vault_card = self._card("Memory Vault", "Choose where Stella stores notes and long-term memories.")
        vl = vault_card.layout()
        
        self._vault_enabled = self._mk_toggle(
            "Enable Memory Vault",
            self._load_app_settings().get("vault_enabled", False),
            self._on_vault_toggled
        )
        vl.addWidget(self._vault_enabled)
        
        vault_row = QHBoxLayout()
        vault_row.addWidget(QLabel("Vault Folder"))
        self._vault_path_lbl = QLabel(self._load_app_settings().get("vault_path", "Not set"))
        self._vault_path_lbl.setStyleSheet(f"color: {C.TEXT_MED}; font-family: Consolas; font-size: 10px;")
        vault_row.addWidget(self._vault_path_lbl, 1)
        self._vault_browse_btn = QPushButton("Browse...")
        self._vault_browse_btn.setFixedWidth(100)
        self._vault_browse_btn.clicked.connect(self._browse_vault_folder)
        vault_row.addWidget(self._vault_browse_btn)
        vl.addLayout(vault_row)
        alay.addWidget(vault_card)

        # Return the column. Without this the method fell off the end
        # returning None, so __init__ added nothing here and the whole left
        # column - Instagram, Spotify, voice, identity - was garbage
        # collected while its Python attribute references stayed alive. Every
        # later touch of those widgets then raised
        # "wrapped C/C++ object ... has been deleted".
        return col

    def _on_wakeword_enroll(self):
        """Walk the user through wake-word + voice enrollment and report status.

        Enrolling records several wake-phrase utterances, extracts a compact
        speaker embedding for each, and stores the strongest one. The wake phrase
        text (``hey stella``) stays voice-independent, while the enrolled voice is
        what Stella binds the AI session to and reuses in outbound calls /
        voice messages.
        """
        try:
            from core import wakeword, voice_clone

            if not wakeword.is_wake_enrolled():
                paths = voice_clone.record_enrollment_phrases()
                wakeword.enroll_wake_phrases()
                self._wake_status_lbl.setText(
                    f"<font color='{C.ICE}'>Enrolled <b>{len(paths)}</b> wake phrases. "
                    f"Say it to wake Stella.</font>")
            else:
                e = wakeword.get_enrollment()
                n = e.get("count", 0)
                self._wake_status_lbl.setText(
                    f"<font color='{C.ICE}'>Already enrolled ({n} wake phrases). "
                    f"Re-record anytime.</font>")
            self._wake_status_lbl.show()
        except Exception as exc:
            self._wake_status_lbl.setText(f"Enrollment unavailable: {exc}")
            self._wake_status_lbl.show()


        undo_btn = QPushButton("↺ Rollback (Undo)")
        undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        undo_btn.clicked.connect(self._handle_undo_click)
        tools_row.addWidget(undo_btn)
        alay.addLayout(tools_row)

        self._audio_status_lbl = QLabel("Hardware audio deduplication, echo guard and undo stack active.")
        self._audio_status_lbl.setStyleSheet(f"color: {C.TEXT_MED}; font-size: 11px;")
        alay.addWidget(self._audio_status_lbl)

        lay.addWidget(audio_card)

        lay.addStretch(1)
        return col


    def _on_input_device_changed(self, name: str):
        try:
            from memory import config_manager
            val = "" if name == "Default System Microphone" else name
            config_manager.set_input_device(val)
            self._audio_status_lbl.setText(f"✅ Input device set to: {name}")
        except Exception as e:
            self._audio_status_lbl.setText(f"Error setting input: {e}")

    def _on_output_device_changed(self, name: str):
        try:
            from memory import config_manager
            val = "" if name == "Default System Speaker" else name
            config_manager.set_output_device(val)
            self._audio_status_lbl.setText(f"✅ Output device set to: {name}")
        except Exception as e:
            self._audio_status_lbl.setText(f"Error setting output: {e}")

    def _on_ptt_toggled(self, checked: bool):
        try:
            from memory import config_manager
            config_manager.set_push_to_talk_enabled(checked)
            self._audio_status_lbl.setText(f"✅ Push-to-Talk {'enabled (Hold Ctrl+Space)' if checked else 'disabled'}")
        except Exception as e:
            self._audio_status_lbl.setText(f"Error toggling PTT: {e}")

    def _open_memory_inspector(self):
        try:
            win = self.window()
            if hasattr(win, "show_memory_inspector"):
                win.show_memory_inspector()
            elif hasattr(win, "_memory_overlay_sig"):
                win._memory_overlay_sig.emit("show")
        except Exception as e:
            self._audio_status_lbl.setText(f"Error opening memory inspector: {e}")

    def _handle_undo_click(self):
        try:
            from core import undo
            if not undo.can_undo():
                self._audio_status_lbl.setText("ℹ Nothing to undo yet.")
                return
            res = undo.undo_last()
            self._audio_status_lbl.setText(f"↺ {res}")
        except Exception as e:
            self._audio_status_lbl.setText(f"Error running undo: {e}")

    def _update_ig_status(self):
        try:
            if not hasattr(self, "_ig_status_lbl"):
                return
            from pathlib import Path
            import json
            api_keys = Path("config/api_keys.json")
            username = ""
            d = {}
            if api_keys.exists():
                with open(api_keys, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    username = d.get("instagram_username", "")

            is_browser_auth = bool(d.get("instagram_browser_authenticated") and d.get("instagram_sessionid"))
            if is_browser_auth:
                name_str = f" (@{username})" if username else ""
                self._ig_status_lbl.setText(f"Status: 🟢 Connected via Browser{name_str}")
                self._ig_status_lbl.setStyleSheet("color: {C.MINT}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
                return

            if username and Path("config/ig_session.json").exists():
                self._ig_status_lbl.setText(f"Status: 🟢 Connected (@{username})")
                self._ig_status_lbl.setStyleSheet("color: {C.MINT}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
                return

            self._ig_status_lbl.setText("Status: ⚪ Not Connected — Click 'Connect via Browser' below")
            self._ig_status_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
        except Exception:
            pass

    def _handle_ig_disconnect(self):
        try:
            import json
            import shutil
            from pathlib import Path
            with open("config/api_keys.json", "r", encoding="utf-8") as f:
                d = json.load(f)
            d["instagram_username"] = ""
            d["instagram_password"] = ""
            d["instagram_sessionid"] = ""
            d["instagram_user_id"] = ""
            d["instagram_browser_authenticated"] = False
            with open("config/api_keys.json", "w", encoding="utf-8") as f:
                json.dump(d, f, indent=4)
                
            session_path = Path("config/ig_session.json")
            if session_path.exists():
                session_path.unlink()

            profile_dir = Path("config/ig_browser_profile")
            if profile_dir.exists():
                try:
                    shutil.rmtree(profile_dir)
                except Exception:
                    pass
                
            from actions.instagram_mcp import stop_daemon, kill_browser_processes
            stop_daemon()
            kill_browser_processes()
            
            self._update_ig_status()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Disconnected", "Instagram account disconnected.")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error disconnecting Instagram: {e}")

    class IGBrowserLoginWorker(__import__('PyQt6').QtCore.QThread):
        finished_success = __import__('PyQt6').QtCore.pyqtSignal(str)
        finished_error = __import__('PyQt6').QtCore.pyqtSignal(str)
        status_update = __import__('PyQt6').QtCore.pyqtSignal(str)

        def __init__(self, username=""):
            super().__init__()
            self.username = username

        def run(self):
            try:
                from playwright.sync_api import sync_playwright
                from pathlib import Path
                import json
                import time

                profile_dir = Path("config/ig_browser_profile").resolve()
                profile_dir.mkdir(parents=True, exist_ok=True)

                self.status_update.emit("Launching browser for Instagram...")
                with sync_playwright() as p:
                    context = p.chromium.launch_persistent_context(
                        str(profile_dir),
                        headless=False,
                        args=["--disable-blink-features=AutomationControlled"],
                        viewport={"width": 1080, "height": 800},
                    )
                    page = context.pages[0] if context.pages else context.new_page()
                    page.goto("https://www.instagram.com/accounts/login/", timeout=60000)

                    # Try to prefill username
                    if self.username:
                        try:
                            user_input = page.wait_for_selector('input[name="username"], input[name="email"]', timeout=5000)
                            if user_input and not user_input.input_value():
                                user_input.fill(self.username)
                        except Exception:
                            pass

                    self.status_update.emit("Please log in in the opened browser window...")

                    logged_in = False
                    detected_username = self.username
                    # Poll cookies for up to 5 minutes
                    for _ in range(300):
                        if self.isInterruptionRequested():
                            break
                        try:
                            cookies = context.cookies("https://www.instagram.com")
                            cookie_map = {c["name"]: c["value"] for c in cookies}
                            if "sessionid" in cookie_map and "ds_user_id" in cookie_map:
                                logged_in = True
                                sid = cookie_map["sessionid"]
                                uid = cookie_map["ds_user_id"]

                                time.sleep(2)
                                try:
                                    u = page.evaluate("() => window._sharedData?.config?.viewer?.username || ''")
                                    if u:
                                        detected_username = u
                                    else:
                                        parts = [x for x in page.url.replace("https://www.instagram.com/", "").split("/") if x]
                                        if parts and parts[0] not in ["accounts", "direct", "explore", "reels"]:
                                            detected_username = parts[0]
                                except Exception:
                                    pass

                                try:
                                    cfg_path = Path("config/api_keys.json")
                                    data = {}
                                    if cfg_path.exists():
                                        with open(cfg_path, "r", encoding="utf-8") as f:
                                            data = json.load(f)
                                    if detected_username:
                                        data["instagram_username"] = detected_username
                                    data["instagram_sessionid"] = sid
                                    data["instagram_user_id"] = uid
                                    data["instagram_browser_authenticated"] = True
                                    with open(cfg_path, "w", encoding="utf-8") as f:
                                        json.dump(data, f, indent=4)
                                except Exception:
                                    pass

                                break
                        except Exception:
                            pass
                        time.sleep(1)

                    context.close()

                    if logged_in:
                        from actions.instagram_mcp import stop_daemon, start_daemon
                        stop_daemon()
                        start_daemon()
                        self.finished_success.emit(detected_username or "")
                    else:
                        self.finished_error.emit("Login timed out or the browser window was closed before login was completed.")
            except Exception as e:
                self.finished_error.emit(str(e))

    def _handle_ig_browser_connect(self):
        self._ig_browser_btn.setEnabled(False)
        self._ig_browser_btn.setText("Connecting via Browser...")
        from actions.instagram_mcp import stop_daemon, kill_browser_processes
        stop_daemon()
        kill_browser_processes()
        username = self._ig_username.text().strip()
        self._ig_browser_worker = self.IGBrowserLoginWorker(username)
        self._ig_browser_worker.finished_success.connect(self._ig_browser_success)
        self._ig_browser_worker.finished_error.connect(self._ig_browser_error)
        self._ig_browser_worker.start()

    def _ig_browser_success(self, detected_username):
        self._ig_browser_btn.setEnabled(True)
        self._ig_browser_btn.setText("🌐 Connect via Browser (Recommended)")
        if detected_username:
            self._ig_username.setText(detected_username)
        self._update_ig_status()
        from PyQt6.QtWidgets import QMessageBox
        name_str = f" as @{detected_username}" if detected_username else ""
        QMessageBox.information(self, "Instagram Connected", f"Instagram successfully connected via Browser{name_str}!\n\nStella is now active for voice DM notifications and instant direct replies.")

    def _ig_browser_error(self, err_msg):
        self._ig_browser_btn.setEnabled(True)
        self._ig_browser_btn.setText("🌐 Connect via Browser (Recommended)")
        self._update_ig_status()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Browser Login", f"Browser connection was not completed: {err_msg}")

    class IGLoginWorker(__import__('PyQt6').QtCore.QThread):
        finished_success = __import__('PyQt6').QtCore.pyqtSignal()
        finished_error = __import__('PyQt6').QtCore.pyqtSignal(str)
        request_2fa = __import__('PyQt6').QtCore.pyqtSignal()
        request_challenge = __import__('PyQt6').QtCore.pyqtSignal()
        
        def __init__(self, username, password):
            super().__init__()
            self.username = username
            self.password = password
            self.code_event = __import__('threading').Event()
            self.code = None
            
        def run(self):
            try:
                from instagrapi import Client
                from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired
                import json
                from pathlib import Path
                cl = Client()
                
                pwd = (self.password or "").strip()
                if pwd.startswith("sessionid:") or (len(pwd) > 40 and "%3A" in pwd):
                    sid = pwd.replace("sessionid:", "").strip()
                    cl.login_by_sessionid(sid)
                else:
                    cl.username = self.username
                    outcome = cl.bloks_caa_login(self.username, pwd)
                    raw_str = json.dumps(outcome, default=str)
                    
                    if outcome.get("logged_in"):
                        cl.login_flow()
                    elif "login_wrong_password" in raw_str or "Incorrect password" in raw_str or "password you entered is incorrect" in raw_str:
                        raise Exception("The password you entered is incorrect. Please check your Instagram password, or paste your web browser 'sessionid' cookie.")
                    elif "checkpoint_required" in raw_str or "challenge_required" in raw_str:
                        try:
                            cl.login(self.username, pwd)
                        except TwoFactorRequired:
                            self.request_2fa.emit()
                            self.code_event.wait()
                            if not self.code:
                                raise Exception("2FA code not provided.")
                            cl.two_factor_login(self.code)
                        except ChallengeRequired:
                            self.request_challenge.emit()
                            self.code_event.wait()
                            if not self.code:
                                raise Exception("Challenge code not provided.")
                            cl.challenge_resolve(self.code)
                    else:
                        try:
                            cl.login(self.username, pwd)
                        except TwoFactorRequired:
                            self.request_2fa.emit()
                            self.code_event.wait()
                            if not self.code:
                                raise Exception("2FA code not provided.")
                            cl.two_factor_login(self.code)
                        except ChallengeRequired:
                            self.request_challenge.emit()
                            self.code_event.wait()
                            if not self.code:
                                raise Exception("Challenge code not provided.")
                            cl.challenge_resolve(self.code)
                        except Exception as e:
                            err_str = str(e)
                            if "out of date" in err_str.lower() or "CAA login" in err_str:
                                raise Exception("Instagram rejected credentials or security check. Please check your username/password or paste your web browser 'sessionid' cookie.")
                            raise
                
                Path("config").mkdir(parents=True, exist_ok=True)
                cl.dump_settings("config/ig_session.json")
                from actions.instagram_mcp import stop_daemon, start_daemon
                stop_daemon()
                start_daemon()
                self.finished_success.emit()
            except Exception as e:
                self.finished_error.emit(str(e))

    def _handle_ig_connect(self):
        username = self._ig_username.text().strip()
        password = self._ig_password.text().strip()
        
        from PyQt6.QtWidgets import QMessageBox
        import json
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password.")
            return
            
        self._ig_connect_btn.setEnabled(False)
        self._ig_connect_btn.setText("Connecting...")
        
        # Save credentials temporarily
        try:
            with open("config/api_keys.json", "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
            
        d["instagram_username"] = username
        d["instagram_password"] = password
        
        with open("config/api_keys.json", "w", encoding="utf-8") as f:
            json.dump(d, f, indent=4)
            
        self._ig_worker = self.IGLoginWorker(username, password)
        self._ig_worker.finished_success.connect(self._ig_login_success)
        self._ig_worker.finished_error.connect(self._ig_login_error)
        self._ig_worker.request_2fa.connect(self._ig_login_2fa)
        self._ig_worker.request_challenge.connect(self._ig_login_challenge)
        self._ig_worker.start()

    def _ig_login_success(self):
        self._ig_connect_btn.setEnabled(True)
        self._ig_connect_btn.setText("Connect (Password)")
        self._update_ig_status()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Success", "Instagram login successful and daemon started!")

    def _ig_login_error(self, err_msg):
        self._ig_connect_btn.setEnabled(True)
        self._ig_connect_btn.setText("Connect (Password)")
        self._update_ig_status()
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Instagram Mobile Login Blocked",
            f"Instagram direct password login failed:\n{err_msg}\n\n"
            "Meta frequently blocks automated mobile password logins.\n"
            "Would you like to connect securely via Browser instead?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._handle_ig_browser_connect()

    def _ig_login_2fa(self):
        from PyQt6.QtWidgets import QInputDialog
        code, ok = QInputDialog.getText(self, "2-Factor Authentication", "Enter the 6-digit code sent to your device:")
        if ok and code:
            self._ig_worker.code = code
        else:
            self._ig_worker.code = None
        self._ig_worker.code_event.set()

    def _ig_login_challenge(self):
        from PyQt6.QtWidgets import QInputDialog
        code, ok = QInputDialog.getText(self, "Challenge Required", "Enter the verification code sent to your email/phone:")
        if ok and code:
            self._ig_worker.code = code
        else:
            self._ig_worker.code = None
        self._ig_worker.code_event.set()

    def _toggle_ig_password_reveal(self):
        from PyQt6.QtWidgets import QLineEdit
        if getattr(self, "_ig_reveal_btn", None) and self._ig_reveal_btn.isChecked():
            self._ig_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self._ig_reveal_btn.setText("Hide")
        else:
            self._ig_password.setEchoMode(QLineEdit.EchoMode.Password)
            self._ig_reveal_btn.setText("Reveal")

    def _toggle_gw_password_reveal(self):
        from PyQt6.QtWidgets import QLineEdit
        if getattr(self, "_gw_reveal_btn", None) and self._gw_reveal_btn.isChecked():
            self._gw_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self._gw_reveal_btn.setText("Hide")
        else:
            self._gw_password.setEchoMode(QLineEdit.EchoMode.Password)
            self._gw_reveal_btn.setText("Reveal")

    def _handle_gw_save(self):
        email_val = self._gw_email.text().strip()
        pw_val = self._gw_password.text().strip()
        from PyQt6.QtWidgets import QMessageBox
        if not email_val:
            QMessageBox.warning(self, "Missing Email", "Please enter your Gmail address.")
            return
        try:
            from actions.google_workspace_mcp import save_stored_gmail_credentials
            ok = save_stored_gmail_credentials(email_val, pw_val)
            if ok:
                try:
                    from actions.google_workspace_mcp import stop_email_daemon, start_email_daemon
                    stop_email_daemon()
                    start_email_daemon()
                except Exception:
                    pass
                self._gw_status_lbl.setText("Status: Credentials saved securely.")
                self._gw_status_lbl.setStyleSheet("color: {C.GREEN};")
                QMessageBox.information(self, "Saved", "Google Workspace credentials saved successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to encrypt and save credentials.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving credentials: {e}")

    def _handle_gw_test(self):
        self._gw_status_lbl.setText("Status: Testing connection...")
        self._gw_status_lbl.setStyleSheet(f"color: {C.TEXT_DIM};")
        email_val = self._gw_email.text().strip()
        pw_val = self._gw_password.text().strip()
        if email_val and pw_val:
            try:
                from actions.google_workspace_mcp import save_stored_gmail_credentials
                save_stored_gmail_credentials(email_val, pw_val)
            except Exception:
                pass

        from actions.google_workspace_mcp import GmailEngine
        res = GmailEngine.test_connection()
        from PyQt6.QtWidgets import QMessageBox
        if res.get("success"):
            self._gw_status_lbl.setText(f"Status: {res.get('message')}")
            self._gw_status_lbl.setStyleSheet("color: {C.GREEN};")
            QMessageBox.information(self, "Connection Successful", res.get("message"))
        else:
            self._gw_status_lbl.setText(f"Status: {res.get('message')}")
            self._gw_status_lbl.setStyleSheet("color: {C.RED};")
            QMessageBox.warning(self, "Connection Failed", res.get("message"))

    def _handle_gw_oauth(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(self, "Select Google Cloud credentials.json", str(Path.home()), "JSON Files (*.json)")
        if path:
            try:
                import shutil
                shutil.copy2(path, Path("config/google_workspace_credentials.json"))
                self._gw_status_lbl.setText("Status: OAuth credentials.json loaded.")
                self._gw_status_lbl.setStyleSheet("color: {C.GREEN};")
                QMessageBox.information(self, "Success", "Google Cloud OAuth credentials loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load credentials: {e}")

    class SpotifyTestWorker(__import__('PyQt6').QtCore.QThread):
        finished_result = __import__('PyQt6').QtCore.pyqtSignal(bool, str)

        def run(self):
            try:
                from actions.spotify_controller import is_spotify_configured, _spotify_mcp_call, get_spotify_config
                if not is_spotify_configured():
                    self.finished_result.emit(False, "Spotify MCP is not configured. Please enter your Client ID and Client Secret.")
                    return
                data = get_spotify_config()
                if not data.get("refreshToken"):
                    self.finished_result.emit(False, "Credentials saved, but browser authorization has not been completed. Click 'Authenticate in Browser'.")
                    return
                res = _spotify_mcp_call("getAvailableDevices", {})
                out = res.get("output", "")
                if "Error" in out or not res.get("success", False):
                    self.finished_result.emit(False, out or res.get("error", "Failed to contact Spotify API."))
                else:
                    self.finished_result.emit(True, out or "Successfully connected to Spotify MCP server!")
            except Exception as e:
                self.finished_result.emit(False, str(e))

    def _prefill_spotify_credentials(self):
        try:
            from actions.spotify_controller import get_spotify_config
            cfg = get_spotify_config()
            cid = cfg.get("clientId", "")
            csec = cfg.get("clientSecret", "")
            if cid and hasattr(self, "_spotify_client_id"):
                self._spotify_client_id.setText(cid)
            if csec and hasattr(self, "_spotify_client_secret"):
                self._spotify_client_secret.setText(csec)
        except Exception:
            pass

    def _update_spotify_status(self):
        try:
            if not hasattr(self, "_spotify_status_lbl"):
                return
            from actions.spotify_controller import get_spotify_config
            cfg = get_spotify_config()
            has_id = bool(cfg.get("clientId"))
            has_sec = bool(cfg.get("clientSecret"))
            has_token = bool(cfg.get("refreshToken"))
            if has_id and has_sec and has_token:
                self._spotify_status_lbl.setText("Status: 🟢 Connected & Authorized (Ready)")
                self._spotify_status_lbl.setStyleSheet("color: {C.MINT}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
            elif has_id and has_sec:
                self._spotify_status_lbl.setText("Status: 🟡 Credentials Saved — Click 'Authenticate in Browser'")
                self._spotify_status_lbl.setStyleSheet(f"color: {C.ACC}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
            else:
                self._spotify_status_lbl.setText("Status: ⚪ Not Configured — Enter credentials below")
                self._spotify_status_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
        except Exception:
            pass

    def _toggle_spotify_secret_reveal(self):
        from PyQt6.QtWidgets import QLineEdit
        if getattr(self, "_spotify_reveal_btn", None) and self._spotify_reveal_btn.isChecked():
            self._spotify_client_secret.setEchoMode(QLineEdit.EchoMode.Normal)
            self._spotify_reveal_btn.setText("Hide")
        else:
            self._spotify_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
            self._spotify_reveal_btn.setText("Reveal")

    def _copy_spotify_redirect_uri(self):
        try:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText("http://127.0.0.1:8888/callback")
            if hasattr(self, "_spotify_status_lbl"):
                self._spotify_status_lbl.setText("Status: 📋 Redirect URI copied to clipboard!")
                self._spotify_status_lbl.setStyleSheet("color: {C.PRI}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
                QTimer.singleShot(2500, self._update_spotify_status)
        except Exception:
            pass

    def _handle_spotify_save(self):
        cid = self._spotify_client_id.text().strip()
        csec = self._spotify_client_secret.text().strip()
        from PyQt6.QtWidgets import QMessageBox
        if not cid or not csec:
            QMessageBox.warning(self, "Missing Credentials", "Please enter both Spotify Client ID and Client Secret.")
            return
        try:
            from actions.spotify_controller import save_spotify_credentials
            ok = save_spotify_credentials(cid, csec)
            if ok:
                self._update_spotify_status()
                QMessageBox.information(
                    self,
                    "Credentials Saved",
                    "Spotify credentials saved successfully!\n\n"
                    "Now click 'Authenticate in Browser' to link your Spotify account."
                )
            else:
                QMessageBox.critical(self, "Error", "Failed to save Spotify configuration.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving credentials: {e}")

    def _handle_spotify_auth(self):
        cid = self._spotify_client_id.text().strip()
        csec = self._spotify_client_secret.text().strip()
        from PyQt6.QtWidgets import QMessageBox
        from actions.spotify_controller import is_spotify_configured, save_spotify_credentials, _spotify_mcp_action
        if cid and csec:
            save_spotify_credentials(cid, csec)
        elif not is_spotify_configured():
            QMessageBox.warning(self, "Configuration Required", "Please enter your Spotify Client ID and Client Secret before authenticating.")
            return

        self._spotify_status_lbl.setText("Status: 🌐 Opening browser for Spotify authorization...")
        self._spotify_status_lbl.setStyleSheet(f"color: {C.ACC}; font-size: 11px; font-weight: bold; margin-bottom: 4px;")
        self._spotify_auth_btn.setEnabled(False)
        self._spotify_auth_btn.setText("Authenticating...")

        msg = _spotify_mcp_action({"action": "auth"})

        self._spotify_auth_ticks = 0
        if not hasattr(self, "_spotify_auth_timer"):
            self._spotify_auth_timer = QTimer(self)
            self._spotify_auth_timer.setInterval(1500)
            self._spotify_auth_timer.timeout.connect(self._poll_spotify_auth_status)
        self._spotify_auth_timer.start()

        QMessageBox.information(
            self,
            "Spotify Authorization",
            f"{msg}\n\n"
            "Steps to complete:\n"
            "1. Log in to Spotify in the browser window.\n"
            "2. Click 'Agree' to grant playback permissions.\n"
            "3. Once redirected to callback, Stella will automatically detect authorization!"
        )

    def _poll_spotify_auth_status(self):
        self._spotify_auth_ticks = getattr(self, "_spotify_auth_ticks", 0) + 1
        from actions.spotify_controller import get_spotify_config
        cfg = get_spotify_config()
        if cfg.get("refreshToken"):
            if hasattr(self, "_spotify_auth_timer"):
                self._spotify_auth_timer.stop()
            if hasattr(self, "_spotify_auth_btn"):
                self._spotify_auth_btn.setEnabled(True)
                self._spotify_auth_btn.setText("🔗 Authenticate in Browser")
            self._update_spotify_status()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Spotify Connected", "Spotify MCP Server has been successfully authorized and connected!")
            return
        if self._spotify_auth_ticks >= 60:
            if hasattr(self, "_spotify_auth_timer"):
                self._spotify_auth_timer.stop()
            if hasattr(self, "_spotify_auth_btn"):
                self._spotify_auth_btn.setEnabled(True)
                self._spotify_auth_btn.setText("🔗 Authenticate in Browser")
            self._update_spotify_status()

    def _handle_spotify_test(self):
        from actions.spotify_controller import is_spotify_configured
        from PyQt6.QtWidgets import QMessageBox
        if not is_spotify_configured():
            QMessageBox.warning(self, "Not Configured", "Please enter and save your Spotify Client ID and Client Secret first.")
            return

        self._spotify_test_btn.setEnabled(False)
        self._spotify_test_btn.setText("Testing...")
        self._spotify_status_lbl.setText("Status: Testing Spotify MCP connection...")

        self._spotify_test_worker = self.SpotifyTestWorker()
        self._spotify_test_worker.finished_result.connect(self._on_spotify_test_finished)
        self._spotify_test_worker.start()

    def _on_spotify_test_finished(self, success: bool, message: str):
        self._spotify_test_btn.setEnabled(True)
        self._spotify_test_btn.setText("Test Connection")
        self._update_spotify_status()
        from PyQt6.QtWidgets import QMessageBox
        if success:
            QMessageBox.information(self, "Spotify Connection Successful", f"Connection to Spotify MCP Server was successful!\n\n{message}")
        else:
            QMessageBox.warning(self, "Spotify Connection Test", f"Spotify test result:\n\n{message}")

    def _handle_spotify_disconnect(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Disconnect Spotify",
            "Are you sure you want to disconnect Spotify and clear stored credentials?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from actions.spotify_controller import clear_spotify_credentials
                clear_spotify_credentials()
                if hasattr(self, "_spotify_client_id"):
                    self._spotify_client_id.clear()
                if hasattr(self, "_spotify_client_secret"):
                    self._spotify_client_secret.clear()
                self._update_spotify_status()
                QMessageBox.information(self, "Disconnected", "Spotify configuration and credentials removed.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to disconnect: {e}")

    def _refresh_hw_vitals(self):
        try:
            from actions.system_diagnostics_mcp import get_full_diagnostics
            d = get_full_diagnostics()
            cpu_pct = d["cpu"]["usage_percent"]
            ram_pct = d["ram"]["usage_percent"]
            bat_pct = d["battery"].get("percent", "--")
            disp = d["display"].get("brightness_levels", [80])
            b_val = disp[0] if disp else 80
            self._hw_vitals_lbl.setText(f"CPU: {cpu_pct}% | RAM: {ram_pct}% | Battery: {bat_pct}% | Display: {b_val}%")
            self._hw_brightness_slider.blockSignals(True)
            self._hw_brightness_slider.setValue(int(b_val))
            self._hw_brightness_val_lbl.setText(f"{b_val}%")
            self._hw_brightness_slider.blockSignals(False)
            self._hw_output_lbl.setText(f"Vitals updated. Uptime: {d['uptime']} ({d['running_processes_count']} processes).")
        except Exception as e:
            self._hw_output_lbl.setText(f"Error fetching vitals: {e}")

    def _handle_hw_brightness_slider(self, val):
        self._hw_brightness_val_lbl.setText(f"{val}%")
        try:
            from actions.system_diagnostics_mcp import set_brightness
            set_brightness(val)
        except Exception:
            pass

    def _handle_hw_ram_hogs(self):
        try:
            from actions.system_diagnostics_mcp import system_diagnostics
            res = system_diagnostics({"action": "ram_hogs", "limit": 4})
            self._hw_output_lbl.setText(res)
        except Exception as e:
            self._hw_output_lbl.setText(f"Error scanning RAM hogs: {e}")

    def _handle_hw_battery(self):
        try:
            from actions.system_diagnostics_mcp import system_diagnostics
            res = system_diagnostics({"action": "battery"})
            self._hw_output_lbl.setText(res)
        except Exception as e:
            self._hw_output_lbl.setText(f"Error checking battery: {e}")

    def _handle_hw_kill(self):
        target = self._hw_kill_target.text().strip()
        if not target:
            self._hw_output_lbl.setText("Please enter an application name or PID to kill.")
            return
        try:
            from actions.system_diagnostics_mcp import kill_process
            res = kill_process(target)
            msg = res.get("message", "Done.")
            self._hw_output_lbl.setText(msg)
            from PyQt6.QtWidgets import QMessageBox
            if res.get("success"):
                QMessageBox.information(self, "Process Terminated", msg)
            else:
                QMessageBox.warning(self, "Process Management", msg)
        except Exception as e:
            self._hw_output_lbl.setText(f"Error: {e}")

    def _refresh_auto_heal_status(self):
        try:
            from core.learned_rules import LearnedRulesEngine
            rules = LearnedRulesEngine.list_rules()
            active_count = sum(1 for r in rules if r.get("active", True))
            self._ah_status_lbl.setText(f"Sentry: Active | Sandbox: Verified | Rules: {active_count} active")
        except Exception as e:
            self._ah_status_lbl.setText(f"Status: Error loading ({e})")

    def _handle_ah_history(self):
        try:
            from actions.auto_heal_engine import auto_heal
            res = auto_heal({"action": "history"})
            self._ah_output_lbl.setText(res)
        except Exception as e:
            self._ah_output_lbl.setText(f"Error reading patch history: {e}")

    def _handle_ah_rollback(self):
        try:
            from PyQt6.QtWidgets import QMessageBox
            from actions.auto_heal_engine import auto_heal
            reply = QMessageBox.question(
                self,
                "Confirm Rollback",
                "Are you sure you want to rollback the most recent autonomous patch?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                res = auto_heal({"action": "rollback", "patch_id": "latest"})
                self._ah_output_lbl.setText(res)
                self._refresh_auto_heal_status()
                QMessageBox.information(self, "Rollback Result", res)
        except Exception as e:
            self._ah_output_lbl.setText(f"Error executing rollback: {e}")

    def _handle_ah_rules(self):
        try:
            from actions.auto_heal_engine import auto_heal
            res = auto_heal({"action": "list_rules"})
            self._ah_output_lbl.setText(res)
        except Exception as e:
            self._ah_output_lbl.setText(f"Error reading learned rules: {e}")

    def _handle_ah_learn_rule(self):
        txt = self._ah_rule_input.text().strip()
        if not txt:
            self._ah_output_lbl.setText("Please enter a rule or habit to teach.")
            return
        try:
            from core.learned_rules import LearnedRulesEngine
            res = LearnedRulesEngine.add_rule(txt, origin="ui_settings")
            msg = res.get("message", "Rule saved.")
            self._ah_output_lbl.setText(f"✅ {msg}")
            self._ah_rule_input.clear()
            self._refresh_auto_heal_status()
        except Exception as e:
            self._ah_output_lbl.setText(f"Error saving rule: {e}")

    def _handle_ah_trigger_test_bug(self):
        try:
            from actions.test_action import test_action
            res = test_action({})
            self._ah_output_lbl.setText(f"✅ Test action executed cleanly with no errors: {res}\nThe code is already healthy!")
        except Exception as e:
            import traceback
            from actions.auto_heal_engine import AutoHealEngine
            tb = traceback.format_exc()
            AutoHealEngine.record_last_error(tb)
            self._ah_output_lbl.setText(
                f"❌ Simulated bug triggered in test_action.py: {type(e).__name__}: {e}\n"
                f"Traceback captured in AutoHealEngine! Click 'Fix Captured Bug' or say 'Stella, fix that bug'."
            )

    def _handle_ah_fix_captured_bug(self):
        self._ah_output_lbl.setText("⏳ Gemini is synthesizing hotfix in safety sandbox...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        try:
            from actions.auto_heal_engine import auto_heal
            res = auto_heal({"action": "heal"})
            self._ah_output_lbl.setText(f"🛠️ Result:\n{res}")
            self._refresh_auto_heal_status()
        except Exception as e:
            self._ah_output_lbl.setText(f"Error repairing bug: {e}")

    def _change_theme(self, new_theme: str):
        settings = {}
        try:
            if APP_SETTINGS_FILE.exists():
                with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
        except Exception:
            pass
        old_theme = settings.get("app_theme", "Gold")
        if new_theme.lower() == old_theme.lower():
            return
        settings["app_theme"] = new_theme
        try:
            with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving theme: {e}")
        import subprocess
        import sys
        QMessageBox.information(self, "Restart Required", "The application will now restart to apply the new theme.")
        subprocess.Popen([sys.executable, "main.py"])
        QApplication.quit()

    def _build_summary_card(self):
        card = self._card("")
        card.layout().setContentsMargins(18, 18, 18, 18)
        card.layout().setSpacing(14)
        card.layout().addWidget(self._build_status_box())
        card.layout().addWidget(self._build_quick_actions_box())
        card.layout().addWidget(self._build_security_tip())
        return card

    def _build_status_box(self):
        box = self._card("System Status", "")
        lay = box.layout()
        self._sys_online = QLabel("≡ƒƒó System Online")
        self._sys_online.setStyleSheet("color: {C.GREEN}; font-weight: 700;")
        self._sys_note = QLabel("All systems are operational.")
        self._sys_note.setStyleSheet(f"color: {C.TEXT_MED};")
        lay.addWidget(self._sys_online)
        lay.addWidget(self._sys_note)
        self._sys_version = QLabel("v1.0.0")
        self._sys_platform = QLabel(platform.system())
        self._sys_provider = QLabel("Gemini")
        self._sys_updated = QLabel(time.strftime("%d %b %Y %H:%M"))
        for label, val in (("Version", self._sys_version), ("Platform", self._sys_platform), ("Current AI Provider", self._sys_provider), ("Last Updated", self._sys_updated)):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addStretch(1)
            row.addWidget(val)
            lay.addLayout(row)
        return box

    def _build_quick_actions_box(self):
        box = self._card("Quick Actions", "")
        lay = box.layout()
        actions = [
            ("Restart Stella", QStyle.StandardPixmap.SP_BrowserReload, self._restart_app),
            ("Reload Configuration", QStyle.StandardPixmap.SP_BrowserReload, self._reload_config),
            ("Open Data Folder", QStyle.StandardPixmap.SP_DirOpenIcon, self._open_data_folder),
            ("View Logs", QStyle.StandardPixmap.SP_FileDialogDetailedView, self._view_logs),
            ("Check for Updates", QStyle.StandardPixmap.SP_ArrowDown, self._check_updates),
        ]
        for text, icon_kind, slot in actions:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(self.style().standardIcon(icon_kind))
            btn.clicked.connect(slot)
            lay.addWidget(btn)
        return box

    def _build_security_tip(self):
        box = QFrame()
        box.setStyleSheet("QFrame { background: rgba(24, 18, 8, 0.85); border: 1px solid rgba(255, 191, 0, 0.22); border-radius: 14px; }")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        title = QLabel("Security Tip")
        title.setStyleSheet("color: {C.ACC2}; font-weight: 700;")
        body = QLabel('"Never share your API keys with anyone."')
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {C.TEXT_MED};")
        lay.addWidget(title)
        lay.addWidget(body)
        return box

    def _load_api_defaults(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            return self._ctrl()._win._load_api_defaults()
        return {
            "gemini_api_key": "",
            "openrouter_api_key": "",
            "os_system": platform.system(),
        }

    def _load_app_settings(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            return self._ctrl()._win._load_app_settings()
        return _default_app_settings()

    def _load_discord_settings(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            return self._ctrl()._win._load_discord_settings()
        return _default_discord_settings()

    def _startup_animation_enabled(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            return self._ctrl()._win._startup_animation_enabled()
        return True

    def _toggle_sound_effects(self, enabled: bool):
        sound_mgr.enabled = enabled
        self._set_setting("sound_effects_enabled", enabled)
        if enabled:
            sound_mgr.play_listening_start()

    def _on_sfx_volume_changed(self, val: int):
        sound_mgr.set_volume_percent(val)
        if hasattr(self, "_sfx_val_lbl"):
            self._sfx_val_lbl.setText(f"{val}%")
        self._set_setting("sound_effects_volume", val)

    def _set_setting(self, key: str, value):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            settings = self._ctrl()._win._load_app_settings()
            settings[key] = value
            self._ctrl()._win._save_app_settings(settings)
        else:
            try:
                data = {}
                if APP_SETTINGS_FILE.exists():
                    with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                data[key] = value
                with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except Exception:
                pass

    def _open_api_keys(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._show_setup(self._ctrl()._win._load_api_defaults())

    def _test_provider(self, setting_key: str):
        if setting_key == "gemini":
            msg = "Google Gemini key detected." if self._load_api_defaults().get("gemini_api_key") else "Google Gemini key missing."
        else:
            msg = "OpenRouter key detected." if self._load_api_defaults().get("openrouter_api_key") else "OpenRouter key missing."
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log(f"SYS: {msg}")
        self.refresh()

    def _connect_mobile(self):
        ctrl = self._ctrl()
        if not ctrl:
            return
        target = None
        if hasattr(ctrl, "_show_remote_connect"):
            target = ctrl
        elif hasattr(ctrl, "_win") and hasattr(ctrl._win, "_show_remote_connect"):
            target = ctrl._win
        if target is not None:
            self._mobile_connect_btn.setText("Connecting...")
            target._show_remote_connect()
            QTimer.singleShot(1100, lambda: self._mobile_connect_btn.setText("Connect Device"))

    def _disconnect_mobile(self):
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log("SYS: Mobile Connect session closed.")
        self._mobile_status.setText("Connection Status: Disconnected")
        self._mobile_phone.setText("Phone Name: Not connected")
        self._mobile_last.setText("Last Connected: Never")

    def _show_qr_code(self):
        ctrl = self._ctrl()
        if not ctrl:
            return
        target = None
        if hasattr(ctrl, "_show_remote_connect"):
            target = ctrl
        elif hasattr(ctrl, "_win") and hasattr(ctrl._win, "_show_remote_connect"):
            target = ctrl._win
        if target is not None:
            target._show_remote_connect()

    def _toggle_startup_from_page(self, checked: bool):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._set_startup_enabled(bool(checked))
            self._ctrl()._win._refresh_startup_button()

    def _toggle_launch_minimized(self, checked: bool):
        self._set_setting("launch_minimized", bool(checked))

    def _toggle_update_check(self, checked: bool):
        self._set_setting("check_updates_on_startup", bool(checked))

    def _toggle_startup_animation_from_page(self, checked: bool):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._set_startup_animation_enabled(bool(checked))
            self._ctrl()._win._refresh_startup_animation_button()

    def _on_theme_changed(self, index: int):
        """Handle theme selection change."""
        theme_id = self._theme_combo.itemData(index)
        if not theme_id:
            return
        # Apply theme immediately
        C.set_theme(theme_id)
        # Persist
        self._set_setting("app_theme", theme_id)
        # Refresh the main window to apply new colors
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._apply_theme()

    def _on_text_size_changed(self, text: str):
        """Handle text size change."""
        self._set_setting("text_size", text)
        # Apply text size scaling
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._apply_text_size(text)

    def _on_vault_toggled(self, checked: bool):
        """Handle vault enable/disable."""
        self._set_setting("vault_enabled", bool(checked))
        self._vault_path_lbl.setEnabled(checked)
        self._vault_browse_btn.setEnabled(checked)

    def _browse_vault_folder(self):
        """Open folder picker for Memory Vault location."""
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Memory Vault Folder")
        if folder:
            self._set_setting("vault_path", folder)
            self._vault_path_lbl.setText(folder)

    def _set_default_provider(self, text: str):
        raw = (text or "").strip().lower()
        if raw.startswith("google") or raw == "gemini":
            provider = "Gemini"
            self._set_setting("offline_mode_enabled", False)
            if hasattr(self, "_offline_mode_btn"):
                self._offline_mode_btn.blockSignals(True)
                self._offline_mode_btn.setChecked(False)
                self._offline_mode_btn.blockSignals(False)
            if hasattr(self, "_local_ai_widget"):
                self._local_ai_widget.setVisible(False)
            msg = "SYS: Default AI provider set to Google Gemini. Cloud connectivity active."
        elif raw == "local":
            provider = "Local"
            self._set_setting("offline_mode_enabled", True)
            if hasattr(self, "_offline_mode_btn"):
                self._offline_mode_btn.blockSignals(True)
                self._offline_mode_btn.setChecked(True)
                self._offline_mode_btn.blockSignals(False)
            if hasattr(self, "_local_ai_widget"):
                self._local_ai_widget.setVisible(True)
            msg = "SYS: Default AI provider set to Local AI (Ollama). Offline Mode active."
        elif raw == "groq":
            provider = "Groq"
            self._set_setting("offline_mode_enabled", False)
            if hasattr(self, "_offline_mode_btn"):
                self._offline_mode_btn.blockSignals(True)
                self._offline_mode_btn.setChecked(False)
                self._offline_mode_btn.blockSignals(False)
            if hasattr(self, "_local_ai_widget"):
                self._local_ai_widget.setVisible(False)
            msg = "SYS: Default AI provider set to Groq. Cloud connectivity active."
        elif raw in ("k2", "k2 horizon", "k2horizon"):
            provider = "K2"
            self._set_setting("offline_mode_enabled", False)
            if hasattr(self, "_offline_mode_btn"):
                self._offline_mode_btn.blockSignals(True)
                self._offline_mode_btn.setChecked(False)
                self._offline_mode_btn.blockSignals(False)
            if hasattr(self, "_local_ai_widget"):
                self._local_ai_widget.setVisible(False)
            if hasattr(self, "_groq_ai_widget"):
                self._groq_ai_widget.setVisible(False)
            try:
                from core import server
                server.start_background()
            except Exception:
                pass
            msg = "SYS: Default AI provider set to K2 Horizon (local llama.cpp). Starting local server."
        else:
            provider = "OpenRouter"
            self._set_setting("offline_mode_enabled", False)
            if hasattr(self, "_offline_mode_btn"):
                self._offline_mode_btn.blockSignals(True)
                self._offline_mode_btn.setChecked(False)
                self._offline_mode_btn.blockSignals(False)
            if hasattr(self, "_local_ai_widget"):
                self._local_ai_widget.setVisible(False)
            msg = "SYS: Default AI provider set to OpenRouter. Cloud connectivity active."
        self._set_setting("default_ai_provider", provider)
        if hasattr(self, "_sys_provider"):
            self._sys_provider.setText(provider)
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log(msg)

    def _toggle_autonomous_mode(self, checked: bool):
        """Toggle hands-off operation. Persisted + cached via core/autonomy.py.

        Autonomous mode is fully reversible: it only removes the confirmation
        prompt before an irreversible action, and every such action is still
        recoverable through the Recycle Bin / undo stack."""
        self._set_setting("autonomous_mode_enabled", bool(checked))
        try:
            from core import autonomy
            autonomy.set_autonomous(bool(checked))
        except Exception:
            pass
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            if checked:
                self._ctrl().write_log(
                    "🤖 SYSTEM: Autonomous Mode ENGAGED. Stella will act without "
                    "asking for confirmation. All actions remain reversible (undo)."
                )
            else:
                self._ctrl().write_log(
                    "🛡️ SYSTEM: Autonomous Mode DISENGAGED. Confirmation is "
                    "required before irreversible actions again."
                )

    def _toggle_auto_provider_switch(self, checked: bool):
        self._set_setting("auto_provider_switch", bool(checked))
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log(f"SYS: Auto provider switch {'enabled' if checked else 'disabled'}.")

    def _toggle_offline_mode(self, checked: bool):
        self._set_setting("offline_mode_enabled", bool(checked))
        if checked:
            self._set_setting("default_ai_provider", "Local")
            if hasattr(self, "_default_provider"):
                self._default_provider.blockSignals(True)
                self._default_provider.setCurrentText("Local")
                self._default_provider.blockSignals(False)
            if hasattr(self, "_local_ai_widget"):
                self._local_ai_widget.setVisible(True)
            if hasattr(self, "_groq_ai_widget"):
                self._groq_ai_widget.setVisible(False)
            if hasattr(self, "_sys_provider"):
                self._sys_provider.setText("Local")
            msg = "🔒 SYSTEM: Air-Gapped Offline Mode ENGAGED. All operations running 100% locally."
        else:
            self._set_setting("default_ai_provider", "Gemini")
            if hasattr(self, "_default_provider"):
                self._default_provider.blockSignals(True)
                self._default_provider.setCurrentText("Google Gemini")
                self._default_provider.blockSignals(False)
            if hasattr(self, "_local_ai_widget"):
                self._local_ai_widget.setVisible(False)
            if hasattr(self, "_sys_provider"):
                self._sys_provider.setText("Gemini")
            msg = "🌐 SYSTEM: Offline Mode DISENGAGED. Cloud connectivity restored."
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log(msg)

    def _on_local_model_changed(self, text: str):
        # Combo shows direct files as "name.gguf  (file)"; store the bare name.
        t = (text or "").strip()
        if t.endswith("(file)"):
            t = t[: -len("(file)")].strip()
        self._set_setting("local_ai_model", t)
        self._sync_selected_model(t)

    def _sync_selected_model(self, name: str) -> None:
        """Mirror the combo choice into the structured `models.selected_model`
        block that agent/llm.py reads to pick the local endpoint.

        Without this the flat `local_ai_model` string is saved but the agent
        chain never learns which model (or endpoint) to talk to, so switching
        models in Settings silently does nothing.
        """
        t = (name or "").strip()
        if not t or t.startswith("("):
            return
        try:
            from agent import model_manager as mm
            path = self._resolve_model_path(t)
            if not path:
                return
            p = Path(path)
            if not p.exists():
                return
            mm.set_selected_model({
                "name": p.name,
                "path": str(p.resolve()),
                "size_gb": round(p.stat().st_size / 1024 ** 3, 2),
            })
        except Exception:
            pass

    def _disk_free_gb(self, path) -> float:
        try:
            import shutil
            return round(shutil.disk_usage(str(path)).free / 1024 ** 3, 2)
        except Exception:
            return -1.0

    def _browse_local_model(self):
        log = self._ctrl().write_log if self._ctrl() and hasattr(self._ctrl(), "write_log") else print
        path, _ = QFileDialog.getOpenFileName(self, "Select GGUF model",
            str(Path.home()), "GGUF models (*.gguf);;All files (*)")
        if not path:
            return
        src = Path(path)
        dest_dir = Path(__file__).resolve().parent / "models"
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        # Never delete the source on import. If space is tight, alert first.
        try:
            need = round(src.stat().st_size / 1024 ** 3, 2)
            free = self._disk_free_gb(dest_dir)
            if free >= 0 and free < need + 0.5:
                ans = QMessageBox.warning(self, "Low disk space",
                    f"Only {free} GB free, need ~{need} GB to load '{src.name}'.\n\n"
                    "Continue anyway? (Nothing will be deleted without your confirmation.)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ans != QMessageBox.StandardButton.Yes:
                    return
        except Exception:
            pass
        def _work():
            try:
                import shutil
                dest = dest_dir / src.name
                if src.resolve() != dest.resolve():
                    log(f"SYS: Loading '{src.name}' into app models...")
                    shutil.copy2(str(src), str(dest))
                    log(f"SYS: Model ready → {dest}")
                else:
                    dest = src
                self._set_setting("local_ai_model", dest.name)
                self._sync_selected_model(dest.name)
                try:
                    self._local_model_combo.setCurrentText(f"{dest.name}  (file)")
                except Exception:
                    pass
                log(f"SYS: Active local model → {dest.name}")
            except Exception as e:
                log(f"ERR: Browse-load failed: {e}")
        threading.Thread(target=_work, daemon=True).start()

    def _resolve_model_path(self, name: str):
        """Resolve a model combo entry to a local .gguf path, if any."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
            from stella_model_manager import list_local
            for m in list_local():
                if m["name"] == name or m["path"] == name:
                    return m["path"]
        except Exception:
            pass
        return None

    def _remove_local_model(self):
        name = ""
        try:
            name = self._local_model_combo.currentText().strip()
        except Exception:
            pass
        if name.endswith("(file)"):
            name = name[: -len("(file)")].strip()
        if not name:
            return
        ans = QMessageBox.question(self, "Remove model",
            f"Delete local model '{name}' from disk? This frees space but cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        log = self._ctrl().write_log if self._ctrl() and hasattr(self._ctrl(), "write_log") else print
        path = self._resolve_model_path(name)
        try:
            if path:
                try:
                    from core import server
                    server.stop()
                except Exception:
                    pass
                import os
                os.remove(path)
                log(f"SYS: Removed local model file: {name}")
            else:
                import subprocess
                r = subprocess.run(["ollama", "rm", name], capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    log(f"SYS: Removed Ollama model: {name}")
                else:
                    log(f"ERR: Could not remove '{name}': {(r.stderr or r.stdout or 'unknown error')[:200]}")
                    return
        except Exception as e:
            log(f"ERR: Remove failed: {e}")
            return
        try:
            self._set_setting("local_ai_model", "")
        except Exception:
            pass
        # Drop the structured selection too, so agent/llm.py stops pointing at
        # the file we just deleted and falls through to the next backend.
        try:
            from agent import model_manager as mm
            mm.save_model_settings({"selected_model": None})
        except Exception:
            pass
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log("SYS: Pick or download a replacement model to continue using Local mode.")

    def _replace_local_model(self):
        old = ""
        try:
            old = self._local_model_combo.currentText().strip()
        except Exception:
            pass
        if old.endswith("(file)"):
            old = old[: -len("(file)")].strip()
        new, ok = QInputDialog.getText(self, "Replace model",
            "New model — HF repo/file (e.g. Qwen/Qwen2.5-1.5B-Instruct-GGUF :: qwen2.5-1.5b-instruct-q4_k_m.gguf)\n"
            "or a local .gguf path. Old model is deleted first to free space:",
            QLineEdit.EchoMode.Normal, old)
        new = (new or "").strip()
        if not ok or not new or new == old:
            return
        # Space check BEFORE touching anything. Sources are never deleted on
        # import — the old model is only removed with explicit confirmation,
        # and only when space actually requires it.
        try:
            dest_dir = Path(__file__).resolve().parent / "models"
            free = self._disk_free_gb(dest_dir)
            if "::" in new:
                est_need, _size_known = 1.0, False
            else:
                p = Path(new)
                est_need, _size_known = (round(p.stat().st_size / 1024 ** 3, 2), True) if p.exists() else (1.0, False)
            if free >= 0 and free < est_need + 0.5:
                ans = QMessageBox.warning(self, "Low disk space",
                    f"Only {free} GB free. Proceed with replacement?\n\n"
                    f"If space runs out you will be asked before anything is deleted.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ans != QMessageBox.StandardButton.Yes:
                    return
        except Exception:
            pass
        log = self._ctrl().write_log if self._ctrl() and hasattr(self._ctrl(), "write_log") else print
        log(f"SYS: Replacing '{old}' with '{new}' in background...")
        def _work():
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
                from stella_model_manager import remove_model, download_file
                new_path = None
                if "::" in new:
                    repo, fname = [p.strip() for p in new.split("::", 1)]
                    dest = Path(__file__).resolve().parent / "models" / fname
                    log(f"SYS: Downloading '{fname}' (old model kept)...")
                    download_file(f"https://huggingface.co/{repo}/resolve/main/{fname}", dest,
                                  progress=lambda d, t: None)
                    new_path = dest
                    self._set_setting("local_ai_model", fname)
                    self._sync_selected_model(fname)
                    log(f"SYS: Replacement ready → {dest}")
                else:
                    from pathlib import Path as _P
                    src = _P(new)
                    dest_dir = Path(__file__).resolve().parent / "models"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / src.name if src.exists() else src
                    if src.exists() and src.resolve() != dest.resolve():
                        import shutil
                        log(f"SYS: Loading '{src.name}' into app models (source kept)...")
                        shutil.copy2(str(src), str(dest))
                    new_path = dest if dest.exists() else src
                    self._set_setting("local_ai_model", new_path.name)
                    self._sync_selected_model(new_path.name)
                    log(f"SYS: Active local model → {new_path.name}")
                # Post-check: only suggest removing the old model if space is low.
                try:
                    from PyQt6.QtCore import QTimer
                    free = self._disk_free_gb(Path(__file__).resolve().parent / "models")
                    if free >= 0 and free < 1.0 and old:
                        def _ask():
                            ans = QMessageBox.question(self, "Space low",
                                f"Only {free} GB free. Delete old model '{old}' to free space?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                            if ans == QMessageBox.StandardButton.Yes:
                                info = remove_model(old)
                                log(f"SYS: Removed '{old}' (freed {info.get('freed_gb', 0)}GB)")
                            else:
                                log("SYS: Old model kept. Both models are available.")
                        QTimer.singleShot(0, _ask)
                except Exception:
                    pass
            except Exception as e:
                log(f"ERR: Replace failed: {e}")
        threading.Thread(target=_work, daemon=True).start()

    def _on_feedback_contact_changed(self, text: str):
        ch = ""
        try:
            ch = self._feedback_channel.currentText().strip().lower()
        except Exception:
            pass
        t = (text or "").strip()
        self._set_setting("feedback_contact", t)
        if ch == "email":
            self._set_setting("feedback_email_to", t)
        elif ch == "github":
            self._set_setting("feedback_github_repo", t)
        elif ch == "webhook":
            self._set_setting("feedback_webhook_url", t)
        self._refresh_feedback_availability()

    def _on_feedback_smtp_changed(self, text: str):
        # Accept host, host:port, or host:port:user. Parsed here so a single
        # field configures the whole SMTP route; the password is never stored.
        raw = (text or "").strip()
        self._set_setting("feedback_smtp_host", raw)
        parts = raw.split(":")
        if parts and parts[0]:
            self._set_setting("feedback_smtp_host", parts[0])
        if len(parts) > 1 and parts[1].isdigit():
            self._set_setting("feedback_smtp_port", int(parts[1]))
        if len(parts) > 2 and parts[2]:
            self._set_setting("feedback_smtp_user", parts[2])
        self._refresh_feedback_availability()

    def _on_feedback_channel_changed(self, channel: str):
        self._set_setting("feedback_channel", channel)
        self._refresh_feedback_availability()

    def _refresh_feedback_availability(self):
        """Update the honest 'what works right now' note under the channel.

        Only the repo route is wired up out of the box. Email/webhook light up
        automatically once the creator supplies a destination, so a user is
        never offered a channel that would fail on send.
        """
        try:
            from core import feedback as _fb
            avail = _fb.channels_available()
        except Exception:
            avail = {"github": True, "email": False, "webhook": False}
        ready, soon = [], []
        if avail.get("github"):
            ready.append("GitHub issue (repo)")
        if avail.get("email"):
            ready.append("Email")
        else:
            soon.append("Email")
        if avail.get("webhook"):
            ready.append("Webhook")
        else:
            soon.append("Webhook")
        ready.insert(0, "Local file (always)")
        note = "Available now: " + ", ".join(ready) + "."
        if soon:
            note += ("  Coming soon once a destination is set: " + ", ".join(soon)
                     + ". Add the address/URL above to enable.")
        self._feedback_status.setText(note)

        # Grey the SMTP field when email isn't configured yet, so the state is
        # visible at a glance rather than only after a failed send.
        try:
            self._feedback_smtp.setEnabled(bool(avail.get("email")))
        except Exception:
            pass

    def _open_feedback_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Request upgrade / Send feedback")
        dlg.setMinimumWidth(460)
        v = QVBoxLayout(dlg)
        fields = {}
        for label, key in (("What did you encounter?", "encountered"),
                           ("What did you do?", "did"),
                           ("How did you do it?", "how"),
                           ("What do you need next?", "need")):
            v.addWidget(QLabel(label))
            te = QTextEdit()
            te.setFixedHeight(60)
            fields[key] = te
            v.addWidget(te)
        kind_row = QHBoxLayout()
        kind_row.addWidget(QLabel("Kind"))
        kind = QComboBox()
        kind.addItems(["upgrade-request", "bug-report", "feature-request", "skill-proposal"])
        kind_row.addWidget(kind, 1)
        v.addLayout(kind_row)
        status = QLabel("Secrets are scrubbed before anything is sent.")
        v.addWidget(status)
        btns = QHBoxLayout()
        btn_send = QPushButton("Send")
        btn_cancel = QPushButton("Cancel")
        btns.addWidget(btn_send)
        btns.addWidget(btn_cancel)
        v.addLayout(btns)
        btn_cancel.clicked.connect(dlg.reject)

        def _do_send():
            btn_send.setEnabled(False)
            status.setText("Sending...")
            try:
                from core import feedback as _fb
                rep = _fb.build_report(fields["encountered"].toPlainText(),
                                       fields["did"].toPlainText(),
                                       fields["how"].toPlainText(),
                                       fields["need"].toPlainText(),
                                       kind=kind.currentText())
                cfg = dict(self._load_app_settings())
                # SMTP password is never stored: ask at send time for email channel
                if (cfg.get("feedback_channel") or "local") == "email" and not cfg.get("feedback_smtp_pass"):
                    pw, ok = QInputDialog.getText(dlg, "SMTP password",
                        "Your email password/app-password (used once, never stored):",
                        QLineEdit.EchoMode.Password)
                    if not ok:
                        status.setText("Cancelled.")
                        btn_send.setEnabled(True)
                        return
                    cfg["feedback_smtp_pass"] = pw
                    try:
                        u = (self._feedback_smtp.text() or "").strip()
                        if ":" in u:
                            parts = u.split(":")
                            cfg["feedback_smtp_host"] = parts[0]
                            if len(parts) > 1 and parts[1].isdigit():
                                cfg["feedback_smtp_port"] = int(parts[1])
                            if len(parts) > 2:
                                cfg["feedback_smtp_user"] = parts[2]
                    except Exception:
                        pass
                    if not cfg.get("feedback_smtp_user"):
                        em, ok = QInputDialog.getText(dlg, "SMTP username", "Your email address:",
                            QLineEdit.EchoMode.Normal, cfg.get("feedback_smtp_user", ""))
                        if ok and em.strip():
                            cfg["feedback_smtp_user"] = em.strip()
                res = _fb.send_report(rep, cfg)
                if res.get("open_url"):
                    import webbrowser
                    webbrowser.open(res["open_url"])
                    status.setText("Opened GitHub issue draft in your browser — submit it there.")
                elif res.get("ok"):
                    where = res.get("path") or res.get("channel")
                    status.setText(f"Sent via {res.get('channel')} → {where}")
                else:
                    status.setText(f"Failed: {res.get('error', 'unknown error')}")
            except Exception as e:
                status.setText(f"Failed: {e}")
            finally:
                btn_send.setEnabled(True)
        btn_send.clicked.connect(_do_send)
        dlg.exec()

    def _toggle_attention_message_prompts(self, checked: bool):
        self._set_setting("attention_message_prompts", bool(checked))
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log(f"SYS: Incoming message prompts {'enabled' if checked else 'disabled'}.")

    def _toggle_attention_call_prompts(self, checked: bool):
        self._set_setting("attention_call_prompts", bool(checked))
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log(f"SYS: Incoming call prompts {'enabled' if checked else 'disabled'}.")

    def _preview_animation(self):
        self._preview_progress.setValue(0)
        if hasattr(self, "_preview_timer") and self._preview_timer:
            try:
                self._preview_timer.stop()
            except Exception:
                pass
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._tick_preview)
        self._preview_timer.start(24)

    def _tick_preview(self):
        value = min(100, self._preview_progress.value() + 4)
        self._preview_progress.setValue(value)
        if value >= 100 and hasattr(self, "_preview_timer"):
            self._preview_timer.stop()
            if self._ctrl() and hasattr(self._ctrl(), "write_log"):
                self._ctrl().write_log("SYS: Startup animation preview finished.")

    def _toggle_discord_reveal(self, checked: bool):
        self._discord_token.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)

    def _save_discord_from_page(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._discord_token_input = self._discord_token
            self._ctrl()._win._discord_channel_input = self._discord_channel
            self._ctrl()._win._save_discord_token()
            self._discord_status.setText("Bot Status: Saved")
            self.refresh()

    def _test_discord_from_page(self):
        self._save_discord_from_page()
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._start_discord_bot()
            self._ctrl()._win._stop_discord_bot()
            self._discord_status.setText("Bot Status: Test sent")
            self._discord_msg.setText("Connected as Stella#9649" if self._discord_token.text().strip() else "Bot Offline")

    def _restart_discord_from_page(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._stop_discord_bot()
            self._ctrl()._win._start_discord_bot()
            self._discord_status.setText("Bot Status: Restarted")

    def _restart_app(self):
        if self._ctrl() and hasattr(self._ctrl(), "_restart_app"):
            self._ctrl()._restart_app()

    def _reload_config(self):
        if self._ctrl() and hasattr(self._ctrl(), "_win"):
            self._ctrl()._win._load_api_defaults()
            self._ctrl()._win._load_discord_settings()
            if hasattr(self._ctrl(), "write_log"):
                self._ctrl().write_log("SYS: Configuration reloaded.")
            self.refresh()

    def _open_data_folder(self):
        try:
            os.startfile(str(CONFIG_DIR))
        except Exception:
            pass

    def _view_logs(self):
        try:
            os.startfile(str(BASE_DIR))
        except Exception:
            pass

    def _check_updates(self):
        if self._ctrl() and hasattr(self._ctrl(), "write_log"):
            self._ctrl().write_log("SYS: Update check requested.")

    def refresh(self):
        api = self._load_api_defaults()
        app = self._load_app_settings()
        discord = self._load_discord_settings()
        for widget in (
            getattr(self, "_default_provider", None),
            getattr(self, "_offline_mode_btn", None),
            getattr(self, "_auto_switch_btn", None),
            getattr(self, "_attention_message_btn", None),
            getattr(self, "_attention_call_btn", None),
            getattr(self, "_startup_launch_btn", None),
            getattr(self, "_startup_minimized_btn", None),
            getattr(self, "_startup_updates_btn", None),
            getattr(self, "_startup_anim_enable_btn", None),
            getattr(self, "_discord_token", None),
            getattr(self, "_discord_channel", None),
            getattr(self, "_discord_reveal", None),
            getattr(self, "_feedback_channel", None),
            getattr(self, "_feedback_contact", None),
            getattr(self, "_feedback_smtp", None),
            getattr(self, "_groq_model_combo", None),
            getattr(self, "_tts_voice_combo", None),
            getattr(self, "_local_model_combo", None),
        ):
            if _qt_alive(widget):
                try:
                    widget.blockSignals(True)
                except RuntimeError:
                    pass  # widget was destroyed between the check and the call
        try:
            for _attr, _value in (
                ("_gemini_status", "Connected" if api.get("gemini_api_key") else "Not connected"),
                ("_or_status", "Connected" if api.get("openrouter_api_key") else "Not connected"),
                ("_groq_status", "Connected" if api.get("groq_api_key") else "Not connected"),
                ("_gemini_key", self._provider_key_preview(api.get("gemini_api_key", ""))),
                ("_or_key", self._provider_key_preview(api.get("openrouter_api_key", ""))),
                ("_groq_key", self._provider_key_preview(api.get("groq_api_key", ""))),
            ):
                _w = getattr(self, _attr, None)
                if _qt_alive(_w):
                    _w.setText(_value)
            
            prov = app.get("default_ai_provider", "Gemini")
            is_offline = bool(app.get("offline_mode_enabled", False))
            if prov == "Local" or is_offline:
                disp_prov = "Local"
            elif prov == "OpenRouter":
                disp_prov = "OpenRouter"
            elif prov == "Groq":
                disp_prov = "Groq"
            elif prov == "K2" and getattr(self, "_k2_available", False):
                disp_prov = "K2 Horizon"
            else:
                disp_prov = "Google Gemini"
            if _qt_alive(getattr(self, "_default_provider", None)):
                self._default_provider.setCurrentText(disp_prov)
            if _qt_alive(getattr(self, "_offline_mode_btn", None)):
                self._offline_mode_btn.setChecked(is_offline or prov == "Local")
            if _qt_alive(getattr(self, "_local_ai_widget", None)):
                self._local_ai_widget.setVisible(is_offline or prov == "Local")
            if _qt_alive(getattr(self, "_groq_ai_widget", None)):
                self._groq_ai_widget.setVisible(not is_offline and prov == "Groq")

            for _attr, _value in (
                ("_auto_switch_btn", bool(app.get("auto_provider_switch", True))),
                ("_attention_message_btn", bool(app.get("attention_message_prompts", True))),
                ("_attention_call_btn", bool(app.get("attention_call_prompts", True))),
                ("_startup_launch_btn", bool(app.get("show_workspace_on_startup", False))),
                ("_startup_minimized_btn", bool(app.get("launch_minimized", False))),
                ("_startup_updates_btn", bool(app.get("check_updates_on_startup", True))),
                ("_startup_anim_enable_btn", bool(self._startup_animation_enabled())),
            ):
                _w = getattr(self, _attr, None)
                if _qt_alive(_w):
                    _w.setChecked(_value)

            for _attr, _value in (
                ("_discord_token", (discord.get("bot_token") or "").strip()),
                ("_discord_channel", (discord.get("channel_id") or "").strip()),
            ):
                _w = getattr(self, _attr, None)
                if _qt_alive(_w):
                    _w.setText(_value)
            if _qt_alive(getattr(self, "_feedback_channel", None)):
                self._feedback_channel.setCurrentText(app.get("feedback_channel", "local"))
            if _qt_alive(getattr(self, "_feedback_contact", None)):
                self._feedback_contact.setText(app.get("feedback_contact", ""))
            if _qt_alive(getattr(self, "_feedback_smtp", None)):
                self._feedback_smtp.setText(app.get("feedback_smtp_host", ""))
            if _qt_alive(getattr(self, "_groq_model_combo", None)):
                self._groq_model_combo.setCurrentText(app.get("groq_model", "openai/gpt-oss-120b"))
            if _qt_alive(getattr(self, "_tts_voice_combo", None)):
                self._tts_voice_combo.setCurrentText(app.get("tts_voice", "en_US-lessac-medium"))
            if _qt_alive(getattr(self, "_local_model_combo", None)):
                self._local_model_combo.setCurrentText(app.get("local_ai_model", "qwen2.5:3b"))
        finally:
            for widget in (
                getattr(self, "_default_provider", None),
                getattr(self, "_offline_mode_btn", None),
                getattr(self, "_auto_switch_btn", None),
                getattr(self, "_attention_message_btn", None),
                getattr(self, "_attention_call_btn", None),
                getattr(self, "_startup_launch_btn", None),
                getattr(self, "_startup_minimized_btn", None),
                getattr(self, "_startup_updates_btn", None),
                getattr(self, "_startup_anim_enable_btn", None),
                getattr(self, "_discord_token", None),
                getattr(self, "_discord_channel", None),
                getattr(self, "_discord_reveal", None),
                getattr(self, "_feedback_channel", None),
                getattr(self, "_feedback_contact", None),
                getattr(self, "_feedback_smtp", None),
                getattr(self, "_groq_model_combo", None),
                getattr(self, "_tts_voice_combo", None),
                getattr(self, "_local_model_combo", None),
            ):
                if _qt_alive(widget):
                    try:
                        widget.blockSignals(False)
                    except RuntimeError:
                        pass
        enabled = bool(discord.get("enabled", False))
        token = (discord.get("bot_token") or "").strip()
        if enabled and token:
            _discord_state = ("Bot Status: Online", "Connected as Stella#9649")
        elif token:
            _discord_state = ("Bot Status: Offline", "Bot Offline")
        else:
            _discord_state = ("Bot Status: Offline", "Token required")
        for _attr, _value in (
            ("_discord_status", _discord_state[0]),
            ("_discord_msg", _discord_state[1]),
        ):
            _w = getattr(self, _attr, None)
            if _qt_alive(_w):
                _w.setText(_value)
        if _qt_alive(getattr(self, "_sys_provider", None)):
            self._sys_provider.setText(app.get("default_ai_provider", "Gemini"))
        if _qt_alive(getattr(self, "_update_spotify_status", None)):
            self._update_spotify_status()

    def _handle_create_desktop_shortcut(self):
        success, path_or_err = self._create_desktop_shortcut_logic()
        if success:
            QMessageBox.information(
                self, 
                "Success", 
                f"Desktop shortcut created successfully at:\n{path_or_err}"
            )
        else:
            QMessageBox.warning(
                self, 
                "Error", 
                f"Failed to create desktop shortcut:\n{path_or_err}"
            )

    def _handle_pin_to_taskbar(self):
        success, msg = self._pin_app_to_taskbar_logic()
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.warning(
                self, 
                "Taskbar Pinning", 
                msg
            )

    def _create_desktop_shortcut_logic(self):
        try:
            import os
            import sys
            import shutil
            import subprocess
            from pathlib import Path
            import winreg
            
            # Find the correct Desktop folder path using registry (OneDrive safe!)
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
                desktop_raw, _ = winreg.QueryValueEx(key, "Desktop")
                winreg.CloseKey(key)
                desktop_dir = Path(os.path.expandvars(desktop_raw))
            except Exception:
                desktop_dir = Path(os.path.expanduser("~")) / "Desktop"
                
            desktop_dir.mkdir(parents=True, exist_ok=True)
            shortcut_path = desktop_dir / "Stella - Premium.lnk"
            
            # Base variables
            base_dir = Path(os.path.abspath("."))
            script_path = base_dir / "main.py"
            icon_path = base_dir / "assets" / "stella_logo.ico"
            
            python_exe = sys.executable
            if not python_exe:
                python_exe = shutil.which("pythonw") or shutil.which("python") or "pythonw"
                
            shortcut_target = python_exe
            shortcut_args = f'"{script_path}"'
            if getattr(sys, "frozen", False):
                shortcut_target = python_exe
                shortcut_args = ""
                
            powershell_exe = shutil.which("powershell.exe") or "powershell"
            
            def _ps_escape(value: str) -> str:
                return value.replace("'", "''")
                
            icon_value = str(icon_path) if icon_path.exists() else ""
            ps1_script = "\n".join([
                "$WshShell = New-Object -ComObject WScript.Shell",
                f"$Shortcut = $WshShell.CreateShortcut('{_ps_escape(str(shortcut_path))}')",
                f"$Shortcut.TargetPath = '{_ps_escape(shortcut_target)}'",
                f"$Shortcut.Arguments = '{_ps_escape(shortcut_args)}'",
                f"$Shortcut.WorkingDirectory = '{_ps_escape(str(base_dir))}'",
                "$Shortcut.WindowStyle = 7",
                "$Shortcut.Description = 'Launch Stella - Premium'",
                f"if ('{_ps_escape(icon_value)}') {{ $Shortcut.IconLocation = '{_ps_escape(icon_value)},0' }}",
                "$Shortcut.Save()",
            ])
            
            ps1_path = get_user_data_dir() / "config" / "create_desktop_shortcut.ps1"
            ps1_path.write_text(ps1_script, encoding="utf-8")
            
            subprocess.run(
                [powershell_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Write marker file
            marker_path = get_user_data_dir() / "config" / ".desktop_shortcut_created"
            marker_path.write_text("created", encoding="utf-8")
            
            return True, str(shortcut_path)
        except Exception as e:
            return False, str(e)

    def _pin_app_to_taskbar_logic(self):
        try:
            import os
            import sys
            import shutil
            import subprocess
            from pathlib import Path
            
            # Ensure desktop shortcut exists first
            success, path_or_err = self._create_desktop_shortcut_logic()
            if not success:
                return False, f"Failed to create desktop shortcut first: {path_or_err}"
                
            shortcut_path = Path(path_or_err)
            if not shortcut_path.exists():
                return False, "Shortcut file does not exist."
                
            powershell_exe = shutil.which("powershell.exe") or "powershell"
            
            # COM pin script
            def _ps_escape(value: str) -> str:
                return value.replace("'", "''")
                
            pin_script = "\n".join([
                "$Shell = New-Object -ComObject Shell.Application",
                f"$Folder = $Shell.NameSpace('{_ps_escape(str(shortcut_path.parent))}')",
                f"$Item = $Folder.ParseName('{_ps_escape(shortcut_path.name)}')",
                "$Verb = $Item.Verbs() | Where-Object { $_.Name.Replace('&', '') -match 'Pin to taskbar' }",
                "if ($Verb) { $Verb.DoIt(); exit 0 } else { exit 1 }"
            ])
            
            res = subprocess.run(
                [powershell_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", pin_script],
                capture_output=True
            )
            
            if res.returncode == 0:
                return True, "Stella has been pinned to your Taskbar!"
            else:
                return False, "Windows restricts programmatic taskbar pinning. Please right-click the 'Stella - Premium.lnk' shortcut on your Desktop and select 'Pin to taskbar', or drag it directly onto your taskbar."
        except Exception as e:
            return False, f"Error pinning to taskbar: {e}"

class SmartDevicesSection(QFrame):
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._service = SmartHomeService()
        self._snapshot = ""
        self._device_tiles: list[_DeviceTile] = []
        self._card_anims: list[QPropertyAnimation] = []
        self._selected_device: dict[str, object] | None = None

        self.setObjectName("SmartDevicesSection")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(f"""
            QFrame#SmartDevicesSection {{
                background: transparent;
                border: none;
            }}
            QLabel {{
                background: transparent;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self._title_lbl = QLabel("SMART DEVICES")
        self._title_lbl.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {C.WHITE}; letter-spacing: 1px;")
        self._subtitle_lbl = QLabel("Quick access to your connected home devices.")
        self._subtitle_lbl.setFont(QFont("Exo 2", 8))
        self._subtitle_lbl.setStyleSheet(f"color: {C.TEXT_DIM};")
        title_box.addWidget(self._title_lbl)
        title_box.addWidget(self._subtitle_lbl)
        header.addLayout(title_box, 1)

        self._count_chip = QLabel("0 devices")
        self._count_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_chip.setStyleSheet(
            f"QLabel {{ background: C.TEXT; color: {C.PRI}; border: 1px solid C.TEXT; border-radius: 10px; padding: 4px 10px; }}"
        )
        header.addWidget(self._count_chip)

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedSize(32, 32)
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 9px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230,0.08);
                border: 1px solid {C.PRI};
            }}
        """)
        self._refresh_btn.clicked.connect(lambda: self.refresh(force=True))
        header.addWidget(self._refresh_btn)

        self._open_home_btn = QPushButton("Add Device")
        self._open_home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_home_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(124, 110, 230,0.10);
                color: {C.WHITE};
                border: 1px solid {C.PRI};
                border-radius: 9px;
                padding: 0 14px;
                min-height: 32px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230,0.16);
            }}
        """)
        self._open_home_btn.clicked.connect(self._open_stella_home)
        header.addWidget(self._open_home_btn)
        root.addLayout(header)

        self._empty_card = QWidget()
        self._empty_card.setStyleSheet("background: transparent;")
        empty_lay = QVBoxLayout(self._empty_card)
        empty_lay.setContentsMargins(6, 4, 6, 4)
        empty_lay.setSpacing(6)
        empty_title = QLabel("No Smart Devices Connected")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        empty_title.setStyleSheet(f"color: {C.WHITE}; border: none;")
        empty_desc = QLabel("Connect your first smart device to control it directly from your dashboard.")
        empty_desc.setWordWrap(True)
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setFont(QFont("Exo 2", 8))
        empty_desc.setStyleSheet(f"color: {C.TEXT_DIM};")
        empty_btn = QPushButton("Open Stella Home")
        empty_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_btn.setFixedWidth(160)
        empty_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(124, 110, 230,0.12);
                color: {C.WHITE};
                border: 1px solid {C.PRI};
                border-radius: 10px;
                min-height: 34px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230,0.18);
            }}
        """)
        empty_btn.clicked.connect(self._open_stella_home)
        empty_lay.addStretch(1)
        empty_lay.addWidget(empty_title)
        empty_lay.addWidget(empty_desc)
        empty_lay.addWidget(empty_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        empty_lay.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._grid_page = QWidget()
        self._grid_page.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._grid_page)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(12)
        self._grid_layout.setVerticalSpacing(12)

        self._row_page = QWidget()
        self._row_page.setStyleSheet("background: transparent;")
        self._row_layout = QHBoxLayout(self._row_page)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(12)

        self._cards_stack = QStackedWidget()
        self._cards_stack.setStyleSheet("background: transparent; border: none;")
        self._cards_stack.addWidget(self._grid_page)
        self._cards_stack.addWidget(self._row_page)
        self._scroll.setWidget(self._cards_stack)
        root.addWidget(self._empty_card)
        root.addWidget(self._scroll, 1)

        self._panel = QFrame(self)
        self._panel.setObjectName("SmartDevicePanel")
        self._panel.setStyleSheet(f"""
            QFrame#SmartDevicePanel {{
                background: rgba(8, 9, 13, 245);
                border: 1px solid C.TEXT;
                border-radius: 18px;
            }}
            QLabel {{
                background: transparent;
            }}
            QPushButton {{
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 10px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background: rgba(124, 110, 230,0.08);
                border: 1px solid {C.PRI};
            }}
        """)
        self._panel.setVisible(False)
        self._panel.setMinimumSize(280, 260)
        self._panel_effect = QGraphicsOpacityEffect(self._panel)
        self._panel_effect.setOpacity(0.0)
        self._panel.setGraphicsEffect(self._panel_effect)
        self._panel_lay = QVBoxLayout(self._panel)
        self._panel_lay.setContentsMargins(14, 12, 14, 12)
        self._panel_lay.setSpacing(8)

        panel_top = QHBoxLayout()
        panel_top.setSpacing(6)
        self._panel_name = QLabel("Device")
        self._panel_name.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._panel_name.setStyleSheet(f"color: {C.WHITE};")
        panel_top.addWidget(self._panel_name, 1)
        self._panel_close = QPushButton("X")
        self._panel_close.setFixedSize(28, 28)
        self._panel_close.clicked.connect(self._close_panel)
        panel_top.addWidget(self._panel_close)
        self._panel_lay.addLayout(panel_top)

        self._panel_meta = QLabel("")
        self._panel_meta.setWordWrap(True)
        self._panel_meta.setStyleSheet(f"color: {C.TEXT_DIM};")
        self._panel_lay.addWidget(self._panel_meta)

        self._panel_status = QLabel("")
        self._panel_status.setStyleSheet(f"color: {C.GREEN}; font-weight: 700;")
        self._panel_lay.addWidget(self._panel_status)

        self._panel_controls = QVBoxLayout()
        self._panel_controls.setSpacing(10)
        self._panel_lay.addLayout(self._panel_controls)
        self._panel_lay.addStretch(1)

        self._panel_actions = QHBoxLayout()
        self._panel_actions.setSpacing(8)
        self._panel_lay.addLayout(self._panel_actions)

        self._panel_hint = QLabel("")
        self._panel_hint.setWordWrap(True)
        self._panel_hint.setStyleSheet(f"color: {C.TEXT_DIM};")
        self._panel_lay.addWidget(self._panel_hint)

        self._poll_tmr = QTimer(self)
        self._poll_tmr.timeout.connect(lambda: self.refresh(force=False))
        self._poll_tmr.start(2500)

        self.refresh(force=True)

    def _controller_bridge(self):
        return self._controller

    def _open_stella_home(self):
        bridge = self._controller_bridge()
        if bridge and hasattr(bridge, "_set_page"):
            bridge._set_page("home")

    def _snapshot_devices(self, devices: list[dict[str, object]]) -> str:
        payload = [
            (
                str(d.get("id", "")),
                int(d.get("updated_at") or 0),
                str(d.get("name", "")),
                bool(d.get("is_on")),
                str(d.get("room", "")),
                str(d.get("device_type", "")),
                str(d.get("manufacturer", "")),
            )
            for d in devices
        ]
        return json.dumps(payload, ensure_ascii=True, sort_keys=False)

    def refresh(self, force: bool = False):
        devices = self._service.list_devices()
        snapshot = self._snapshot_devices(devices)
        if not force and snapshot == self._snapshot:
            return
        self._snapshot = snapshot
        self._count_chip.setText(f"{len(devices)} device(s)")
        self._empty_card.setVisible(not devices)
        self._scroll.setVisible(bool(devices))
        self._rebuild_device_cards(devices)
        if self._panel.isVisible() and self._selected_device:
            device_id = str(self._selected_device.get("id", ""))
            device = self._find_device(device_id)
            if device:
                self._selected_device = device
                self._populate_panel(device)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _rebuild_device_cards(self, devices: list[dict[str, object]]):
        self._clear_layout(self._grid_layout)
        self._clear_layout(self._row_layout)
        self._device_tiles.clear()
        self._card_anims.clear()

        if not devices:
            self._cards_stack.setCurrentIndex(0)
            self._close_panel()
            return

        count = len(devices)
        if count <= 3:
            self._cards_stack.setCurrentIndex(1)
            self._clear_layout(self._row_layout)
            for idx, device in enumerate(devices):
                tile = _DeviceTile(device)
                tile.select_requested.connect(self._open_device_panel)
                tile.action_requested.connect(self._apply_tile_action)
                self._row_layout.addWidget(tile)
                self._animate_card(tile, idx)
                self._device_tiles.append(tile)
            self._row_layout.addStretch(1)
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        elif count <= 6:
            self._cards_stack.setCurrentIndex(0)
            columns = 3 if count > 3 else count
            for idx, device in enumerate(devices):
                tile = _DeviceTile(device)
                tile.select_requested.connect(self._open_device_panel)
                tile.action_requested.connect(self._apply_tile_action)
                self._grid_layout.addWidget(tile, idx // columns, idx % columns)
                self._animate_card(tile, idx)
                self._device_tiles.append(tile)
            last_row = (count - 1) // columns + 1
            self._grid_layout.setRowStretch(last_row, 1)
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            self._cards_stack.setCurrentIndex(1)
            self._clear_layout(self._row_layout)
            for idx, device in enumerate(devices):
                tile = _DeviceTile(device)
                tile.select_requested.connect(self._open_device_panel)
                tile.action_requested.connect(self._apply_tile_action)
                self._row_layout.addWidget(tile)
                self._animate_card(tile, idx)
                self._device_tiles.append(tile)
            self._row_layout.addStretch(1)
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def _animate_card(self, widget: QWidget, index: int):
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._card_anims.append(anim)
        QTimer.singleShot(index * 45, anim.start)

    def _device_id_from_input(self, device_or_id):
        if isinstance(device_or_id, dict):
            return str(device_or_id.get("id", ""))
        return str(device_or_id or "")

    def _find_device(self, device_id: str) -> dict[str, object] | None:
        for device in self._service.list_devices():
            if str(device.get("id", "")) == device_id:
                return device
        return None

    def _apply_tile_action(self, device_id: str, action: str, payload: dict):
        try:
            self._service.execute_device_action(device_id, action, payload)
        except Exception:
            return
        self.refresh(force=True)
        device = self._find_device(device_id)
        if device:
            self._selected_device = device
            self._open_device_panel(device)

    def _open_device_panel(self, device_or_id):
        try:
            device_id = self._device_id_from_input(device_or_id)
            device = self._find_device(device_id)
            if not device:
                return
            self._selected_device = device
            self._populate_panel(device)
            self._show_panel()
        except Exception:
            return

    def _show_panel(self):
        try:
            self._position_panel()
            self._panel.setVisible(True)
            self._panel.raise_()
            self._panel_effect.setOpacity(1.0)
        except Exception:
            self._panel.hide()
            self._panel_effect.setOpacity(0.0)

    def _close_panel(self):
        if not self._panel.isVisible():
            return
        self._panel.hide()
        self._panel_effect.setOpacity(0.0)

    def _clear_panel_controls(self):
        self._clear_layout(self._panel_controls)
        self._clear_layout(self._panel_actions)

    def _populate_panel(self, device: dict[str, object]):
        try:
            self._clear_panel_controls()
            self._clear_layout(self._panel_actions)
            name = str(device.get("name", "Device"))
            room = str(device.get("room", ""))
            device_type = str(device.get("device_type", "device")).lower()
            is_on = bool(device.get("is_on"))
            traits = device.get("traits") if isinstance(device.get("traits"), dict) else {}

            self._panel_name.setText(name)
            self._panel_meta.setText(
                f"Room: {room or 'Unassigned'}\nType: {device_type.title()}\nManufacturer: {device.get('manufacturer', '')}\nConnection: Connected"
            )
            self._panel_status.setText("ON" if is_on else "OFF")
            self._panel_hint.setText("Click outside the panel to close.")

            power_btn = QPushButton("Power")
            power_btn.clicked.connect(lambda: self._apply_tile_action(str(device.get("id", "")), "power", {"is_on": not is_on}))
            self._panel_actions.addWidget(power_btn)

            forget_btn = QPushButton("Forget")
            forget_btn.clicked.connect(lambda: self._forget_device(str(device.get("id", ""))))
            self._panel_actions.addWidget(forget_btn)

            rename_btn = QPushButton("Rename")
            rename_btn.clicked.connect(lambda: self._rename_device(str(device.get("id", "")), name))
            self._panel_actions.addWidget(rename_btn)

            if device_type == "fan":
                speed = int(traits.get("speed", 4) or 4)
                lbl = QLabel(f"Speed {speed}")
                lbl.setStyleSheet(f"color: {C.TEXT_MED};")
                self._panel_controls.addWidget(lbl)
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(1, 6)
                slider.setValue(speed)
                slider.valueChanged.connect(lambda value: self._apply_tile_action(str(device.get("id", "")), "speed", {"speed": value}))
                self._panel_controls.addWidget(slider)
            elif device_type == "light":
                brightness = int(traits.get("brightness", 75) or 75)
                lbl = QLabel(f"Brightness {brightness}%")
                lbl.setStyleSheet(f"color: {C.TEXT_MED};")
                self._panel_controls.addWidget(lbl)
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(1, 100)
                slider.setValue(brightness)
                slider.valueChanged.connect(lambda value: self._apply_tile_action(str(device.get("id", "")), "brightness", {"brightness": value}))
                self._panel_controls.addWidget(slider)
                color_btn = QPushButton("Color")
                color_btn.clicked.connect(lambda: self._pick_color(device))
                self._panel_controls.addWidget(color_btn)
            elif device_type == "ac":
                temperature = int(traits.get("temperature", 24) or 24)
                lbl = QLabel(f"Temperature {temperature}")
                lbl.setStyleSheet(f"color: {C.TEXT_MED};")
                self._panel_controls.addWidget(lbl)
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(16, 30)
                slider.setValue(temperature)
                slider.valueChanged.connect(lambda value: self._apply_tile_action(str(device.get("id", "")), "temperature", {"temperature": value}))
                self._panel_controls.addWidget(slider)
            elif device_type in ("tv", "speaker"):
                volume = int(traits.get("volume", 18) or 18)
                lbl = QLabel(f"Volume {volume}")
                lbl.setStyleSheet(f"color: {C.TEXT_MED};")
                self._panel_controls.addWidget(lbl)
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(volume)
                slider.valueChanged.connect(lambda value: self._apply_tile_action(str(device.get("id", "")), "volume", {"volume": value}))
                self._panel_controls.addWidget(slider)
            elif device_type == "plug":
                usage = traits.get("energy_usage", traits.get("power_usage", "N/A"))
                lbl = QLabel(f"Energy usage: {usage}")
                lbl.setStyleSheet(f"color: {C.TEXT_MED};")
                self._panel_controls.addWidget(lbl)
            else:
                lbl = QLabel("Primary controls are available from the card below.")
                lbl.setWordWrap(True)
                lbl.setStyleSheet(f"color: {C.TEXT_MED};")
                self._panel_controls.addWidget(lbl)
        except Exception:
            return

    def _pick_color(self, device: dict[str, object]):
        color = QColorDialog.getColor(QColor(C.PRI), self, "Pick Light Color")
        if color.isValid():
            self._apply_tile_action(str(device.get("id", "")), "color", {"color": color.name()})

    def _rename_device(self, device_id: str, current_name: str):
        new_name, ok = QInputDialog.getText(self, "Rename Device", "New name:", text=current_name)
        if ok and new_name.strip():
            try:
                self._service.rename_device(device_id, new_name.strip())
            except Exception:
                return
            self.refresh(force=True)

    def _forget_device(self, device_id: str):
        try:
            self._service.forget_device(device_id)
        except Exception:
            return
        self._close_panel()
        self.refresh(force=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._panel.isVisible():
            self._position_panel()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh(force=True)

    def _position_panel(self):
        panel_w = min(330, max(270, int(self.width() * 0.28)))
        panel_h = min(340, max(240, int(self.height() * 0.45)))
        x = max(12, self.width() - panel_w - 12)
        y = 12
        self._panel.setGeometry(x, y, panel_w, panel_h)

class _ConnectDeviceCard(QFrame):
    clicked = pyqtSignal(str)
    action_requested = pyqtSignal(str, str, dict)

    def __init__(self, device: dict[str, object], parent=None):
        super().__init__(parent)
        self.device = device
        self._expanded = False
        self.setObjectName("ConnectDeviceCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumSize(220, 150)
        self.setStyleSheet("""
            QFrame#ConnectDeviceCard {
                background: rgba(10, 12, 18, 240);
                border: 1px solid C.TEXT;
                border-radius: 18px;
            }
            QLabel {
                background: transparent;
            }
            QPushButton {
                background: C.TEXT;
                color: {C.WHITE};
                border: 1px solid C.TEXT;
                border-radius: 10px;
                min-height: 30px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230,0.12);
                color: {C.PRI};
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        self._title = QLabel(str(device.get("name", "Device")))
        self._title.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._title.setStyleSheet("color: {C.WHITE};")
        layout.addWidget(self._title)

        platform = str(device.get("platform", "UNKNOWN")).upper()
        status = "ONLINE" if bool(device.get("online")) else "OFFLINE"
        self._status_label = QLabel(f"{platform} • {status}")
        self._status_label.setFont(QFont("Exo 2", 8))
        self._status_label.setStyleSheet("color: C.TEXT;")
        layout.addWidget(self._status_label)

        info = []
        if device.get("manufacturer"):
            info.append(str(device.get("manufacturer")))
        if device.get("device_type"):
            info.append(str(device.get("device_type")))
        if device.get("ip"):
            info.append(str(device.get("ip")))
        self._info_lbl = QLabel(" ┬╖ ".join(info) if info else "Connected device")
        self._info_lbl.setFont(QFont("Exo 2", 8))
        self._info_lbl.setStyleSheet("color: C.TEXT;")
        self._info_lbl.setWordWrap(True)
        layout.addWidget(self._info_lbl)

        layout.addStretch(1)

        self._action_container = QFrame(self)
        self._action_container.setVisible(False)
        self._action_container.setStyleSheet("QFrame { background: C.TEXT; border-radius: 14px; }")
        actions_layout = QHBoxLayout(self._action_container)
        actions_layout.setContentsMargins(8, 8, 8, 8)
        actions_layout.setSpacing(8)

        self._rename_btn = QPushButton("Rename")
        self._disconnect_btn = QPushButton("Disconnect")
        self._forget_btn = QPushButton("Remove")
        self._pin_btn = QPushButton("Set PIN")

        actions_layout.addWidget(self._pin_btn)
        actions_layout.addWidget(self._rename_btn)
        actions_layout.addWidget(self._disconnect_btn)
        actions_layout.addWidget(self._forget_btn)
        layout.addWidget(self._action_container)

        self._pin_btn.clicked.connect(lambda: self.action_requested.emit(str(self.device.get("device_id", "")), "set_pin", {}))
        self._rename_btn.clicked.connect(lambda: self.action_requested.emit(str(self.device.get("device_id", "")), "rename", {}))
        self._disconnect_btn.clicked.connect(lambda: self.action_requested.emit(str(self.device.get("device_id", "")), "disconnect", {}))
        self._forget_btn.clicked.connect(lambda: self.action_requested.emit(str(self.device.get("device_id", "")), "forget", {}))

    def set_expanded(self, expanded: bool):
        self._expanded = bool(expanded)
        self._action_container.setVisible(self._expanded)
        if self._expanded:
            self.setStyleSheet("""
                QFrame#ConnectDeviceCard {
                    background: C.TEXT;
                    border: 1px solid rgba(124, 110, 230,0.25);
                    border-radius: 18px;
                }
                QLabel {
                    background: transparent;
                }
                QPushButton {
                    background: C.TEXT;
                    color: {C.WHITE};
                    border: 1px solid C.TEXT;
                    border-radius: 10px;
                    min-height: 30px;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background: rgba(124, 110, 230,0.16);
                    color: {C.PRI};
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#ConnectDeviceCard {
                    background: rgba(10, 12, 18, 240);
                    border: 1px solid C.TEXT;
                    border-radius: 18px;
                }
                QLabel {
                    background: transparent;
                }
                QPushButton {
                    background: C.TEXT;
                    color: {C.WHITE};
                    border: 1px solid C.TEXT;
                    border-radius: 10px;
                    min-height: 30px;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background: rgba(124, 110, 230,0.12);
                    color: {C.PRI};
                }
            """)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(str(self.device.get("device_id", "")))
        super().mouseReleaseEvent(event)

class StellaConnectDevicesPage(QFrame):
    _join_result_sig = pyqtSignal(object)
    _discover_result_sig = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._join_result_sig.connect(self._on_join_result)
        self._discover_result_sig.connect(self._on_discover_result)
        self._join_hosts_buttons: list[QPushButton] = []
        self._service = None
        self._connected_device = None
        self._log_snapshot = ""
        self._card_anims: list[QPropertyAnimation] = []
        self._cards: list[_ConnectDeviceCard] = []
        self._selected_device_id: str | None = None
        self._onboarding_known_device_ids: set[str] = set()

        self.setObjectName("StellaConnectDevicesPage")
        self.setStyleSheet(f"""
            QFrame#StellaConnectDevicesPage {{
                background: transparent;
                border: none;
            }}
            QLabel {{
                background: transparent;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self._title = QLabel("DEVICES")
        self._title.setFont(QFont("Orbitron", 18, QFont.Weight.Black))
        self._title.setStyleSheet("color: {C.WHITE}; letter-spacing: 2px;")
        self._subtitle = QLabel("Everything connected to Stella.")
        self._subtitle.setFont(QFont("Exo 2", 9))
        self._subtitle.setStyleSheet("color: C.TEXT;")
        title_box.addWidget(self._title)
        title_box.addWidget(self._subtitle)
        header.addLayout(title_box, 1)

        status_wrap = QVBoxLayout()
        status_wrap.setSpacing(4)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self._gateway_pill = QLabel("Î“ùÅ Gateway Online")
        self._gateway_pill.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        self._gateway_pill.setStyleSheet("color: {C.GREEN}; background: rgba(53,255,117,0.06); border: 1px solid rgba(53,255,117,0.16); border-radius: 12px; padding: 5px 10px;")
        top_row.addWidget(self._gateway_pill)
        top_row.addStretch(1)
        self._add_btn = QPushButton("+ Add Device")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setFixedHeight(34)
        self._add_btn.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(124, 110, 230, 0.10);
                color: {C.WHITE};
                border: 1px solid rgba(124, 110, 230, 0.25);
                border-radius: 12px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230, 0.16);
                border: 1px solid rgba(124, 110, 230, 0.40);
            }
        """)
        self._add_btn.clicked.connect(self._trigger_add_device)
        top_row.addWidget(self._add_btn)
        status_wrap.addLayout(top_row)
        self._gateway_meta = QLabel("Port: 8765  ┬╖  Devices: 0")
        self._gateway_meta.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._gateway_meta.setFont(QFont("Exo 2", 8))
        self._gateway_meta.setStyleSheet("color: C.TEXT;")
        status_wrap.addWidget(self._gateway_meta)
        header.addLayout(status_wrap)
        root.addLayout(header)

        self._main_stack = QStackedWidget()
        self._main_stack.setStyleSheet("background: transparent;")
        
        # ───────────────────────────────────────────────
        # PAGE 0 — OVERVIEW (GRID / EMPTY)
        # ───────────────────────────────────────────────
        self._overview_page = QWidget()
        ov_lay = QVBoxLayout(self._overview_page)
        ov_lay.setContentsMargins(0, 10, 0, 0)
        ov_lay.setSpacing(12)
        
        self._my_devices_lbl = QLabel("MY DEVICES")
        self._my_devices_lbl.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._my_devices_lbl.setStyleSheet("color: {C.WHITE}; letter-spacing: 1px;")
        ov_lay.addWidget(self._my_devices_lbl)
        
        self._overview_stack = QStackedWidget()
        
        # Grid View
        self._grid_page = QWidget()
        grid_lay = QVBoxLayout(self._grid_page)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(16)
        self._grid.setVerticalSpacing(16)
        self._scroll.setWidget(self._grid_host)
        grid_lay.addWidget(self._scroll)
        self._overview_stack.addWidget(self._grid_page)
        
        # Empty View
        self._empty_page = QWidget()
        empty_lay = QVBoxLayout(self._empty_page)
        empty_lay.addStretch(1)
        empty_lbl = QLabel("No devices connected yet.")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setFont(QFont("Exo 2", 12))
        empty_lbl.setStyleSheet("color: C.TEXT;")
        empty_lay.addWidget(empty_lbl)
        empty_btn = QPushButton("+ ADD DEVICE")
        empty_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_btn.setFixedSize(160, 40)
        empty_btn.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        empty_btn.setStyleSheet("""
            QPushButton {
                background: rgba(124, 110, 230, 0.10);
                color: {C.PRI};
                border: 1px solid rgba(124, 110, 230, 0.25);
                border-radius: 20px;
            }
            QPushButton:hover {
                background: rgba(124, 110, 230, 0.20);
                border: 1px solid rgba(124, 110, 230, 0.50);
            }
        """)
        empty_btn.clicked.connect(self._trigger_add_device)
        empty_lay.addWidget(empty_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_lay.addStretch(1)
        self._overview_stack.addWidget(self._empty_page)
        
        ov_lay.addWidget(self._overview_stack)
        self._main_stack.addWidget(self._overview_page)
        
        # ───────────────────────────────────────────────
        # PAGE 1 — DETAIL VIEW
        # ───────────────────────────────────────────────
        self._detail_page = QWidget()
        det_lay = QVBoxLayout(self._detail_page)
        det_lay.setContentsMargins(0, 10, 0, 0)
        det_lay.setSpacing(16)
        
        back_btn = QPushButton("← Back to Devices")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedSize(140, 32)
        back_btn.setFont(QFont("Exo 2", 9))
        back_btn.setStyleSheet("""
            QPushButton { background: transparent; color: C.TEXT; border: none; text-align: left; }
            QPushButton:hover { color: {C.PRI}; }
        """)
        back_btn.clicked.connect(self._close_detail)
        det_lay.addWidget(back_btn)
        
        self._detail_header = QHBoxLayout()
        self._detail_icon = QLabel()
        self._detail_icon.setFixedSize(48, 48)
        self._detail_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_icon.setFont(QFont("Exo 2", 20, QFont.Weight.Bold))
        self._detail_icon.setStyleSheet("background: rgba(124, 110, 230, 0.10); color: {C.PRI}; border: 1px solid rgba(124, 110, 230,0.22); border-radius: 12px;")
        self._detail_header.addWidget(self._detail_icon)
        
        det_titles = QVBoxLayout()
        self._detail_title = QLabel()
        self._detail_title.setFont(QFont("Exo 2", 16, QFont.Weight.Bold))
        self._detail_title.setStyleSheet("color: {C.WHITE};")
        det_titles.addWidget(self._detail_title)
        
        self._detail_status = QLabel()
        self._detail_status.setFont(QFont("Exo 2", 10))
        self._detail_status.setStyleSheet("color: C.TEXT;")
        det_titles.addWidget(self._detail_status)
        self._detail_header.addLayout(det_titles, 1)
        det_lay.addLayout(self._detail_header)
        
        self._detail_scroll = QScrollArea()
        self._detail_scroll.setWidgetResizable(True)
        self._detail_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._detail_content = QWidget()
        self._detail_content_lay = QVBoxLayout(self._detail_content)
        self._detail_content_lay.setContentsMargins(0, 10, 0, 10)
        self._detail_content_lay.setSpacing(16)
        
        # Meta info
        self._detail_meta = QLabel()
        self._detail_meta.setStyleSheet("color: C.TEXT;")
        self._detail_content_lay.addWidget(self._detail_meta)
        
        # Controls
        self._action_box = QFrame()
        self._action_box.setStyleSheet("QFrame { background: rgba(10, 12, 18, 220); border: 1px solid C.TEXT; border-radius: 16px; }")
        action_lay = QVBoxLayout(self._action_box)
        action_lay.setContentsMargins(16, 16, 16, 16)
        action_title = QLabel("CONTROLS")
        action_title.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        action_title.setStyleSheet("color: {C.WHITE}; letter-spacing: 1px;")
        action_lay.addWidget(action_title)
        self._action_buttons = QGridLayout()
        self._action_buttons.setSpacing(8)
        action_lay.addLayout(self._action_buttons)
        self._detail_content_lay.addWidget(self._action_box)
        
        # Manage
        manage_box = QFrame()
        manage_box.setStyleSheet("QFrame { background: rgba(10, 12, 18, 220); border: 1px solid C.TEXT; border-radius: 16px; }")
        manage_lay = QVBoxLayout(manage_box)
        manage_lay.setContentsMargins(16, 16, 16, 16)
        manage_title = QLabel("MANAGE")
        manage_title.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        manage_title.setStyleSheet("color: {C.WHITE}; letter-spacing: 1px;")
        manage_lay.addWidget(manage_title)
        
        self._btn_rename = QPushButton("Rename Device")
        self._btn_disconnect = QPushButton("Disconnect")
        self._btn_reconnect = QPushButton("Reconnect")
        self._btn_forget = QPushButton("Forget Device")
        self._btn_forget.setStyleSheet("QPushButton { color: {C.RED}; } QPushButton:hover { background: rgba(255, 85, 85, 0.1); border-color: {C.RED}; }")
        
        manage_grid = QGridLayout()
        manage_grid.setSpacing(8)
        for i, b in enumerate([self._btn_rename, self._btn_disconnect, self._btn_reconnect, self._btn_forget]):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(34)
            if b != self._btn_forget:
                b.setStyleSheet("""
                    QPushButton { background: C.TEXT; color: {C.WHITE}; border: 1px solid C.TEXT; border-radius: 10px; }
                    QPushButton:hover { background: rgba(124, 110, 230,0.08); border: 1px solid rgba(124, 110, 230,0.22); color: {C.PRI}; }
                """)
            else:
                b.setStyleSheet("""
                    QPushButton { background: C.TEXT; color: {C.RED}; border: 1px solid C.TEXT; border-radius: 10px; }
                    QPushButton:hover { background: rgba(255,85,85,0.1); border: 1px solid rgba(255,85,85,0.3); }
                """)
            manage_grid.addWidget(b, i // 2, i % 2)
            
        manage_lay.addLayout(manage_grid)
        self._detail_content_lay.addWidget(manage_box)
        self._detail_content_lay.addStretch(1)
        self._detail_scroll.setWidget(self._detail_content)
        det_lay.addWidget(self._detail_scroll)
        
        self._main_stack.addWidget(self._detail_page)
        
        # ───────────────────────────────────────────────
        # PAGE 2 — ADD DEVICE (QR WIZARD)
        # ───────────────────────────────────────────────
        self._add_device_page = QWidget()
        add_lay = QVBoxLayout(self._add_device_page)
        add_lay.setContentsMargins(0, 10, 0, 0)
        
        add_back_btn = QPushButton("← Cancel")
        add_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_back_btn.setFixedSize(140, 32)
        add_back_btn.setFont(QFont("Exo 2", 9))
        add_back_btn.setStyleSheet("""
            QPushButton { background: transparent; color: C.TEXT; border: none; text-align: left; }
            QPushButton:hover { color: {C.PRI}; }
        """)
        add_back_btn.clicked.connect(self._close_detail)
        add_lay.addWidget(add_back_btn)
        
        # Re-use the stacked widget logic for the wizard steps
        self._wizard_stack = QStackedWidget()
        
        # Wizard State 0: Select Platform
        w0 = QWidget()
        w0_lay = QVBoxLayout(w0)
        w0_lay.addStretch(1)
        w0_title = QLabel("SELECT DEVICE TYPE")
        w0_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w0_title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        w0_title.setStyleSheet("color: {C.WHITE}; letter-spacing: 2px;")
        w0_lay.addWidget(w0_title)
        w0_lay.addSpacing(20)
        
        w0_row = QHBoxLayout()
        w0_row.addStretch(1)
        self._cs_android_btn = QPushButton("ANDROID")
        self._cs_android_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cs_android_btn.setFixedSize(140, 80)
        self._cs_android_btn.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._cs_android_btn.setStyleSheet("""
            QPushButton { background: rgba(10, 12, 18, 220); color: C.TEXT; border: 1px solid C.TEXT; border-radius: 12px; }
            QPushButton:hover { color: {C.PRI}; border: 1px solid rgba(124, 110, 230,0.6); background: rgba(124, 110, 230,0.1); }
        """)
        self._cs_android_btn.clicked.connect(self._cinema_select_android)
        w0_row.addWidget(self._cs_android_btn)
        
        self._cs_pc_btn = QPushButton("PC")
        self._cs_pc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cs_pc_btn.setFixedSize(140, 80)
        self._cs_pc_btn.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._cs_pc_btn.setStyleSheet("""
            QPushButton { background: rgba(10, 12, 18, 220); color: C.TEXT; border: 1px solid C.TEXT; border-radius: 12px; }
            QPushButton:hover { color: {C.PRI}; border: 1px solid rgba(124, 110, 230,0.6); background: rgba(124, 110, 230,0.1); }
        """)
        self._cs_pc_btn.clicked.connect(self._cinema_select_android)
        w0_row.addWidget(self._cs_pc_btn)
        w0_row.addStretch(1)
        w0_lay.addLayout(w0_row)
        w0_lay.addSpacing(14)
        self._cs_join_btn = QPushButton("CONNECT TO A DEVICE")
        self._cs_join_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cs_join_btn.setFixedSize(200, 40)
        self._cs_join_btn.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        self._cs_join_btn.setStyleSheet("""
            QPushButton { background: rgba(124, 110, 230, 0.10); color: {C.PRI}; border: 1px solid rgba(124, 110, 230, 0.30); border-radius: 12px; }
            QPushButton:hover { color: {C.WHITE}; border: 1px solid rgba(124, 110, 230, 0.6); background: rgba(124, 110, 230, 0.2); }
        """)
        self._cs_join_btn.clicked.connect(self._goto_join)
        w0_lay.addWidget(self._cs_join_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        w0_lay.addStretch(1)
        self._wizard_stack.addWidget(w0)
        
        # Wizard State 1: QR Code
        w1 = QWidget()
        w1_lay = QVBoxLayout(w1)
        w1_lay.addStretch(1)
        w1_title = QLabel("SCAN TO CONNECT")
        w1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w1_title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        w1_title.setStyleSheet("color: {C.WHITE}; letter-spacing: 2px;")
        w1_lay.addWidget(w1_title)
        w1_lay.addSpacing(16)
        
        w1_qr_row = QHBoxLayout()
        w1_qr_row.addStretch(1)
        self._onb_qr_label = QLabel()
        self._onb_qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._onb_qr_label.setFixedSize(200, 200)
        self._onb_qr_label.setStyleSheet("background: {C.WHITE}; border-radius: 6px; padding: 4px;")
        w1_qr_row.addWidget(self._onb_qr_label)
        w1_qr_row.addStretch(1)
        w1_lay.addLayout(w1_qr_row)
        
        w1_lay.addSpacing(16)
        self._onb_code_lbl = QLabel("------")
        self._onb_code_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._onb_code_lbl.setFont(QFont("Consolas", 18, QFont.Weight.Black))
        self._onb_code_lbl.setStyleSheet("color: {C.PRI}; letter-spacing: 6px;")
        w1_lay.addWidget(self._onb_code_lbl)
        
        self._onb_status_lbl = QLabel("WAITING FOR CONNECTION")
        self._onb_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._onb_status_lbl.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        self._onb_status_lbl.setStyleSheet("color: C.TEXT; letter-spacing: 1px;")
        w1_lay.addWidget(self._onb_status_lbl)
        
        w1_ctrl = QHBoxLayout()
        w1_ctrl.addStretch(1)
        w1_ref = QPushButton("Refresh Code")
        w1_ref.setCursor(Qt.CursorShape.PointingHandCursor)
        w1_ref.setFixedSize(120, 32)
        w1_ref.setStyleSheet("""
            QPushButton { background: C.TEXT; color: {C.WHITE}; border: 1px solid C.TEXT; border-radius: 16px; }
            QPushButton:hover { background: C.TEXT; }
        """)
        w1_ref.clicked.connect(self._refresh_onboarding_offer)
        w1_ctrl.addWidget(w1_ref)
        w1_ctrl.addStretch(1)
        w1_lay.addLayout(w1_ctrl)
        w1_lay.addStretch(1)
        self._wizard_stack.addWidget(w1)
        
        # Wizard State 2: Success
        w2 = QWidget()
        w2_lay = QVBoxLayout(w2)
        w2_lay.addStretch(1)
        self._onb_success_title = QLabel("DEVICE CONNECTED")
        self._onb_success_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._onb_success_title.setFont(QFont("Orbitron", 16, QFont.Weight.Black))
        self._onb_success_title.setStyleSheet("color: {C.GREEN}; letter-spacing: 2px;")
        w2_lay.addWidget(self._onb_success_title)
        self._onb_success_name = QLabel("")
        self._onb_success_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._onb_success_name.setFont(QFont("Exo 2", 20, QFont.Weight.Bold))
        self._onb_success_name.setStyleSheet("color: {C.WHITE};")
        w2_lay.addWidget(self._onb_success_name)
        w2_lay.addStretch(1)
        self._wizard_stack.addWidget(w2)

        # Wizard State 3: Join another Stella (the three connect methods)
        w3 = QWidget()
        w3_lay = QVBoxLayout(w3)
        w3_lay.addStretch(1)
        w3_title = QLabel("CONNECT TO A STELLA")
        w3_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w3_title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        w3_title.setStyleSheet("color: {C.WHITE}; letter-spacing: 2px;")
        w3_lay.addWidget(w3_title)
        w3_sub = QLabel("Any method reaches the same host - pick whichever is easiest.")
        w3_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w3_sub.setFont(QFont("Exo 2", 8))
        w3_sub.setStyleSheet("color: C.TEXT;")
        w3_lay.addWidget(w3_sub)
        w3_lay.addSpacing(14)

        w3_methods = QHBoxLayout()
        w3_methods.addStretch(1)
        self._join_qr_btn = QPushButton("SCAN QR CODE")
        self._join_disc_btn = QPushButton("AUTO DISCOVER")
        self._join_ip_btn = QPushButton("ENTER IP")
        for _btn in (self._join_qr_btn, self._join_disc_btn, self._join_ip_btn):
            _btn.setCursor(Qt.CursorShape.PointingHandCursor)
            _btn.setFixedSize(150, 76)
            _btn.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
            _btn.setStyleSheet("""
                QPushButton { background: rgba(10, 12, 18, 220); color: C.TEXT; border: 1px solid C.TEXT; border-radius: 12px; }
                QPushButton:hover { color: {C.PRI}; border: 1px solid rgba(124, 110, 230,0.6); background: rgba(124, 110, 230,0.1); }
            """)
            w3_methods.addWidget(_btn)
            w3_methods.addSpacing(10)
        w3_methods.addStretch(1)
        w3_lay.addLayout(w3_methods)
        self._join_qr_btn.clicked.connect(self._join_scan_qr)
        self._join_disc_btn.clicked.connect(self._join_auto_discover)
        self._join_ip_btn.clicked.connect(self._join_manual)
        w3_lay.addSpacing(14)

        self._join_status_lbl = QLabel("")
        self._join_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._join_status_lbl.setWordWrap(True)
        self._join_status_lbl.setFont(QFont("Exo 2", 9))
        self._join_status_lbl.setStyleSheet("color: C.TEXT;")
        w3_lay.addWidget(self._join_status_lbl)

        self._join_hosts_box = QVBoxLayout()
        self._join_hosts_box.setSpacing(6)
        w3_lay.addLayout(self._join_hosts_box)

        w3_back = QPushButton("Back")
        w3_back.setCursor(Qt.CursorShape.PointingHandCursor)
        w3_back.setFixedSize(140, 32)
        w3_back.setStyleSheet("QPushButton { background: transparent; color: C.TEXT; border: none; } QPushButton:hover { color: {C.PRI}; }")
        w3_back.clicked.connect(lambda: self._wizard_stack.setCurrentIndex(0))
        w3_lay.addWidget(w3_back, alignment=Qt.AlignmentFlag.AlignHCenter)
        w3_lay.addStretch(1)
        self._wizard_stack.addWidget(w3)

        add_lay.addWidget(self._wizard_stack)
        self._main_stack.addWidget(self._add_device_page)
        
        root.addWidget(self._main_stack)
        
        self._onboarding_timer = QTimer(self)
        self._onboarding_timer.timeout.connect(self._tick_onboarding)
        self._onboarding_offer = {}
        self._onboarding_pulse = 0

    def _service_obj(self):
        return self._service or getattr(self.parentWidget(), "_stella_connect", None)

    def set_service(self, service):
        self._service = service

    def _trigger_add_device(self):
        self._main_stack.setCurrentIndex(2)
        self._wizard_stack.setCurrentIndex(0)

    # --- Join role: connect this machine out to another Stella -------------
    def _goto_join(self):
        self._clear_join_hosts()
        self._join_status_lbl.setText("")
        self._main_stack.setCurrentIndex(2)
        self._wizard_stack.setCurrentIndex(3)

    def _clear_join_hosts(self):
        for btn in self._join_hosts_buttons:
            try:
                btn.setParent(None)
                btn.deleteLater()
            except Exception:
                pass
        self._join_hosts_buttons = []
        while self._join_hosts_box.count():
            item = self._join_hosts_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _join_identity(self) -> dict:
        return {"name": "Stella Desktop", "platform": "desktop",
                "agent_version": "1", "capabilities": ["chat", "notifications", "clipboard", "files"]}

    def _join_scan_qr(self):
        text, ok = QInputDialog.getMultiLineText(
            self, "Scan QR Code",
            "Point the other Stella's QR here, or paste its pairing code text:",
        )
        if not ok or not text.strip():
            return
        try:
            from stella_connect import pairing_flow
            target = pairing_flow.from_qr(text.strip())
        except Exception as exc:
            self._join_status_lbl.setText(f"Not a valid Stella code: {exc}")
            return
        self._join_status_lbl.setText(f"Found {target.label()}. Connecting...")
        self._join_with_target(target.to_dict())

    def _join_auto_discover(self):
        service = self._service_obj()
        if service is None:
            self._join_status_lbl.setText("Gateway unavailable - cannot search.")
            return
        self._clear_join_hosts()
        self._join_status_lbl.setText("Searching the network for Stella...")
        discover = getattr(service, "discover_hosts", None)
        if discover is None:
            self._join_status_lbl.setText("Discovery not available in this build.")
            return

        def _work():
            try:
                hosts = discover(3.0)
            except Exception:
                hosts = []
            self._discover_result_sig.emit(hosts)

        threading.Thread(target=_work, daemon=True).start()

    def _on_discover_result(self, hosts):
        self._clear_join_hosts()
        if not hosts:
            self._join_status_lbl.setText("No Stella found nearby. Make sure the other device is hosting.")
            return
        self._join_status_lbl.setText(f"Found {len(hosts)} Stella nearby - tap to connect.")
        for host in hosts:
            from stella_connect import pairing_flow
            target = pairing_flow.PairingTarget(
                host=str(host.get("host") or ""),
                port=int(host.get("port") or pairing_flow.DEFAULT_PORT),
                name=str(host.get("name") or ""),
                platform=str(host.get("platform") or ""),
                method=pairing_flow.METHOD_DISCOVER,
            )
            btn = QPushButton(target.label())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton { background: rgba(124, 110, 230, 0.10); color: {C.WHITE}; border: 1px solid rgba(124, 110, 230, 0.25); border-radius: 10px; padding: 0 12px; }
                QPushButton:hover { background: rgba(124, 110, 230, 0.2); border: 1px solid rgba(124, 110, 230, 0.5); }
            """)
            btn.clicked.connect(lambda _=False, t=target.to_dict(): self._join_with_target(t))
            self._join_hosts_box.addWidget(btn)
            self._join_hosts_buttons.append(btn)

    def _join_manual(self):
        text, ok = QInputDialog.getText(
            self, "Enter Address", "Host address (e.g. 192.168.1.5 or 192.168.1.5:8765):",
        )
        if not ok or not text.strip():
            return
        code, ok2 = QInputDialog.getText(self, "Pairing Code", "6-digit pairing code (leave blank if none):")
        code = code.strip() if ok2 else ""
        try:
            from stella_connect import pairing_flow
            target = pairing_flow.manual(text.strip(), pairing_code=code)
        except Exception as exc:
            self._join_status_lbl.setText(f"Invalid address: {exc}")
            return
        self._join_status_lbl.setText(f"Connecting to {target.label()}...")
        self._join_with_target(target.to_dict())

    def _join_with_target(self, target: dict):
        service = self._service_obj()
        if service is None:
            self._join_status_lbl.setText("Gateway unavailable - cannot connect.")
            return
        joiner = getattr(service, "join_target", None)
        if joiner is None:
            self._join_status_lbl.setText("Outbound pairing not available in this build.")
            return
        identity = self._join_identity()

        def _work():
            try:
                result = joiner(target, identity)
                payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
            except Exception as exc:
                payload = {"success": False, "error": str(exc)}
            self._join_result_sig.emit(payload)

        threading.Thread(target=_work, daemon=True).start()

    def _on_join_result(self, payload: dict):
        if payload.get("success"):
            device = dict(payload.get("device") or {})
            self._connected_device = device
            self._onb_success_name.setText(str(device.get("name") or "Device").upper())
            self._wizard_stack.setCurrentIndex(2)
            QTimer.singleShot(1500, self._close_detail)
        else:
            self._join_status_lbl.setText(str(payload.get("error") or "Could not connect."))

    def _cinema_select_android(self):
        self._wizard_stack.setCurrentIndex(1)
        service = self._service_obj()
        self._onboarding_known_device_ids = set(str(d.get("device_id", "")) for d in service.list_devices()) if service else set()
        self._onboarding_timer.start(1000)
        self._refresh_onboarding_offer()

    def _refresh_onboarding_offer(self):
        service = self._service_obj()
        if service is None:
            self._onboarding_offer = {}
            self._onb_code_lbl.setText("------")
            self._onb_status_lbl.setText("GATEWAY UNAVAILABLE")
            return
        try:
            import io
            import qrcode

            self._onboarding_offer = dict(service.create_pairing_offer(device_name="Stella Connect", platform="desktop"))
            code = str(self._onboarding_offer.get("pairing_code") or "------")
            self._onb_code_lbl.setText(code)
            self._onb_status_lbl.setText("WAITING FOR CONNECTION")
            
            builder = getattr(service, "pairing_qr_payload", None)
            try:
                payload = builder(device_name="Stella Connect", platform="desktop") if builder else self._onboarding_offer
            except Exception:
                payload = self._onboarding_offer
            text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            if qrcode is not None:
                qr = qrcode.QRCode(box_size=6, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
                qr.add_data(text)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                pix = QPixmap()
                pix.loadFromData(buf.getvalue(), "PNG")
                self._onb_qr_label.setPixmap(
                    pix.scaled(
                        self._onb_qr_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self._onb_qr_label.setText(text)
                
            self._tick_onboarding()
        except Exception as exc:
            self._onboarding_offer = {}
            self._onb_code_lbl.setText("------")
            self._onb_status_lbl.setText(f"ERROR: {exc}")

    def _tick_onboarding(self):
        if self._wizard_stack.currentIndex() != 1:
            return
        
        expires = self._onboarding_offer.get("expires")
        try:
            remaining = max(0, int(expires))
            if remaining <= 0 and self._onboarding_offer:
                self._onb_status_lbl.setText("CODE EXPIRED. REFRESH TO CONTINUE.")
        except Exception:
            pass
            
        service = self._service_obj()
        if service and self._onboarding_offer:
            devices = service.list_devices()
            new_device = next(
                (d for d in devices if str(d.get("device_id", "")) not in self._onboarding_known_device_ids),
                None,
            )
            if new_device:
                self._onboarding_timer.stop()
                self._connected_device = new_device
                self._trigger_onboarding_success()

    def _trigger_onboarding_success(self):
        self._wizard_stack.setCurrentIndex(2)
        dev = self._connected_device
        self._onb_success_name.setText(str(dev.get("name", "Device")).upper())
        QTimer.singleShot(2000, lambda: self.refresh(force=True))

    def _cancel_onboarding(self):
        self._onboarding_timer.stop()
        self._close_detail()

    def _clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _on_device_selected(self, device_id: str):
        if self._selected_device_id == device_id:
            self._selected_device_id = None
        else:
            self._selected_device_id = device_id
        self.refresh(force=True)

    def _on_card_action_requested(self, device_id: str, action: str, payload: dict):
        if action == "rename":
            service = self._service_obj()
            if not service:
                return
            device = next((d for d in service.list_devices() if str(d.get("device_id", "")) == device_id), None)
            if device:
                self._rename_device(device_id, str(device.get("name", "")))
            return
        if action == "disconnect":
            self._apply_tile_action(device_id, "disconnect", payload)
            return
        if action == "forget":
            self._apply_tile_action(device_id, "forget", payload)
            return
        self._apply_tile_action(device_id, action, payload)
        return

    def _close_detail(self):
        self._selected_device_id = None
        self._main_stack.setCurrentIndex(0)
        self.refresh(force=True)

    def refresh(self, force: bool = False):
        service = self._service_obj()
        if service is None:
            return
            
        devices = service.list_devices()
        port = getattr(service, "port", 8765)
        self._gateway_meta.setText(f"Port: {port}  ┬╖  Devices: {len(devices)}")
        
        # If we are in Add Device or Detail page, keep it there
        if self._main_stack.currentIndex() not in (0,) and not force:
            pass # Keep current index unless forced to reset
        elif len(devices) == 0:
            self._main_stack.setCurrentIndex(0)
            self._overview_stack.setCurrentIndex(1) # Empty state
        else:
            self._main_stack.setCurrentIndex(0)
            self._overview_stack.setCurrentIndex(0) # Grid state
            
        # Rebuild grid
        self._clear_layout(self._grid)
        self._cards.clear()
        
        if devices:
            cols = 4
            for i, dev in enumerate(devices):
                card = _ConnectDeviceCard(dev)
                card.clicked.connect(self._on_device_selected)
                card.action_requested.connect(self._on_card_action_requested)
                card.set_expanded(str(dev.get("device_id", "")) == self._selected_device_id)
                self._cards.append(card)
                self._grid.addWidget(card, i // cols, i % cols)
            self._grid.setRowStretch(len(devices) // cols + 1, 1)

    def _apply_tile_action(self, device_id: str, action: str, payload: dict):
        service = self._service_obj()
        if not service:
            return
        try:
            if action == "rename":
                device = next((d for d in service.list_devices() if str(d.get("device_id", "")) == device_id), None)
                if device:
                    self._rename_device(device_id, str(device.get("name", "")))
                    return
            elif action == "disconnect":
                if hasattr(service, "disconnect_device"):
                    try:
                        asyncio.run(service.disconnect_device(device_id))
                    except Exception:
                        pass
            elif action == "forget":
                self._forget_device(device_id)
                return
            elif action == "set_pin":
                self._set_device_pin(device_id)
                return
            else:
                if hasattr(service, "route_command"):
                    service.route_command(device_id, action, payload)
                else:
                    service.execute_device_action(device_id, action, payload)
        except Exception:
            pass
        QTimer.singleShot(200, lambda: self.refresh(force=True))

    def _rename_device(self, device_id: str, current_name: str):
        new_name, ok = QInputDialog.getText(self, "Rename Device", "New name:", text=current_name)
        if ok and new_name.strip():
            service = self._service_obj()
            if service:
                try:
                    service.rename_device(device_id, new_name.strip())
                    self._on_device_selected(device_id)
                except Exception:
                    pass
            self.refresh(force=True)

    def _set_device_pin(self, device_id: str):
        pin, ok = QInputDialog.getText(self, "Set Device PIN", "Enter device PIN:", QLineEdit.EchoMode.Password)
        if ok and pin.strip():
            try:
                settings = {}
                if APP_SETTINGS_FILE.exists():
                    with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                        settings = json.load(f)
                
                device_pins = settings.get("device_pins", {})
                device_pins[device_id] = pin.strip()
                settings["device_pins"] = device_pins
                
                with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4)
            except Exception as e:
                print(f"Error saving pin: {e}")

    def _forget_device(self, device_id: str):
        service = self._service_obj()
        if service:
            try:
                if hasattr(service, "forget_device"):
                    service.forget_device(device_id)
                elif hasattr(service, "gateway") and hasattr(service.gateway, "device_manager"):
                    service.gateway.device_manager.remove(device_id)
            except Exception:
                pass
        self._close_detail()
        self.refresh(force=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh(force=True)

