from __future__ import annotations

from pathlib import Path
from typing import Any

from ._imports import *
from .common import *
from .chat import (
    StellaHologramWidget, MessageCard, ChatBubble, ConversationFeed,
    AttachmentCard, EventCard, ArtifactCard, TaskCard, TaskDock,
    HistoryConversationItem,
)
from .hud import DesktopHud, FloatingLauncher, FloatingGestureCard
from .overlays import (
    BootSequenceOverlay, CommandBar, ConfirmationOverlay,
    DailyBriefingOverlay, DeveloperModeDialog, IncomingAlertDialog,
    MeetingOverlay, MemoryInspectorOverlay, RemoteKeyOverlay,
    ScanningOverlay, SetupOverlay,
)
from .launcher import (
    LauncherControlPanel, StellaTelemetryWing, StellaResultWing, SmallPanelCard,
)
from .settings import (
    SystemConnectivitySidebar, SettingsHubPage, SystemConnectivityPage,
    SmartDevicesSection, _ConnectDeviceCard, StellaConnectDevicesPage,
)
from .settings_pages import (
    SettingsSidebar, SettingsContentPage, AIModelsPage, ConnectionsPage,
    MemoryDataPage, PermissionsPage, AppearancePage, SystemPage,
    SettingsWidget,
)
from .workspace import WorkspaceSidebar, InlineChatWorkspace

from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import QGuiApplication, QScreen, QDesktopServices
from PyQt6.QtCore import QObject, QBuffer

from agent.tools import Registry, ToolResult, Honesty
from agent.outcome import DONE, UNVERIFIED, FAILED, ASK, STARTED

try:
    from core.echo import EchoGuard
except Exception:
    EchoGuard = None

try:
    from core.hotkey import PushToTalk
except Exception:
    PushToTalk = None

try:
    from core.sensorium import sensorium
except Exception:
    sensorium = None

try:
    from core.protocols import protocols
except Exception:
    protocols = None

try:
    from memory.memory_manager import search_memory
except Exception:
    search_memory = None


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _logo_icon() -> QIcon:
    """Return the Stella application icon."""
    ico_path = _PROJECT_ROOT / "assets" / "stella_logo.ico"
    png_path = _PROJECT_ROOT / "assets" / "stella_logo.png"
    icon = QIcon()
    if ico_path.exists():
        icon.addFile(str(ico_path))
    if png_path.exists():
        icon.addFile(str(png_path))
    return icon


_MIN_W = 900
_MIN_H = 600
_DEFAULT_W = 1200
_DEFAULT_H = 800
_RIGHT_W = 350

_BACKGROUND_IMAGE_FILE = _PROJECT_ROOT / "assets" / "stella_logo.png"


# Module-level variables
_ER = None
_active_net_label = None
_attach_pulse_glow = None
_camera_available = False
_current_boot_stamp = None
_default_app_settings = None
_default_discord_settings = None
_hidden_launch_args = None
_install_hud = None
_launched_from_windows_startup = False
_logo_icon = _logo_icon
_startup_registry_key = None
_startup_run_value = None
finished_callback = None
hang_up_active_call = None
speak_native = None
suggest_improvement = None
take_over_active_call = None
translate_error = None
workspace_store = None


def _attach_pulse_glow(widget, color=None, blur_min=6.0, blur_max=14.0, alpha=36, period_ms=4200):
    """Placeholder pulse glow effect."""
    return widget


def _icon_pixmap(name: str, size: int = 20) -> QPixmap:
    from PyQt6.QtGui import QPixmap
    return QPixmap(size, size)


def _chat_measure(vw: int) -> float:
    """Responsive chat width ratio."""
    try:
        from core.hud_theme import measure_ratio
        return measure_ratio(vw)
    except Exception:
        return 0.84


def speak_native(text: str) -> None:
    """Speak text using native TTS."""
    try:
        from core.voice_gate import speak_native as _speak_native
        _speak_native(text)
    except Exception:
        pass


class Animation(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class Archives(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class CircuitPopupOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class ClipboardSentry(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class Code(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class CreateKey(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class Data(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class DeleteValue(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class Documents(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class Images(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class OpenKey(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class StreamThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)


class Thread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)


class UpdateChecker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.update_available_sig = pyqtSignal()

    def start(self):
        pass


class Video(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class Audio(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class BackgroundWidget(QWidget):
    """Simple background widget that displays an image."""

    def __init__(self, image_path: str | Path | None = None, parent=None):
        super().__init__(parent)
        self._image_path = Path(image_path) if image_path else None
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPixmap
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._image_path and self._image_path.exists():
            pixmap = QPixmap(str(self._image_path))
            if not pixmap.isNull():
                painter.drawPixmap(self.rect(), pixmap)
            else:
                painter.fillRect(self.rect(), QColor(12, 13, 20))
        else:
            painter.fillRect(self.rect(), QColor(12, 13, 20))


class FloatingGestureCard(QWidget):
    """Simple floating gesture card widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 21, 30))


class SmartDevicesSection(QWidget):
    """Simple smart devices section widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(18, 19, 28))


class StellaResultWing(QWidget):
    """Simple result wing widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(16, 17, 26))


class StellaTelemetryWing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class MainWindow(QMainWindow):
    _log_sig = pyqtSignal(str)
    _stream_chunk_sig = pyqtSignal(str)
    _stream_end_sig = pyqtSignal(str)
    _state_sig = pyqtSignal(str)
    _scan_sig = pyqtSignal(bool, str)
    _briefing_sig = pyqtSignal(object)
    _briefing_hide_sig = pyqtSignal()
    _attention_sig = pyqtSignal(object)
    _meeting_sig = pyqtSignal(object)
    _task_workspace_sig = pyqtSignal(object)
    _screen_capture_sig = pyqtSignal()
    discord_config_changed = pyqtSignal(str)
    discord_status_changed = pyqtSignal(str)
    mic_requested = pyqtSignal()

    def __init__(self, face_path: str):
        super().__init__()
        self.setWindowTitle("Stella")
        self.setWindowIcon(_logo_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        self._center_panel = BackgroundWidget(_BACKGROUND_IMAGE_FILE)
        self.setCentralWidget(self._center_panel)

        root = QVBoxLayout(self._center_panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._inline_workspace = InlineChatWorkspace(self)
        root.addWidget(self._inline_workspace)

        from core.voice_gate import VoiceGateSignals
        self._voice_gate = VoiceGateSignals()
        self._inline_workspace.mic_requested.connect(
            lambda: self._voice_gate.set_voice_activated(
                not self._voice_gate.is_voice_activated()
            )
        )

        self._workspace_sidebar = WorkspaceSidebar()
        root.addWidget(self._workspace_sidebar)

        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

    def _startup_enabled(self):
        pass

    def set_settings_bridge(self, bridge):
        self._settings_bridge = bridge

    def _load_app_settings(self):
        return {}

    def _load_discord_settings(self):
        return {}
        return {}

    def _build_right_panel_modern(self):
        return None


class StellaUI:
    def __init__(self, face_path: str, size=None, *, show_immediately: bool = True):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._app.setQuitOnLastWindowClosed(False)
        self._app.setApplicationDisplayName("Stella")
        self._app.setWindowIcon(self._make_app_icon())

        try:
            from core.hud_theme import install as _install_hud
            _install_hud(self._app)
        except Exception:
            pass

        try:
            current_store = workspace_store()
            current_store.rollover_active_conversation_on_startup()
        except Exception:
            pass

        self._win = MainWindow(face_path)

        try:
            from core.updater import UpdateChecker
            self._updater = UpdateChecker()
            self._updater.update_available_sig.connect(self._show_update_prompt)
            self._updater.start()
        except Exception as e:
            print(f"Failed to start updater: {e}")

        try:
            self._win._startup_enabled()
        except Exception:
            pass

        self._win.set_settings_bridge(self)
        self._discord_service = None
        try:
            from actions.discord_bot import DiscordBotService
            self._discord_service = DiscordBotService(
                status_callback=self._win.discord_status_changed.emit,
                log_callback=self._win._log_sig.emit,
            )
            self._discord_service.bind_app_submitter(self._win.submit_command)
            self._win.discord_config_changed.connect(self._on_discord_config_changed)
            self._win.on_chat_event = self._on_chat_event
            self._app.aboutToQuit.connect(self._discord_service.stop)
        except Exception:
            pass

        self._launcher = FloatingLauncher()
        self._hud = DesktopHud()
        self._hud_timer = QTimer(self._app)
        self._hud_timer.setInterval(2000)
        self._hud_timer.timeout.connect(self._refresh_hud_engine_health)
        self._hud_timer.start()
        self._command_bar = CommandBar()
        self._workspace_sidebar = WorkspaceSidebar()
        self._control_panel = None
        self._boot_overlay = None
        self._app_settings_cache = None

        self._launcher.single_clicked.connect(self._toggle_workspace_sidebar)
        self._launcher.double_clicked.connect(self._on_launcher_double_clicked)
        self._launcher.action_requested.connect(self._handle_launcher_action)
        self._launcher.position_changed.connect(self._save_launcher_position)
        self._hud.position_changed.connect(self._save_hud_position)
        self._hud.mute_toggled.connect(self._toggle_mute)
        self._command_bar.submitted.connect(self._submit_command)
        self._command_bar.attach_clicked.connect(self._browse_attachment)
        self._command_bar.mic_clicked.connect(self._toggle_mute)
        self._command_bar.developer_clicked.connect(self._open_developer_mode_dialog)
        self._workspace_sidebar.command_submitted.connect(self._submit_command)
        self._workspace_sidebar.attach_requested.connect(self._browse_attachment)
        self._workspace_sidebar.mic_requested.connect(
            lambda: self._voice_gate.set_voice_activated(
                not self._voice_gate.is_voice_activated()
            )
        )
        self._workspace_sidebar.close_requested.connect(self._close_workspace_sidebar)
        self._win.mic_requested.connect(
            lambda: self._voice_gate.set_voice_activated(
                not self._voice_gate.is_voice_activated()
            )
        )
        self._win.mic_requested.connect(
            lambda: self._voice_gate.set_voice_activated(
                not self._voice_gate.is_voice_activated()
            )
        )
        self._win._log_sig.connect(self._workspace_sidebar.append_log)
        self._win._task_workspace_sig.connect(self._workspace_sidebar.apply_task_workspace)

        inline_workspace = getattr(self._win, "_inline_workspace", None)
        if inline_workspace is not None:
            self._win._task_workspace_sig.connect(inline_workspace.apply_task_workspace)

        self._on_discord_config_changed(self._win._load_discord_settings())
        launcher_pos = self._load_app_settings().get("launcher_pos")
        if isinstance(launcher_pos, (list, tuple)) and len(launcher_pos) == 2:
            try:
                self._launcher.move(int(launcher_pos[0]), int(launcher_pos[1]))
            except Exception:
                pass
        hud_pos = self._load_app_settings().get("hud_pos")
        if isinstance(hud_pos, (list, tuple)) and len(hud_pos) == 2:
            try:
                self._hud.move(int(hud_pos[0]), int(hud_pos[1]))
            except Exception:
                pass
        try:
            if not (isinstance(hud_pos, (list, tuple)) and len(hud_pos) == 2):
                screen = QApplication.primaryScreen().availableGeometry()
                self._hud.move(
                    max(screen.left(), screen.right() - self._hud.width() - 24),
                    max(screen.top(), screen.bottom() - self._hud.height() - 48),
                )
                self._hud.show()
                self._hud.raise_()
        except Exception:
            pass
        if bool(self._load_app_settings().get("show_workspace_on_startup", False)):
            self._workspace_sidebar.show_workspace(animate=False)
        else:
            self._workspace_sidebar.hide_workspace(animate=False)
        self.set_dashboard_page(
            getattr(self._win, "_current_page", "dashboard") == "dashboard"
        )
        self._apply_developer_mode_ui()
        self._apply_saved_theme()
        if show_immediately:
            self._launcher.hide()
            if self._should_play_boot_sequence():
                self.play_boot_sequence()
            else:
                self.show_main()
        else:
            self._show_floating_icon()
        self.root = _RootShim(self._app)

    def _make_app_icon(self) -> QIcon:
        return _logo_icon()

    def set_stella_connect_service(self, service):
        self._win.set_stella_connect_service(service)

    def show_main(self):
        if self._boot_overlay is not None and not getattr(self._boot_overlay, "_boot_finished", False):
            return
        try:
            self._win.setWindowState(
                (self._win.windowState() & ~Qt.WindowState.WindowMinimized)
                | Qt.WindowState.WindowActive
            )
            self._win.showNormal()
        except Exception:
            self._win.show()
        self._win.raise_()
        self._win.activateWindow()
        self._launcher.hide()
        self._greet_on_startup()

    def _greet_on_startup(self):
        if getattr(self, "_has_greeted", False):
            return
        self._has_greeted = True
        try:
            if not self._load_app_settings().get("startup_greeting", True):
                return
        except Exception:
            pass
        try:
            from core import intro
            name = intro.owner_name() or None
            greeting = intro.build_greeting(name)
            first_run = intro.is_first_run()
        except Exception:
            greeting = (
                "Welcome to Stella. I'm online and ready. "
                "Use the prompt box below to type, attach files, or hit Voice to speak - "
                "or jump straight into Dashboard, Devices and Settings from the nav above. "
                "How can I help?"
            )
            first_run = False
        card_summary = greeting
        if first_run:
            try:
                from core import intro as _intro
                card_summary = greeting + "\n\n" + _intro.build_intro_questions()
            except Exception:
                pass
        try:
            self._win._inline_workspace.append_user_message(card_summary)
        except Exception:
            pass

    def _show_floating_icon(self):
        self._launcher.show()
        self._launcher.raise_()
        self._launcher.activateWindow()

    def _show_update_prompt(self):
        pass

    def _refresh_hud_engine_health(self):
        pass

    def _toggle_workspace_sidebar(self):
        if self._workspace_sidebar.isVisible():
            self._workspace_sidebar.hide_workspace(animate=False)
        else:
            self._workspace_sidebar.show_workspace(animate=False)

    def _on_launcher_double_clicked(self):
        self.show_main()

    def _handle_launcher_action(self, action):
        pass

    def _save_launcher_position(self):
        pass

    def _save_hud_position(self):
        pass

    def _toggle_mute(self):
        if hasattr(self, "_voice_gate") and self._voice_gate:
            self._voice_gate.set_voice_activated(
                not self._voice_gate.is_voice_activated()
            )

    def _toggle_workspace_sidebar(self):
        if self._workspace_sidebar.isVisible():
            self._workspace_sidebar.hide_workspace(animate=False)
        else:
            self._workspace_sidebar.show_workspace(animate=False)

    def _close_workspace_sidebar(self):
        self._workspace_sidebar.hide_workspace(animate=False)

    def _on_discord_config_changed(self, value):
        pass

    def _on_chat_event(self, event):
        pass

    def _sync_launcher_state(self):
        pass

    def _sync_hud_state(self):
        pass

    def _on_minimized(self):
        self._win.hide()

    def _on_restored(self):
        self._win.showNormal()

    def _submit_command(self, text):
        pass

    def _browse_attachment(self):
        pass

    def _open_developer_mode_dialog(self):
        pass

    def _apply_developer_mode_ui(self):
        pass

    def _apply_saved_theme(self):
        pass

    def _should_play_boot_sequence(self):
        return False

    def play_boot_sequence(self):
        pass

    def _load_app_settings(self):
        return {}

    def write_log(self, text):
        try:
            self._win._log_sig.emit(text)
        except Exception:
            pass

    def set_state(self, state):
        try:
            self._win._state_sig.emit(state)
        except Exception:
            pass

    def set_muted_state(self, muted):
        pass

    def set_audio_level(self, level):
        try:
            self._hud.set_audio_level(level)
        except Exception:
            pass

    def show_hud_deliverable(self, deliverable):
        pass

    def show_hud_operation(self, operation):
        pass

    def set_meeting_mode(self, active):
        pass

    def close(self):
        self._win.close()
        return {}
