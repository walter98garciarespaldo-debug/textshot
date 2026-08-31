#!/usr/bin/env python3
"""
TextShot GUI — System tray application with global hotkey Ctrl+Alt+S.

Architecture:
  - TextShotApp  : QSystemTrayIcon that lives in background
  - MainWindow   : History panel showing captured text items
  - HotkeyThread : Background thread listening for Ctrl+Alt+S
  - SnipWorker   : Runs the overlay (Snipper) and returns result to the GUI
"""

import sys
import os
import datetime
import threading

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QSystemTrayIcon, QMenu, QAction, QFrame, QSplitter, QSizePolicy,
    QGraphicsDropShadowEffect, QScrollArea,
)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QFont, QPalette, QImage, QPainter, QBrush

from .ocr import ensure_tesseract_installed
from .textshot import OneTimeSnipper

# Ensure pytesseract can find Tesseract even if PATH hasn't propagated yet
try:
    import pytesseract, shutil
    if not shutil.which("tesseract"):
        # Fallback to standard install locations on Windows
        _local = os.environ.get("LOCALAPPDATA", "")
        _candidates = [
            os.path.join(_local, "Programs", "Tesseract-OCR", "tesseract.exe") if _local else "",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for _p in _candidates:
            if _p and os.path.exists(_p):
                pytesseract.pytesseract.tesseract_cmd = _p
                break
except Exception:
    pass

# ──────────────────────────────────────────────
# Hotkey listener thread
# ──────────────────────────────────────────────

class HotkeyThread(QThread):
    """Background thread that listens for Ctrl+Alt+S using the `keyboard` lib."""
    triggered = pyqtSignal()

    def run(self):
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+alt+s", self._on_hotkey)
            keyboard.wait()           # blocks until the thread is killed
        except Exception as e:
            print(f"[TextShot] Hotkey error: {e}")

    def _on_hotkey(self):
        self.triggered.emit()

    def stop(self):
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        self.quit()





class _CallbackSnipper(OneTimeSnipper):
    """
    OneTimeSnipper that uses a nested QEventLoop so it can run as an overlay
    on top of the main app without calling QApplication.quit().
    """

    def __init__(self, parent, langs, loop: QtCore.QEventLoop, flags=Qt.WindowFlags()):
        super().__init__(parent=parent, langs=langs, flags=flags)
        self._loop = loop
        self.result_text = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._loop.quit()
        return super(OneTimeSnipper, self).keyPressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.start == self.end:
            return super(OneTimeSnipper, self).mouseReleaseEvent(event)

        self.result_text = self.snipOcr()
        self._loop.quit()   # exit the nested event loop, NOT the whole app


# ──────────────────────────────────────────────
# History item widget
# ──────────────────────────────────────────────

class HistoryItemWidget(QFrame):
    selected = pyqtSignal(str)
    deleted  = pyqtSignal(object)  # self

    def __init__(self, text: str, timestamp: str, parent=None):
        super().__init__(parent)
        self.full_text = text
        self.timestamp = timestamp
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("historyItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # Icon area
        icon_label = QLabel("📋")
        icon_label.setFixedWidth(24)
        icon_label.setStyleSheet("font-size: 18px;")

        # Text area
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        preview = self.full_text.replace("\n", " ")[:80]
        if len(self.full_text) > 80:
            preview += "…"

        self.preview_label = QLabel(preview)
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setWordWrap(False)

        self.time_label = QLabel(self.timestamp)
        self.time_label.setObjectName("timeLabel")

        text_col.addWidget(self.preview_label)
        text_col.addWidget(self.time_label)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setObjectName("deleteBtn")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.deleted.emit(self))

        layout.addWidget(icon_label)
        layout.addLayout(text_col, stretch=1)
        layout.addWidget(del_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.full_text)
        super().mousePressEvent(event)


# ──────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────

DARK_STYLE = """
/* ── Root ── */
QMainWindow, QWidget#root {
    background-color: #0d0d1a;
}

/* ── Header ── */
QWidget#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0d0d1a, stop:1 #111128);
    border-bottom: 1px solid #1e1e3a;
}

QLabel#appTitle {
    font-family: 'Segoe UI', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: #00d4ff;
    letter-spacing: 1px;
}

QLabel#appSubtitle {
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    color: #4a4a7a;
}

/* ── Capture button ── */
QPushButton#captureBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #00d4ff, stop:1 #0066cc);
    color: #0d0d1a;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 10px 22px;
    letter-spacing: 0.5px;
}
QPushButton#captureBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #33ddff, stop:1 #0088ee);
}
QPushButton#captureBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #00aacc, stop:1 #004499);
}

/* ── Hotkey badge ── */
QLabel#hotkeyBadge {
    background-color: #1a1a2e;
    color: #00d4ff;
    font-family: 'Segoe UI', monospace;
    font-size: 11px;
    border: 1px solid #00d4ff;
    border-radius: 6px;
    padding: 4px 10px;
}

/* ── Section titles ── */
QLabel#sectionTitle {
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #4a4a7a;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* ── History items ── */
QFrame#historyItem {
    background-color: #111128;
    border: 1px solid #1e1e3a;
    border-radius: 10px;
    margin: 2px 0px;
}
QFrame#historyItem:hover {
    background-color: #161635;
    border: 1px solid #00d4ff;
}

QLabel#previewLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    color: #e0e0ff;
}
QLabel#timeLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 10px;
    color: #3a3a6a;
}

QPushButton#deleteBtn {
    background: transparent;
    color: #3a3a6a;
    border: none;
    border-radius: 4px;
    font-size: 12px;
}
QPushButton#deleteBtn:hover {
    background: rgba(255, 60, 60, 0.15);
    color: #ff4444;
}

/* ── Preview panel ── */
QWidget#previewPanel {
    background-color: #0a0a18;
    border-left: 1px solid #1e1e3a;
}

QTextEdit#previewText {
    background-color: #0a0a18;
    color: #c8c8f0;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
    border: none;
    padding: 10px;
    selection-background-color: #00d4ff;
    selection-color: #0d0d1a;
}

/* ── Copy button ── */
QPushButton#copyBtn {
    background-color: #1a1a2e;
    color: #00d4ff;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid #00d4ff;
    border-radius: 8px;
    padding: 8px 18px;
}
QPushButton#copyBtn:hover {
    background-color: rgba(0, 212, 255, 0.1);
}
QPushButton#copyBtn:pressed {
    background-color: rgba(0, 212, 255, 0.2);
}

/* ── Clear all button ── */
QPushButton#clearBtn {
    background-color: transparent;
    color: #3a3a6a;
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    border: none;
    padding: 4px 8px;
}
QPushButton#clearBtn:hover {
    color: #ff4444;
}

/* ── Status bar ── */
QWidget#statusBar {
    background-color: #08080f;
    border-top: 1px solid #1e1e3a;
}
QLabel#statusText {
    font-family: 'Segoe UI', sans-serif;
    font-size: 10px;
    color: #3a3a6a;
}
QLabel#statusDot {
    font-size: 10px;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #0d0d1a;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #2a2a4a;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #00d4ff;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* ── Divider ── */
QFrame#divider {
    color: #1e1e3a;
}

/* ── Empty state ── */
QLabel#emptyLabel {
    color: #2a2a4a;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
"""


class MainWindow(QMainWindow):
    capture_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TextShot")
        self.setMinimumSize(760, 520)
        self.resize(900, 580)
        self.setObjectName("root")
        self.setStyleSheet(DARK_STYLE)

        self._history_widgets = []  # list of HistoryItemWidget
        self._current_text = ""

        self._setup_ui()
        self._setup_shadow()

    def _setup_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 212, 255, 60))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(70)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        # Logo + title
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        app_title = QLabel("⌖ TextShot")
        app_title.setObjectName("appTitle")
        app_subtitle = QLabel("OCR · Screenshot · Clipboard")
        app_subtitle.setObjectName("appSubtitle")
        title_col.addWidget(app_title)
        title_col.addWidget(app_subtitle)

        # Hotkey badge
        hotkey_badge = QLabel("Ctrl + Alt + S")
        hotkey_badge.setObjectName("hotkeyBadge")

        # Capture button
        self.capture_btn = QPushButton("⊕  Capture")
        self.capture_btn.setObjectName("captureBtn")
        self.capture_btn.setFixedHeight(40)
        self.capture_btn.setCursor(Qt.PointingHandCursor)
        self.capture_btn.clicked.connect(self.capture_requested.emit)

        h_layout.addLayout(title_col)
        h_layout.addStretch()
        h_layout.addWidget(hotkey_badge)
        h_layout.addSpacing(12)
        h_layout.addWidget(self.capture_btn)

        main_layout.addWidget(header)

        # ── Body splitter ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #1e1e3a; }")

        # Left: history panel
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 14, 12, 0)
        left_layout.setSpacing(8)

        # Section header row
        section_row = QHBoxLayout()
        hist_label = QLabel("HISTORY")
        hist_label.setObjectName("sectionTitle")
        self.clear_btn = QPushButton("Clear all")
        self.clear_btn.setObjectName("clearBtn")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_history)
        section_row.addWidget(hist_label)
        section_row.addStretch()
        section_row.addWidget(self.clear_btn)
        left_layout.addLayout(section_row)

        # Scroll area for history items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(0, 0, 6, 0)
        self._history_layout.setSpacing(4)
        self._history_layout.setAlignment(Qt.AlignTop)

        self._empty_label = QLabel("No captures yet.\nPress  Ctrl+Alt+S  to start.")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._history_layout.addWidget(self._empty_label)

        scroll.setWidget(self._history_container)
        left_layout.addWidget(scroll)

        # Right: preview panel
        right_panel = QWidget()
        right_panel.setObjectName("previewPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        preview_header = QHBoxLayout()
        preview_label = QLabel("PREVIEW")
        preview_label.setObjectName("sectionTitle")
        self.copy_btn = QPushButton("⎘  Copy")
        self.copy_btn.setObjectName("copyBtn")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_current)
        preview_header.addWidget(preview_label)
        preview_header.addStretch()
        preview_header.addWidget(self.copy_btn)
        right_layout.addLayout(preview_header)

        self.preview_text = QTextEdit()
        self.preview_text.setObjectName("previewText")
        self.preview_text.setReadOnly(False)
        self.preview_text.setPlaceholderText(
            "Select a capture from the history\nor press Ctrl+Alt+S to take a new one…"
        )
        right_layout.addWidget(self.preview_text)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([320, 580])

        main_layout.addWidget(splitter, stretch=1)

        # ── Status bar ──
        status_bar = QWidget()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(28)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(16, 0, 16, 0)

        self._status_dot = QLabel("●")
        self._status_dot.setObjectName("statusDot")
        self._status_dot.setStyleSheet("color: #00ff88;")

        self._status_text = QLabel("Ready  ·  Hotkey active: Ctrl+Alt+S")
        self._status_text.setObjectName("statusText")

        count_label_text = QLabel("TextShot v0.1.2")
        count_label_text.setObjectName("statusText")

        sb_layout.addWidget(self._status_dot)
        sb_layout.addSpacing(4)
        sb_layout.addWidget(self._status_text)
        sb_layout.addStretch()
        sb_layout.addWidget(count_label_text)

        main_layout.addWidget(status_bar)

    # ── Public API ──────────────────────────────

    def add_capture(self, text: str):
        """Add a new OCR result to the history list."""
        if self._empty_label.isVisible():
            self._empty_label.hide()

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        item = HistoryItemWidget(text, ts)
        item.selected.connect(self._show_preview)
        item.deleted.connect(self._remove_item)

        # Insert at top
        self._history_layout.insertWidget(0, item)
        self._history_widgets.insert(0, item)

        # Show preview immediately
        self._show_preview(text)
        self._set_status(f"Captured at {ts}  ·  {len(text)} chars")

    def _show_preview(self, text: str):
        self._current_text = text
        self.preview_text.setPlainText(text)
        self.copy_btn.setEnabled(True)

    def _copy_current(self):
        import pyperclip
        text = self.preview_text.toPlainText()
        if text:
            pyperclip.copy(text)
            self._set_status("Copied to clipboard ✓")
            # Brief flash on button
            self.copy_btn.setText("✓  Copied!")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("⎘  Copy"))

    def _remove_item(self, widget: HistoryItemWidget):
        self._history_layout.removeWidget(widget)
        self._history_widgets.remove(widget)
        widget.deleteLater()
        if not self._history_widgets:
            self._empty_label.show()
            self.preview_text.clear()
            self.copy_btn.setEnabled(False)

    def _clear_history(self):
        for w in list(self._history_widgets):
            self._history_layout.removeWidget(w)
            w.deleteLater()
        self._history_widgets.clear()
        self._empty_label.show()
        self.preview_text.clear()
        self.copy_btn.setEnabled(False)
        self._set_status("History cleared")

    def _set_status(self, msg: str):
        self._status_text.setText(msg)
        QTimer.singleShot(4000, lambda: self._status_text.setText(
            "Ready  ·  Hotkey active: Ctrl+Alt+S"
        ))

    def set_hotkey_error(self):
        self._status_dot.setStyleSheet("color: #ffaa00;")
        self._status_text.setText(
            "Hotkey unavailable — run as admin for global Ctrl+Alt+S"
        )

    def closeEvent(self, event):
        """Closing the window hides it to tray instead of quitting."""
        event.ignore()
        self.hide()


# ──────────────────────────────────────────────
# System tray application
# ──────────────────────────────────────────────

def _make_tray_icon(icon_path: str | None) -> QIcon:
    """Return a QIcon from file, or draw a fallback programmatically."""
    if icon_path and os.path.exists(icon_path):
        return QIcon(icon_path)
    # Fallback: draw a simple coloured circle
    px = QPixmap(64, 64)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor("#00d4ff")))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(8, 8, 48, 48)
    painter.end()
    return QIcon(px)


class TextShotApp:
    """Wraps QApplication + MainWindow + Tray + HotkeyThread."""

    def __init__(self, icon_path: str | None = None, langs: str = "eng"):
        self.langs = langs
        self._icon_path = icon_path
        self._capturing = False

        # Qt app
        QtCore.QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("TextShot")
        self.app.setQuitOnLastWindowClosed(False)   # keep running in tray

        # Window
        self.window = MainWindow()
        self.window.capture_requested.connect(self._start_capture)

        # Tray
        icon = _make_tray_icon(icon_path)
        self.tray = QSystemTrayIcon(icon, parent=self.app)
        self.tray.setToolTip("TextShot — Ctrl+Alt+S to capture")
        self._setup_tray_menu()
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # Hotkey thread
        self.hotkey_thread = HotkeyThread()
        self.hotkey_thread.triggered.connect(self._start_capture)
        self.hotkey_thread.start()

        # Ensure tesseract
        try:
            ensure_tesseract_installed()
        except SystemExit:
            pass  # error already displayed by ensure_tesseract_installed

    def _setup_tray_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #111128;
                color: #e0e0ff;
                border: 1px solid #1e1e3a;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: rgba(0, 212, 255, 0.15); }
            QMenu::separator { height: 1px; background: #1e1e3a; margin: 4px 0; }
        """)

        capture_action = QAction("⊕  Capture  (Ctrl+Alt+S)", self.app)
        capture_action.triggered.connect(self._start_capture)

        show_action = QAction("◫  Show Window", self.app)
        show_action.triggered.connect(self._show_window)

        quit_action = QAction("✕  Quit TextShot", self.app)
        quit_action.triggered.connect(self._quit)

        menu.addAction(capture_action)
        menu.addSeparator()
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:   # single click
            self._show_window()
        elif reason == QSystemTrayIcon.DoubleClick:
            self._start_capture()

    def _show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _start_capture(self):
        if self._capturing:
            return
        self._capturing = True

        # Hide main window so overlay can show cleanly
        was_visible = self.window.isVisible()
        self.window.hide()

        # Small delay so the window hides before the overlay appears
        QTimer.singleShot(150, lambda: self._launch_overlay(was_visible))

    def _launch_overlay(self, restore_window: bool):
        import pyperclip

        # Nested event loop: blocks here until snipper is done, without
        # killing the main QApplication event loop.
        loop = QtCore.QEventLoop()
        parent = QtWidgets.QMainWindow()
        snipper = _CallbackSnipper(parent, self.langs, loop)
        snipper.show()
        loop.exec_()   # block until snipper calls loop.quit()

        text = snipper.result_text
        snipper.deleteLater()
        parent.deleteLater()

        self._capturing = False
        if text:
            pyperclip.copy(text)
            self.window.add_capture(text)
            self.tray.showMessage(
                "TextShot",
                f"Copied: {text[:60]}{'…' if len(text) > 60 else ''}",
                QSystemTrayIcon.Information,
                2500,
            )
        if restore_window:
            QTimer.singleShot(200, self._show_window)

    def _quit(self):
        self.hotkey_thread.stop()
        self.tray.hide()
        self.app.quit()

    def run(self):
        """Start the Qt event loop. Blocks until quit."""
        # Show window on first launch so the user knows the app started
        self.window.show()
        # Notify via tray balloon so user finds the icon
        QTimer.singleShot(800, lambda: self.tray.showMessage(
            "TextShot activo",
            "Presioná Ctrl+Alt+S para capturar texto.\nClic en este ícono para abrir el historial.",
            QSystemTrayIcon.Information,
            4000,
        ))
        return self.app.exec_()



# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main(langs: str = "eng"):
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    icon_path = os.path.join(assets_dir, "icon.png")

    app = TextShotApp(icon_path=icon_path, langs=langs)
    sys.exit(app.run())
