from __future__ import annotations

from ._imports import *
from .common import *
from .settings import SettingsHubPage


class SettingsSidebar(QWidget):
    """Settings sidebar with 6-section IA (AnythingLLM pattern)."""
    
    section_changed = pyqtSignal(str)
    
    SECTIONS = [
        ("ai_models", "AI & Models", "🤖"),
        ("connections", "Connections", "🔗"),
        ("memory_data", "Memory & Data", "🧠"),
        ("permissions", "Permissions & Automation", "🔐"),
        ("appearance", "Appearance", "🎨"),
        ("system", "System", "⚙️"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
            }}
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(8)
        
        # Title
        title = QLabel("SETTINGS")
        title.setFont(QFont("Orbitron", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.TEXT_DIM}; letter-spacing: 1px;")
        lay.addWidget(title)
        
        lay.addSpacing(8)
        
        # Section buttons
        self._buttons = {}
        self._active_section = "ai_models"
        
        for section_id, section_name, icon in self.SECTIONS:
            btn = QPushButton(f"  {icon}  {section_name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setFont(QFont("Exo 2", 11))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {C.TEXT_DIM};
                    border: none;
                    border-radius: 10px;
                    padding: 0 14px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {C.PRI_GHO};
                    color: {C.TEXT};
                }}
                QPushButton:checked {{
                    background: {C.PRI};
                    color: {C.BG};
                    font-weight: bold;
                }}
            """)
            btn.clicked.connect(lambda checked, sid=section_id: self._on_section_clicked(sid))
            self._buttons[section_id] = btn
            lay.addWidget(btn)
        
        lay.addStretch(1)
        
        # Version info
        version = QLabel("v1.0.0")
        version.setFont(QFont("Exo 2", 8))
        version.setStyleSheet(f"color: {C.TEXT_MED};")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(version)
        
        # Set initial active
        self._buttons[self._active_section].setChecked(True)
    
    def _on_section_clicked(self, section_id: str):
        if section_id == self._active_section:
            return
        self._buttons[self._active_section].setChecked(False)
        self._active_section = section_id
        self._buttons[section_id].setChecked(True)
        self.section_changed.emit(section_id)


class SettingsContentPage(QWidget):
    """Base class for settings section pages."""
    
    def __init__(self, section_id: str, section_name: str, controller=None, parent=None):
        super().__init__(parent)
        self._section_id = section_id
        self._section_name = section_name
        self._controller = controller
        self.setStyleSheet("background: transparent;")
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)
        
        # Header
        header = QLabel(section_name)
        header.setFont(QFont("Orbitron", 24, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {C.TEXT}; letter-spacing: 1px;")
        lay.addWidget(header)
        
        self._content_layout = lay
    
    def get_content_layout(self):
        return self._content_layout
    
    def _make_card(self, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background: {C.SURFACE};
                border: 1px solid {C.BORDER};
                border-radius: 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Exo 2", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {C.TEXT};")
        lay.addWidget(title_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setFont(QFont("Exo 2", 10))
        desc_lbl.setStyleSheet(f"color: {C.TEXT_DIM};")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)
        
        return card

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                selection-background-color: {C.PRI};
            }}
        """

    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
            }}
        """


class AIModelsPage(SettingsContentPage):
    """AI & Models section - Cloud Providers, On-device Model, Routing."""
    
    PROVIDER_MAP = {
        "Groq": "groq", "Google Gemini": "gemini", "OpenAI": "openai",
        "Anthropic": "anthropic", "OpenRouter": "openrouter",
        "Ollama (Local)": "ollama", "LM Studio (Local)": "lmstudio",
        "Custom (OpenAI-compatible)": "custom",
    }
    
    def __init__(self, controller=None, parent=None):
        super().__init__("ai_models", "AI & Models", controller, parent)
        
        # Cloud Providers
        self._add_cloud_providers_section()
        
        # On-device Model
        self._add_local_model_section()
        
        # Routing
        self._add_routing_section()
    
    def _add_cloud_providers_section(self):
        card = self._make_card("Cloud Providers", "Configure AI providers for chat, agent, and voice.")
        lay = card.layout()
        
        # Provider selector
        from core.theme_tokens import theme_manager
        
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider:"))
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(list(self.PROVIDER_MAP.keys()))
        self._provider_combo.setFixedHeight(36)
        self._provider_combo.setStyleSheet(self._combo_style())
        self._provider_combo.currentTextChanged.connect(self._on_provider_selected)
        provider_row.addWidget(self._provider_combo, 1)
        lay.addLayout(provider_row)
        
        # API Key
        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("API Key:"))
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Enter API key")
        self._api_key.setStyleSheet(self._input_style())
        api_row.addWidget(self._api_key, 1)
        self._api_reveal = QPushButton("👁")
        self._api_reveal.setCheckable(True)
        self._api_reveal.setFixedWidth(40)
        self._api_reveal.clicked.connect(self._toggle_api_reveal)
        api_row.addWidget(self._api_reveal)
        lay.addLayout(api_row)
        
        # Model (with fetch button)
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        self._model_combo.setFixedHeight(36)
        self._model_combo.setStyleSheet(self._combo_style())
        model_row.addWidget(self._model_combo, 1)
        self._fetch_models = QPushButton("Fetch Models")
        self._fetch_models.setFixedHeight(36)
        self._fetch_models.clicked.connect(self._fetch_models_clicked)
        model_row.addWidget(self._fetch_models)
        lay.addLayout(model_row)
        
        # Base URL (for Local/Custom)
        self._base_url_row = QHBoxLayout()
        self._base_url_row.addWidget(QLabel("Base URL:"))
        self._base_url = QLineEdit()
        self._base_url.setPlaceholderText("http://localhost:11434/v1")
        self._base_url.setStyleSheet(self._input_style())
        self._base_url_row.addWidget(self._base_url, 1)
        lay.addLayout(self._base_url_row)
        
        # Extra headers (Custom)
        self._headers_row = QHBoxLayout()
        self._headers_row.addWidget(QLabel("Headers (JSON):"))
        self._headers = QLineEdit()
        self._headers.setPlaceholderText('{"Authorization": "Bearer ..."}')
        self._headers.setStyleSheet(self._input_style())
        self._headers_row.addWidget(self._headers, 1)
        lay.addLayout(self._headers_row)
        
        # Params
        params_row = QHBoxLayout()
        params_row.addWidget(QLabel("Params:"))
        self._params = QLineEdit()
        self._params.setPlaceholderText('{"temperature": 0.7, "max_tokens": 2048}')
        self._params.setStyleSheet(self._input_style())
        params_row.addWidget(self._params, 1)
        lay.addLayout(params_row)
        
        # Actions
        actions = QHBoxLayout()
        self._test_conn = QPushButton("Test Connection")
        self._test_conn.clicked.connect(self._test_connection)
        self._save_provider = QPushButton("Save")
        self._save_provider.setStyleSheet(f"background: {C.PRI}; color: {C.BG};")
        self._save_provider.clicked.connect(self._save_provider_clicked)
        self._forget_provider = QPushButton("Forget")
        self._forget_provider.setStyleSheet(f"background: rgba(255,85,85,0.15); color: {C.RED};")
        self._forget_provider.clicked.connect(self._forget_provider_clicked)
        actions.addWidget(self._test_conn)
        actions.addWidget(self._save_provider)
        actions.addWidget(self._forget_provider)
        actions.addStretch(1)
        lay.addLayout(actions)
        
        self._content_layout.addWidget(card)
        
        self._load_provider_into_form(self.PROVIDER_MAP[self._provider_combo.currentText()])
    
    def _on_provider_selected(self, label: str):
        pid = self.PROVIDER_MAP.get(label, "custom")
        self._load_provider_into_form(pid)
    
    def _load_provider_into_form(self, pid: str):
        from core.cloud_config import PRESETS, load_provider
        cfg = None
        try:
            cfg = load_provider(pid)
        except Exception:
            cfg = None
        self._api_key.clear()
        self._model_combo.clear()
        self._headers.clear()
        self._params.clear()
        if cfg:
            self._model_combo.setEditText(cfg.get("model", ""))
            self._base_url.setText(cfg.get("base_url", ""))
            if cfg.get("headers"):
                import json
                self._headers.setText(json.dumps(cfg["headers"]))
            if cfg.get("params"):
                import json
                self._params.setText(json.dumps(cfg["params"]))
            if cfg.get("api_key"):
                self._api_key.setPlaceholderText("Saved key (hidden)")
            else:
                self._api_key.setPlaceholderText("Enter API key")
        else:
            self._api_key.setPlaceholderText("Enter API key")
            preset = PRESETS.get(pid)
            self._base_url.setText(preset.get("base_url", "") if preset else "")
    
    def _add_local_model_section(self):
        card = self._make_card("On-device Model", "Status, import .gguf, runtime engine, remove/unload.")
        lay = card.layout()
        
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self._local_status = QLabel("Not loaded")
        self._local_status.setStyleSheet(f"color: {C.TEXT_MED};")
        status_row.addWidget(self._local_status, 1)
        lay.addLayout(status_row)
        
        # Import/Download
        import_row = QHBoxLayout()
        self._import_btn = QPushButton("Import .gguf")
        self._import_btn.clicked.connect(self._import_model)
        self._browse_btn = QPushButton("Browse Models")
        self._browse_btn.clicked.connect(self._browse_models)
        import_row.addWidget(self._import_btn)
        import_row.addWidget(self._browse_btn)
        import_row.addStretch(1)
        lay.addLayout(import_row)
        
        # Engine selector
        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Engine:"))
        self._engine_combo = QComboBox()
        self._engine_combo.addItems(["llama.cpp", "Ollama", "LM Studio"])
        self._engine_combo.setStyleSheet(self._combo_style())
        engine_row.addWidget(self._engine_combo, 1)
        lay.addLayout(engine_row)
        
        # Unload
        self._unload_btn = QPushButton("Unload Model")
        self._unload_btn.setStyleSheet(f"background: rgba(255,85,85,0.15); color: {C.RED};")
        self._unload_btn.clicked.connect(self._unload_model)
        lay.addWidget(self._unload_btn)
        
        self._content_layout.addWidget(card)
        
        # Image generation
        self._add_image_gen_section()
    
    def _add_image_gen_section(self):
        card = self._make_card("Image Generation", "Generate images from text prompts using a local model or remote endpoint.")
        lay = card.layout()
        
        # Endpoint
        endpoint_row = QHBoxLayout()
        endpoint_row.addWidget(QLabel("Endpoint URL:"))
        self._img_endpoint = QLineEdit()
        self._img_endpoint.setPlaceholderText("http://localhost:11434/v1/images/generations")
        self._img_endpoint.setStyleSheet(self._input_style())
        endpoint_row.addWidget(self._img_endpoint, 1)
        lay.addLayout(endpoint_row)
        
        # API key
        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("API Key:"))
        self._img_api_key = QLineEdit()
        self._img_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._img_api_key.setPlaceholderText("API key (optional)")
        self._img_api_key.setStyleSheet(self._input_style())
        api_row.addWidget(self._img_api_key, 1)
        lay.addLayout(api_row)
        
        # Default size
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Default size:"))
        self._img_size = QComboBox()
        self._img_size.addItems(["512x512", "1024x1024", "768x768"])
        self._img_size.setFixedHeight(36)
        self._img_size.setStyleSheet(self._combo_style())
        size_row.addWidget(self._img_size, 1)
        lay.addLayout(size_row)
        
        # Test button
        btn_row = QHBoxLayout()
        self._test_img_btn = QPushButton("Test Image Generation")
        self._test_img_btn.setStyleSheet(f"background: {C.PRI}; color: {C.BG};")
        self._test_img_btn.clicked.connect(self._test_image_gen)
        btn_row.addWidget(self._test_img_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        
        self._content_layout.addWidget(card)
    
    def _test_image_gen(self):
        from PyQt6.QtWidgets import QMessageBox
        endpoint = self._img_endpoint.text().strip()
        api_key = self._img_api_key.text().strip()
        if not endpoint:
            QMessageBox.warning(self, "Image Generation", "Enter a Base URL first.")
            return
        try:
            import urllib.request, json
            payload = {
                "prompt": "A simple test image",
                "width": 256,
                "height": 256,
            }
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            req = urllib.request.Request(
                endpoint.rstrip("/") + "/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    QMessageBox.information(self, "Image Generation", "Image generation endpoint is working.")
                else:
                    QMessageBox.warning(self, "Image Generation", f"Endpoint returned HTTP {resp.status}.")
        except Exception as e:
            QMessageBox.warning(self, "Image Generation", f"Could not connect: {e}")
    
    def _add_routing_section(self):
        card = self._make_card("Routing", "Default provider + fallback order: chat/agent/voice.")
        lay = card.layout()
        
        saved = {}
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            saved = settings.get("routing", {})
            if not isinstance(saved, dict):
                saved = {}
        self._routing_combos = {}
        for mode in ["Chat", "Agent", "Voice"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{mode}:"))
            combo = QComboBox()
            combo.addItems(["Auto", "Groq", "Gemini", "OpenAI", "Anthropic", "OpenRouter", "Local"])
            combo.setStyleSheet(self._combo_style())
            key = mode.lower()
            current = saved.get(key, "Auto")
            if current in [combo.itemText(i) for i in range(combo.count())]:
                combo.setCurrentText(current)
            combo.currentTextChanged.connect(
                lambda value, k=key: self._on_routing_changed(k, value)
            )
            row.addWidget(combo, 1)
            lay.addLayout(row)
            self._routing_combos[key] = combo
        
        self._content_layout.addWidget(card)
    
    def _on_routing_changed(self, mode: str, value: str):
        if not (self._controller and hasattr(self._controller, "_win")):
            return
        settings = self._controller._win._load_app_settings()
        routing = settings.get("routing", {})
        if not isinstance(routing, dict):
            routing = {}
        routing[mode] = value
        settings["routing"] = routing
        self._controller._win._save_app_settings(settings)
    
    def _make_card(self, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background: {C.SURFACE};
                border: 1px solid {C.BORDER};
                border-radius: 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Exo 2", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {C.TEXT};")
        lay.addWidget(title_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setFont(QFont("Exo 2", 10))
        desc_lbl.setStyleSheet(f"color: {C.TEXT_DIM};")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)
        
        return card
    
    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                selection-background-color: {C.PRI};
            }}
        """
    
    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
            }}
        """
    
    def _toggle_api_reveal(self, checked: bool):
        self._api_key.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
    
    def _fetch_models_clicked(self):
        provider = self._provider_combo.currentText()
        pid = self.PROVIDER_MAP.get(provider, "custom")
        base_url = self._base_url.text().strip()
        api_key = self._api_key.text().strip()
        headers = self._headers.text().strip()
        if not api_key or not headers:
            try:
                from core.cloud_config import load_provider
                saved = load_provider(pid) or {}
            except Exception:
                saved = {}
            api_key = api_key or saved.get("api_key", "")
            if not headers and saved.get("headers"):
                import json
                headers = json.dumps(saved["headers"])
        if not base_url:
            from core.cloud_config import PRESETS
            if pid in PRESETS:
                base_url = PRESETS[pid]["base_url"]
        if not base_url:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Fetch Models",
                "Enter a Base URL first (required for Custom providers).",
            )
            return
        # Fetch models in background
        from PyQt6.QtCore import QThread, pyqtSignal
        class FetchWorker(QThread):
            finished = pyqtSignal(list)
            error = pyqtSignal(str)
            def __init__(self, url, api_key, headers):
                super().__init__()
                self.url = url.rstrip("/") + "/models"
                self.api_key = api_key
                self.headers = headers
            def run(self):
                try:
                    import requests
                    h = {"Content-Type": "application/json"}
                    if self.api_key:
                        h["Authorization"] = f"Bearer {self.api_key}"
                    if self.headers:
                        import json
                        h.update(json.loads(self.headers))
                    r = requests.get(self.url, headers=h, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    models = []
                    if "data" in data:
                        for m in data["data"]:
                            if "id" in m:
                                models.append(m["id"])
                    self.finished.emit(models)
                except Exception as e:
                    self.error.emit(str(e))
        self._fetch_models.setEnabled(False)
        self._fetch_models.setText("Fetching...")
        self._worker = FetchWorker(base_url, self._api_key.text(), self._headers.text())
        self._worker.finished.connect(self._on_models_fetched)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()
    
    def _on_models_fetched(self, models):
        self._model_combo.clear()
        self._model_combo.addItems(models)
        self._fetch_models.setEnabled(True)
        self._fetch_models.setText("Fetch Models")
    
    def _on_fetch_error(self, err):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Fetch Failed", f"Could not fetch models: {err}")
        self._fetch_models.setEnabled(True)
        self._fetch_models.setText("Fetch Models")
    
    def _test_connection(self):
        provider = self._provider_combo.currentText()
        pid = self.PROVIDER_MAP.get(provider, "custom")
        api_key = self._api_key.text().strip()
        base_url = self._base_url.text().strip()
        model = self._model_combo.currentText().strip()
        headers = self._headers.text().strip()
        params = self._params.text().strip()
        # Fall back to the saved (encrypted) provider config when the key
        # field is left blank - keys are never echoed back into the form.
        if not api_key or not headers or not model:
            try:
                from core.cloud_config import load_provider
                saved = load_provider(pid) or {}
            except Exception:
                saved = {}
            api_key = api_key or saved.get("api_key", "")
            model = model or saved.get("model", "")
            if not headers and saved.get("headers"):
                import json
                headers = json.dumps(saved["headers"])
            if not params and saved.get("params"):
                import json
                params = json.dumps(saved["params"])
        if not api_key and pid not in ("ollama", "lmstudio"):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Test Connection", "API key required for cloud providers")
            return
        if not base_url:
            from core.cloud_config import PRESETS
            if pid in PRESETS:
                base_url = PRESETS[pid]["base_url"]
        if not base_url:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Test Connection", "Base URL required")
            return
        # Test in background
        from PyQt6.QtCore import QThread, pyqtSignal
        class TestWorker(QThread):
            finished = pyqtSignal(bool, str)
            def __init__(self, url, api_key, model, headers, params):
                super().__init__()
                self.url = url.rstrip("/") + "/chat/completions"
                self.api_key = api_key
                self.model = model or "test"
                self.headers = headers
                self.params = params
            def run(self):
                try:
                    import requests, json
                    h = {"Content-Type": "application/json"}
                    if self.api_key:
                        h["Authorization"] = f"Bearer {self.api_key}"
                    if self.headers:
                        h.update(json.loads(self.headers))
                    p = {"model": self.model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
                    if self.params:
                        p.update(json.loads(self.params))
                    r = requests.post(self.url, headers=h, json=p, timeout=15)
                    ok = r.status_code == 200
                    msg = "Connection successful" if ok else f"HTTP {r.status_code}: {r.text[:200]}"
                    self.finished.emit(ok, msg)
                except Exception as e:
                    self.finished.emit(False, str(e))
        self._test_conn.setEnabled(False)
        self._test_conn.setText("Testing...")
        self._test_worker = TestWorker(base_url, api_key, model, headers, params)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.start()
    
    def _on_test_finished(self, ok, msg):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Test Connection", msg)
        self._test_conn.setEnabled(True)
        self._test_conn.setText("Test Connection")
    
    def _save_provider_clicked(self):
        provider = self._provider_combo.currentText()
        api_key = self._api_key.text().strip()
        base_url = self._base_url.text().strip()
        model = self._model_combo.currentText().strip()
        headers = self._headers.text().strip()
        params = self._params.text().strip()
        pid = self.PROVIDER_MAP.get(provider, "custom")
        previous = None
        try:
            from core.cloud_config import load_provider
            previous = load_provider(pid)
        except Exception:
            previous = None
        if not api_key and pid not in ("ollama", "lmstudio") and previous:
            api_key = previous.get("api_key", "")
        if not api_key and pid not in ("ollama", "lmstudio"):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Save Provider", "API key required for cloud providers")
            return
        if not base_url:
            from core.cloud_config import PRESETS
            if pid in PRESETS:
                base_url = PRESETS[pid]["base_url"]
        import json
        try:
            headers_obj = json.loads(headers) if headers else {}
            params_obj = json.loads(params) if params else {}
        except ValueError as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Save Provider", f"Invalid JSON: {e}")
            return
        config = {
            "provider": pid,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "headers": headers_obj,
            "params": params_obj,
            "fallback": [],
        }
        from core.cloud_config import save_provider
        if save_provider(config):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Provider Saved", f"{provider} saved successfully")
            self._api_key.clear()
            self._api_key.setPlaceholderText("Saved key (hidden)")
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Failed", "Could not save provider config")
    
    def _forget_provider_clicked(self):
        provider = self._provider_combo.currentText()
        pid = self.PROVIDER_MAP.get(provider, "custom")
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Forget Provider", 
            f"Delete {provider} configuration?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from core.cloud_config import delete_provider
            if delete_provider(pid):
                QMessageBox.information(self, "Provider Forgotten", f"{provider} removed")
                self._load_provider_into_form(pid)
            else:
                QMessageBox.critical(self, "Error", "Could not delete provider")
    
    def _import_model(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            self, "Import .gguf Model", "", "GGUF Files (*.gguf)"
        )
        if not path:
            return
        try:
            import shutil
            from core.user_paths import get_user_data_dir
            models_dir = get_user_data_dir() / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            src = Path(path)
            dst = models_dir / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            self._local_status.setText(f"Imported: {dst.name}")
            if self._controller and hasattr(self._controller, "_win"):
                settings = self._controller._win._load_app_settings()
                settings["local_model_path"] = str(dst)
                settings["local_model_loaded"] = False
                self._controller._win._save_app_settings(settings)
            QMessageBox.information(
                self, "Model Imported",
                f"Copied to:\n{dst}\n\nIt will load on the next engine start.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))

    def _browse_models(self):
        from PyQt6.QtWidgets import QDialog, QMessageBox
        catalogue = [
            ("Llama 3.2 3B", "~2.0 GB", "ollama pull llama3.2"),
            ("Qwen 2.5 7B", "~4.7 GB", "ollama pull qwen2.5"),
            ("Mistral 7B", "~4.1 GB", "ollama pull mistral"),
            ("Phi-3 Mini", "~2.3 GB", "ollama pull phi3"),
            ("Gemma 2 2B", "~1.6 GB", "ollama pull gemma2:2b"),
        ]
        dlg = QDialog(self)
        dlg.setWindowTitle("Model Catalogue")
        dlg.setMinimumWidth(460)
        dlg.setStyleSheet(f"background: {C.BG}; color: {C.TEXT};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        intro = QLabel(
            "Recommended open models. Pull with Ollama, or import a .gguf above."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {C.TEXT_DIM};")
        lay.addWidget(intro)
        for name, size, command in catalogue:
            row = QHBoxLayout()
            lbl = QLabel(f"{name}  -  {size}")
            lbl.setStyleSheet(f"color: {C.TEXT};")
            row.addWidget(lbl, 1)
            copy_btn = QPushButton("Copy")
            copy_btn.setFixedWidth(70)
            copy_btn.clicked.connect(
                lambda _=False, cmd=command: QApplication.clipboard().setText(cmd)
            )
            row.addWidget(copy_btn)
            lay.addLayout(row)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    def _unload_model(self):
        from PyQt6.QtWidgets import QMessageBox
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["local_model_loaded"] = False
            self._controller._win._save_app_settings(settings)
            unload = getattr(self._controller._win, "unload_local_model", None)
            if callable(unload):
                try:
                    unload()
                except Exception:
                    pass
        self._local_status.setText("Not loaded")
        QMessageBox.information(self, "Model Unloaded", "Local model unloaded; memory freed.")


class ConnectionsPage(SettingsContentPage):
    """Connections section - PC Link, Devices, Smart Home."""
    
    def __init__(self, controller=None, parent=None):
        super().__init__("connections", "Connections", controller, parent)
        self._add_pc_link()
        self._add_devices()
        self._add_smart_home()
    
    def _add_pc_link(self):
        card = self._make_card("PC Link", "Pair with your computer for cross-device control.")
        lay = card.layout()
        
        self._pair_btn = QPushButton("Pair with PC")
        self._pair_btn.setStyleSheet(f"background: {C.PRI}; color: {C.BG};")
        self._pair_btn.clicked.connect(self._show_pairing_qr)
        lay.addWidget(self._pair_btn)
        
        self._qr_lbl = QLabel()
        self._qr_lbl.setFixedSize(200, 200)
        self._qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_lbl.setStyleSheet(f"background: {C.SURFACE_RAISED}; border-radius: 8px;")
        self._qr_lbl.hide()
        lay.addWidget(self._qr_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self._pair_hint = QLabel("")
        self._pair_hint.setWordWrap(True)
        self._pair_hint.setStyleSheet(f"color: {C.TEXT_DIM};")
        self._pair_hint.hide()
        lay.addWidget(self._pair_hint)
        
        self._content_layout.addWidget(card)
    
    def _show_pairing_qr(self):
        from PyQt6.QtWidgets import QMessageBox
        service = getattr(self._controller, "_stella_connect", None) if self._controller else None
        if service is None:
            QMessageBox.information(self, "PC Link", "Stella Connect service is not running.")
            return
        try:
            payload = service.pairing_qr_payload(device_name="Desktop", platform="windows")
            from stella_connect.pairing_flow import encode_qr_png
            png = encode_qr_png(payload, box_size=5, border=2)
            if not png:
                self._pair_hint.setText(
                    "Install qrcode[pil] to display the pairing code, or pair "
                    "with the code shown on your phone."
                )
                self._pair_hint.show()
                return
            pix = QPixmap()
            pix.loadFromData(png, "PNG")
            self._qr_lbl.setPixmap(pix.scaled(
                200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self._qr_lbl.show()
            self._pair_hint.setText("Scan this code in Stella Connect on your phone.")
            self._pair_hint.show()
        except Exception as e:
            QMessageBox.warning(self, "PC Link", f"Could not create pairing code: {e}")
    
    def _add_devices(self):
        card = self._make_card("Devices", "Stella Connect nodes.")
        lay = card.layout()
        
        self._scan_btn = QPushButton("Scan for Devices")
        self._scan_btn.clicked.connect(self._scan_devices)
        lay.addWidget(self._scan_btn)
        
        self._devices_list = QListWidget()
        self._devices_list.setStyleSheet(f"""
            QListWidget {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        lay.addWidget(self._devices_list)
        
        self._content_layout.addWidget(card)
    
    def _add_smart_home(self):
        card = self._make_card("Smart Home", "Home Assistant, Matter, Zigbee devices.")
        lay = card.layout()
        
        self._ha_url = QLineEdit()
        self._ha_url.setPlaceholderText("http://homeassistant.local:8123")
        self._ha_url.setStyleSheet(self._input_style())
        lay.addWidget(self._ha_url)
        
        self._ha_token = QLineEdit()
        self._ha_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._ha_token.setPlaceholderText("Long-lived access token")
        self._ha_token.setStyleSheet(self._input_style())
        lay.addWidget(self._ha_token)
        
        self._ha_status = QLabel("Not connected")
        self._ha_status.setStyleSheet(f"color: {C.TEXT_DIM};")
        lay.addWidget(self._ha_status)
        
        self._connect_ha = QPushButton("Connect")
        self._connect_ha.setStyleSheet(f"background: {C.PRI}; color: {C.BG};")
        self._connect_ha.clicked.connect(self._save_smart_home)
        lay.addWidget(self._connect_ha)
        
        self._load_smart_home()
        
        self._content_layout.addWidget(card)
    
    def _load_smart_home(self):
        try:
            from core.cloud_config import load_provider
            cfg = load_provider("home_assistant")
        except Exception:
            cfg = None
        if cfg:
            self._ha_url.setText(cfg.get("base_url", ""))
            if cfg.get("api_key"):
                self._ha_token.setPlaceholderText("Saved token (hidden)")
            self._ha_status.setText("Connected - token stored securely")
    
    def _save_smart_home(self):
        from PyQt6.QtWidgets import QMessageBox
        url = self._ha_url.text().strip()
        token = self._ha_token.text().strip()
        if not url:
            QMessageBox.warning(self, "Smart Home", "Enter a Home Assistant URL.")
            return
        try:
            from core.cloud_config import load_provider, save_provider
            existing = load_provider("home_assistant") or {}
            if not token:
                token = existing.get("api_key", "")
            if not token:
                QMessageBox.warning(self, "Smart Home", "Enter an access token.")
                return
            ok = save_provider({
                "provider": "home_assistant",
                "api_key": token,
                "base_url": url,
                "model": "",
                "headers": {},
                "params": {},
            })
            if ok:
                self._ha_token.clear()
                self._ha_token.setPlaceholderText("Saved token (hidden)")
                self._ha_status.setText("Connected - token stored securely")
                QMessageBox.information(self, "Smart Home", "Home Assistant saved.")
            else:
                QMessageBox.critical(self, "Smart Home", "Could not save settings.")
        except Exception as e:
            QMessageBox.critical(self, "Smart Home", str(e))
    
    def _scan_devices(self):
        from PyQt6.QtWidgets import QMessageBox
        service = getattr(self._controller, "_stella_connect", None) if self._controller else None
        if service is None:
            QMessageBox.information(self, "Scan", "Stella Connect service is not available")
            return
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning...")
        self._devices_list.clear()
        
        class _ScanThread(QThread):
            done = pyqtSignal(object, object)
            
            def run(self):
                try:
                    hosts = service.discover_hosts(timeout=3.0)
                    devices = service.list_devices()
                    self.done.emit(hosts, devices)
                except Exception as e:
                    self.done.emit([], e)
        
        self._scan_thread = _ScanThread(self)
        self._scan_thread.done.connect(self._on_scan_finished)
        self._scan_thread.start()
    
    def _on_scan_finished(self, hosts, devices):
        self._devices_list.clear()
        if isinstance(devices, Exception):
            self._devices_list.addItem(f"Scan failed: {devices}")
        else:
            for d in hosts or []:
                name = d.get("name") or d.get("host") or "Unknown"
                addr = d.get("address") or d.get("host") or ""
                self._devices_list.addItem(f"{name} - {addr} (discovered)")
            for d in devices or []:
                self._devices_list.addItem(
                    f"{d.get('name', 'Device')} - {d.get('address', d.get('host', ''))}"
                )
            if self._devices_list.count() == 0:
                self._devices_list.addItem("No devices found.")
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan for Devices")


class MemoryDataPage(SettingsContentPage):
    """Memory & Data section - Memory Vault, Inspector, Backup, Audit."""
    
    def __init__(self, controller=None, parent=None):
        super().__init__("memory_data", "Memory & Data", controller, parent)
        self._add_vault()
        self._add_inspector()
        self._add_backup()
        self._add_audit()
    
    def _add_vault(self):
        card = self._make_card("Memory Vault", "Choose where Stella stores notes and long-term memories.")
        lay = card.layout()
        
        self._vault_enabled = QCheckBox("Enable Memory Vault")
        self._vault_enabled.setStyleSheet(f"color: {C.TEXT};")
        self._vault_enabled.stateChanged.connect(self._on_vault_toggled)
        lay.addWidget(self._vault_enabled)
        
        vault_row = QHBoxLayout()
        vault_row.addWidget(QLabel("Vault Folder:"))
        self._vault_path = QLabel("Not set")
        self._vault_path.setStyleSheet(f"color: {C.TEXT_MED}; font-family: Consolas; font-size: 10px;")
        vault_row.addWidget(self._vault_path, 1)
        self._vault_browse = QPushButton("Browse...")
        self._vault_browse.setFixedWidth(100)
        self._vault_browse.clicked.connect(self._browse_vault)
        vault_row.addWidget(self._vault_browse)
        lay.addLayout(vault_row)
        
        self._content_layout.addWidget(card)
    
    def _add_inspector(self):
        card = self._make_card("What Stella Remembers", "Inspect and manage stored memories.")
        lay = card.layout()
        
        self._inspect_btn = QPushButton("Open Memory Inspector")
        self._inspect_btn.setStyleSheet(f"background: {C.PRI}; color: {C.BG};")
        lay.addWidget(self._inspect_btn)
        
        self._content_layout.addWidget(card)
    
    def _add_backup(self):
        card = self._make_card("Backup & Restore", "Export/import all data.")
        lay = card.layout()
        
        export_btn = QPushButton("Export All Data")
        export_btn.clicked.connect(self._export_data)
        import_btn = QPushButton("Import Data")
        import_btn.clicked.connect(self._import_data)
        
        btn_row = QHBoxLayout()
        btn_row.addWidget(export_btn)
        btn_row.addWidget(import_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        
        self._content_layout.addWidget(card)
    
    def _add_audit(self):
        card = self._make_card("Audit Log", "View append-only action log.")
        lay = card.layout()
        
        self._audit_btn = QPushButton("Open Audit Log")
        self._audit_btn.clicked.connect(self._open_audit)
        lay.addWidget(self._audit_btn)
        
        self._content_layout.addWidget(card)
    
    def _on_vault_toggled(self, state):
        enabled = bool(state)
        self._vault_path.setEnabled(enabled)
        self._vault_browse.setEnabled(enabled)
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["vault_enabled"] = enabled
            self._controller._win._save_app_settings(settings)
    
    def _browse_vault(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Memory Vault Folder")
        if folder:
            self._vault_path.setText(folder)
            # Save to settings
            if self._controller and hasattr(self._controller, "_win"):
                settings = self._controller._win._load_app_settings()
                settings["vault_path"] = folder
                settings["vault_enabled"] = True
                self._controller._win._save_app_settings(settings)
    
    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(
            self, "Export All Data", "stella_backup.zip", "Zip Archives (*.zip)"
        )
        if not path:
            return
        try:
            import zipfile
            from core.user_paths import get_user_data_dir
            config_dir = get_user_data_dir() / "config"
            files = [
                config_dir / "workspace_store.sqlite3",
                config_dir / "app_settings.json",
                config_dir / "cloud_providers.json",
                config_dir / "discord_bot.json",
            ]
            written = 0
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    if f.exists():
                        zf.write(f, f"config/{f.name}")
                        written += 1
            if written == 0:
                QMessageBox.warning(
                    self, "Nothing to Export", "No Stella data files were found."
                )
            else:
                QMessageBox.information(
                    self, "Export Complete",
                    f"Backed up {written} file(s) to:\n{path}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def _import_data(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Data", "", "Zip Archives (*.zip)"
        )
        if not path:
            return
        reply = QMessageBox.question(
            self, "Restore Backup",
            "Restoring overwrites current settings and workspace data.\n"
            "A safety copy of the current data is kept. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            import shutil, tempfile, time, zipfile
            from core.user_paths import get_user_data_dir
            data_dir = get_user_data_dir()
            config_dir = data_dir / "config"
            staging = Path(tempfile.mkdtemp(prefix="stella_restore_"))
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    names = [
                        n for n in zf.namelist()
                        if n.startswith("config/") and not n.endswith("/")
                    ]
                    if not names:
                        QMessageBox.warning(
                            self, "Import Failed",
                            "Not a Stella backup (no config/ entries found).",
                        )
                        return
                    zf.extractall(staging)
                config_dir.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                backup_dir = data_dir / f"restore-backup-{stamp}"
                if config_dir.exists():
                    shutil.copytree(config_dir, backup_dir)
                restored = 0
                for name in names:
                    src = staging / name
                    if src.exists():
                        shutil.copy2(src, config_dir / Path(name).name)
                        restored += 1
                QMessageBox.information(
                    self, "Restore Complete",
                    f"Restored {restored} file(s).\n"
                    f"Previous data kept at:\n{backup_dir}\n\nRestart Stella to apply.",
                )
            finally:
                shutil.rmtree(staging, ignore_errors=True)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))
    
    def _open_audit(self):
        from PyQt6.QtWidgets import QMessageBox
        from core.user_paths import get_user_data_dir
        audit_path = get_user_data_dir() / "audit.log"
        if audit_path.exists():
            QMessageBox.information(self, "Audit Log", f"Audit log at:\n{audit_path}")
        else:
            QMessageBox.information(self, "Audit Log", "No audit log found yet.")


class PermissionsPage(SettingsContentPage):
    """Permissions & Automation section."""
    
    def __init__(self, controller=None, parent=None):
        super().__init__("permissions", "Permissions & Automation", controller, parent)
        self._add_permissions()
        self._add_automation()
        self._add_voice_hud()
    
    def _add_permissions(self):
        card = self._make_card("Agent Capabilities", "Allow Stella to act on this device and connected devices.")
        lay = card.layout()
        
        perms = ["Files", "Shell", "Screen", "GUI", "Browser", "Location", "Microphone", "Camera"]
        saved = {}
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            saved = settings.get("agent_permissions", {})
            if not isinstance(saved, dict):
                saved = {}
        self._perm_toggles = {}
        for perm in perms:
            row = QHBoxLayout()
            row.addWidget(QLabel(perm))
            toggle = QCheckBox()
            toggle.setChecked(bool(saved.get(perm, True)))
            toggle.setStyleSheet(f"""
                QCheckBox::indicator {{
                    width: 20px; height: 20px;
                    border: 2px solid {C.BORDER};
                    border-radius: 4px;
                    background: {C.SURFACE_RAISED};
                }}
                QCheckBox::indicator:checked {{
                    background: {C.PRI};
                    border-color: {C.PRI};
                }}
            """)
            toggle.stateChanged.connect(
                lambda _state, key=perm: self._on_permission_changed(key)
            )
            row.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignRight)
            row.addStretch(1)
            lay.addLayout(row)
            self._perm_toggles[perm] = toggle
        
        self._content_layout.addWidget(card)
    
    def _on_permission_changed(self, perm: str):
        if not (self._controller and hasattr(self._controller, "_win")):
            return
        toggle = self._perm_toggles.get(perm)
        if toggle is None:
            return
        settings = self._controller._win._load_app_settings()
        perms = settings.get("agent_permissions", {})
        if not isinstance(perms, dict):
            perms = {}
        perms[perm] = toggle.isChecked()
        settings["agent_permissions"] = perms
        self._controller._win._save_app_settings(settings)
    
    def _add_automation(self):
        card = self._make_card("Automations", "Scheduled and event-driven tasks (populated by Phase 5).")
        lay = card.layout()
        
        self._automation_list = QListWidget()
        self._automation_list.setStyleSheet(f"""
            QListWidget {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
            }}
        """)
        lay.addWidget(self._automation_list)
        
        add_row = QHBoxLayout()
        self._new_automation = QPushButton("New Automation")
        self._new_automation.setStyleSheet(f"background: {C.PRI}; color: {C.BG};")
        self._new_automation.clicked.connect(self._new_automation_clicked)
        add_row.addWidget(self._new_automation)
        add_row.addStretch(1)
        lay.addLayout(add_row)
        
        self._automation_list.itemDoubleClicked.connect(self._remove_automation)
        self._refresh_automations()
        
        self._content_layout.addWidget(card)
    
    def _load_automations(self) -> list:
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            items = settings.get("automations", [])
            if isinstance(items, list):
                return items
        return []
    
    def _save_automations(self, items: list):
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["automations"] = items
            self._controller._win._save_app_settings(settings)
    
    def _refresh_automations(self):
        if not hasattr(self, "_automation_list"):
            return
        self._automation_list.clear()
        items = self._load_automations()
        if not items:
            self._automation_list.addItem("No automations yet. Click New Automation.")
            return
        for item in items:
            name = item.get("name", "Untitled")
            when = item.get("when", "")
            act = item.get("action", "")
            self._automation_list.addItem(f"{name}  -  {when}  ->  {act}")
    
    def _new_automation_clicked(self):
        from PyQt6.QtWidgets import QDialog
        dlg = QDialog(self)
        dlg.setWindowTitle("New Automation")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet(f"background: {C.BG}; color: {C.TEXT};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)
        
        name = QLineEdit()
        name.setPlaceholderText("Name (e.g. Morning briefing)")
        name.setStyleSheet(self._input_style())
        when = QLineEdit()
        when.setPlaceholderText("When (e.g. daily at 09:00)")
        when.setStyleSheet(self._input_style())
        action = QLineEdit()
        action.setPlaceholderText("Action (e.g. summarize today's calendar)")
        action.setStyleSheet(self._input_style())
        for label, widget in (
            ("Name:", name), ("When:", when), ("Action:", action)
        ):
            lay.addWidget(QLabel(label))
            lay.addWidget(widget)
        
        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dlg.reject)
        save = QPushButton("Save")
        save.setStyleSheet(f"background: {C.PRI}; color: {C.BG};")
        save.clicked.connect(dlg.accept)
        btn_row.addStretch(1)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)
        
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not name.text().strip():
            return
        items = self._load_automations()
        items.append({
            "name": name.text().strip(),
            "when": when.text().strip() or "manual",
            "action": action.text().strip(),
        })
        self._save_automations(items)
        self._refresh_automations()
    
    def _remove_automation(self, item):
        from PyQt6.QtWidgets import QMessageBox
        items = self._load_automations()
        if not items:
            return
        idx = self._automation_list.row(item)
        if idx < 0 or idx >= len(items):
            return
        name = items[idx].get("name", "this automation")
        reply = QMessageBox.question(
            self, "Delete Automation", f"Delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        items.pop(idx)
        self._save_automations(items)
        self._refresh_automations()
    
    def _add_voice_hud(self):
        card = self._make_card("Voice & HUD", "Wake word, HUD overlay settings.")
        lay = card.layout()
        
        wake_row = QHBoxLayout()
        wake_row.addWidget(QLabel("Wake Word:"))
        self._wake_word = QLineEdit("hey stella")
        self._wake_word.setStyleSheet(self._input_style())
        wake_row.addWidget(self._wake_word, 1)
        lay.addLayout(wake_row)
        
        self._hud_enabled = QCheckBox("Enable HUD Overlay")
        self._hud_enabled.setStyleSheet(f"color: {C.TEXT};")
        lay.addWidget(self._hud_enabled)
        
        self._wake_word.textChanged.connect(self._on_wake_word_changed)
        self._hud_enabled.stateChanged.connect(self._on_hud_toggled)
        
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            self._wake_word.blockSignals(True)
            self._hud_enabled.blockSignals(True)
            self._wake_word.setText(settings.get("wake_word", "hey stella"))
            self._hud_enabled.setChecked(bool(settings.get("hud_enabled", False)))
            self._wake_word.blockSignals(False)
            self._hud_enabled.blockSignals(False)
        
        self._content_layout.addWidget(card)
    
    def _on_wake_word_changed(self, text: str):
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["wake_word"] = text
            self._controller._win._save_app_settings(settings)
    
    def _on_hud_toggled(self, state):
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["hud_enabled"] = bool(state)
            self._controller._win._save_app_settings(settings)
    
    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
            }}
        """


class AppearancePage(SettingsContentPage):
    """Appearance section - Theme picker with live preview + Text Size."""
    
    def __init__(self, controller=None, parent=None):
        super().__init__("appearance", "Appearance", controller, parent)
        from core.theme_tokens import theme_manager
        
        # Theme picker
        theme_card = self._make_card("Theme", "Select a complete theme for Stella.")
        lay = theme_card.layout()
        
        self._theme_combo = QComboBox()
        self._theme_combo.setFixedHeight(36)
        self._theme_combo.setStyleSheet(self._combo_style())
        
        for tid in theme_manager.list_themes():
            name = theme_manager.get_name(tid)
            desc = theme_manager.get_description(tid)
            preview = theme_manager.get_preview(tid)
            self._theme_combo.addItem(f"{name}  —  {desc}", tid)
            idx = self._theme_combo.count() - 1
            if preview:
                self._theme_combo.setItemData(idx, preview[0], Qt.ItemDataRole.UserRole)
        
        # Load saved theme
        try:
            if APP_SETTINGS_FILE.exists():
                with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    _d = json.load(f)
                    saved = _d.get("app_theme", "void")
                    self._theme_combo.setCurrentIndex(
                        theme_manager.list_themes().index(saved) if saved in theme_manager.list_themes() else 0
                    )
        except:
            pass
        
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        theme_row.addWidget(self._theme_combo, 1)
        lay.addLayout(theme_row)
        
        # Preview swatch
        self._preview_frame = QFrame()
        self._preview_frame.setFixedHeight(40)
        self._preview_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {theme_manager.get_preview('void')[0]}, 
                    stop:1 {theme_manager.get_preview('void')[1]});
                border-radius: 8px;
                border: 1px solid {C.BORDER};
            }}
        """)
        lay.addWidget(self._preview_frame)
        
        self._content_layout.addWidget(theme_card)
        
        # Text Size
        size_card = self._make_card("Text Size", "Adjust UI text scaling.")
        size_lay = size_card.layout()
        
        self._size_combo = QComboBox()
        self._size_combo.addItems(["Normal", "Large"])
        self._size_combo.setFixedHeight(36)
        self._size_combo.setStyleSheet(self._combo_style())
        
        try:
            if APP_SETTINGS_FILE.exists():
                with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    _d = json.load(f)
                    self._size_combo.setCurrentText(_d.get("text_size", "Normal"))
        except:
            pass
        
        self._size_combo.currentTextChanged.connect(self._on_size_changed)
        
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Text Size:"))
        size_row.addWidget(self._size_combo, 1)
        size_lay.addLayout(size_row)
        
        self._content_layout.addWidget(size_card)
    
    def _on_theme_changed(self, index: int):
        from core.theme_tokens import theme_manager
        theme_id = self._theme_combo.itemData(index)
        if not theme_id:
            return
        
        # Update preview
        preview = theme_manager.get_preview(theme_id)
        if preview:
            self._preview_frame.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 {preview[0]}, stop:1 {preview[1]});
                    border-radius: 8px;
                    border: 1px solid {C.BORDER};
                }}
            """)
        
        # Apply theme
        C.set_theme(theme_id)
        if self._controller and hasattr(self._controller, "_win"):
            self._controller._win._apply_theme()
            self._controller._win._set_setting("app_theme", theme_id)
    
    def _on_size_changed(self, text: str):
        if self._controller and hasattr(self._controller, "_win"):
            self._controller._win._apply_text_size(text)
            self._controller._win._set_setting("text_size", text)
    
    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                selection-background-color: {C.PRI};
            }}
        """
    
    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
            }}
        """
    
    def _make_card(self, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background: {C.SURFACE};
                border: 1px solid {C.BORDER};
                border-radius: 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Exo 2", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {C.TEXT};")
        lay.addWidget(title_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setFont(QFont("Exo 2", 10))
        desc_lbl.setStyleSheet(f"color: {C.TEXT_DIM};")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)
        
        return card


class SystemPage(SettingsContentPage):
    """System section - Build, About, Feedback, Unload model."""
    
    def __init__(self, controller=None, parent=None):
        super().__init__("system", "System", controller, parent)
        self._add_build_info()
        self._add_feedback()
        self._add_model_management()
    
    def _add_build_info(self):
        card = self._make_card("Build Information", "Version, platform, and build details.")
        lay = card.layout()
        
        info = [
            ("Version", "1.0.0"),
            ("Platform", platform.system()),
            ("Python", platform.python_version()),
            ("PyQt", "6.x"),
        ]
        for key, val in info:
            row = QHBoxLayout()
            row.addWidget(QLabel(key))
            row.addWidget(QLabel(val), alignment=Qt.AlignmentFlag.AlignRight)
            row.addStretch(1)
            lay.addLayout(row)
        
        self._content_layout.addWidget(card)
    
    def _add_feedback(self):
        card = self._make_card("Feedback & Updates", "Update channel, crash reports, feedback.")
        lay = card.layout()
        
        # Channel
        channel_row = QHBoxLayout()
        channel_row.addWidget(QLabel("Channel:"))
        self._channel = QComboBox()
        self._channel.addItems(["Stable", "Beta", "Nightly"])
        self._channel.setStyleSheet(self._combo_style())
        channel_row.addWidget(self._channel, 1)
        lay.addLayout(channel_row)
        
        # Check updates
        self._check_updates = QCheckBox("Check for updates on startup")
        self._check_updates.setStyleSheet(f"color: {C.TEXT};")
        lay.addWidget(self._check_updates)
        
        self._content_layout.addWidget(card)
        
        # Load saved settings
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            self._channel.setCurrentText(settings.get("feedback_channel", "Stable"))
            self._check_updates.setChecked(settings.get("check_updates_on_startup", True))
        
        self._channel.currentTextChanged.connect(self._on_channel_changed)
        self._check_updates.stateChanged.connect(self._on_check_updates_changed)
     
    def _add_model_management(self):
        card = self._make_card("Model Management", "Unload models to free memory.")
        lay = card.layout()
        
        self._unload_all = QPushButton("Unload All Models")
        self._unload_all.setStyleSheet(f"background: rgba(255,85,85,0.15); color: {C.RED};")
        lay.addWidget(self._unload_all)
        
        self._content_layout.addWidget(card)
        
        self._unload_all.clicked.connect(self._unload_all_models)
     
    def _on_channel_changed(self, text: str):
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["feedback_channel"] = text
            self._controller._win._save_app_settings(settings)
    
    def _on_check_updates_changed(self, state):
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["check_updates_on_startup"] = self._check_updates.isChecked()
            self._controller._win._save_app_settings(settings)
    
    def _unload_all_models(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Unload All Models", 
            "Unload all loaded models to free memory?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            settings["local_model_loaded"] = False
            self._controller._win._save_app_settings(settings)
            for hook in ("unload_local_model", "_unload_all_models"):
                fn = getattr(self._controller._win, hook, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception:
                        pass
                    break
        QMessageBox.information(self, "Models Unloaded", "All models have been unloaded")
     
    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {C.SURFACE_RAISED};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                selection-background-color: {C.PRI};
            }}
        """
    
    def _make_card(self, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet(f"""
            QFrame#SettingsCard {{
                background: {C.SURFACE};
                border: 1px solid {C.BORDER};
                border-radius: 16px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Exo 2", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {C.TEXT};")
        lay.addWidget(title_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setFont(QFont("Exo 2", 10))
        desc_lbl.setStyleSheet(f"color: {C.TEXT_DIM};")
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)
        
        return card


class SettingsWidget(QWidget):
    """Main settings widget with sidebar + content area (6-section IA)."""
    
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self.setStyleSheet("background: transparent;")
        
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # Sidebar
        self._sidebar = SettingsSidebar()
        root.addWidget(self._sidebar)
        
        # Content stack
        self._content_stack = QStackedWidget()
        self._content_stack.setStyleSheet("background: transparent;")
        
        # Create all section pages
        self._pages = {
            "ai_models": AIModelsPage(controller),
            "connections": ConnectionsPage(controller),
            "memory_data": MemoryDataPage(controller),
            "permissions": PermissionsPage(controller),
            "appearance": AppearancePage(controller),
            "system": SystemPage(controller),
        }
        
        for page in self._pages.values():
            self._content_stack.addWidget(page)
        
        root.addWidget(self._content_stack, 1)
        
        # Connect sidebar
        self._sidebar.section_changed.connect(self._on_section_changed)
        
        # Load saved section
        self._load_saved_section()
    
    def _on_section_changed(self, section_id: str):
        page = self._pages.get(section_id)
        if page:
            self._content_stack.setCurrentWidget(page)
            # Save preference
            if self._controller and hasattr(self._controller, "_win"):
                self._controller._win._set_setting("settings_section", section_id)
    
    def _load_saved_section(self):
        if self._controller and hasattr(self._controller, "_win"):
            settings = self._controller._win._load_app_settings()
            section = settings.get("settings_section", "ai_models")
            if section in self._pages:
                self._sidebar._on_section_clicked(section)
                self._content_stack.setCurrentWidget(self._pages[section])