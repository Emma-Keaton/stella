from __future__ import annotations

from ._imports import *
from .common import *
from .chat import TaskCard, ConversationFeed

from workspace_store import store as workspace_store

class WorkspaceSidebar(QWidget):
    """AnythingLLM-style workspace sidebar: workspaces with nested threads, search, actions."""
    
    command_submitted = pyqtSignal(str)
    close_requested = pyqtSignal()
    attach_requested = pyqtSignal()
    mic_requested = pyqtSignal()
    new_conversation_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._collapsed = True
        self._expanded_w = 468
        self._target_h = 860
        self._active_conversation_id: str | None = None
        self._store = workspace_store()
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._panel = QFrame(self)
        self._panel.setObjectName("WorkspaceSidebarPanel")
        self._panel.setStyleSheet(
            f"""
            QFrame#WorkspaceSidebarPanel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(16, 18, 24, 230),
                stop:0.55 rgba(10, 12, 18, 210),
                stop:1 rgba(5, 7, 11, 200));
                border: 1px solid {C.BORDER};
                border-radius: 22px;
            }}
            """
        )
        try:
            shadow = QGraphicsDropShadowEffect(self._panel)
            shadow.setBlurRadius(35)
            shadow.setColor(QColor(0, 0, 0, 72))
            shadow.setOffset(0, 12)
            self._panel.setGraphicsEffect(shadow)
        except Exception:
            pass
        root = QHBoxLayout(self._panel)
        root.setContentsMargins(14, 14, 12, 14)
        root.setSpacing(10)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        content = QVBoxLayout(self._content)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(10)

        # Header with title + new workspace
        header = QHBoxLayout()
        header.setSpacing(10)
        self._title = QLabel("Workspaces")
        self._title.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {C.TEXT}; background: transparent; letter-spacing: 0.5px;")
        header.addWidget(self._title)
        header.addStretch()
        self._new_workspace_btn = QPushButton("+")
        self._new_workspace_btn.setToolTip("New Workspace")
        self._new_workspace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_workspace_btn.setFixedSize(28, 28)
        self._new_workspace_btn.setFont(QFont("Exo 2", 16, QFont.Weight.Bold))
        self._new_workspace_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {C.PRI};
                color: {C.TEXT};
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background: {C.PRI};
                color: {C.BG};
            }}
            """
        )
        self._new_workspace_btn.clicked.connect(self._create_workspace)
        header.addWidget(self._new_workspace_btn)
        
        self._close_btn = QPushButton("✕")
        self._close_btn.setToolTip("Close Workspace")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        self._close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: C.TEXT;
                color: C.TEXT;
                border: 1px solid C.TEXT;
                border-radius: 14px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(255, 82, 82, 0.25);
                color: {C.RED};
                border: 1px solid rgba(255, 82, 82, 0.50);
            }}
            """
        )
        self._close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(self._close_btn)
        content.addLayout(header)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search workspaces & threads...")
        self._search.setFont(QFont("Exo 2", 10))
        self._search.setFixedHeight(38)
        self._search.setStyleSheet(
            f"""
            QLineEdit {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 12px;
                padding: 0 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
            }}
            """
        )
        self._search.textChanged.connect(self._refresh_tree)
        content.addWidget(self._search)

        # Tree view for workspaces + threads
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setFrameShape(QFrame.Shape.NoFrame)
        self._tree.setIndentation(18)
        self._tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background: transparent;
                border: none;
                color: {C.TEXT};
                font-size: 12px;
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
                border-radius: 8px;
            }}
            QTreeWidget::item:selected {{
                background: {C.PRI};
                color: {C.BG};
            }}
            QTreeWidget::item:hover {{
                background: {C.PRI_GHO};
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:has-children:has-siblings:closed {{
                image: none;
                border-image: none;
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
            """
        )
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        content.addWidget(self._tree, 1)

        self._feed = ConversationFeed(self)
        content.addWidget(self._feed)

        self._memory_items = None
        self._memory_frame = None

        root.addWidget(self._content, stretch=1)

        self._panel.hide()
        self.hide()
        self._ensure_active_conversation()
        self._load_active_conversation()
        self._refresh_tree()
        self._apply_state()

        # Wire voice state signals to UI
        from core.voice_gate import voice_signals
        voice_signals().voice_activated_changed.connect(self._on_voice_activated_changed)
        voice_signals().mic_allowed_changed.connect(self._on_mic_allowed_changed)
        voice_signals().audio_level.connect(self._on_audio_level)

    def _on_voice_activated_changed(self, active: bool):
        """Voice activated state changed - update hologram and voice indicator."""
        self._voice_lbl.setVisible(active)
        self._voice_lbl.setStyleSheet(
            f"QLabel {{ background: {C.PRI if active else C.TEXT_DIM}; "
            f"color: {C.BG if active else C.TEXT_DIM}; border-radius: 5px; }}"
        )
        # Hologram state: listening when voice active, idle otherwise
        if hasattr(self, '_feed') and self._feed is not None:
            self._feed.set_holo_state("listening" if active else "idle")

    def _on_mic_allowed_changed(self, allowed: bool):
        """Mic allowed state changed - update mic button appearance."""
        if hasattr(self, '_mic_btn'):
            color = C.PRI if allowed else C.TEXT_DIM
            self._mic_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color}; border: none; font-size: 16px; }}"
                f"QPushButton:hover {{ color: {C.PRI}; }}"
            )

    def _on_audio_level(self, level: float):
        """Audio level changed - update hologram waveform."""
        if hasattr(self, '_feed') and self._feed is not None:
            self._feed.set_audio_level(level)

    # -------------------------------------------------------------------------
    # Workspace/Thread tree
    # -------------------------------------------------------------------------
    def _refresh_tree(self, *_):
        search = self._search.text().strip()
        self._tree.clear()
        
        if search:
            results = self._store.search_all(search)
            if not results:
                item = QTreeWidgetItem(self._tree)
                item.setText(0, "No matches")
                item.setForeground(0, QColor(C.TEXT_DIM))
                self._tree.addTopLevelItem(item)
                return
            for r in results:
                item = QTreeWidgetItem(self._tree)
                item.setText(0, f"  {r['title']}")
                item.setData(0, Qt.ItemDataRole.UserRole, {"type": "thread", "id": r["id"], "workspace_id": r["workspaceId"]})
                item.setForeground(0, QColor(C.TEXT))
                item.setToolTip(0, f"Workspace: {r['workspaceName']}")
                self._tree.addTopLevelItem(item)
            return
        
        workspaces = self._store.list_workspaces()
        if not workspaces:
            empty = QTreeWidgetItem(self._tree)
            empty.setText(0, "S  T  E  L  L  A")
            empty.setFont(0, QFont("Exo 2", 16, QFont.Weight.Bold))
            empty.setForeground(0, QColor(C.TEXT))
            empty.setTextAlignment(0, Qt.AlignmentFlag.AlignCenter)
            self._tree.addTopLevelItem(empty)
            hint = QTreeWidgetItem(self._tree)
            hint.setText(0, "  Create a workspace to begin")
            hint.setForeground(0, QColor(C.TEXT_MED))
            self._tree.addTopLevelItem(hint)
            return
        
        active_ws = self._store.get_active_workspace_id() or "personal"
        
        for ws in workspaces:
            ws_item = QTreeWidgetItem(self._tree)
            ws_item.setText(0, f"  {ws['name']}")
            ws_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "workspace", "id": ws["id"]})
            ws_item.setForeground(0, QColor(C.TEXT))
            ws_item.setFont(0, QFont("Exo 2", 11, QFont.Weight.Bold))
            ws_item.setExpanded(True)
            if ws["id"] == active_ws:
                ws_item.setText(0, f"  {ws['name']}  ●")
                ws_item.setForeground(0, QColor(C.PRI))
            
            threads = self._store.list_threads(ws["id"])
            for item in threads:
                thread_item = QTreeWidgetItem(ws_item)
                thread_item.setText(0, f"  {item['title']}")
                thread_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "thread", "id": item["id"], "workspace_id": ws["id"]})
                thread_item.setForeground(0, QColor(C.TEXT_MED))
                if item["pinned"]:
                    thread_item.setText(0, f"  📌 {item['title']}")
                if item["id"] == self._active_conversation_id:
                    thread_item.setForeground(0, QColor(C.PRI))
                    font = thread_item.font(0)
                    font.setBold(True)
                    thread_item.setFont(0, font)
            
            self._tree.addTopLevelItem(ws_item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data["type"] == "thread":
            self._load_conversation(data["id"])
        elif data["type"] == "workspace":
            ws_id = data["id"]
            self._store.set_active_workspace_id(ws_id)
            self._refresh_tree()
            # Create new conversation in this workspace
            self._active_conversation_id = self._store.create_conversation("New Conversation", workspace_id=ws_id)
            self._feed.clear_messages()
            self._hide_memory_banner()

    def _show_context_menu(self, pos: QPoint):
        item = self._tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(
            f"""
            QMenu {{
                background: {C.SURFACE};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background: {C.PRI};
                color: {C.BG};
            }}
            """
        )
        
        if data["type"] == "workspace":
            ws_id = data["id"]
            if ws_id != "personal":
                rename_action = menu.addAction("Rename")
                rename_action.triggered.connect(lambda: self._rename_workspace(ws_id))
                delete_action = menu.addAction("Delete")
                delete_action.triggered.connect(lambda: self._delete_workspace(ws_id))
            else:
                rename_action = menu.addAction("Rename")
                rename_action.triggered.connect(lambda: self._rename_workspace(ws_id))
        elif data["type"] == "thread":
            thread_id = data["id"]
            ws_id = data["workspace_id"]
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._rename_thread(thread_id))
            move_action = menu.addAction("Move to Workspace")
            move_action.triggered.connect(lambda: self._move_thread(thread_id))
            pin_action = menu.addAction("Unpin" if self._is_pinned(thread_id) else "Pin")
            pin_action.triggered.connect(lambda: self._toggle_pin(thread_id))
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_thread(thread_id))
        
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _is_pinned(self, thread_id: str) -> bool:
        with self._store._lock, self._store._connect() as conn:
            row = conn.execute("SELECT pinned FROM conversations WHERE id = ?", (thread_id,)).fetchone()
            return bool(row["pinned"]) if row else False

    def _rename_workspace(self, ws_id: str):
        workspaces = self._store.list_workspaces()
        current = next((w["name"] for w in workspaces if w["id"] == ws_id), "Workspace")
        title, ok = QInputDialog.getText(self, "Rename Workspace", "Workspace name:", text=current)
        if ok and title.strip():
            self._store.rename_workspace(ws_id, title.strip())
            self._refresh_tree()

    def _delete_workspace(self, ws_id: str):
        if ws_id == "personal":
            return
        reply = QMessageBox.question(self, "Delete Workspace", 
            "Delete this workspace? All threads will move to Personal.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._store.delete_workspace(ws_id)
            self._refresh_tree()

    def _rename_thread(self, thread_id: str):
        convo = self._store.get_conversation(thread_id)
        current = (convo or {}).get("title") or "Conversation"
        title, ok = QInputDialog.getText(self, "Rename Thread", "Thread title:", text=current)
        if ok and title.strip():
            self._store.rename_conversation(thread_id, title.strip())
            self._refresh_tree()

    def _move_thread(self, thread_id: str):
        workspaces = self._store.list_workspaces()
        names = [w["name"] for w in workspaces]
        ids = [w["id"] for w in workspaces]
        choice, ok = QInputDialog.getItem(self, "Move Thread", "Destination workspace:", names, 0, False)
        if ok and choice:
            dest_id = ids[names.index(choice)]
            self._store.move_thread(thread_id, dest_id)
            self._refresh_tree()

    def _toggle_pin(self, thread_id: str):
        pinned = self._is_pinned(thread_id)
        self._store.pin_conversation(thread_id, not pinned)
        self._refresh_tree()

    def _delete_thread(self, thread_id: str):
        reply = QMessageBox.question(self, "Delete Thread", "Delete this conversation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._store.delete_conversation(thread_id)
            if self._active_conversation_id == thread_id:
                self._active_conversation_id = None
                self._new_conversation()
            self._refresh_tree()

    def _create_workspace(self):
        name, ok = QInputDialog.getText(self, "New Workspace", "Workspace name:")
        if ok and name.strip():
            ws_id = self._store.create_workspace(name.strip())
            self._store.set_active_workspace_id(ws_id)
            self._active_conversation_id = self._store.create_conversation("New Conversation", workspace_id=ws_id)
            self._feed.clear_messages()
            self._hide_memory_banner()
            self._refresh_tree()

    # -------------------------------------------------------------------------
    # Conversation handling
    # -------------------------------------------------------------------------
    def _ensure_active_conversation(self, first_message: str | None = None) -> str:
        convo_id = self._active_conversation_id
        if convo_id:
            convo = self._store.get_conversation(convo_id)
            if convo:
                return convo_id
        ws_id = self._store.get_active_workspace_id() or "personal"
        convo_id = self._store.ensure_active_conversation(first_message or "")
        if not self._store.conversation_exists(convo_id):
            convo_id = self._store.create_conversation(_title_from_message(first_message or "New Conversation"), workspace_id=ws_id)
        self._active_conversation_id = convo_id
        return convo_id

    def _load_active_conversation(self):
        convo_id = self._ensure_active_conversation()
        convo = self._store.get_conversation(convo_id)
        if convo:
            self._feed.load_messages(convo.get("messages") or [])
            self._active_conversation_id = convo_id
            self._hide_memory_banner()

    def _load_conversation(self, conversation_id: str):
        convo = self._store.get_conversation(conversation_id)
        if not convo:
            return
        self._active_conversation_id = conversation_id
        self._store.set_active_conversation_id(conversation_id)
        self._store.set_active_workspace_id(convo.get("workspace_id", "personal"))
        self._feed.load_messages(convo.get("messages") or [])
        self._hide_memory_banner()
        self._refresh_tree()

    def _new_conversation(self):
        ws_id = self._store.get_active_workspace_id() or "personal"
        self._active_conversation_id = self._store.create_conversation("New Conversation", workspace_id=ws_id)
        self._feed.clear_messages()
        self._hide_memory_banner()
        self._refresh_tree()
        self.new_conversation_requested.emit()

    # -------------------------------------------------------------------------
    # UI helpers (reuse existing)
    # -------------------------------------------------------------------------
    def _group_label(self, title: str) -> QLabel:
        lbl = QLabel(title.upper())
        lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;")
        return lbl

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_memory_banner(self, memories: list[dict[str, object]]):
        texts = [str(m.get("content") or "").strip() for m in memories if str(m.get("content") or "").strip()]
        if not texts:
            self._memory_items.setText("")
            self._memory_frame.hide()
            return
        self._memory_items.setText("• " + "\n• ".join(texts[:4]))
        self._memory_frame.show()

    def _hide_memory_banner(self):
        if hasattr(self, '_memory_items') and self._memory_items:
            self._memory_items.setText("")
        if hasattr(self, '_memory_frame') and self._memory_frame:
            self._memory_frame.hide()

    def _build_chat_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._task_card = TaskCard()
        lay.addWidget(self._task_card)

        self._memory_frame = QFrame()
        self._memory_frame.setVisible(False)
        self._memory_frame.setStyleSheet(
            f"""
            QFrame {{
                background: rgba(124, 110, 230,0.05);
                border: 1px solid rgba(124, 110, 230,0.24);
                border-radius: 12px;
            }}
            """
        )
        mem_lay = QVBoxLayout(self._memory_frame)
        mem_lay.setContentsMargins(12, 10, 12, 10)
        mem_lay.setSpacing(6)
        mem_title = QLabel("Using Memory:")
        mem_title.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        mem_title.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        self._memory_items = QLabel("")
        self._memory_items.setWordWrap(True)
        self._memory_items.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        mem_lay.addWidget(mem_title)
        mem_lay.addWidget(self._memory_items)
        lay.addWidget(self._memory_frame)

        self._feed = ConversationFeed()
        lay.addWidget(self._feed, 1)

        # Sleek modern chat input container for Workspace
        input_container = QFrame()
        input_container.setStyleSheet(
            f"QFrame {{ "
            f"  background: rgba(14, 17, 24, 0.75); "
            f"  border: 1px solid {C.BORDER_B}; "
            f"  border-radius: 14px; "
            f"}}"
        )
        input_row = QHBoxLayout(input_container)
        input_row.setContentsMargins(10, 6, 10, 6)
        input_row.setSpacing(8)

        self._attach_btn = QPushButton("📎")
        self._attach_btn.setFixedSize(30, 30)
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip("Attach file")
        self._attach_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C.TEXT}; border: none; font-size: 14px; }}"
            f"QPushButton:hover {{ color: {C.PRI}; }}"
        )
        self._attach_btn.clicked.connect(self.attach_requested.emit)
        input_row.addWidget(self._attach_btn)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Message Stella...")
        self._input.setFont(QFont("Exo 2", 10))
        self._input.setMinimumHeight(40)
        self._input.setStyleSheet(
            f"QLineEdit {{ background: transparent; color: {C.TEXT}; border: none; padding: 6px 8px; selection-background-color: {C.PRI_GHO}; }}"
        )
        self._input.returnPressed.connect(self._send)
        self._input.textChanged.connect(lambda t: voice_gate.set_typing(bool((t or "").strip())))
        input_row.addWidget(self._input, 1)

        self._mic_btn = QPushButton("🎙")
        self._mic_btn.setFixedSize(34, 34)
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setToolTip("Toggle Voice")
        self._mic_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C.TEXT}; border: none; font-size: 16px; }}"
            f"QPushButton:hover {{ color: {C.PRI}; }}"
        )
        self._mic_btn.clicked.connect(self.mic_requested.emit)
        input_row.addWidget(self._mic_btn)

        # Voice state indicator
        self._voice_lbl = QLabel("●")
        self._voice_lbl.setFixedSize(10, 10)
        self._voice_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._voice_lbl.setStyleSheet(
            f"QLabel {{ background: {C.TEXT_DIM}; color: {C.TEXT_DIM}; border-radius: 5px; }}"
        )
        self._voice_lbl.hide()
        input_row.addWidget(self._voice_lbl)

        self._send_btn = QPushButton("➤")
        self._send_btn.setFixedSize(32, 30)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setToolTip("Send message (Enter)")
        self._send_btn.setStyleSheet(
            f"QPushButton {{ background: {C.PRI_GHO}; color: {C.PRI}; border: 1px solid {C.BORDER_B}; border-radius: 8px; font-weight: bold; font-size: 13px; }}"
            f"QPushButton:hover {{ background: {C.PRI}; color: {C.BG}; border-color: {C.PRI}; }}"
        )
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._send_btn)

        lay.addWidget(input_container)
        return page

    # -------------------------------------------------------------------------
    # Window management (reuse existing)
    # -------------------------------------------------------------------------
    def show_at(self):
        self.show_workspace(animate=False)

    def reposition(self):
        if not self.isVisible():
            return
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self._expanded_w + 1
        y = screen.top() + 18
        h = max(640, screen.height() - 36)
        self.setGeometry(x, y, self._expanded_w, h)
        self._target_h = h
        self._panel.setGeometry(0, 0, self._expanded_w, h)

    def _dock_rect(self) -> QRectF:
        screen = QApplication.primaryScreen().availableGeometry()
        h = max(640, screen.height() - 36)
        y = screen.top() + 18
        w = self._expanded_w
        x = screen.right() - w + 1
        return QRectF(x, y, w, h)

    def _collapsed_rect(self) -> QRectF:
        screen = QApplication.primaryScreen().availableGeometry()
        h = max(640, screen.height() - 36)
        y = screen.top() + 18
        w = self._expanded_w
        x = screen.right() + 8
        return QRectF(x, y, w, h)

    def focus_input(self):
        if hasattr(self, "_input") and self._input.isVisible():
            self._input.setFocus(Qt.FocusReason.OtherFocusReason)

    def show_workspace(self, animate: bool = True):
        self._collapsed = False
        self._panel.show()
        self._content.show()
        dock = self._dock_rect()
        start = self._collapsed_rect() if animate else dock
        self.setGeometry(start.toRect())
        self.show()
        self.raise_()
        self.activateWindow()
        self._apply_state()
        if animate:
            self._anim.stop()
            self._anim.setStartValue(start.toRect())
            self._anim.setEndValue(dock.toRect())
            self._anim.start()
        else:
            self.setGeometry(dock.toRect())
        self._panel.setGeometry(0, 0, self.width(), self.height())
        QTimer.singleShot(100, self.focus_input)

    def hide_workspace(self, animate: bool = True):
        self._collapsed = True
        if not self.isVisible():
            self._panel.hide()
            self.hide()
            return
        if animate:
            dock = self.geometry()
            end = self._collapsed_rect()
            self._anim.stop()
            self._anim.setStartValue(dock)
            self._anim.setEndValue(end.toRect())
            self._anim.finished.connect(self._hide_after_anim)
            self._anim.start()
        else:
            self._hide_after_anim()

    def _hide_after_anim(self):
        try:
            self._anim.finished.disconnect(self._hide_after_anim)
        except Exception:
            pass
        self._panel.hide()
        self.hide()

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool):
        if bool(collapsed):
            self.hide_workspace(animate=True)
        else:
            self.show_workspace(animate=True)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def _apply_state(self):
        self._panel.setVisible(not self._collapsed)
        self._content.setVisible(not self._collapsed)
        if self.isVisible() and not self._collapsed:
            self.reposition()

    def append_log(self, text: str):
        raw = (text or "").strip()
        if not raw:
            return
        low = raw.lower()
        if low.startswith(("you:", "stella evo:", "stella:")):
            return
        if low.startswith("sys:"):
            self.record_chat_event({"role": "system", "text": raw.split(":", 1)[1].strip(), "source": "local"})

    def record_chat_event(self, event: object):
        data = event if isinstance(event, dict) else {}
        role = (data.get("role") or "").strip().lower()
        text = (data.get("text") or data.get("content") or "").strip()
        if not role or not text:
            return
        attachments = data.get("attachments") or []
        stamp = data.get("timestamp")
        convo_id = data.get("conversation_id") or self._active_conversation_id
        if role == "user":
            convo_id = self._store.record_chat("user", text, conversation_id=convo_id, attachments=attachments)
            self._active_conversation_id = convo_id
            self._feed.add_message("user", "You", text, _fmt_time_stamp(stamp), attachments=attachments)
            memories = self._store.search_memories(text)
            self._show_memory_banner(memories)
        elif role == "assistant":
            convo_id = self._store.record_chat("assistant", text, conversation_id=convo_id, attachments=attachments)
            self._active_conversation_id = convo_id
            self._feed.add_message("assistant", "Stella", text, _fmt_time_stamp(stamp), attachments=attachments, animate=True)
            self._hide_memory_banner()
        elif role == "system":
            convo_id = self._store.record_chat("system", text, conversation_id=convo_id, attachments=attachments)
            self._active_conversation_id = convo_id
            self._feed.add_message("system", "System", text, _fmt_time_stamp(stamp), attachments=attachments, event_type=text)
        elif role == "file":
            convo_id = self._store.record_chat("assistant", text, conversation_id=convo_id, attachments=attachments)
            self._active_conversation_id = convo_id
            self._feed.add_message("file", "Files", text, _fmt_time_stamp(stamp), attachments=attachments)
        self._refresh_tree()

    def apply_task_workspace(self, event: object):
        data = event if isinstance(event, dict) else {}
        action = (data.get("action") or "update").strip().lower()
        if action == "start":
            command = data.get("command") or ""
            plan = data.get("plan") or []
            plan_text = plan if isinstance(plan, str) else "\n".join(f"• {item}" for item in plan) if plan else ""
            self._task_card.show()
            self._task_card.start_workspace(command, plan, data.get("source") or "local")
        elif action == "update":
            self._task_card.show()
            self._task_card.update_workspace(
                title=data.get("title"),
                command=data.get("command"),
                plan=data.get("plan"),
                status=data.get("status"),
                output=data.get("output"),
                percent=data.get("percent"),
                footer=data.get("footer"),
            )
            chunks = [data.get("status") or "", data.get("output") or "", data.get("footer") or ""]
            text = "\n".join(chunk for chunk in chunks if chunk)
            if text:
                self.record_chat_event({"role": "system", "text": text, "source": data.get("source") or "local"})
        elif action == "finish":
            self._task_card.show()
            self._task_card.finish_workspace(
                data.get("result") or data.get("output") or "Done.",
                data.get("status") or "Task completed.",
                int(data.get("percent") or 100),
            )
            self.record_chat_event({
                "role": "system",
                "text": data.get("result") or data.get("output") or "Done.",
                "source": data.get("source") or "local",
            })
            QTimer.singleShot(4000, self._task_card.hide)
        elif action == "clear":
            self._task_card.clear_workspace()

    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._ensure_active_conversation(text)
        self.command_submitted.emit(text)


class InlineChatWorkspace(QFrame):
    """Embedded chat workspace for main window center panel."""
    
    command_submitted = pyqtSignal(str)
    attach_requested = pyqtSignal()
    mic_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InlineChatWorkspace")
        self._store = workspace_store()
        self._active_conversation_id: str | None = None
        self.setStyleSheet("QFrame#InlineChatWorkspace { background: transparent; border: none; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # No tabs - workspace switcher in toolbar
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_chat_tab())
        root.addWidget(self._stack, 1)

        self._ensure_conversation()
        self._load_active_conversation()

        # Wire voice state signals to UI
        from core.voice_gate import voice_signals
        voice_signals().voice_activated_changed.connect(self._on_voice_activated_changed)
        voice_signals().mic_allowed_changed.connect(self._on_mic_allowed_changed)
        voice_signals().audio_level.connect(self._on_audio_level)

    def apply_task_workspace(self, event: object):
        data = event if isinstance(event, dict) else {}
        action = (data.get("action") or "update").strip().lower()
        if action == "start":
            command = data.get("command") or ""
            plan = data.get("plan") or []
            self._task_card.show()
            self._task_card.start_workspace(command, plan, data.get("source") or "local")
        elif action == "update":
            self._task_card.show()
            self._task_card.update_workspace(
                data.get("plan") or [],
                data.get("step", ""),
                data.get("status", ""),
                data.get("note", "")
            )
        elif action == "complete":
            self._task_card.show()
            self._task_card.complete_workspace(data.get("result", ""))

    def _on_voice_activated_changed(self, active: bool):
        self._voice_lbl.setVisible(active)
        self._voice_lbl.setStyleSheet(
            f"QLabel {{ background: {C.PRI if active else C.TEXT_DIM}; "
            f"color: {C.BG if active else C.TEXT_DIM}; border-radius: 5px; }}"
        )
        if hasattr(self, '_feed') and self._feed is not None:
            self._feed.set_holo_state("listening" if active else "idle")

    def _on_mic_allowed_changed(self, allowed: bool):
        if hasattr(self, '_mic_btn'):
            color = C.PRI if allowed else C.TEXT_DIM
            self._mic_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color}; border: none; font-size: 16px; }}"
                f"QPushButton:hover {{ color: {C.PRI}; }}"
            )

    def _on_audio_level(self, level: float):
        if hasattr(self, '_feed') and self._feed is not None:
            self._feed.set_audio_level(level)

    def _build_chat_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        today_bar = QHBoxLayout()
        today_bar.addStretch()
        today_pill = QLabel("Today")
        today_pill.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        today_pill.setStyleSheet(f"""
            QLabel {{
                background: {C.PRI_GHO};
                color: {C.PRI};
                border: 1px solid {C.BORDER_B};
                border-radius: 12px;
                padding: 4px 14px;
            }}
        """)
        today_bar.addWidget(today_pill)
        today_bar.addStretch()
        lay.addLayout(today_bar)

        self._task_card = TaskCard()
        self._task_card.hide()
        lay.addWidget(self._task_card)

        self._memory_frame = QFrame()
        self._memory_frame.setVisible(False)
        self._memory_frame.setStyleSheet(f"""
            QFrame {{
                background: {C.PRI_GHO};
                border: 1px solid {C.BORDER_B};
                border-radius: 12px;
            }}
        """)
        mlay = QVBoxLayout(self._memory_frame)
        mlay.setContentsMargins(12, 10, 12, 10)
        mlay.setSpacing(6)
        title = QLabel("Using Memory:")
        title.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        self._memory_lbl = QLabel("")
        self._memory_lbl.setWordWrap(True)
        self._memory_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        mlay.addWidget(title)
        mlay.addWidget(self._memory_lbl)
        lay.addWidget(self._memory_frame)

        self._feed = ConversationFeed()
        lay.addWidget(self._feed, 1)

        input_container = QFrame()
        input_container.setStyleSheet(
            f"QFrame {{ "
            f"  background: rgba(14, 17, 24, 0.75); "
            f"  border: 1px solid {C.BORDER_B}; "
            f"  border-radius: 14px; "
            f"}}"
        )
        input_row = QHBoxLayout(input_container)
        input_row.setContentsMargins(10, 6, 10, 6)
        input_row.setSpacing(8)

        self._attach_btn = QPushButton("📎")
        self._attach_btn.setFixedSize(30, 30)
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip("Attach file")
        self._attach_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C.TEXT}; border: none; font-size: 14px; }}"
            f"QPushButton:hover {{ color: {C.PRI}; }}"
        )
        self._attach_btn.clicked.connect(self.attach_requested.emit)
        input_row.addWidget(self._attach_btn)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Message Stella...")
        self._input.setFont(QFont("Exo 2", 10))
        self._input.setMinimumHeight(40)
        self._input.setStyleSheet(
            f"QLineEdit {{ background: transparent; color: {C.TEXT}; border: none; padding: 6px 8px; selection-background-color: {C.PRI_GHO}; }}"
        )
        self._input.returnPressed.connect(self._send)
        self._input.textChanged.connect(lambda t: voice_gate.set_typing(bool((t or "").strip())))
        input_row.addWidget(self._input, 1)

        self._mic_btn = QPushButton("🎙")
        self._mic_btn.setFixedSize(34, 34)
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setToolTip("Toggle Voice")
        self._mic_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C.TEXT}; border: none; font-size: 16px; }}"
            f"QPushButton:hover {{ color: {C.PRI}; }}"
        )
        self._mic_btn.clicked.connect(self.mic_requested.emit)
        input_row.addWidget(self._mic_btn)

        # Voice state indicator
        self._voice_lbl = QLabel("●")
        self._voice_lbl.setFixedSize(10, 10)
        self._voice_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._voice_lbl.setStyleSheet(
            f"QLabel {{ background: {C.TEXT_DIM}; color: {C.TEXT_DIM}; border-radius: 5px; }}"
        )
        self._voice_lbl.hide()
        input_row.addWidget(self._voice_lbl)

        self._send_btn = QPushButton("➤")
        self._send_btn.setFixedSize(32, 30)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setToolTip("Send message (Enter)")
        self._send_btn.setStyleSheet(
            f"QPushButton {{ background: {C.PRI_GHO}; color: {C.PRI}; border: 1px solid {C.BORDER_B}; border-radius: 8px; font-weight: bold; font-size: 13px; }}"
            f"QPushButton:hover {{ background: {C.PRI}; color: {C.BG}; border-color: {C.PRI}; }}"
        )
        self._send_btn.clicked.connect(self._send)
        input_row.addWidget(self._send_btn)

        lay.addWidget(input_container)
        return page

    def _ensure_conversation(self):
        convo_id = self._active_conversation_id
        if convo_id:
            convo = self._store.get_conversation(convo_id)
            if convo:
                return
        ws_id = self._store.get_active_workspace_id() or "personal"
        self._active_conversation_id = self._store.create_conversation("New Conversation", workspace_id=ws_id)

    def _load_active_conversation(self):
        convo_id = self._ensure_conversation()
        convo = self._store.get_conversation(convo_id)
        if convo:
            self._feed.load_messages(convo.get("messages") or [])
            self._active_conversation_id = convo_id

    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._ensure_conversation(text)
        self.command_submitted.emit(text)

    def focus_input(self):
        if hasattr(self, "_input") and self._input.isVisible():
            self._input.setFocus(Qt.FocusReason.OtherFocusReason)