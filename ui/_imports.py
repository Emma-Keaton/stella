from __future__ import annotations
from core.user_paths import get_user_data_dir

import asyncio
import json
import html as html_lib
import math
import os


def _qt_alive(widget):
    """True only if `widget` is a live Qt object.

    PyQt keeps the Python wrapper alive after the underlying C++ widget is
    destroyed, and `hasattr` still returns True for it - every attribute access
    then raises RuntimeError. Settings pages get rebuilt, so this is normal,
    not exceptional. Guarding access with this keeps one deleted combo box
    from aborting a whole settings refresh.
    """
    if widget is None:
        return False
    try:
        from PyQt6 import sip
        return not sip.isdeleted(widget)
    except Exception:
        return True

# Hardware acceleration & WebGL flags for smooth 180fps+ rendering in Chromium
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist --enable-accelerated-2d-canvas --enable-webgl --enable-webgl2-compute-context --disable-frame-rate-limit --disable-gpu-vsync --num-raster-threads=4 --use-angle=d3d11 --disable-gpu-driver-bug-workarounds"
)

import platform
import random
import re
import sys
import threading
import time
from collections import deque
from pathlib import Path

import psutil
if platform.system() == "Windows":
    import winreg

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QPoint, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, QPropertyAnimation, pyqtSignal, QCoreApplication, QThread,
)
from PyQt6.QtGui import (
    QAction, QBrush, QColor, QDragEnterEvent, QDropEvent, QFont,
    QIcon, QImage, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMenu, QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSlider, QTextEdit,
    QGraphicsDropShadowEffect,
    QStyle, QSystemTrayIcon, QVBoxLayout, QWidget, QProgressBar,
    QStackedWidget, QInputDialog, QMessageBox, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
)

try:
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
except Exception:
    pass

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except Exception:
    WEB_ENGINE_AVAILABLE = False

from discord_bot import DiscordBotService
from gesture_utils import estimate_gesture_state, GestureTracker
from smart_home import SmartHomeService
from smart_home_page_new import StellaHomePage, _DeviceTile
from core.local_brain import local_brain
from core import voice_gate
from workspace_store import store as workspace_store
from core.identity import identity
from sound_manager import sound_mgr
