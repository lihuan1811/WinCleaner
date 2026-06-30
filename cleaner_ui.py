#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 用户界面
"""

import os
import sys
import subprocess
import hashlib
import datetime
import re
try:
    import psutil
except ImportError:  # pragma: no cover - optional runtime dependency
    psutil = None

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QProgressBar, QCheckBox,
                            QTreeWidget, QTreeWidgetItem, QMessageBox,
                            QFrame, QGridLayout, QStackedWidget, QScrollArea,
                            QFileDialog, QTabWidget, QTableWidget,
                            QTableWidgetItem, QHeaderView, QAbstractItemView,
                            QFileIconProvider, QGraphicsOpacityEffect, QLineEdit,
                            QTextEdit)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QFileInfo, QPropertyAnimation, QEasingCurve,
    QTimer
)
from PyQt5.QtGui import QIcon, QFont, QPixmap

from cleaner_logic import CleanerLogic
from category_display import category_tree_label
from config import APP_NAME
from local_account_service import AccountError, DEMO_CARD_CODES, LocalAccountService
from qt_backup_manager import QtBackupManagerDialog
from system_repair import SystemRepairService


APP_DISPLAY_NAME = "C盘清理精灵"


def hidden_windows_subprocess_kwargs():
    if not sys.platform.startswith("win"):
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


# 主题主色（青绿 teal），从旧版绿色 #35C878 切换而来
APP_QSS = """
QMainWindow {
    background: #EFF6F4;
}

QWidget#appRoot {
    background: #EFF6F4;
    color: #15241F;
    font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", Arial, sans-serif;
    font-size: 13px;
}

QWidget#contentArea {
    background: #EFF6F4;
}

QFrame#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #14B8A6, stop:1 #0D9488);
    border: none;
}

QLabel#brandTitle {
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 700;
}

QLabel#brandSubtitle,
QLabel#sidebarFooter {
    color: rgba(255, 255, 255, 0.82);
    font-size: 12px;
}

QPushButton#sidebarButton,
QPushButton#sidebarButtonActive {
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 14px;
    min-height: 40px;
    padding: 0 14px;
    text-align: left;
}

QPushButton#sidebarButton {
    background: transparent;
}

QPushButton#sidebarButtonActive {
    background: rgba(255, 255, 255, 0.22);
    font-weight: 700;
}

QPushButton#sidebarButton:hover {
    background: rgba(255, 255, 255, 0.14);
}

QFrame#heroPanel,
QFrame#resultCard,
QFrame#statusStrip,
QFrame#featureCard {
    background: #FFFFFF;
    border: 1px solid #D6E8E4;
    border-radius: 10px;
}

QLabel#heroTitle,
QLabel#pageTitle {
    color: #15241C;
    font-size: 22px;
    font-weight: 700;
}

QLabel#heroSubtitle,
QLabel#pageSubtitle,
QLabel#diskInfo,
QLabel#resultSummary,
QLabel#statusLabel,
QLabel#scanPathLabel,
QLabel#selectedSummary {
    color: #5E726B;
}

QFrame#statBlock {
    background: #F2FAF8;
    border: 1px solid #DEEFEA;
    border-radius: 8px;
}

QLabel#statTitle {
    color: #66807A;
    font-size: 12px;
}

QLabel#statValue {
    color: #16271F;
    font-size: 16px;
    font-weight: 700;
}

QLabel#cleanableValue {
    color: #0D9488;
    font-size: 16px;
    font-weight: 700;
}

QPushButton#scanPrimaryButton {
    background: #14B8A6;
    border: none;
    border-radius: 6px;
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
    min-height: 42px;
    padding: 0 24px;
}

QPushButton#scanPrimaryButton:hover {
    background: #0D9488;
}

QPushButton#scanPrimaryButton:disabled {
    background: #9FE0D8;
}

QPushButton#cleanSecondaryButton {
    background: #FFFFFF;
    border: 1px solid #14B8A6;
    border-radius: 6px;
    color: #0D7E72;
    font-size: 14px;
    font-weight: 700;
    min-height: 38px;
    padding: 0 22px;
}

QPushButton#cleanSecondaryButton:hover {
    background: #E7F7F4;
}

QPushButton#cleanSecondaryButton:disabled {
    border-color: #C7DDD8;
    color: #93A8A2;
    background: #F7FBFA;
}

QProgressBar#scanProgress {
    background: #E2F2EF;
    border: none;
    border-radius: 7px;
    height: 14px;
    text-align: center;
}

QProgressBar#scanProgress::chunk {
    background: #14B8A6;
    border-radius: 7px;
}

QLabel#scanPathLabel {
    background: #F2FAF8;
    border: 1px solid #D6E8E4;
    border-radius: 7px;
    min-height: 28px;
    padding: 0 12px;
}

QLabel#resultTitle {
    color: #16271F;
    font-size: 17px;
    font-weight: 700;
}

QTreeWidget#resultTree {
    background: #FFFFFF;
    border: none;
    color: #1C2C26;
    alternate-background-color: #F5FBF9;
    outline: 0;
    selection-background-color: #CCEFE8;
    selection-color: #15241C;
}

QTreeWidget#resultTree::item {
    min-height: 30px;
    padding: 4px 2px;
}

QTreeWidget#optimizerTable,
QTableWidget#optimizerTable,
QTableWidget#uninstallTable,
QTableWidget#fileManageTable {
    background: #FFFFFF;
    border: 1px solid #D6E8E4;
    border-radius: 8px;
    color: #1C2C26;
    gridline-color: #E3EFEC;
    outline: 0;
    selection-background-color: #CCEFE8;
    selection-color: #15241C;
}

QTreeWidget#optimizerTable::item,
QTableWidget#optimizerTable::item,
QTableWidget#uninstallTable::item,
QTableWidget#fileManageTable::item {
    min-height: 30px;
    padding: 4px 6px;
}

QTabWidget#optimizerTabs::pane {
    background: #FFFFFF;
    border: 1px solid #D6E8E4;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: #FFFFFF;
    border: 1px solid #D6E8E4;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #0E6F66;
    font-weight: 700;
    min-height: 28px;
    min-width: 82px;
    padding: 5px 12px;
}

QTabBar::tab:selected {
    background: #14B8A6;
    color: #FFFFFF;
    border-color: #14B8A6;
}

QTabBar::tab:hover:!selected {
    background: #E7F7F4;
}

QHeaderView::section {
    background: #F1F8F6;
    border: none;
    border-bottom: 1px solid #D6E8E4;
    color: #5E7268;
    font-weight: 700;
    min-height: 32px;
    padding-left: 8px;
}

QCheckBox {
    color: #36473F;
    spacing: 8px;
}

QCheckBox::indicator {
    height: 16px;
    width: 16px;
}

QLineEdit {
    background: #FFFFFF;
    border: 1px solid #D6E8E4;
    border-radius: 6px;
    color: #15241F;
    min-height: 34px;
    padding: 0 10px;
}

QLineEdit:focus {
    border-color: #14B8A6;
}

QLabel#featureCardTitle {
    color: #16271F;
    font-size: 15px;
    font-weight: 700;
}

QLabel#featureCardDesc {
    color: #5E726B;
    font-size: 12px;
}

QPushButton#featureButton {
    background: #14B8A6;
    border: none;
    border-radius: 6px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    min-height: 34px;
    min-width: 112px;
    padding: 0 16px;
}

QPushButton#featureButton:hover {
    background: #0D9488;
}

QPushButton#miniActionButton {
    background: #FFFFFF;
    border: 1px solid #14B8A6;
    border-radius: 12px;
    color: #0D7E72;
    font-size: 12px;
    font-weight: 700;
    min-height: 24px;
    min-width: 64px;
    padding: 0 12px;
}

QPushButton#miniActionButton:hover {
    background: #E7F7F4;
}

QScrollArea#pageScroll {
    background: transparent;
    border: none;
}

QWidget#pageScrollInner {
    background: transparent;
}
"""


class ScanThread(QThread):
    """扫描线程，避免UI冻结"""
    update_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, cleaner):
        super().__init__()
        self.cleaner = cleaner

    def run(self):
        """运行扫描过程"""
        try:
            results = self.cleaner.scan_system(self.update_signal)
            self.finished_signal.emit(results)
        except Exception as exc:  # pragma: no cover - depends on host filesystem
            self.error_signal.emit(str(exc))


class CleanThread(QThread):
    """清理线程，避免UI冻结"""
    update_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, cleaner, selected_items):
        super().__init__()
        self.cleaner = cleaner
        self.selected_items = selected_items

    def run(self):
        """运行清理过程"""
        try:
            results = self.cleaner.clean_selected(self.selected_items, self.update_signal)
            self.finished_signal.emit(results)
        except Exception as exc:  # pragma: no cover - depends on host filesystem
            self.error_signal.emit(str(exc))


class FileScanThread(QThread):
    """文件管理扫描线程，避免大文件/重复文件扫描阻塞 UI。"""
    file_scan_finished_signal = pyqtSignal(str, object)
    file_scan_error_signal = pyqtSignal(str, str)

    def __init__(self, mode, root_dir, min_size=100 * 1024 * 1024, max_files=5000):
        super().__init__()
        self.mode = mode
        self.root_dir = root_dir
        self.min_size = min_size
        self.max_files = max_files

    def run(self):
        try:
            if self.mode == "large":
                payload = self.find_large_files(self.root_dir, self.min_size, self.max_files)
            elif self.mode == "duplicates":
                payload = self.find_duplicate_files(self.root_dir, self.max_files)
            else:
                raise ValueError(f"未知文件扫描类型: {self.mode}")
            self.file_scan_finished_signal.emit(self.mode, payload)
        except Exception as exc:  # pragma: no cover - depends on host filesystem
            self.file_scan_error_signal.emit(self.mode, str(exc))

    @staticmethod
    def find_large_files(root_dir, min_size=100 * 1024 * 1024, max_files=5000):
        large_files = []
        scanned = 0
        for root, _dirs, files in os.walk(root_dir):
            for file_name in files:
                if scanned >= max_files:
                    break
                path = os.path.join(root, file_name)
                try:
                    if not os.path.isfile(path):
                        continue
                    scanned += 1
                    size = os.path.getsize(path)
                    if size >= min_size:
                        large_files.append({
                            "path": path,
                            "size": size,
                            "name": file_name,
                        })
                except (OSError, PermissionError):
                    continue
            if scanned >= max_files:
                break
        large_files.sort(key=lambda item: item["size"], reverse=True)
        return large_files[:200]

    @staticmethod
    def find_duplicate_files(root_dir, max_files=5000):
        by_size = {}
        scanned = 0
        for root, _dirs, files in os.walk(root_dir):
            for file_name in files:
                if scanned >= max_files:
                    break
                path = os.path.join(root, file_name)
                try:
                    if not os.path.isfile(path):
                        continue
                    size = os.path.getsize(path)
                    if size <= 0:
                        continue
                    by_size.setdefault(size, []).append(path)
                    scanned += 1
                except (OSError, PermissionError):
                    continue

        duplicates = []
        for size, paths in by_size.items():
            if len(paths) < 2:
                continue
            by_digest = {}
            for path in paths:
                digest = FileScanThread.file_digest(path)
                if digest:
                    by_digest.setdefault(digest, []).append(path)
            for digest_paths in by_digest.values():
                if len(digest_paths) > 1:
                    duplicates.append((size, digest_paths))

        duplicates.sort(key=lambda group: group[0] * (len(group[1]) - 1), reverse=True)
        return duplicates

    @staticmethod
    def file_digest(path):
        digest = hashlib.sha256()
        try:
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except (OSError, PermissionError):
            return None


class DefragThread(QThread):
    """Windows 磁盘碎片扫描/整理线程。"""
    defrag_progress_signal = pyqtSignal(str)
    defrag_finished_signal = pyqtSignal(str, dict)
    defrag_error_signal = pyqtSignal(str, str)

    def __init__(self, mode, drive="C:"):
        super().__init__()
        self.mode = mode
        self.drive = drive

    def run(self):
        if self.drive.upper() == "C:":
            command = "defrag C: /A /V" if self.mode == "scan" else "defrag C: /U /V"
        else:
            command = f"defrag {self.drive} /A /V" if self.mode == "scan" else f"defrag {self.drive} /U /V"
        label = "扫描碎片" if self.mode == "scan" else "整理碎片"
        try:
            self.defrag_progress_signal.emit(f"{label}中: {command}")
            if not sys.platform.startswith("win"):
                self.defrag_finished_signal.emit(
                    self.mode,
                    {
                        "command": command,
                        "output": f"该操作将在 Windows 上执行: {command}",
                        "fragment_count": "--",
                        "fragment_files": "--",
                        "fragment_rate": "--",
                        "exit_code": 0,
                    },
                )
                return

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=60 * 60,
                **hidden_windows_subprocess_kwargs(),
            )
            output = "\n".join(
                part.strip()
                for part in (result.stdout, result.stderr)
                if part and part.strip()
            )
            payload = self.parse_output(output)
            payload.update({
                "command": command,
                "output": output or "命令无输出",
                "exit_code": result.returncode,
            })
            self.defrag_finished_signal.emit(self.mode, payload)
        except Exception as exc:  # pragma: no cover - depends on Windows defrag
            self.defrag_error_signal.emit(self.mode, str(exc))

    @staticmethod
    def parse_output(output):
        rate = DefragThread.first_match(
            output,
            [
                r"碎片率\s*[:：]\s*([\d.]+)\s*%",
                r"总碎片(?:百分比|率)?\s*[:：]\s*([\d.]+)\s*%",
                r"Total fragmentation\s*[:：]\s*([\d.]+)\s*%",
            ],
        )
        fragment_files = DefragThread.first_match(
            output,
            [
                r"碎片文件(?:数)?\s*[:：]\s*(\d+)",
                r"fragmented files\s*[:：]\s*(\d+)",
            ],
        )
        fragment_count = DefragThread.first_match(
            output,
            [
                r"碎片数\s*[:：]\s*(\d+)",
                r"文件碎片总数\s*[:：]\s*(\d+)",
                r"fragments\s*[:：]\s*(\d+)",
            ],
        )
        return {
            "fragment_count": fragment_count or "--",
            "fragment_files": fragment_files or "--",
            "fragment_rate": f"{rate}%" if rate else "--",
            "fragment_rate_value": float(rate) if rate else 0.0,
        }

    @staticmethod
    def first_match(output, patterns):
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""


class SystemRepairThread(QThread):
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, service, actions):
        super().__init__()
        self.service = service
        self.actions = actions

    def run(self):
        try:
            for action in self.actions:
                self.progress_signal.emit(f"正在执行 {action.name}...")
                self.result_signal.emit(self.service.run_action(action))
            self.finished_signal.emit()
        except Exception as exc:  # pragma: no cover - depends on host commands
            self.error_signal.emit(str(exc))


class BXOptimizationThread(QThread):
    """BoosterX 风格优化执行线程，避免批量命令阻塞 UI。"""
    bx_progress_signal = pyqtSignal(str)
    bx_item_finished_signal = pyqtSignal(str, bool, str)
    bx_finished_signal = pyqtSignal(dict)
    bx_error_signal = pyqtSignal(str)

    def __init__(self, items):
        super().__init__()
        self.items = list(items)

    def run(self):
        summary = {"executed": 0, "failed": 0, "skipped": 0}
        try:
            for item in self.items:
                title = item.get("title", "优化项")
                command = item.get("command", "")
                self.bx_progress_signal.emit(f"正在处理: {title}")
                if not command:
                    summary["skipped"] += 1
                    self.bx_item_finished_signal.emit(title, False, "该项目仅展示或检查")
                    continue

                if not sys.platform.startswith("win"):
                    summary["executed"] += 1
                    self.bx_item_finished_signal.emit(
                        title,
                        True,
                        f"将在 Windows 上执行: {command}",
                    )
                    continue

                result = subprocess.run(
                    command,
                    shell=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                    timeout=120,
                    **hidden_windows_subprocess_kwargs(),
                )
                output = "\n".join(
                    part.strip()
                    for part in (result.stdout, result.stderr)
                    if part and part.strip()
                )
                if result.returncode == 0:
                    summary["executed"] += 1
                    self.bx_item_finished_signal.emit(title, True, output or "已处理")
                else:
                    summary["failed"] += 1
                    self.bx_item_finished_signal.emit(
                        title,
                        False,
                        output or f"命令返回 {result.returncode}",
                    )
            self.bx_finished_signal.emit(summary)
        except Exception as exc:  # pragma: no cover - depends on host commands
            self.bx_error_signal.emit(str(exc))


# 侧边栏导航项：(标签, 页面构建方法名)
NAV_ITEMS = [
    ("C盘清理", "_build_clean_page"),
    ("系统优化", "_build_optimize_page"),
    ("BX(优化)", "_build_bx_page"),
    ("软件卸载", "_build_uninstall_page"),
    ("文件管理", "_build_file_page"),
    ("系统修复", "_build_repair_page"),
    ("账号会员", "_build_account_page"),
]


class CleanerMainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.cleaner = CleanerLogic()
        self.scan_results = {}
        self.selected_items = []
        self.cleanable_items = []
        self.app_icon = self._load_app_icon()
        self.icon_provider = QFileIconProvider()
        self.nav_buttons = []
        self.optimizer_tables = {}
        self.uninstall_apps = []
        self.file_scan_root = ""
        self.file_large_items = []
        self.file_duplicate_groups = []
        self.file_scan_thread = None
        self.defrag_thread = None
        self.fragment_grid_cells = []
        self.bx_mode = "basic"
        self.bx_active_category = "基础"
        self.bx_category_buttons = {}
        self.bx_thread = None
        self.active_animations = []
        self.account_service = LocalAccountService()
        self.account_state = self.account_service.current_state()

        self.init_ui()

    def _load_app_icon(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "icons",
            "cleaner.ico",
        )
        return QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    def _load_logo_pixmap(self):
        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "icons",
            "cleaner.png",
        )
        return QPixmap(logo_path) if os.path.exists(logo_path) else QPixmap()

    # ------------------------------------------------------------------
    # 侧边栏
    # ------------------------------------------------------------------
    def _make_sidebar_button(self, text, active=False):
        button = QPushButton(text)
        button.setObjectName("sidebarButtonActive" if active else "sidebarButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumWidth(148)
        return button

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(196)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(8)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)

        logo_label = QLabel()
        logo_label.setFixedSize(44, 44)
        logo_pixmap = self._load_logo_pixmap()
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        elif not self.app_icon.isNull():
            logo_label.setPixmap(self.app_icon.pixmap(QSize(44, 44)))
        else:
            logo_label.setText("C")
            logo_label.setAlignment(Qt.AlignCenter)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(2)
        brand_title = QLabel("C盘")
        brand_title.setObjectName("brandTitle")
        brand_subtitle = QLabel("清理精灵")
        brand_subtitle.setObjectName("brandSubtitle")
        brand_col.addWidget(brand_title)
        brand_col.addWidget(brand_subtitle)

        logo_row.addWidget(logo_label)
        logo_row.addLayout(brand_col, 1)
        layout.addLayout(logo_row)
        layout.addSpacing(14)

        self.nav_buttons = []
        for index, (text, _builder) in enumerate(NAV_ITEMS):
            button = self._make_sidebar_button(text, active=(index == 0))
            button.clicked.connect(lambda _checked, i=index: self._select_page(i))
            layout.addWidget(button)
            self.nav_buttons.append(button)

        layout.addStretch(1)

        footer = QLabel("推荐模式\n路径统计")
        footer.setObjectName("sidebarFooter")
        footer.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        layout.addWidget(footer)

        return sidebar

    def _select_page(self, index):
        """切换主区域页面并更新侧边栏选中态。"""
        previous_index = self.stack.currentIndex()
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setObjectName(
                "sidebarButtonActive" if i == index else "sidebarButton"
            )
            # 重新应用样式表，让 objectName 变化即时生效
            button.style().unpolish(button)
            button.style().polish(button)
        if index != previous_index:
            self.animate_page_transition(self.stack.currentWidget())
            if 0 <= index < len(self.nav_buttons):
                self.animate_status_pulse(self.nav_buttons[index])

    def page_index_for_label(self, label):
        for index, (text, _builder) in enumerate(NAV_ITEMS):
            if text == label:
                return index
        return 0

    # ------------------------------------------------------------------
    # 通用小组件
    # ------------------------------------------------------------------
    def run_opacity_animation(self, widget, start_opacity, end_opacity, duration):
        if widget is None:
            return None

        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(start_opacity)
        widget.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(duration)
        animation.setStartValue(start_opacity)
        animation.setEndValue(end_opacity)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        self.active_animations.append(animation)

        def cleanup():
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
            if animation in self.active_animations:
                self.active_animations.remove(animation)

        animation.finished.connect(cleanup)
        animation.start()
        return animation

    def animate_page_transition(self, widget):
        """页面切换只做短 opacity 动画，避免触发布局重算。"""
        return self.run_opacity_animation(widget, 0.62, 1.0, 160)

    def animate_status_pulse(self, widget):
        """给按钮/状态文案一个轻量反馈，不改变尺寸。"""
        return self.run_opacity_animation(widget, 0.55, 1.0, 140)

    def _make_stat_block(self, title, value="--", value_object_name="statValue"):
        frame = QFrame()
        frame.setObjectName("statBlock")
        frame.setMinimumWidth(112)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        value_label = QLabel(value)
        value_label.setObjectName(value_object_name)

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return frame, value_label

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(APP_DISPLAY_NAME or APP_NAME)
        self.setMinimumSize(1040, 680)
        self.resize(1120, 720)
        if not self.app_icon.isNull():
            self.setWindowIcon(self.app_icon)
        self.setStyleSheet(APP_QSS)

        central_widget = QWidget()
        central_widget.setObjectName("appRoot")

        shell_layout = QHBoxLayout(central_widget)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        shell_layout.addWidget(self._build_sidebar())

        # 主区域：多页面堆叠，侧边栏点击切换
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        for _text, builder_name in NAV_ITEMS:
            page = getattr(self, builder_name)()
            self.stack.addWidget(page)
        shell_layout.addWidget(self.stack, 1)

        self.setCentralWidget(central_widget)

        # 初始化磁盘信息
        self.update_disk_info()

    # ------------------------------------------------------------------
    # 页面：C盘清理
    # ------------------------------------------------------------------
    def _build_clean_page(self):
        content_area = QWidget()
        content_area.setObjectName("contentArea")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(20, 18, 20, 18)
        content_layout.setSpacing(14)

        hero_panel = QFrame()
        hero_panel.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero_panel)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(18)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(6)

        hero_title = QLabel(APP_DISPLAY_NAME)
        hero_title.setObjectName("heroTitle")
        hero_subtitle = QLabel("扫描缓存、日志、更新残留、EdgeCore 和 AppData 路径")
        hero_subtitle.setObjectName("heroSubtitle")
        self.disk_info_label = QLabel("C盘使用情况: 正在加载...")
        self.disk_info_label.setObjectName("diskInfo")
        self.disk_info_label.setWordWrap(True)

        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_subtitle)
        hero_text.addWidget(self.disk_info_label)
        hero_layout.addLayout(hero_text, 2)

        stat_grid = QGridLayout()
        stat_grid.setContentsMargins(0, 0, 0, 0)
        stat_grid.setHorizontalSpacing(10)
        stat_grid.setVerticalSpacing(10)

        total_block, self.total_value_label = self._make_stat_block("总空间")
        used_block, self.used_value_label = self._make_stat_block("已用空间")
        free_block, self.free_value_label = self._make_stat_block("可用空间")
        cleanable_block, self.cleanable_value_label = self._make_stat_block(
            "可释放", "0 B", value_object_name="cleanableValue"
        )

        stat_grid.addWidget(total_block, 0, 0)
        stat_grid.addWidget(used_block, 0, 1)
        stat_grid.addWidget(free_block, 1, 0)
        stat_grid.addWidget(cleanable_block, 1, 1)
        hero_layout.addLayout(stat_grid, 3)

        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)

        self.scan_button = QPushButton("一键扫描")
        self.scan_button.setObjectName("scanPrimaryButton")
        self.scan_button.setCursor(Qt.PointingHandCursor)
        if not self.app_icon.isNull():
            self.scan_button.setIcon(self.app_icon)
            self.scan_button.setIconSize(QSize(18, 18))
        self.scan_button.clicked.connect(self.start_scan)

        self.clean_all_button = QPushButton("一键清理")
        self.clean_all_button.setObjectName("cleanSecondaryButton")
        self.clean_all_button.setCursor(Qt.PointingHandCursor)
        self.clean_all_button.setToolTip("清理全部可清理项，自动跳过仅统计路径")
        self.clean_all_button.setEnabled(False)
        self.clean_all_button.clicked.connect(self.start_clean_all)

        self.clean_button = QPushButton("清理选中")
        self.clean_button.setObjectName("cleanSecondaryButton")
        self.clean_button.setCursor(Qt.PointingHandCursor)
        self.clean_button.setToolTip("只清理当前勾选的可清理项")
        self.clean_button.setEnabled(False)
        self.clean_button.clicked.connect(self.start_clean)

        action_layout.addWidget(self.scan_button)
        action_layout.addWidget(self.clean_all_button)
        action_layout.addWidget(self.clean_button)
        action_layout.addStretch(1)
        hero_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("scanProgress")
        self.progress_bar.setVisible(False)

        self.current_scan_path_label = QLabel("当前扫描: --")
        self.current_scan_path_label.setObjectName("scanPathLabel")
        self.current_scan_path_label.setVisible(False)
        self.current_scan_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        result_card = QFrame()
        result_card.setObjectName("resultCard")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(16, 14, 16, 14)
        result_layout.setSpacing(10)

        result_header = QHBoxLayout()
        result_header.setSpacing(12)

        result_title = QLabel("扫描结果")
        result_title.setObjectName("resultTitle")
        self.result_summary_label = QLabel("等待扫描")
        self.result_summary_label.setObjectName("resultSummary")

        result_header.addWidget(result_title)
        result_header.addWidget(self.result_summary_label, 1)

        self.recommended_checkbox = QCheckBox("推荐")
        self.recommended_checkbox.setToolTip("推荐模式只清理相对安全的缓存、日志、更新残留")
        self.recommended_checkbox.setChecked(True)
        self.recommended_checkbox.stateChanged.connect(self.on_clean_mode_changed)

        self.professional_checkbox = QCheckBox("专业")
        self.professional_checkbox.setToolTip("专业模式只清理 WinSxS、WindowsApps、Defender、EdgeCore 等专业项")
        self.professional_checkbox.stateChanged.connect(self.on_clean_mode_changed)

        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.setToolTip("全选模式包含推荐项和专业项")
        self.select_all_checkbox.setEnabled(False)
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)

        self.simulate_checkbox = QCheckBox("模拟模式")
        self.simulate_checkbox.setToolTip("默认不实际删除文件")
        self.simulate_checkbox.setChecked(True)

        self.backup_checkbox = QCheckBox("删除前备份")
        self.backup_checkbox.setChecked(True)

        backup_dir_button = QPushButton("备份目录")
        backup_dir_button.setObjectName("cleanSecondaryButton")
        backup_dir_button.setToolTip("选择清理前备份保存目录")
        backup_dir_button.clicked.connect(self.browse_backup_dir)

        backup_manager_button = QPushButton("备份管理")
        backup_manager_button.setObjectName("cleanSecondaryButton")
        backup_manager_button.setToolTip("查看、恢复、删除和清理旧备份")
        backup_manager_button.clicked.connect(self.open_backup_manager)

        result_header.addWidget(self.recommended_checkbox)
        result_header.addWidget(self.professional_checkbox)
        result_header.addWidget(self.select_all_checkbox)
        result_header.addWidget(self.simulate_checkbox)
        result_header.addWidget(self.backup_checkbox)
        result_header.addWidget(backup_dir_button)
        result_header.addWidget(backup_manager_button)
        result_layout.addLayout(result_header)

        self.results_tree = QTreeWidget()
        self.results_tree.setObjectName("resultTree")
        self.results_tree.setHeaderLabels(["项目", "大小", "路径"])
        self.results_tree.setColumnWidth(0, 320)
        self.results_tree.setColumnWidth(1, 110)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setIndentation(22)
        self.results_tree.setUniformRowHeights(True)
        self.results_tree.header().setStretchLastSection(True)
        self.results_tree.itemChanged.connect(self.on_item_changed)
        result_layout.addWidget(self.results_tree, 1)

        status_strip = QFrame()
        status_strip.setObjectName("statusStrip")
        status_layout = QHBoxLayout(status_strip)
        status_layout.setContentsMargins(14, 8, 14, 8)
        status_layout.setSpacing(12)

        self.status_label = QLabel("准备扫描 C 盘可清理路径")
        self.status_label.setObjectName("statusLabel")
        self.selected_summary_label = QLabel("已选 0 项 / 0 B")
        self.selected_summary_label.setObjectName("selectedSummary")
        self.selected_summary_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.selected_summary_label)

        content_layout.addWidget(hero_panel)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(self.current_scan_path_label)
        content_layout.addWidget(result_card, 1)
        content_layout.addWidget(status_strip)

        return content_area

    # ------------------------------------------------------------------
    # 页面：功能中心（系统优化 / 软件卸载 / 文件管理）
    # ------------------------------------------------------------------
    def _build_feature_page(self, title, subtitle, cards):
        """构建一个带功能卡片网格的页面。cards 为 (标题, 描述, 按钮文本, 处理函数)。"""
        page = QWidget()
        page.setObjectName("contentArea")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)

        header = QVBoxLayout()
        header.setSpacing(6)
        page_title = QLabel(title)
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel(subtitle)
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("pageScrollInner")
        grid = QGridLayout(inner)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        columns = 2
        for index, (card_title, card_desc, button_text, handler) in enumerate(cards):
            row, col = divmod(index, columns)
            grid.addWidget(
                self._make_feature_card(card_title, card_desc, button_text, handler),
                row,
                col,
            )
        grid.setRowStretch((len(cards) + columns - 1) // columns, 1)
        for col in range(columns):
            grid.setColumnStretch(col, 1)

        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        return page

    def _make_feature_card(self, title, desc, button_text, handler):
        card = QFrame()
        card.setObjectName("featureCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("featureCardTitle")
        desc_label = QLabel(desc)
        desc_label.setObjectName("featureCardDesc")
        desc_label.setWordWrap(True)

        button = QPushButton(button_text)
        button.setObjectName("featureButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(handler)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch(1)
        button_row = QHBoxLayout()
        button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        return card

    def _build_optimize_page(self):
        page = QWidget()
        page.setObjectName("contentArea")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(5)
        page_title = QLabel("系统优化")
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel("开机启动、运行内存、系统优化、隐私清理、注册表清理都在软件内查看和处理。")
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        self.optimizer_tabs = QTabWidget()
        self.optimizer_tabs.setObjectName("optimizerTabs")
        self.optimizer_tables = {}

        tab_specs = [
            ("开机加速", ["启动项", "启动位置", "操作"], self.populate_startup_items()),
            ("运行内存", ["进程名称", "内存使用率", "CPU使用率", "操作"], self.populate_memory_items()),
            ("系统优化", ["系统优化项", "操作"], self.populate_optimization_items()),
            ("隐私清理", ["电脑隐私记录", "操作"], self.populate_privacy_items()),
            ("注册表清理", ["注册表清理项", "操作"], self.populate_registry_items()),
        ]

        for tab_name, headers, rows in tab_specs:
            table = self._make_optimizer_table(headers)
            self.optimizer_tables[tab_name] = table
            self._populate_optimizer_table(table, rows)
            self.optimizer_tabs.addTab(table, tab_name)

        outer.addWidget(self.optimizer_tabs, 1)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(12)
        self.optimizer_select_all = QCheckBox("全选")
        self.optimizer_select_all.stateChanged.connect(self.set_current_optimizer_checked)
        self.optimizer_recommended_checkbox = QCheckBox("推荐")
        self.optimizer_recommended_checkbox.setChecked(True)
        self.optimizer_recommended_checkbox.stateChanged.connect(self.apply_optimizer_recommended_filter)

        refresh_button = QPushButton("刷新")
        refresh_button.setObjectName("cleanSecondaryButton")
        refresh_button.clicked.connect(self.refresh_optimizer_tab)

        optimize_button = QPushButton("一键优化")
        optimize_button.setObjectName("scanPrimaryButton")
        optimize_button.clicked.connect(self.apply_current_optimization_tab)

        action_bar.addWidget(self.optimizer_select_all)
        action_bar.addWidget(self.optimizer_recommended_checkbox)
        action_bar.addStretch(1)
        action_bar.addWidget(refresh_button)
        action_bar.addWidget(optimize_button)
        outer.addLayout(action_bar)

        self.optimizer_status_label = QLabel("准备处理系统优化项。")
        self.optimizer_status_label.setObjectName("statusLabel")
        outer.addWidget(self.optimizer_status_label)

        return page

    def _build_bx_page(self):
        page = QWidget()
        page.setObjectName("contentArea")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(5)
        page_title = QLabel("BX(优化)")
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel("参考 BoosterX 的基础设置工作流，提供基本和最佳两个模式，直接在软件内应用 Windows 优化项。")
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)

        category_panel = QFrame()
        category_panel.setObjectName("featureCard")
        category_panel.setFixedWidth(240)
        category_layout = QVBoxLayout(category_panel)
        category_layout.setContentsMargins(16, 16, 16, 16)
        category_layout.setSpacing(8)

        category_title = QLabel("我的调整")
        category_title.setObjectName("featureCardTitle")
        category_layout.addWidget(category_title)

        self.bx_category_buttons = {}
        for category in self.bx_category_order():
            button = QPushButton(category)
            button.setObjectName("featureButton" if category == self.bx_active_category else "cleanSecondaryButton")
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(34)
            button.clicked.connect(lambda _checked=False, target=category: self.select_bx_category(target))
            category_layout.addWidget(button)
            self.bx_category_buttons[category] = button

        category_layout.addSpacing(12)
        quick_title = QLabel("快速方法")
        quick_title.setObjectName("featureCardTitle")
        category_layout.addWidget(quick_title)

        quick_basic_button = QPushButton("基本")
        quick_basic_button.setObjectName("cleanSecondaryButton")
        quick_basic_button.clicked.connect(lambda: self.select_bx_mode("basic"))
        quick_best_button = QPushButton("最佳")
        quick_best_button.setObjectName("scanPrimaryButton")
        quick_best_button.clicked.connect(lambda: self.select_bx_mode("best"))
        category_layout.addWidget(quick_basic_button)
        category_layout.addWidget(quick_best_button)
        category_layout.addStretch(1)

        main_panel = QVBoxLayout()
        main_panel.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("featureCard")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        toolbar_title = QLabel("基础设置")
        toolbar_title.setObjectName("featureCardTitle")
        self.bx_basic_button = QPushButton("基本")
        self.bx_basic_button.setMinimumWidth(96)
        self.bx_basic_button.clicked.connect(lambda: self.select_bx_mode("basic"))
        self.bx_best_button = QPushButton("最佳")
        self.bx_best_button.setMinimumWidth(96)
        self.bx_best_button.clicked.connect(lambda: self.select_bx_mode("best"))
        bx_refresh_button = QPushButton("更新")
        bx_refresh_button.setObjectName("cleanSecondaryButton")
        bx_refresh_button.setMinimumWidth(96)
        bx_refresh_button.clicked.connect(self.refresh_bx_page)
        self.bx_apply_button = QPushButton("应用")
        self.bx_apply_button.setObjectName("scanPrimaryButton")
        self.bx_apply_button.setMinimumWidth(112)
        self.bx_apply_button.clicked.connect(self.apply_bx_optimization)

        toolbar_layout.addWidget(toolbar_title)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.bx_basic_button)
        toolbar_layout.addWidget(self.bx_best_button)
        toolbar_layout.addWidget(bx_refresh_button)
        toolbar_layout.addWidget(self.bx_apply_button)
        main_panel.addWidget(toolbar)

        self.bx_table = QTreeWidget()
        self.bx_table.setObjectName("optimizerTable")
        self.bx_table.setColumnCount(4)
        self.bx_table.setHeaderLabels(["优化项", "状态", "风险", "说明"])
        self.bx_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.bx_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.bx_table.setAlternatingRowColors(True)
        self.bx_table.setIconSize(QSize(20, 20))
        self.bx_table.setRootIsDecorated(True)
        self.bx_table.setItemsExpandable(True)
        self.bx_table.itemChanged.connect(lambda _item, _column: self.update_bx_status())
        bx_header = self.bx_table.header()
        bx_header.setMinimumSectionSize(86)
        bx_header.setSectionResizeMode(0, QHeaderView.Stretch)
        bx_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        bx_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        bx_header.setSectionResizeMode(3, QHeaderView.Stretch)
        main_panel.addWidget(self.bx_table, 1)

        self.bx_status_label = QLabel("基本模式已就绪。")
        self.bx_status_label.setObjectName("statusLabel")
        main_panel.addWidget(self.bx_status_label)

        body.addWidget(category_panel)
        body.addLayout(main_panel, 1)
        outer.addLayout(body, 1)

        self.update_bx_mode_buttons()
        self.populate_bx_categories()
        self.populate_bx_items()
        return page

    def bx_category_order(self):
        return [
            "我的调整",
            "基础",
            "安全性",
            "自定义",
            "Nvidia 面板",
            "电源管理",
            "应用程序移除",
            "清理",
            "隐私",
            "调整",
            "自启动",
            "中断",
            "设备",
            "网络适配器",
            "任务",
            "组件",
            "过时",
        ]

    def bx_catalog(self):
        return [
            {
                "category": "基础",
                "title": "自动更新地图",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "关闭离线地图自动下载和更新。",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Maps" /v AutoDownloadAndUpdateMapData /t REG_DWORD /d 0 /f',
                "icon_hint": "windows",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "商店应用程序的自动更新",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "减少 Microsoft Store 后台自动更新占用。",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\WindowsStore" /v AutoDownload /t REG_DWORD /d 2 /f',
                "icon_hint": "windows",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "全局全屏优化（FSO）",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "禁用游戏全屏优化，降低部分游戏输入延迟。",
                "command": r'reg add "HKCU\System\GameConfigStore" /v GameDVR_FSEBehaviorMode /t REG_DWORD /d 2 /f',
                "icon_hint": "game",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "游戏栏",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "关闭 Game DVR 和游戏栏后台录制。",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR" /v AppCaptureEnabled /t REG_DWORD /d 0 /f',
                "icon_hint": "game",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "交付优化",
                "target_state": "将被调整",
                "risk": "基础",
                "description": "停止交付优化服务并改为按需启动。",
                "command": r'cmd /c "sc stop DoSvc & sc config DoSvc start= demand"',
                "icon_hint": "update",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "加速 Microsoft Edge 启动和后台运行",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "关闭 Edge 启动增强和后台运行策略。",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v StartupBoostEnabled /t REG_DWORD /d 0 /f & reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v BackgroundModeEnabled /t REG_DWORD /d 0 /f',
                "icon_hint": "edge",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "索引",
                "target_state": "将被禁用",
                "risk": "谨慎",
                "description": "停用 Windows Search 索引服务，适合低配或游戏环境。",
                "command": r'cmd /c "sc stop WSearch & sc config WSearch start= disabled"',
                "icon_hint": "search",
                "basic": False,
                "best": True,
            },
            {
                "category": "基础",
                "title": "SysMain（预取、Superfetch...）",
                "target_state": "将被禁用",
                "risk": "谨慎",
                "description": "停用 SysMain 预取服务，SSD 游戏机常用。",
                "command": r'cmd /c "sc stop SysMain & sc config SysMain start= disabled"',
                "icon_hint": "windows",
                "basic": False,
                "best": True,
            },
            {
                "category": "基础",
                "title": "打印服务",
                "target_state": "将被禁用",
                "risk": "谨慎",
                "description": "没有打印机时可停用 Print Spooler。",
                "command": r'cmd /c "sc stop Spooler & sc config Spooler start= disabled"',
                "icon_hint": "printer",
                "basic": False,
                "best": True,
            },
            {
                "category": "基础",
                "title": "诊断驱动程序",
                "target_state": "将被禁用",
                "risk": "谨慎",
                "description": "停用 Diagnostic Policy Service 后台诊断。",
                "command": r'cmd /c "sc stop DPS & sc config DPS start= disabled"',
                "icon_hint": "driver",
                "basic": False,
                "best": True,
            },
            {
                "category": "基础",
                "title": "暂停 Windows 更新",
                "target_state": "将被调整",
                "risk": "谨慎",
                "description": "停止 Windows Update 并设置为按需启动。",
                "command": r'cmd /c "sc stop wuauserv & sc config wuauserv start= demand"',
                "icon_hint": "update",
                "basic": False,
                "best": True,
            },
            {
                "category": "基础",
                "title": "OneDrive",
                "target_state": "将被禁用",
                "risk": "谨慎",
                "description": "通过策略禁用 OneDrive 同步客户端。",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\OneDrive" /v DisableFileSyncNGSC /t REG_DWORD /d 1 /f',
                "icon_hint": "onedrive",
                "basic": False,
                "best": True,
            },
            {
                "category": "基础",
                "title": "HAGS",
                "target_state": "将被启用",
                "risk": "谨慎",
                "description": "启用硬件加速 GPU 调度，部分显卡需重启生效。",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f',
                "icon_hint": "nvidia",
                "basic": False,
                "best": True,
            },
            {
                "category": "安全性",
                "title": "SmartScreen 后台提示",
                "target_state": "仅检查",
                "risk": "谨慎",
                "description": "安全相关项目默认不直接处理，避免降低防护。",
                "command": "",
                "icon_hint": "defender",
                "basic": False,
                "best": False,
            },
            {
                "category": "隐私",
                "title": "遥测和体验改善",
                "target_state": "将被限制",
                "risk": "基础",
                "description": "限制 Windows 遥测等级。",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection" /v AllowTelemetry /t REG_DWORD /d 0 /f',
                "icon_hint": "privacy",
                "basic": True,
                "best": True,
            },
            {
                "category": "自启动",
                "title": "Edge 自动启动批准项",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "禁止 Edge 作为用户启动批准项自动运行。",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" /v MicrosoftEdgeAutoLaunch /t REG_BINARY /d 030000000000000000000000 /f',
                "icon_hint": "edge",
                "basic": False,
                "best": True,
            },
        ]

    def bx_mode_items(self):
        if self.bx_mode == "best":
            return [item for item in self.bx_catalog() if item.get("best")]
        return [item for item in self.bx_catalog() if item.get("basic")]

    def bx_visible_items(self):
        items = self.bx_mode_items()
        if self.bx_active_category == "我的调整":
            return items
        return [item for item in items if item.get("category") == self.bx_active_category]

    def populate_bx_categories(self):
        if not self.bx_category_buttons:
            return
        mode_items = self.bx_mode_items()
        for category, button in self.bx_category_buttons.items():
            if category == "我的调整":
                count = len(mode_items)
            else:
                count = sum(1 for item in mode_items if item.get("category") == category)
            button.setText(f"{category}    {count}" if count else category)
            button.setObjectName("featureButton" if category == self.bx_active_category else "cleanSecondaryButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def select_bx_category(self, category):
        self.bx_active_category = category
        self.populate_bx_categories()
        self.populate_bx_items()

    def update_bx_mode_buttons(self):
        if not hasattr(self, "bx_basic_button"):
            return
        self.bx_basic_button.setObjectName("scanPrimaryButton" if self.bx_mode == "basic" else "cleanSecondaryButton")
        self.bx_best_button.setObjectName("scanPrimaryButton" if self.bx_mode == "best" else "cleanSecondaryButton")
        for button in (self.bx_basic_button, self.bx_best_button):
            button.style().unpolish(button)
            button.style().polish(button)

    def select_bx_mode(self, mode):
        if mode == "best":
            self.bx_mode = "best"
        else:
            self.bx_mode = "basic"
        self.update_bx_mode_buttons()
        self.populate_bx_categories()
        self.populate_bx_items()

    def refresh_bx_page(self):
        self.populate_bx_categories()
        self.populate_bx_items()
        if hasattr(self, "bx_status_label"):
            self.bx_status_label.setText("BX(优化) 项目已刷新。")
            self.animate_status_pulse(self.bx_status_label)

    def populate_bx_items(self):
        if not hasattr(self, "bx_table"):
            return
        items = self.bx_visible_items()
        self.bx_table.setUpdatesEnabled(False)
        self.bx_table.blockSignals(True)
        self.bx_table.clear()
        for item in items:
            row = QTreeWidgetItem()
            row.setText(0, item["title"])
            row.setText(1, item["target_state"])
            row.setText(2, item["risk"])
            row.setText(3, item["description"])
            row.setToolTip(0, item["title"])
            row.setToolTip(3, item["description"])
            row.setFlags(row.flags() | Qt.ItemIsUserCheckable)
            row.setCheckState(0, Qt.Checked)
            row.setData(0, Qt.UserRole, item)
            icon = self.category_icon_for_name(item.get("icon_hint") or item["title"])
            if not icon.isNull():
                row.setIcon(0, icon)

            detail = QTreeWidgetItem(row)
            detail.setText(0, "命令")
            detail.setText(1, item.get("command") or "仅展示/检查")
            detail.setText(2, item.get("category", ""))
            detail.setText(3, "执行后部分项目需要重启或重新登录生效。")
            detail.setToolTip(1, item.get("command") or "仅展示/检查")
            row.setExpanded(False)
            self.bx_table.addTopLevelItem(row)
        self.bx_table.blockSignals(False)
        self.bx_table.setUpdatesEnabled(True)
        self.update_bx_status()

    def selected_bx_items(self):
        if not hasattr(self, "bx_table"):
            return []
        items = []
        for index in range(self.bx_table.topLevelItemCount()):
            row = self.bx_table.topLevelItem(index)
            if row and row.checkState(0) == Qt.Checked:
                payload = row.data(0, Qt.UserRole)
                if payload:
                    items.append(payload)
        return items

    def update_bx_status(self):
        if not hasattr(self, "bx_status_label"):
            return
        selected_count = len(self.selected_bx_items())
        total_count = self.bx_table.topLevelItemCount() if hasattr(self, "bx_table") else 0
        mode_name = "最佳" if self.bx_mode == "best" else "基本"
        self.bx_status_label.setText(
            f"{mode_name}模式 / {self.bx_active_category} / 已勾选 {selected_count} 项 / 共 {total_count} 项"
        )

    def apply_bx_optimization(self):
        if self.bx_thread and self.bx_thread.isRunning():
            self.bx_status_label.setText("BX(优化) 正在执行，请稍后。")
            self.animate_status_pulse(self.bx_status_label)
            return

        items = self.selected_bx_items()
        if not items:
            self.bx_status_label.setText("请先勾选需要应用的 BX 优化项。")
            self.animate_status_pulse(self.bx_status_label)
            return

        self.set_bx_busy(True)
        self.bx_status_label.setText(f"开始应用 BX(优化) {len(items)} 项...")
        self.bx_thread = BXOptimizationThread(items)
        self.bx_thread.bx_progress_signal.connect(self.on_bx_progress)
        self.bx_thread.bx_item_finished_signal.connect(self.on_bx_item_finished)
        self.bx_thread.bx_finished_signal.connect(self.on_bx_finished)
        self.bx_thread.bx_error_signal.connect(self.on_bx_error)
        self.bx_thread.finished.connect(self.bx_thread.deleteLater)
        self.bx_thread.start()

    def set_bx_busy(self, busy):
        if hasattr(self, "bx_apply_button"):
            self.bx_apply_button.setEnabled(not busy)
            self.bx_apply_button.setText("应用中..." if busy else "应用")
        if hasattr(self, "bx_table"):
            self.bx_table.setEnabled(not busy)
        if hasattr(self, "bx_basic_button"):
            self.bx_basic_button.setEnabled(not busy)
            self.bx_best_button.setEnabled(not busy)
        for button in getattr(self, "bx_category_buttons", {}).values():
            button.setEnabled(not busy)

    def on_bx_progress(self, message):
        self.bx_status_label.setText(message)

    def on_bx_item_finished(self, title, success, message):
        for index in range(self.bx_table.topLevelItemCount()):
            row = self.bx_table.topLevelItem(index)
            if row and row.text(0) == title:
                row.setText(1, "已应用" if success else "跳过/失败")
                row.setToolTip(1, message)
                break

    def on_bx_finished(self, summary):
        self.set_bx_busy(False)
        self.bx_thread = None
        self.bx_status_label.setText(
            f"BX(优化) 完成: 已处理 {summary.get('executed', 0)} 项，"
            f"跳过 {summary.get('skipped', 0)} 项，失败 {summary.get('failed', 0)} 项。"
        )
        self.animate_status_pulse(self.bx_status_label)

    def on_bx_error(self, message):
        self.set_bx_busy(False)
        self.bx_thread = None
        self.bx_status_label.setText(f"BX(优化) 失败: {message}")
        QMessageBox.warning(self, "BX(优化)", f"执行失败:\n{message}")

    def _build_uninstall_page(self):
        page = QWidget()
        page.setObjectName("contentArea")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(5)
        page_title = QLabel("软件卸载")
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel("读取 Windows 卸载注册表，在软件内查看、选择并调用目标程序的卸载命令。")
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        reload_button = QPushButton("刷新列表")
        reload_button.setObjectName("cleanSecondaryButton")
        reload_button.setMinimumWidth(96)
        reload_button.clicked.connect(lambda: self.load_installed_apps(show_message=True))
        uninstall_button = QPushButton("卸载选中")
        uninstall_button.setObjectName("scanPrimaryButton")
        uninstall_button.setMinimumWidth(96)
        uninstall_button.clicked.connect(self.uninstall_selected_app)
        toolbar.addStretch(1)
        toolbar.addWidget(reload_button)
        toolbar.addWidget(uninstall_button)
        outer.addLayout(toolbar)

        self.uninstall_table = QTableWidget()
        self.uninstall_table.setObjectName("uninstallTable")
        self.uninstall_table.setColumnCount(5)
        self.uninstall_table.setHorizontalHeaderLabels(["软件名称", "发布者", "版本", "安装位置", "操作"])
        self.uninstall_table.verticalHeader().setVisible(False)
        self.uninstall_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.uninstall_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.uninstall_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.uninstall_table.setAlternatingRowColors(True)
        self.uninstall_table.setIconSize(QSize(20, 20))
        header_view = self.uninstall_table.horizontalHeader()
        header_view.setMinimumSectionSize(86)
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.Fixed)
        self.uninstall_table.setColumnWidth(4, 96)
        outer.addWidget(self.uninstall_table, 1)

        self.uninstall_status_label = QLabel("正在读取软件列表...")
        self.uninstall_status_label.setObjectName("statusLabel")
        outer.addWidget(self.uninstall_status_label)

        self.load_installed_apps(show_message=False)
        return page

    def _build_account_page(self):
        page = QWidget()
        page.setObjectName("contentArea")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)

        header = QVBoxLayout()
        header.setSpacing(5)
        page_title = QLabel("账号会员")
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel("在软件内登录、注册并兑换会员卡密；离线时使用本地账号状态保存。")
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        status_card = QFrame()
        status_card.setObjectName("featureCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(18, 16, 18, 16)
        status_layout.setSpacing(8)

        self.account_status_title = QLabel("未登录")
        self.account_status_title.setObjectName("featureCardTitle")
        self.account_status_detail = QLabel("登录后可兑换会员卡密。")
        self.account_status_detail.setObjectName("featureCardDesc")
        self.account_status_detail.setWordWrap(True)
        self.account_plan_label = QLabel("当前权益: Guest")
        self.account_plan_label.setObjectName("statusLabel")
        self.account_plan_label.setWordWrap(True)

        self.account_logout_button = QPushButton("退出登录")
        self.account_logout_button.setObjectName("cleanSecondaryButton")
        self.account_logout_button.setMinimumWidth(96)
        self.account_logout_button.clicked.connect(self.logout_account)

        status_layout.addWidget(self.account_status_title)
        status_layout.addWidget(self.account_status_detail)
        status_layout.addWidget(self.account_plan_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.account_logout_button, 0, Qt.AlignLeft)

        auth_card = QFrame()
        auth_card.setObjectName("featureCard")
        auth_layout = QVBoxLayout(auth_card)
        auth_layout.setContentsMargins(18, 16, 18, 16)
        auth_layout.setSpacing(9)

        auth_title = QLabel("登录 / 注册")
        auth_title.setObjectName("featureCardTitle")
        self.account_email_input = QLineEdit()
        self.account_email_input.setPlaceholderText("邮箱")
        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText("昵称（注册时使用）")
        self.account_password_input = QLineEdit()
        self.account_password_input.setPlaceholderText("密码，至少 6 位")
        self.account_password_input.setEchoMode(QLineEdit.Password)

        auth_actions = QHBoxLayout()
        login_button = QPushButton("登录")
        login_button.setObjectName("scanPrimaryButton")
        login_button.setMinimumWidth(96)
        login_button.clicked.connect(self.login_account)
        register_button = QPushButton("注册")
        register_button.setObjectName("cleanSecondaryButton")
        register_button.setMinimumWidth(96)
        register_button.clicked.connect(self.register_account)
        auth_actions.addWidget(login_button)
        auth_actions.addWidget(register_button)
        auth_actions.addStretch(1)

        auth_layout.addWidget(auth_title)
        auth_layout.addWidget(self.account_email_input)
        auth_layout.addWidget(self.account_name_input)
        auth_layout.addWidget(self.account_password_input)
        auth_layout.addLayout(auth_actions)

        cards_row.addWidget(status_card, 1)
        cards_row.addWidget(auth_card, 1)
        outer.addLayout(cards_row)

        card_box = QFrame()
        card_box.setObjectName("featureCard")
        card_layout = QVBoxLayout(card_box)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(9)

        card_title = QLabel("会员卡密")
        card_title.setObjectName("featureCardTitle")
        card_desc = QLabel("登录后输入卡密兑换会员。测试卡密: " + " / ".join(DEMO_CARD_CODES.keys()))
        card_desc.setObjectName("featureCardDesc")
        card_desc.setWordWrap(True)

        card_row = QHBoxLayout()
        card_row.setSpacing(10)
        self.card_code_input = QLineEdit()
        self.card_code_input.setPlaceholderText("输入会员卡密，例如 WINCLEANER-VIP-30D")
        redeem_button = QPushButton("兑换卡密")
        redeem_button.setObjectName("scanPrimaryButton")
        redeem_button.setMinimumWidth(112)
        redeem_button.clicked.connect(self.redeem_account_card)
        card_row.addWidget(self.card_code_input, 1)
        card_row.addWidget(redeem_button)

        self.account_message_label = QLabel("本地测试卡密可直接兑换，后续可切换为后端 API 授权。")
        self.account_message_label.setObjectName("statusLabel")
        self.account_message_label.setWordWrap(True)

        card_layout.addWidget(card_title)
        card_layout.addWidget(card_desc)
        card_layout.addLayout(card_row)
        card_layout.addWidget(self.account_message_label)
        outer.addWidget(card_box)
        outer.addStretch(1)

        self.refresh_account_state()
        return page

    def _build_repair_page(self):
        page = QWidget()
        page.setObjectName("contentArea")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(5)
        page_title = QLabel("CMD 系统修复工具箱")
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel("封装微软官方原生命令，支持推荐安全修复、深度系统修复和独立勾选执行。")
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)
        recommended_button = QPushButton("推荐安全修复")
        recommended_button.setObjectName("scanPrimaryButton")
        recommended_button.setMinimumWidth(126)
        recommended_button.clicked.connect(self.select_recommended_repairs)

        deep_button = QPushButton("深度系统修复")
        deep_button.setObjectName("cleanSecondaryButton")
        deep_button.setMinimumWidth(126)
        deep_button.clicked.connect(self.select_deep_repairs)

        self.run_repair_button = QPushButton("一键执行选中修复")
        self.run_repair_button.setObjectName("scanPrimaryButton")
        self.run_repair_button.setMinimumWidth(148)
        self.run_repair_button.clicked.connect(self.run_selected_repairs)

        clear_log_button = QPushButton("清空本次日志")
        clear_log_button.setObjectName("cleanSecondaryButton")
        clear_log_button.setMinimumWidth(112)
        clear_log_button.clicked.connect(self.clear_repair_log)

        action_bar.addWidget(recommended_button)
        action_bar.addWidget(deep_button)
        action_bar.addWidget(self.run_repair_button)
        action_bar.addStretch(1)
        action_bar.addWidget(clear_log_button)
        outer.addLayout(action_bar)

        self.repair_status_label = QLabel("等待选择修复项目")
        self.repair_status_label.setObjectName("statusLabel")
        outer.addWidget(self.repair_status_label)

        self.repair_table = QTableWidget()
        self.repair_table.setObjectName("optimizerTable")
        self.repair_table.setColumnCount(5)
        self.repair_table.setHorizontalHeaderLabels(["修复项", "风险", "说明", "命令", "操作"])
        self.repair_table.verticalHeader().setVisible(False)
        self.repair_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.repair_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.repair_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.repair_table.setAlternatingRowColors(True)
        self.repair_table.setIconSize(QSize(20, 20))
        repair_header = self.repair_table.horizontalHeader()
        repair_header.setMinimumSectionSize(86)
        repair_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        repair_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        repair_header.setSectionResizeMode(2, QHeaderView.Stretch)
        repair_header.setSectionResizeMode(3, QHeaderView.Stretch)
        repair_header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.repair_table.setColumnWidth(4, 96)
        self.repair_table.itemChanged.connect(lambda _item: self.update_repair_status())
        outer.addWidget(self.repair_table, 1)

        self.repair_log_output = QTextEdit()
        self.repair_log_output.setObjectName("repairLogOutput")
        self.repair_log_output.setReadOnly(True)
        self.repair_log_output.setMinimumHeight(130)
        self.repair_log_output.setPlaceholderText("系统修复日志会显示在这里。")
        outer.addWidget(self.repair_log_output)

        self.repair_service = SystemRepairService()
        self.repair_actions = SystemRepairService.default_actions()
        self.repair_thread = None
        self.populate_repair_table(self.repair_actions)
        self.select_recommended_repairs()
        return page

    def populate_repair_table(self, actions):
        self.repair_table.setRowCount(0)
        for row_index, action in enumerate(actions):
            self.repair_table.insertRow(row_index)

            name_item = QTableWidgetItem(action.name)
            name_item.setFlags(name_item.flags() | Qt.ItemIsUserCheckable)
            name_item.setCheckState(Qt.Checked if action.recommended else Qt.Unchecked)
            name_item.setData(Qt.UserRole, action)
            icon = self.category_icon_for_name("windows")
            if not icon.isNull():
                name_item.setIcon(icon)
            self.repair_table.setItem(row_index, 0, name_item)

            risk_item = QTableWidgetItem(action.risk.label)
            risk_item.setToolTip(action.risk.description)
            self.repair_table.setItem(row_index, 1, risk_item)

            description_item = QTableWidgetItem(action.description)
            description_item.setToolTip(action.description)
            self.repair_table.setItem(row_index, 2, description_item)

            command_item = QTableWidgetItem(action.command)
            command_item.setToolTip(action.command)
            self.repair_table.setItem(row_index, 3, command_item)

            run_button = QPushButton("执行")
            run_button.setObjectName("miniActionButton")
            run_button.setCursor(Qt.PointingHandCursor)
            run_button.setMinimumWidth(72)
            run_button.clicked.connect(
                lambda _checked=False, target=action: self.run_repair_actions([target])
            )
            self.repair_table.setCellWidget(row_index, 4, run_button)
            self.repair_table.setRowHeight(row_index, 36)

    def set_repair_selection(self, selected_ids):
        selected_ids = set(selected_ids)
        self.repair_table.blockSignals(True)
        try:
            for row_index in range(self.repair_table.rowCount()):
                item = self.repair_table.item(row_index, 0)
                action = item.data(Qt.UserRole) if item else None
                if item and action:
                    item.setCheckState(Qt.Checked if action.id in selected_ids else Qt.Unchecked)
        finally:
            self.repair_table.blockSignals(False)
        self.update_repair_status()

    def select_recommended_repairs(self):
        self.set_repair_selection(action.id for action in SystemRepairService.recommended_preset())

    def select_deep_repairs(self):
        self.set_repair_selection(action.id for action in SystemRepairService.deep_preset())

    def selected_repair_actions(self):
        actions = []
        for row_index in range(self.repair_table.rowCount()):
            item = self.repair_table.item(row_index, 0)
            if not item or item.checkState() != Qt.Checked:
                continue
            action = item.data(Qt.UserRole)
            if action:
                actions.append(action)
        return actions

    def update_repair_status(self):
        if not hasattr(self, "repair_status_label"):
            return
        selected_count = len(self.selected_repair_actions())
        self.repair_status_label.setText(f"已选择 {selected_count} 个修复项目")

    def clear_repair_log(self):
        self.repair_log_output.clear()
        self.repair_status_label.setText("已清空本次日志")

    def run_selected_repairs(self):
        actions = self.selected_repair_actions()
        if not actions:
            QMessageBox.information(self, "系统修复", "请先勾选需要执行的修复项目。")
            return
        self.run_repair_actions(actions)

    def run_repair_actions(self, actions):
        if self.repair_thread and self.repair_thread.isRunning():
            self.repair_status_label.setText("系统修复正在执行，请稍后。")
            self.animate_status_pulse(self.repair_status_label)
            return

        self.set_repair_busy(True)
        self.repair_log_output.append(f"开始执行 {len(actions)} 个系统修复项目。")
        self.repair_thread = SystemRepairThread(self.repair_service, list(actions))
        self.repair_thread.progress_signal.connect(self.on_repair_progress)
        self.repair_thread.result_signal.connect(self.on_repair_result)
        self.repair_thread.finished_signal.connect(self.on_repair_finished)
        self.repair_thread.error_signal.connect(self.on_repair_error)
        self.repair_thread.finished.connect(self.repair_thread.deleteLater)
        self.repair_thread.start()

    def set_repair_busy(self, busy):
        self.run_repair_button.setEnabled(not busy)
        for row_index in range(self.repair_table.rowCount()):
            widget = self.repair_table.cellWidget(row_index, 4)
            if widget:
                widget.setEnabled(not busy)
        self.repair_status_label.setText("系统修复执行中..." if busy else "系统修复已就绪")

    def on_repair_progress(self, message):
        self.repair_status_label.setText(message)
        self.repair_log_output.append(message)

    def on_repair_result(self, result):
        status = "成功" if result.success else "未执行" if result.unsupported else f"失败({result.exit_code})"
        self.repair_log_output.append(f"[{status}] {result.action.name}")
        if result.output:
            self.repair_log_output.append(result.output)

    def on_repair_finished(self):
        self.set_repair_busy(False)
        self.repair_thread = None
        self.repair_status_label.setText("系统修复执行完成")
        self.animate_status_pulse(self.repair_status_label)

    def on_repair_error(self, message):
        self.set_repair_busy(False)
        self.repair_thread = None
        self.repair_status_label.setText(f"系统修复失败: {message}")
        QMessageBox.warning(self, "系统修复", f"执行失败:\n{message}")

    def _make_optimizer_table(self, headers):
        table = QTreeWidget()
        table.setObjectName("optimizerTable")
        table.setColumnCount(len(headers))
        table.setHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setIconSize(QSize(20, 20))
        table.setRootIsDecorated(True)
        table.setItemsExpandable(True)

        header = table.header()
        header.setMinimumSectionSize(86)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeToContents)
        return table

    def _populate_optimizer_table(self, table, rows):
        table.clear()
        for payload in rows:
            item = self._make_optimizer_tree_item(payload, table.columnCount())
            table.addTopLevelItem(item)
            for child_payload in payload.get("children", []):
                child_item = self._make_optimizer_tree_item(
                    child_payload,
                    table.columnCount(),
                    is_child=True,
                )
                item.addChild(child_item)
            if payload.get("children"):
                item.setExpanded(payload.get("expanded", True))

            action_button = QPushButton(payload.get("action", "处理"))
            action_button.setObjectName("miniActionButton")
            action_button.setCursor(Qt.PointingHandCursor)
            action_button.clicked.connect(
                lambda _checked=False, row=dict(payload): self.run_optimizer_row_action_from_button(row, confirm=False)
            )
            table.setItemWidget(item, table.columnCount() - 1, action_button)

    def _make_optimizer_tree_item(self, payload, column_count, is_child=False):
        item = QTreeWidgetItem()
        columns = payload.get("columns", [])
        for column_index in range(column_count - 1):
            text = columns[column_index] if column_index < len(columns) else ""
            item.setText(column_index, text)
            item.setToolTip(column_index, text)
            if column_index == 0:
                if is_child:
                    item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                else:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Checked if payload.get("recommended", True) else Qt.Unchecked)
                    item.setData(0, Qt.UserRole, payload)
                icon = self.category_icon_for_name(payload.get("icon_hint") or text)
                if not icon.isNull():
                    item.setIcon(0, icon)
        if is_child:
            item.setForeground(0, self.palette().mid())
        return item

    def optimizer_top_level_items(self, table):
        for row_index in range(table.topLevelItemCount()):
            yield table.topLevelItem(row_index)

    def iter_optimizer_items(self, item):
        yield item
        for child_index in range(item.childCount()):
            yield from self.iter_optimizer_items(item.child(child_index))

    def optimizer_child_columns(self, values, column_count):
        columns = list(values)
        while len(columns) < max(1, column_count - 1):
            columns.append("")
        return columns[:max(1, column_count - 1)]

    def optimizer_child(self, *values, icon_hint="registry"):
        return {
            "columns": list(values),
            "icon_hint": icon_hint,
            "recommended": False,
        }

    def optimizer_detail_children(self, values, column_count, icon_hint="registry"):
        return [
            self.optimizer_child(*self.optimizer_child_columns([value], column_count), icon_hint=icon_hint)
            for value in values
        ]

    def _dedupe_optimizer_rows(self, rows):
        deduped = []
        seen = set()
        for row in rows:
            columns = row.get("columns", [])
            key = tuple(str(value).strip().lower() for value in columns[:2])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    def _fallback_startup_rows(self):
        rows = [
            {
                "columns": ["Windows Security notification icon", r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run"],
                "icon_hint": "defender",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Realtek高清晰音频管理器", r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run"],
                "icon_hint": "realtek",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Windows 命令处理程序", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"],
                "icon_hint": "cmd",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Windows 命令处理程序", r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run"],
                "icon_hint": "cmd",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Windows 命令处理程序", "Startup 文件夹"],
                "icon_hint": "cmd",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Microsoft OneDrive", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"],
                "icon_hint": "onedrive",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["网易UU远程", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"],
                "icon_hint": "uu",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Microsoft Edge", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"],
                "icon_hint": "edge",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Microsoft Edge Update Service (edgeupdate)", r"HKLM\SYSTEM\CurrentControlSet\Services\edgeupdate"],
                "icon_hint": "edge",
                "action": "查看",
                "command": "services.msc",
                "action_type": "command",
            },
            {
                "columns": ["GameViewerService", r"HKLM\SYSTEM\CurrentControlSet\Services\GameViewerService"],
                "icon_hint": "GameViewer",
                "action": "查看",
                "command": "services.msc",
                "action_type": "command",
            },
            {
                "columns": [r"@C:\ProgramData\Microsoft\Windows Defender\platform\4.18.26050.15", r"HKLM\SYSTEM\CurrentControlSet\Services"],
                "icon_hint": "defender",
                "action": "查看",
                "command": "services.msc",
                "action_type": "command",
                "recommended": False,
            },
            {
                "columns": ["NVIDIA Display Container LS", r"HKLM\SYSTEM\CurrentControlSet\Services\NVDisplay.ContainerLocalSystem"],
                "icon_hint": "nvidia",
                "action": "查看",
                "command": "services.msc",
                "action_type": "command",
            },
            {
                "columns": ["Microsoft PC Manager Service", r"HKLM\SYSTEM\CurrentControlSet\Services\MSPCManagerService"],
                "icon_hint": "pcmanager",
                "action": "查看",
                "command": "services.msc",
                "action_type": "command",
            },
            {
                "columns": ["ToDesk Service", r"HKLM\SYSTEM\CurrentControlSet\Services\ToDeskService"],
                "icon_hint": "todesk",
                "action": "查看",
                "command": "services.msc",
                "action_type": "command",
            },
        ]
        for row in rows:
            row["recommended"] = False
            row["action_type"] = None
        return rows

    def startup_folder_items(self):
        folders = [
            os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "StartUp"),
        ]
        rows = []
        for folder in folders:
            if not folder or not os.path.isdir(folder):
                continue
            try:
                entries = sorted(os.listdir(folder))
            except OSError:
                continue
            for entry in entries[:40]:
                path = os.path.join(folder, entry)
                rows.append({
                    "columns": [entry, folder],
                    "icon_hint": path,
                    "action": "打开",
                    "action_type": "command",
                    "command": f'explorer "{folder}"',
                    "recommended": False,
                })
        return rows

    def populate_startup_service_items(self):
        if not sys.platform.startswith("win"):
            return []

        try:
            import winreg
        except ImportError:
            return []

        rows = []
        services_key = r"SYSTEM\CurrentControlSet\Services"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, services_key) as parent:
                service_count, _value_count, _modified = winreg.QueryInfoKey(parent)
                for index in range(service_count):
                    if len(rows) >= 80:
                        break
                    try:
                        service_name = winreg.EnumKey(parent, index)
                        with winreg.OpenKey(parent, service_name) as service_key:
                            start_value, _value_type = winreg.QueryValueEx(service_key, "Start")
                            if int(start_value) != 2:
                                continue
                            display_name = self._registry_value(service_key, "DisplayName") or service_name
                    except (OSError, ValueError):
                        continue
                    rows.append({
                        "columns": [display_name, f"HKLM\\{services_key}\\{service_name}"],
                        "icon_hint": display_name,
                        "action": "查看",
                        "command": "services.msc",
                        "action_type": None,
                        "recommended": False,
                    })
        except OSError:
            return []
        return rows

    def populate_startup_items(self):
        if not sys.platform.startswith("win"):
            return self._fallback_startup_rows()

        try:
            import winreg
        except ImportError:
            return self._fallback_startup_rows()

        locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
        ]

        rows = []
        for root, subkey, root_name in locations:
            try:
                with winreg.OpenKey(root, subkey) as key:
                    index = 0
                    while True:
                        try:
                            value_name, value_data, _value_type = winreg.EnumValue(key, index)
                        except OSError:
                            break
                        rows.append({
                            "columns": [value_name, f"{root_name}\\{subkey}"],
                            "icon_hint": value_name,
                            "action": "禁用",
                            "action_type": "disable_startup",
                            "root_name": root_name,
                            "subkey": subkey,
                            "value_name": value_name,
                            "command": str(value_data),
                        })
                        index += 1
            except OSError:
                continue

        rows.extend(self.startup_folder_items())
        rows.extend(self.populate_startup_service_items())
        rows.extend(self._fallback_startup_rows())
        return self._dedupe_optimizer_rows(rows)

    def _fallback_memory_rows(self):
        return [
            {"columns": ["C盘清理精灵.exe", "446.61MB", "3.59%"], "icon_hint": "cleaner", "action": "保留", "action_type": None, "recommended": False},
            {"columns": ["ToDesk.exe", "213.56MB", "0.00%"], "icon_hint": "todesk", "action": "结束", "action_type": "kill_process_by_name", "process_name": "ToDesk.exe", "recommended": False},
            {"columns": ["GameViewer.exe", "79.41MB", "0.00%"], "icon_hint": "GameViewer", "action": "结束", "action_type": "kill_process_by_name", "process_name": "GameViewer.exe", "recommended": False},
            {"columns": ["msedge.exe", "--", "--"], "icon_hint": "edge", "action": "结束", "action_type": "kill_process_by_name", "process_name": "msedge.exe", "recommended": False},
            {"columns": ["explorer.exe", "--", "--"], "icon_hint": "explorer", "action": "保留", "action_type": None, "recommended": False},
            {"columns": ["crashpad_handler.exe", "7.89MB", "0.00%"], "icon_hint": "crashpad", "action": "结束", "action_type": "kill_process_by_name", "process_name": "crashpad_handler.exe", "recommended": False},
            {"columns": ["CDriveCleanerSpirit.exe", "7.39MB", "0.00%"], "icon_hint": "cleaner", "action": "保留", "action_type": None, "recommended": False},
        ]

    def populate_memory_items(self):
        rows = []
        if psutil is not None:
            try:
                total_memory = max(psutil.virtual_memory().total, 1)
                processes = []
                for process in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
                    try:
                        info = process.info
                        memory_info = info.get("memory_info")
                        rss = memory_info.rss if memory_info else 0
                        processes.append((rss, info))
                    except (psutil.Error, AttributeError):
                        continue

                for rss, info in sorted(processes, reverse=True)[:60]:
                    pid = info.get("pid")
                    name = info.get("name") or f"PID {pid}"
                    memory_percent = rss / total_memory * 100
                    cpu_percent = info.get("cpu_percent") or 0.0
                    current_process = pid == os.getpid()
                    rows.append({
                        "columns": [
                            f"{name}  (PID {pid})",
                            f"{self.format_size(rss)} / {memory_percent:.2f}%",
                            f"{cpu_percent:.2f}%",
                        ],
                        "icon_hint": name,
                        "action": "保留" if current_process else "结束",
                        "action_type": None if current_process else "kill_process",
                        "pid": pid,
                        "recommended": not current_process,
                    })
            except Exception:
                rows = []

        if len(rows) < 8:
            rows.extend(self._fallback_memory_rows())

        return self._dedupe_optimizer_rows(rows)

    def populate_optimization_items(self):
        return [
            {
                "columns": ["刷新 DNS 解析缓存"],
                "icon_hint": "windows",
                "action": "执行",
                "action_type": "command",
                "command": "ipconfig /flushdns",
                "children": self.optimizer_detail_children(
                    [r"ipconfig /flushdns", r"DNS Client 缓存"],
                    2,
                    icon_hint="cmd",
                ),
            },
            {
                "columns": ["执行系统空闲任务整理"],
                "icon_hint": "windows",
                "action": "执行",
                "action_type": "command",
                "command": "rundll32.exe advapi32.dll,ProcessIdleTasks",
                "children": self.optimizer_detail_children(
                    ["ProcessIdleTasks", "Prefetch / SuperFetch 维护队列"],
                    2,
                    icon_hint="windows",
                ),
            },
            {
                "columns": ["关闭系统自动调试功能(32位)"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AeDebug" /v Auto /t REG_SZ /d 0 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AeDebug\Auto"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["关闭系统自动调试功能(64位)"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\AeDebug" /v Auto /t REG_SZ /d 0 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\AeDebug\Auto"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["启动时减少等待磁盘错误检查时间"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": "chkntfs /t:3",
                "children": self.optimizer_detail_children(["chkntfs /t:3"], 2, icon_hint="cmd"),
            },
            {
                "columns": ["启用大系统缓存以提高性能"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            },
            {
                "columns": ["禁止系统内核与驱动程序分页到硬盘"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            },
            {
                "columns": ["系统自动管理文件管理系统缓存"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            },
            {
                "columns": ["将Windows预读调整为关闭预读"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters" /v EnablePrefetcher /t REG_DWORD /d 0 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters\EnablePrefetcher"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["禁用处理器的幽灵和熔断补丁"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            },
            {
                "columns": ["关闭TSX漏洞补丁"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            },
            {
                "columns": ["Windows 启动优化功能（碎片整理预取）"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SOFTWARE\Microsoft\Dfrg\BootOptimizeFunction" /v Enable /t REG_SZ /d Y /f',
                "children": self.optimizer_detail_children(
                    [r"HKLM\SOFTWARE\Microsoft\Dfrg\BootOptimizeFunction\Enable"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["Windows 启动优化功能（碎片整理预取）"],
                "icon_hint": "windows",
                "action": "执行",
                "action_type": "command",
                "command": "defrag C: /b /u",
                "recommended": False,
                "children": self.optimizer_detail_children(["defrag C: /b /u"], 2, icon_hint="cmd"),
            },
            {
                "columns": ["禁用自动更新商店应用"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\WindowsStore" /v AutoDownload /t REG_DWORD /d 2 /f',
                "children": self.optimizer_detail_children(
                    [r"HKLM\SOFTWARE\Policies\Microsoft\WindowsStore\AutoDownload"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["禁止自动安装推荐的应用程序"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v SilentInstalledAppsEnabled /t REG_DWORD /d 0 /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager\SilentInstalledAppsEnabled"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["禁用Windows预安装和应用推荐功能"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v PreInstalledAppsEnabled /t REG_DWORD /d 0 /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager\PreInstalledAppsEnabled"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["禁用Windows预安装和应用推荐功能"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v OemPreInstalledAppsEnabled /t REG_DWORD /d 0 /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager\OemPreInstalledAppsEnabled"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["关闭“使用 Windows 时获取技巧和建议”"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v SubscribedContent-338389Enabled /t REG_DWORD /d 0 /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager\SubscribedContent-338389Enabled"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["关闭开始菜单建议广告"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v SystemPaneSuggestionsEnabled /t REG_DWORD /d 0 /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager\SystemPaneSuggestionsEnabled"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["关闭锁屏界面内容广告"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v RotatingLockScreenOverlayEnabled /t REG_DWORD /d 0 /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager\RotatingLockScreenOverlayEnabled"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["禁用自动更新地图"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Maps" /v AutoDownloadAndUpdateMapData /t REG_DWORD /d 0 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Maps\AutoDownloadAndUpdateMapData"],
                    2,
                    icon_hint="registry",
                ),
            },
        ]

    def populate_privacy_items(self):
        return [
            {
                "columns": ["最近打开文件记录"],
                "icon_hint": "windows",
                "action": "清理",
                "action_type": "command",
                "command": r'cmd /c del /f /q "%APPDATA%\Microsoft\Windows\Recent\*"',
                "children": self.optimizer_detail_children(
                    [
                        r"%APPDATA%\Microsoft\Windows\Recent",
                        r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations",
                        r"%APPDATA%\Microsoft\Windows\Recent\CustomDestinations",
                    ],
                    2,
                    icon_hint="windows",
                ),
            },
            {
                "columns": ["开始菜单运行记录"],
                "icon_hint": "windows",
                "action": "清理",
                "action_type": "command",
                "command": r'reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["开始菜单运行记录"],
                "icon_hint": "windows",
                "action": "清理",
                "action_type": "command",
                "command": r'reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths" /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["Internet Explorer 上网痕迹"],
                "icon_hint": "ie",
                "action": "清理",
                "action_type": "command",
                "command": "RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess 255",
                "children": self.optimizer_detail_children(
                    [
                        r"%LOCALAPPDATA%\Microsoft\Windows\INetCache",
                        r"%LOCALAPPDATA%\Microsoft\Windows\WebCache",
                        r"%LOCALAPPDATA%\Microsoft\Internet Explorer\DOMStore",
                    ],
                    2,
                    icon_hint="ie",
                ),
            },
            {
                "columns": ["系统通知区及图标缓存"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [
                        r"HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify",
                        r"%LOCALAPPDATA%\IconCache.db",
                    ],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["系统通知区及图标缓存"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [
                        r"%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*",
                        r"%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*",
                    ],
                    2,
                    icon_hint="windows",
                ),
            },
            {
                "columns": ["登录缓存配置文件"],
                "icon_hint": "windows",
                "action": "清理",
                "action_type": "command",
                "command": r'cmd /c del /f /q "%LOCALAPPDATA%\Microsoft\Windows\UsrClass.dat.LOG*"',
                "children": self.optimizer_detail_children(
                    [r"%LOCALAPPDATA%\Microsoft\Windows\UsrClass.dat.LOG*"],
                    2,
                    icon_hint="windows",
                ),
            },
            {
                "columns": ["程序安装信息"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "children": self.optimizer_detail_children(
                    [
                        r"C:\Windows\Panther",
                        r"C:\Windows\INF\setupapi.dev.log",
                        r"C:\Windows\setupact.log",
                    ],
                    2,
                    icon_hint="windows",
                ),
            },
            {
                "columns": ["快速访问的缓存数据存储"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [
                        r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations",
                        r"%APPDATA%\Microsoft\Windows\Recent\CustomDestinations",
                    ],
                    2,
                    icon_hint="windows",
                ),
            },
            {
                "columns": ["IE 浏览器自动完成"],
                "icon_hint": "ie",
                "action": "检查",
                "action_type": None,
                "children": self.optimizer_detail_children(
                    [
                        r"HKCU\Software\Microsoft\Internet Explorer\TypedURLs",
                        r"HKCU\Software\Microsoft\Internet Explorer\IntelliForms",
                    ],
                    2,
                    icon_hint="ie",
                ),
            },
            {
                "columns": ["(MMC)控制台文件的最近打开历史记录"],
                "icon_hint": "windows",
                "action": "清理",
                "action_type": "command",
                "command": r'reg delete "HKCU\Software\Microsoft\Microsoft Management Console\Recent File List" /f',
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\Microsoft Management Console\Recent File List"],
                    2,
                    icon_hint="registry",
                ),
            },
        ]

    def populate_registry_items(self):
        return [
            {"columns": ["缺失的共享 DLL"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\SharedDLLs"], 2)},
            {"columns": ["未使用的文件扩展名"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([".bak", ".cfg", ".idx", ".ipa", ".itc2", ".itdb", ".itl", ".map", ".mdb", ".pls", ".pptx", ".pst", ".rar"], 2)},
            {"columns": ["无效的默认图标"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCR\*\DefaultIcon", r"HKCR\Applications\*\DefaultIcon"], 2)},
            {"columns": ["应用程序打开方式文件问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts", r"HKCR\Applications"], 2)},
            {"columns": ["CLSID问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCR\CLSID\*\InprocServer32", r"HKCR\Wow6432Node\CLSID\*\InprocServer32"], 2)},
            {"columns": ["CLSID问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCR\CLSID\*\LocalServer32", r"HKCR\Wow6432Node\CLSID\*\LocalServer32"], 2)},
            {"columns": ["CLSID问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCR\Interface", r"HKCR\TypeLib"], 2)},
            {"columns": ["CLSID问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKLM\SOFTWARE\Classes\CLSID", r"HKCU\SOFTWARE\Classes\CLSID"], 2)},
            {"columns": ["CLSID问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCR\AppID", r"HKCR\Component Categories"], 2)},
            {"columns": ["应用程序卸载残留"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall"], 2)},
            {"columns": ["应用程序卸载残留"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"], 2)},
            {"columns": ["应用程序卸载残留"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall"], 2)},
            {"columns": ["应用程序卸载残留"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCR\Installer\Products", r"HKLM\SOFTWARE\Classes\Installer\Products"], 2)},
            {"columns": ["无效的防火墙规则"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKLM\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules"], 2)},
            {"columns": ["Windows 兼容性助手功能的记忆库"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store"], 2)},
            {"columns": ["统计和管理用户界面交互行为"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False, "children": self.optimizer_detail_children([r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"], 2)},
        ]

    def set_current_optimizer_checked(self, state):
        table = self.optimizer_tabs.currentWidget()
        if not table:
            return
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for item in self.optimizer_top_level_items(table):
            if item:
                item.setCheckState(0, check_state)

    def apply_optimizer_recommended_filter(self, state):
        table = self.optimizer_tabs.currentWidget()
        if not table or state != Qt.Checked:
            return
        for item in self.optimizer_top_level_items(table):
            payload = item.data(0, Qt.UserRole) if item else {}
            if item:
                item.setCheckState(0, Qt.Checked if payload.get("recommended", True) else Qt.Unchecked)

    def selected_optimizer_rows(self):
        table = self.optimizer_tabs.currentWidget()
        if not table:
            return []
        rows = []
        for item in self.optimizer_top_level_items(table):
            if item and item.checkState(0) == Qt.Checked:
                payload = item.data(0, Qt.UserRole)
                if payload:
                    rows.append(payload)
        return rows

    def refresh_optimizer_tab(self):
        tab_name = self.optimizer_tabs.tabText(self.optimizer_tabs.currentIndex())
        loaders = {
            "开机加速": self.populate_startup_items,
            "运行内存": self.populate_memory_items,
            "系统优化": self.populate_optimization_items,
            "隐私清理": self.populate_privacy_items,
            "注册表清理": self.populate_registry_items,
        }
        table = self.optimizer_tables.get(tab_name)
        loader = loaders.get(tab_name)
        if table and loader:
            self._populate_optimizer_table(table, loader())

    def apply_current_optimization_tab(self):
        rows = self.selected_optimizer_rows()
        tab_name = self.optimizer_tabs.tabText(self.optimizer_tabs.currentIndex())
        if not rows:
            QMessageBox.information(self, "一键优化", "请先勾选需要处理的项目。")
            return

        executed = 0
        skipped = 0
        for row in rows:
            if self.run_optimizer_row_action(row, confirm=False, quiet=True):
                executed += 1
            else:
                skipped += 1

        if hasattr(self, "optimizer_status_label"):
            self.optimizer_status_label.setText(
                f"{tab_name} 已直接处理 {executed} 项，跳过 {skipped} 项。"
            )
            self.animate_status_pulse(self.optimizer_status_label)
        self.refresh_optimizer_tab()

    def run_optimizer_row_action_from_button(self, row, confirm=False):
        label = row.get("columns", ["系统优化"])[0]
        handled = self.run_optimizer_row_action(row, confirm=confirm, quiet=False)
        if hasattr(self, "optimizer_status_label"):
            if handled:
                self.optimizer_status_label.setText(f"{label} 已处理，正在刷新当前列表。")
                QTimer.singleShot(650, self.refresh_optimizer_tab)
            else:
                self.optimizer_status_label.setText("该项目仅展示或检查，不需要执行处理。")
            self.animate_status_pulse(self.optimizer_status_label)
        return handled

    def run_optimizer_row_action(self, row, confirm=False, quiet=False):
        action_type = row.get("action_type")
        if action_type == "disable_startup":
            return self.disable_startup_item(row, confirm=confirm)
        if action_type in {"kill_process", "kill_process_by_name"}:
            return self.kill_process_item(row, confirm=confirm)
        if action_type == "command" and row.get("command"):
            self._run_shell_command(row.get("columns", ["系统优化"])[0], row["command"], quiet=quiet)
            return True

        if not quiet and hasattr(self, "optimizer_status_label"):
            self.optimizer_status_label.setText("该项目仅展示或检查，不需要执行处理。")
            self.animate_status_pulse(self.optimizer_status_label)
        return False

    def _run_shell_command(self, label, command, quiet=False):
        if sys.platform.startswith("win"):
            try:
                subprocess.Popen(
                    command,
                    shell=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **hidden_windows_subprocess_kwargs(),
                )
                return True
            except Exception as exc:  # pragma: no cover - Windows shell dependent
                QMessageBox.warning(self, label, f"执行失败: {exc}")
                return False
        if not quiet:
            QMessageBox.information(self, label, f"该操作将在 Windows 上执行:\n{command}")
        return True

    def disable_startup_item(self, row, confirm=False):
        if not sys.platform.startswith("win"):
            QMessageBox.information(self, "开机加速", "禁用启动项功能将在 Windows 上写入启动项注册表。")
            return False
        if confirm:
            answer = QMessageBox.question(
                self,
                "禁用启动项",
                f"确定禁用“{row.get('value_name')}”吗？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False

        try:
            import winreg
            root = winreg.HKEY_CURRENT_USER if row.get("root_name") == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            with winreg.OpenKey(root, row["subkey"], 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, row["value_name"])
            return True
        except Exception as exc:  # pragma: no cover - Windows registry dependent
            QMessageBox.warning(self, "禁用启动项", f"禁用失败: {exc}")
            return False

    def kill_process_item(self, row, confirm=False):
        pid = row.get("pid")
        process_name = row.get("process_name") or row.get("columns", ["进程"])[0].split("  (PID", 1)[0].strip()
        if not pid and not process_name:
            return False
        if confirm:
            answer = QMessageBox.question(
                self,
                "结束进程",
                f"确定结束“{process_name}”吗？未保存的数据可能丢失。",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False

        try:
            if sys.platform.startswith("win") and self.taskkill_process(pid=pid, process_name=process_name):
                return True

            if pid and psutil is not None:
                process = psutil.Process(pid)
                process.terminate()
                try:
                    process.wait(1.5)
                except psutil.TimeoutExpired:
                    process.kill()
                    process.wait(1.5)
            elif process_name and psutil is not None:
                killed = False
                for process in psutil.process_iter(["pid", "name"]):
                    try:
                        if process.info.get("pid") == os.getpid():
                            continue
                        if (process.info.get("name") or "").lower() == process_name.lower():
                            process.terminate()
                            try:
                                process.wait(1.5)
                            except psutil.TimeoutExpired:
                                process.kill()
                                process.wait(1.5)
                            killed = True
                    except (psutil.Error, AttributeError):
                        continue
                if not killed:
                    return False
            else:
                return False
            return True
        except Exception as exc:  # pragma: no cover - process state dependent
            QMessageBox.warning(self, "结束进程", f"结束失败: {exc}")
            return False

    def taskkill_process(self, pid=None, process_name=None):
        if not sys.platform.startswith("win"):
            return False
        if pid:
            target = f"/PID {int(pid)}"
        elif process_name:
            target = f'/IM "{process_name}"'
        else:
            return False
        try:
            result = subprocess.run(
                f"taskkill {target} /F /T",
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                **hidden_windows_subprocess_kwargs(),
            )
            return result.returncode == 0
        except Exception:
            return False

    def _build_file_page(self):
        page = QWidget()
        page.setObjectName("contentArea")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(5)
        page_title = QLabel("文件管理")
        page_title.setObjectName("pageTitle")
        page_subtitle = QLabel("在软件内扫描大文件和重复文件，直接查看目标路径、大小和所在目录。")
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        choose_dir_button = QPushButton("选择目录")
        choose_dir_button.setObjectName("cleanSecondaryButton")
        choose_dir_button.setMinimumWidth(96)
        choose_dir_button.clicked.connect(self.select_file_scan_root)

        self.scan_large_button = QPushButton("扫描大文件")
        self.scan_large_button.setObjectName("scanPrimaryButton")
        self.scan_large_button.setMinimumWidth(112)
        self.scan_large_button.clicked.connect(self.scan_large_files)

        self.scan_duplicate_button = QPushButton("扫描重复文件")
        self.scan_duplicate_button.setObjectName("cleanSecondaryButton")
        self.scan_duplicate_button.setMinimumWidth(128)
        self.scan_duplicate_button.clicked.connect(self.scan_duplicate_files)

        self.delete_selected_file_button = QPushButton("删除选中文件")
        self.delete_selected_file_button.setObjectName("cleanSecondaryButton")
        self.delete_selected_file_button.setMinimumWidth(128)
        self.delete_selected_file_button.clicked.connect(self.delete_selected_files)

        self.delete_duplicate_copies_button = QPushButton("删除重复副本")
        self.delete_duplicate_copies_button.setObjectName("cleanSecondaryButton")
        self.delete_duplicate_copies_button.setMinimumWidth(128)
        self.delete_duplicate_copies_button.clicked.connect(self.delete_duplicate_copies)

        toolbar.addWidget(choose_dir_button)
        toolbar.addWidget(self.scan_large_button)
        toolbar.addWidget(self.scan_duplicate_button)
        toolbar.addWidget(self.delete_selected_file_button)
        toolbar.addWidget(self.delete_duplicate_copies_button)
        toolbar.addStretch(1)
        outer.addLayout(toolbar)

        self.file_root_label = QLabel(f"扫描目录: {self.current_file_scan_root()}")
        self.file_root_label.setObjectName("statusLabel")
        self.file_root_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self.file_root_label)

        self.file_tabs = QTabWidget()
        self.file_tabs.setObjectName("optimizerTabs")

        self.file_large_table = self._make_file_manage_table(["文件名", "大小", "路径", "操作"])
        self.file_duplicate_table = self._make_file_manage_table(["文件名", "大小", "重复组", "路径", "操作"])
        self.fragment_page = self._build_fragment_page()
        self.file_tabs.addTab(self.file_large_table, "大文件")
        self.file_tabs.addTab(self.file_duplicate_table, "重复文件")
        self.file_tabs.addTab(self.fragment_page, "碎片整理")
        outer.addWidget(self.file_tabs, 1)

        self.file_status_label = QLabel("准备扫描文件。")
        self.file_status_label.setObjectName("statusLabel")
        outer.addWidget(self.file_status_label)

        return page

    def _make_file_manage_table(self, headers):
        table = QTableWidget()
        table.setObjectName("fileManageTable")
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setIconSize(QSize(20, 20))
        table.setSortingEnabled(True)

        header_view = table.horizontalHeader()
        header_view.setMinimumSectionSize(86)
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        if len(headers) == 4:
            header_view.setSectionResizeMode(2, QHeaderView.Stretch)
            header_view.setSectionResizeMode(3, QHeaderView.Fixed)
            table.setColumnWidth(3, 164)
        else:
            header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header_view.setSectionResizeMode(3, QHeaderView.Stretch)
            header_view.setSectionResizeMode(4, QHeaderView.Fixed)
            table.setColumnWidth(4, 164)
        return table

    def _build_fragment_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(14)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.fragment_count_label = self._make_fragment_stat(stats_row, "碎片数", "--")
        self.fragment_files_label = self._make_fragment_stat(stats_row, "碎片文件", "--")
        self.fragment_rate_label = self._make_fragment_stat(stats_row, "碎片率", "--")
        outer.addLayout(stats_row)

        self.fragment_progress = QProgressBar()
        self.fragment_progress.setRange(0, 100)
        self.fragment_progress.setValue(0)
        self.fragment_progress.setTextVisible(False)
        outer.addWidget(self.fragment_progress)

        grid_card = QFrame()
        grid_card.setObjectName("featureCard")
        grid_card_layout = QVBoxLayout(grid_card)
        grid_card_layout.setContentsMargins(16, 16, 16, 16)
        grid_card_layout.setSpacing(12)

        self.fragment_grid = QGridLayout()
        self.fragment_grid.setHorizontalSpacing(4)
        self.fragment_grid.setVerticalSpacing(4)
        self.fragment_grid_cells = []
        for row in range(12):
            for column in range(28):
                cell = QLabel()
                cell.setFixedSize(14, 14)
                cell.setStyleSheet("background: #A0A0A0; border-radius: 1px;")
                self.fragment_grid.addWidget(cell, row, column)
                self.fragment_grid_cells.append(cell)
        grid_card_layout.addLayout(self.fragment_grid)

        legend = QHBoxLayout()
        legend.setSpacing(8)
        legend_label = QLabel("映射颜色")
        legend_label.setObjectName("statusLabel")
        legend.addWidget(legend_label)
        for color in ["#E5E7EB", "#67D4EA", "#2E9BEF", "#F59E0B", "#35C878", "#F5E46B", "#F56565"]:
            swatch = QLabel()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(f"background: {color}; border-radius: 2px;")
            legend.addWidget(swatch)
        legend.addStretch(1)
        grid_card_layout.addLayout(legend)
        outer.addWidget(grid_card, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.scan_fragment_button = QPushButton("扫描碎片")
        self.scan_fragment_button.setObjectName("scanPrimaryButton")
        self.scan_fragment_button.setMinimumWidth(112)
        self.scan_fragment_button.clicked.connect(self.scan_fragments)
        self.optimize_fragment_button = QPushButton("整理碎片")
        self.optimize_fragment_button.setObjectName("cleanSecondaryButton")
        self.optimize_fragment_button.setMinimumWidth(112)
        self.optimize_fragment_button.clicked.connect(self.optimize_fragments)
        actions.addWidget(self.scan_fragment_button)
        actions.addWidget(self.optimize_fragment_button)
        outer.addLayout(actions)

        self.paint_fragment_grid(0)
        return page

    def _make_fragment_stat(self, parent_layout, title, value):
        card = QFrame()
        card.setObjectName("featureCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        label = QLabel(title)
        label.setObjectName("featureCardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        layout.addWidget(label)
        layout.addWidget(value_label)
        parent_layout.addWidget(card, 1)
        return value_label

    def paint_fragment_grid(self, fragment_rate):
        colors = ["#A0A0A0", "#67D4EA", "#2E9BEF", "#F59E0B", "#35C878", "#F5E46B", "#F56565"]
        hot_ratio = max(0.0, min(float(fragment_rate or 0.0) / 100.0, 1.0))
        hot_cells = int(len(self.fragment_grid_cells) * hot_ratio)
        for index, cell in enumerate(self.fragment_grid_cells):
            if index < hot_cells:
                color = colors[2 + (index % (len(colors) - 2))]
            elif index % 17 == 0:
                color = colors[1]
            else:
                color = colors[0]
            cell.setStyleSheet(f"background: {color}; border-radius: 1px;")

    def set_fragment_busy(self, busy):
        self.scan_fragment_button.setEnabled(not busy)
        self.optimize_fragment_button.setEnabled(not busy)
        self.fragment_progress.setRange(0, 0 if busy else 100)
        if not busy:
            self.fragment_progress.setValue(100)

    def scan_fragments(self):
        self.start_defrag_thread("scan")

    def optimize_fragments(self):
        self.start_defrag_thread("optimize")

    def start_defrag_thread(self, mode):
        if self.defrag_thread and self.defrag_thread.isRunning():
            self.file_status_label.setText("碎片处理正在进行，请稍后。")
            self.animate_status_pulse(self.file_status_label)
            return

        self.file_tabs.setCurrentWidget(self.fragment_page)
        self.set_fragment_busy(True)
        self.file_status_label.setText("正在扫描碎片..." if mode == "scan" else "正在整理碎片...")
        self.defrag_thread = DefragThread(mode, "C:")
        self.defrag_thread.defrag_progress_signal.connect(self.on_defrag_progress)
        self.defrag_thread.defrag_finished_signal.connect(self.on_defrag_finished)
        self.defrag_thread.defrag_error_signal.connect(self.on_defrag_error)
        self.defrag_thread.finished.connect(self.defrag_thread.deleteLater)
        self.defrag_thread.start()

    def on_defrag_progress(self, message):
        self.file_status_label.setText(message)

    def on_defrag_finished(self, mode, payload):
        self.set_fragment_busy(False)
        self.defrag_thread = None
        self.fragment_count_label.setText(str(payload.get("fragment_count", "--")))
        self.fragment_files_label.setText(str(payload.get("fragment_files", "--")))
        self.fragment_rate_label.setText(str(payload.get("fragment_rate", "--")))
        self.paint_fragment_grid(payload.get("fragment_rate_value", 0.0))
        action = "扫描" if mode == "scan" else "整理"
        exit_code = payload.get("exit_code", 0)
        status = "完成" if exit_code == 0 else f"返回 {exit_code}"
        self.file_status_label.setText(f"碎片{action}{status}: {payload.get('command', '')}")
        self.animate_status_pulse(self.file_status_label)

    def on_defrag_error(self, mode, message):
        self.set_fragment_busy(False)
        self.defrag_thread = None
        action = "扫描" if mode == "scan" else "整理"
        self.file_status_label.setText(f"碎片{action}失败: {message}")
        QMessageBox.warning(self, "碎片整理", f"碎片{action}失败:\n{message}")

    def _open_system_tool(self, label, command):
        """在 Windows 上启动系统工具；其他平台给出提示。"""
        if sys.platform.startswith("win"):
            try:
                if command.startswith("ms-settings:"):
                    os.startfile(command)  # noqa: P201 - Windows 专用
                else:
                    subprocess.Popen(command, shell=True)
            except Exception as exc:  # pragma: no cover - 依赖系统环境
                QMessageBox.warning(self, label, f"无法启动 {label}：{exc}")
        else:
            QMessageBox.information(
                self,
                label,
                f"“{label}” 为 Windows 系统功能，将在 Windows 上调用：\n{command}",
            )

    def run_system_action(self, label, command):
        """执行或打开一个 Windows 系统动作。"""
        self._open_system_tool(label, command)

    def browse_backup_dir(self):
        """选择清理前备份目录。"""
        selected = QFileDialog.getExistingDirectory(
            self,
            "选择备份目录",
            self.cleaner.backup_dir,
        )
        if selected:
            self.cleaner.set_options({"backup_dir": selected})
            self.status_label.setText(f"备份目录已设置: {selected}")

    def open_backup_manager(self):
        """打开 Qt 备份管理窗口。"""
        dialog = QtBackupManagerDialog(self, self.cleaner, self.format_size)
        dialog.exec_()

    def show_installed_apps(self):
        """切到软件卸载页并刷新内置软件列表。"""
        self._select_page(self.page_index_for_label("软件卸载"))
        self.load_installed_apps(show_message=True)

    def load_installed_apps(self, show_message=False):
        apps = self.installed_apps_from_registry()
        self.uninstall_apps = apps
        if not hasattr(self, "uninstall_table"):
            return

        self.uninstall_table.setRowCount(0)
        for row_index, app in enumerate(apps):
            self.uninstall_table.insertRow(row_index)

            name_item = QTableWidgetItem(app.get("name", ""))
            icon = self.icon_for_installed_app(app)
            if not icon.isNull():
                name_item.setIcon(icon)
            name_item.setData(Qt.UserRole, app)
            self.uninstall_table.setItem(row_index, 0, name_item)
            self.uninstall_table.setItem(row_index, 1, QTableWidgetItem(app.get("publisher", "")))
            self.uninstall_table.setItem(row_index, 2, QTableWidgetItem(app.get("version", "")))
            self.uninstall_table.setItem(row_index, 3, QTableWidgetItem(app.get("install_location", "")))

            uninstall_button = QPushButton("卸载")
            uninstall_button.setObjectName("miniActionButton")
            uninstall_button.setCursor(Qt.PointingHandCursor)
            uninstall_button.setMinimumWidth(72)
            uninstall_button.clicked.connect(
                lambda _checked=False, target=dict(app): self.run_uninstall_command(target)
            )
            self.uninstall_table.setCellWidget(row_index, 4, uninstall_button)
            self.uninstall_table.setRowHeight(row_index, 34)

        if apps:
            self.uninstall_status_label.setText(f"已读取 {len(apps)} 个已安装软件。")
        else:
            message = "当前环境未读取到软件列表；Windows 上会读取卸载注册表。"
            self.uninstall_status_label.setText(message)
            if show_message:
                QMessageBox.information(self, "软件卸载", message)

    def installed_apps_from_registry(self):
        if not sys.platform.startswith("win"):
            return []

        try:
            import winreg
        except ImportError:
            return []

        locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        apps = []
        seen = set()
        for root, subkey in locations:
            try:
                with winreg.OpenKey(root, subkey) as parent:
                    subkey_count, _value_count, _modified = winreg.QueryInfoKey(parent)
                    for index in range(subkey_count):
                        try:
                            child_name = winreg.EnumKey(parent, index)
                            with winreg.OpenKey(parent, child_name) as app_key:
                                app = self._installed_app_from_key(app_key)
                        except OSError:
                            continue
                        if not app.get("name"):
                            continue
                        dedupe_key = (
                            app.get("name", "").lower(),
                            app.get("publisher", "").lower(),
                            app.get("version", ""),
                        )
                        if dedupe_key in seen:
                            continue
                        seen.add(dedupe_key)
                        apps.append(app)
            except OSError:
                continue

        apps.sort(key=lambda app: app.get("name", "").lower())
        return apps

    def _installed_app_from_key(self, key):
        return {
            "name": self._registry_value(key, "DisplayName"),
            "publisher": self._registry_value(key, "Publisher"),
            "version": self._registry_value(key, "DisplayVersion"),
            "install_location": self._registry_value(key, "InstallLocation"),
            "uninstall": self._registry_value(key, "UninstallString"),
            "quiet_uninstall": self._registry_value(key, "QuietUninstallString"),
        }

    @staticmethod
    def _registry_value(key, name):
        try:
            import winreg
            value, _value_type = winreg.QueryValueEx(key, name)
            return str(value)
        except OSError:
            return ""

    def icon_for_installed_app(self, app):
        for candidate in (
            app.get("install_location", ""),
            self.executable_path_from_command(app.get("uninstall", "")),
            self.executable_path_from_command(app.get("quiet_uninstall", "")),
        ):
            if candidate and os.path.exists(candidate):
                return self.icon_provider.icon(QFileInfo(candidate))
        return self.app_icon

    @staticmethod
    def executable_path_from_command(command):
        command = (command or "").strip()
        if not command:
            return ""
        if command.startswith('"'):
            return command.split('"', 2)[1] if '"' in command[1:] else command.strip('"')
        return command.split(" ", 1)[0]

    def uninstall_selected_app(self):
        row = self.uninstall_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "软件卸载", "请先在列表中选择一个软件。")
            return
        item = self.uninstall_table.item(row, 0)
        app = item.data(Qt.UserRole) if item else None
        if app:
            self.run_uninstall_command(app)

    def run_uninstall_command(self, app):
        command = app.get("quiet_uninstall") or app.get("uninstall")
        if not command:
            QMessageBox.warning(self, "软件卸载", f"“{app.get('name', '')}”没有可用卸载命令。")
            return

        command = self.normalize_uninstall_command(command)
        answer = QMessageBox.question(
            self,
            "软件卸载",
            f"确定卸载“{app.get('name', '')}”吗？\n\n将执行：\n{command}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if not sys.platform.startswith("win"):
            QMessageBox.information(self, "软件卸载", f"此命令将在 Windows 上执行:\n{command}")
            return

        try:
            subprocess.Popen(command, shell=True)
            self.uninstall_status_label.setText(f"已启动卸载程序: {app.get('name', '')}，完成后将自动刷新列表。")
            QTimer.singleShot(3000, lambda: self.load_installed_apps(show_message=False))
            QTimer.singleShot(10000, lambda: self.load_installed_apps(show_message=False))
        except Exception as exc:  # pragma: no cover - Windows shell dependent
            QMessageBox.warning(self, "软件卸载", f"启动卸载失败: {exc}")

    @staticmethod
    def normalize_uninstall_command(command):
        lowered = command.lower()
        if "msiexec" in lowered and " /i" in lowered:
            command = command.replace(" /I", " /X").replace(" /i", " /X")
        return command

    def refresh_account_state(self, message=None):
        self.account_state = self.account_service.current_state()
        if not hasattr(self, "account_status_title"):
            return

        user = self.account_state.get("user")
        if user:
            self.account_status_title.setText(user.get("displayName") or user.get("email", "已登录"))
            self.account_status_detail.setText(user.get("email", ""))
            subscription = user.get("subscription")
            if subscription:
                self.account_plan_label.setText(
                    f"当前权益: {subscription.get('planName', '专业会员')}，剩余 {subscription.get('remainingDays', 0)} 天"
                )
            else:
                self.account_plan_label.setText("当前权益: Free，登录后可兑换会员卡密")
            self.account_logout_button.setEnabled(True)
        else:
            self.account_status_title.setText("未登录")
            self.account_status_detail.setText("请先登录或注册账户，再兑换会员卡。")
            self.account_plan_label.setText("当前权益: Guest")
            self.account_logout_button.setEnabled(False)

        if message:
            self.account_message_label.setText(message)
            self.animate_status_pulse(self.account_message_label)

    def account_credentials(self):
        return (
            self.account_email_input.text().strip(),
            self.account_password_input.text(),
            self.account_name_input.text().strip(),
        )

    def register_account(self):
        email, password, display_name = self.account_credentials()
        try:
            self.account_service.register(email, password, display_name)
            self.account_password_input.clear()
            self.refresh_account_state("注册并登录成功。")
        except AccountError as exc:
            self.refresh_account_state(str(exc))

    def login_account(self):
        email, password, _display_name = self.account_credentials()
        try:
            self.account_service.login(email, password)
            self.account_password_input.clear()
            self.refresh_account_state("登录成功。")
        except AccountError as exc:
            self.refresh_account_state(str(exc))

    def logout_account(self):
        self.account_service.logout()
        self.refresh_account_state("已退出登录。")

    def redeem_account_card(self):
        try:
            result = self.account_service.redeem_card(self.card_code_input.text())
            self.card_code_input.clear()
            self.refresh_account_state(result["message"])
        except AccountError as exc:
            self.refresh_account_state(str(exc))

    def scan_large_files(self):
        """在文件管理页内扫描大文件并填充表格。"""
        root_dir = self.current_file_scan_root()
        if hasattr(self, "file_tabs"):
            self.file_tabs.setCurrentWidget(self.file_large_table)
        self.file_status_label.setText(f"正在扫描大文件: {root_dir}")
        self.start_file_scan_thread("large", root_dir)

    def scan_duplicate_files(self):
        """在文件管理页内按大小+SHA256 查找重复文件。"""
        root_dir = self.current_file_scan_root()
        if hasattr(self, "file_tabs"):
            self.file_tabs.setCurrentWidget(self.file_duplicate_table)
        self.file_status_label.setText(f"正在扫描重复文件: {root_dir}")
        self.start_file_scan_thread("duplicates", root_dir)

    def set_file_scan_controls_enabled(self, enabled):
        for button_name in ("scan_large_button", "scan_duplicate_button"):
            if hasattr(self, button_name):
                getattr(self, button_name).setEnabled(enabled)

    def start_file_scan_thread(self, mode, root_dir):
        if self.file_scan_thread and self.file_scan_thread.isRunning():
            QMessageBox.information(self, "文件管理", "文件扫描正在进行，请稍后。")
            return

        self.set_file_scan_controls_enabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        thread = FileScanThread(mode, root_dir)
        self.file_scan_thread = thread
        thread.file_scan_finished_signal.connect(self.on_file_scan_finished)
        thread.file_scan_error_signal.connect(self.on_file_scan_error)
        thread.finished.connect(lambda: self.set_file_scan_controls_enabled(True))
        thread.finished.connect(lambda: setattr(self, "file_scan_thread", None))
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: QApplication.restoreOverrideCursor())
        thread.start()

    def on_file_scan_finished(self, mode, payload):
        if mode == "large":
            self.file_large_items = payload
            self.populate_large_files_table(self.file_large_items)
            total_size = sum(item["size"] for item in self.file_large_items)
            self.file_status_label.setText(
                f"大文件扫描完成: {len(self.file_large_items)} 个，合计 {self.format_size(total_size)}"
            )
            self.animate_status_pulse(self.file_status_label)
            return

        if mode == "duplicates":
            self.file_duplicate_groups = payload
            total_waste = 0
            for size, paths in self.file_duplicate_groups:
                total_waste += size * (len(paths) - 1)
            self.populate_duplicate_files_table(self.file_duplicate_groups)
            self.file_status_label.setText(
                f"重复文件扫描完成: {len(self.file_duplicate_groups)} 组，约可处理 {self.format_size(total_waste)}"
            )
            self.animate_status_pulse(self.file_status_label)

    def on_file_scan_error(self, mode, message):
        labels = {
            "large": "大文件扫描",
            "duplicates": "重复文件扫描",
        }
        label = labels.get(mode, "文件扫描")
        self.file_status_label.setText(f"{label}失败: {message}")
        QMessageBox.warning(self, "文件管理", f"{label}失败:\n{message}")

    def default_file_scan_root(self):
        if sys.platform.startswith("win"):
            return os.environ.get("SystemDrive", "C:") + os.sep
        return os.path.expanduser("~")

    def current_file_scan_root(self):
        return self.file_scan_root or self.default_file_scan_root()

    def select_file_scan_root(self):
        selected = QFileDialog.getExistingDirectory(
            self,
            "选择文件扫描目录",
            self.current_file_scan_root(),
        )
        if selected:
            self.file_scan_root = selected
            self.file_root_label.setText(f"扫描目录: {selected}")
            self.file_status_label.setText("已更新扫描目录。")

    def find_large_files(self, root_dir, min_size=100 * 1024 * 1024, max_files=5000):
        large_files = []
        scanned = 0
        for root, _dirs, files in os.walk(root_dir):
            for file_name in files:
                if scanned >= max_files:
                    break
                path = os.path.join(root, file_name)
                try:
                    if not os.path.isfile(path):
                        continue
                    scanned += 1
                    size = os.path.getsize(path)
                    if size >= min_size:
                        large_files.append({
                            "path": path,
                            "size": size,
                            "name": file_name,
                        })
                except (OSError, PermissionError):
                    continue
            if scanned >= max_files:
                break
        large_files.sort(key=lambda item: item["size"], reverse=True)
        return large_files[:200]

    def populate_large_files_table(self, items):
        if not hasattr(self, "file_large_table"):
            return
        self.file_large_table.setSortingEnabled(False)
        self.file_large_table.setRowCount(0)
        for row_index, item in enumerate(items):
            self.file_large_table.insertRow(row_index)
            path = item["path"]
            name_item = QTableWidgetItem(os.path.basename(path) or path)
            if os.path.exists(path):
                name_item.setIcon(self.icon_provider.icon(QFileInfo(path)))
            name_item.setToolTip(path)
            self.file_large_table.setItem(row_index, 0, name_item)

            size_item = QTableWidgetItem(self.format_size(item["size"]))
            size_item.setData(Qt.UserRole, item["size"])
            self.file_large_table.setItem(row_index, 1, size_item)

            path_item = QTableWidgetItem(path)
            path_item.setToolTip(path)
            path_item.setData(Qt.UserRole, {"path": path, "size": item["size"], "mode": "large"})
            self.file_large_table.setItem(row_index, 2, path_item)

            self.file_large_table.setCellWidget(
                row_index,
                3,
                self._make_file_action_widget({"path": path, "size": item["size"], "mode": "large"}),
            )
            self.file_large_table.setRowHeight(row_index, 34)
        self.file_large_table.setSortingEnabled(True)

    def populate_duplicate_files_table(self, duplicates):
        if not hasattr(self, "file_duplicate_table"):
            return
        self.file_duplicate_table.setSortingEnabled(False)
        self.file_duplicate_table.setRowCount(0)
        row_index = 0
        for group_index, (size, paths) in enumerate(duplicates, start=1):
            for path_offset, path in enumerate(paths):
                self.file_duplicate_table.insertRow(row_index)
                name_item = QTableWidgetItem(os.path.basename(path) or path)
                if os.path.exists(path):
                    name_item.setIcon(self.icon_provider.icon(QFileInfo(path)))
                name_item.setToolTip(path)
                self.file_duplicate_table.setItem(row_index, 0, name_item)

                size_item = QTableWidgetItem(self.format_size(size))
                size_item.setData(Qt.UserRole, size)
                self.file_duplicate_table.setItem(row_index, 1, size_item)
                self.file_duplicate_table.setItem(row_index, 2, QTableWidgetItem(f"第 {group_index} 组"))

                path_item = QTableWidgetItem(path)
                path_item.setToolTip(path)
                path_item.setData(
                    Qt.UserRole,
                    {
                        "path": path,
                        "size": size,
                        "mode": "duplicate",
                        "group": group_index,
                        "keep": path_offset == 0,
                    },
                )
                self.file_duplicate_table.setItem(row_index, 3, path_item)

                self.file_duplicate_table.setCellWidget(
                    row_index,
                    4,
                    self._make_file_action_widget(
                        {
                            "path": path,
                            "size": size,
                            "mode": "duplicate",
                            "group": group_index,
                            "keep": path_offset == 0,
                        }
                    ),
                )
                self.file_duplicate_table.setRowHeight(row_index, 34)
                row_index += 1
        self.file_duplicate_table.setSortingEnabled(True)

    def _make_file_action_widget(self, payload):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        open_button = QPushButton("打开")
        open_button.setObjectName("miniActionButton")
        open_button.setCursor(Qt.PointingHandCursor)
        open_button.setMinimumWidth(64)
        open_button.clicked.connect(lambda _checked=False, target=payload["path"]: self.open_file_location(target))

        delete_button = QPushButton("保留" if payload.get("keep") else "删除")
        delete_button.setObjectName("miniActionButton")
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setMinimumWidth(64)
        delete_button.setEnabled(not payload.get("keep", False))
        delete_button.clicked.connect(lambda _checked=False, target=dict(payload): self.delete_file_payloads([target]))

        layout.addWidget(open_button)
        layout.addWidget(delete_button)
        layout.addStretch(1)
        return widget

    def _make_open_location_button(self, path):
        button = QPushButton("打开位置")
        button.setObjectName("miniActionButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumWidth(86)
        button.clicked.connect(lambda _checked=False, target=path: self.open_file_location(target))
        return button

    def open_file_location(self, path):
        directory = path if os.path.isdir(path) else os.path.dirname(path)
        if not directory:
            return
        if sys.platform.startswith("win"):
            try:
                os.startfile(directory)  # noqa: P201 - Windows 专用
            except Exception as exc:  # pragma: no cover - Windows shell dependent
                QMessageBox.warning(self, "打开位置", f"无法打开位置: {exc}")
            return
        QMessageBox.information(self, "打开位置", f"此操作将在 Windows 上打开:\n{directory}")

    def current_file_table_config(self):
        if self.file_tabs.currentWidget() is self.file_duplicate_table:
            return self.file_duplicate_table, 3, "duplicate"
        return self.file_large_table, 2, "large"

    def selected_file_payloads(self):
        table, path_column, _mode = self.current_file_table_config()
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows and table.currentRow() >= 0:
            selected_rows = [table.model().index(table.currentRow(), 0)]

        payloads = []
        for model_index in selected_rows:
            item = table.item(model_index.row(), path_column)
            payload = item.data(Qt.UserRole) if item else None
            if payload:
                payloads.append(payload)
        return payloads

    def delete_selected_files(self):
        payloads = self.selected_file_payloads()
        if not payloads:
            self.file_status_label.setText("请先选择需要删除的文件。")
            self.animate_status_pulse(self.file_status_label)
            return
        self.delete_file_payloads(payloads)

    def delete_duplicate_copies(self):
        payloads = []
        for group_index, (size, paths) in enumerate(self.file_duplicate_groups, start=1):
            for path in paths[1:]:
                payloads.append({
                    "path": path,
                    "size": size,
                    "mode": "duplicate",
                    "group": group_index,
                    "keep": False,
                })
        if not payloads:
            self.file_status_label.setText("没有可删除的重复副本。")
            self.animate_status_pulse(self.file_status_label)
            return
        self.file_tabs.setCurrentWidget(self.file_duplicate_table)
        self.delete_file_payloads(payloads)

    def delete_file_payloads(self, payloads):
        backup_dir = self.file_delete_backup_dir() if self.cleaner.options.get("backup", True) else None
        deleted_count = 0
        skipped_count = 0
        freed_bytes = 0
        errors = []

        for payload in payloads:
            path = payload.get("path")
            if payload.get("keep"):
                skipped_count += 1
                continue
            if not path or not self.is_user_deletable_file(path):
                skipped_count += 1
                continue
            try:
                freed_bytes += self.delete_file_path(path, backup_dir=backup_dir)
                deleted_count += 1
            except Exception as exc:  # pragma: no cover - filesystem dependent
                errors.append(f"{path}: {exc}")

        self.refresh_file_tables_after_delete()
        status = f"已删除 {deleted_count} 个文件，释放 {self.format_size(freed_bytes)}"
        if skipped_count:
            status += f"，跳过 {skipped_count} 个受保护/保留项"
        if errors:
            status += f"，失败 {len(errors)} 个"
        self.file_status_label.setText(status)
        self.animate_status_pulse(self.file_status_label)

    def file_delete_backup_dir(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.cleaner.backup_dir, f"file_manager_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    def delete_file_path(self, path, backup_dir=None):
        previous_simulate = self.cleaner.options.get("simulate", True)
        self.cleaner.options["simulate"] = False
        try:
            return self.cleaner._clean_file(path, backup_dir)
        finally:
            self.cleaner.options["simulate"] = previous_simulate

    def is_user_deletable_file(self, path):
        if not path or not os.path.isfile(path):
            return False
        file_name = os.path.basename(path).lower()
        if file_name in {"pagefile.sys", "hiberfil.sys", "swapfile.sys"}:
            return False
        normalized = path.replace("/", "\\").lower()
        protected_roots = (
            "c:\\windows\\",
            "c:\\program files\\",
            "c:\\program files (x86)\\",
        )
        return not any(normalized.startswith(root) for root in protected_roots)

    def refresh_file_tables_after_delete(self):
        self.file_large_items = [
            item for item in self.file_large_items
            if os.path.exists(item.get("path", ""))
        ]
        self.file_duplicate_groups = [
            (size, [path for path in paths if os.path.exists(path)])
            for size, paths in self.file_duplicate_groups
        ]
        self.file_duplicate_groups = [
            (size, paths) for size, paths in self.file_duplicate_groups
            if len(paths) > 1
        ]
        self.populate_large_files_table(self.file_large_items)
        self.populate_duplicate_files_table(self.file_duplicate_groups)

    def _find_duplicate_files(self, root_dir, max_files=5000):
        by_size = {}
        scanned = 0
        for root, _dirs, files in os.walk(root_dir):
            for file_name in files:
                if scanned >= max_files:
                    break
                path = os.path.join(root, file_name)
                try:
                    if not os.path.isfile(path):
                        continue
                    size = os.path.getsize(path)
                    if size <= 0:
                        continue
                    by_size.setdefault(size, []).append(path)
                    scanned += 1
                except (OSError, PermissionError):
                    continue

        duplicates = []
        for size, paths in by_size.items():
            if len(paths) < 2:
                continue
            by_digest = {}
            for path in paths:
                digest = self._file_digest(path)
                if digest:
                    by_digest.setdefault(digest, []).append(path)
            for digest_paths in by_digest.values():
                if len(digest_paths) > 1:
                    duplicates.append((size, digest_paths))

        duplicates.sort(key=lambda group: group[0] * (len(group[1]) - 1), reverse=True)
        return duplicates

    @staticmethod
    def _file_digest(path):
        digest = hashlib.sha256()
        try:
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except (OSError, PermissionError):
            return None

    def update_disk_info(self):
        """更新磁盘信息"""
        disk_info = self.cleaner.get_disk_info()
        self.disk_info_label.setText(
            f"C盘总空间: {disk_info['total']:.2f} GB | "
            f"已用空间: {disk_info['used']:.2f} GB ({disk_info['percent']}%) | "
            f"可用空间: {disk_info['free']:.2f} GB"
        )
        self.total_value_label.setText(f"{disk_info['total']:.2f} GB")
        self.used_value_label.setText(f"{disk_info['used']:.2f} GB")
        self.free_value_label.setText(f"{disk_info['free']:.2f} GB")

    def start_scan(self):
        """开始扫描系统"""
        self.scan_button.setEnabled(False)
        self.scan_button.setText("扫描中...")
        self.clean_all_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.select_all_checkbox.setEnabled(False)
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(False)
        self.select_all_checkbox.blockSignals(False)
        self.results_tree.clear()
        self.scan_results = {}
        self.selected_items = []
        self.cleanable_items = []
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.current_scan_path_label.setVisible(True)
        self.current_scan_path_label.setText("当前扫描: 正在准备扫描 C 盘路径...")
        self.current_scan_path_label.setToolTip("")
        self.cleanable_value_label.setText("0 B")
        self.result_summary_label.setText("扫描进行中")
        self.selected_summary_label.setText("已选 0 项 / 0 B")
        self.status_label.setText("正在扫描系统，请稍候...")
        self.animate_status_pulse(self.current_scan_path_label)

        # 启动扫描线程
        self.scan_thread = ScanThread(self.cleaner)
        self.scan_thread.update_signal.connect(self.on_scan_progress)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.error_signal.connect(self.on_scan_error)
        self.scan_thread.start()

    def on_scan_progress(self, path, count):
        """实时展示扫描线程正在处理或刚发现的路径。"""
        compact = self.compact_path(path)
        if count > 0:
            message = f"当前扫描: {compact}"
        else:
            message = f"当前扫描项: {compact}"
        self.current_scan_path_label.setVisible(True)
        self.current_scan_path_label.setText(message)
        self.current_scan_path_label.setToolTip(path)
        self.status_label.setText(message)

    def on_scan_finished(self, results):
        """扫描完成后的处理"""
        self.scan_results = results
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self.scan_button.setText("重新扫描")
        self.current_scan_path_label.setVisible(True)
        self.current_scan_path_label.setText("当前扫描: 扫描完成，正在整理结果")
        self.animate_status_pulse(self.current_scan_path_label)

        total_items = self.refresh_cleanable_totals()

        if not results or total_items == 0:
            self.status_label.setText("扫描完成，未发现可清理项目")
            self.update_selected_items()
            return

        # 填充结果树
        self.populate_results_tree(results)
        self.select_all_checkbox.setEnabled(total_items > 0)
        self.clean_all_button.setEnabled(bool(self.cleanable_items))
        self.update_selected_items()

        # 更新磁盘信息
        self.update_disk_info()

    def on_scan_error(self, message):
        """扫描线程异常回传。"""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self.scan_button.setText("重新扫描")
        self.current_scan_path_label.setVisible(True)
        self.current_scan_path_label.setText(f"当前扫描: 失败 - {message}")
        self.clean_all_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.select_all_checkbox.setEnabled(False)
        self.status_label.setText(f"扫描失败: {message}")
        QMessageBox.warning(self, "扫描错误", f"扫描过程中出错:\n{message}")

    @staticmethod
    def display_name_from_path(path):
        """从 Windows 或 POSIX 路径中提取用于树节点的短名称。"""
        normalized = path.rstrip("\\/")
        if not normalized:
            return path
        return normalized.replace("\\", "/").rsplit("/", 1)[-1] or normalized

    @staticmethod
    def compact_path(path, max_length=128):
        if len(path) <= max_length:
            return path
        keep = max(24, (max_length - 5) // 2)
        return f"{path[:keep]} ... {path[-keep:]}"

    def professional_mode_enabled(self):
        return self.current_clean_mode() == "professional"

    def full_clean_mode_enabled(self):
        return hasattr(self, "select_all_checkbox") and self.select_all_checkbox.isChecked()

    def current_clean_mode(self):
        if self.full_clean_mode_enabled():
            return "all"
        if hasattr(self, "professional_checkbox") and self.professional_checkbox.isChecked():
            return "professional"
        return "recommended"

    def clean_mode_name(self):
        names = {
            "recommended": "推荐",
            "professional": "专业",
            "all": "全选",
        }
        return names.get(self.current_clean_mode(), "推荐")

    def set_clean_mode(self, mode):
        checkbox_map = {
            "recommended": self.recommended_checkbox,
            "professional": self.professional_checkbox,
            "all": self.select_all_checkbox,
        }
        for checkbox in checkbox_map.values():
            checkbox.blockSignals(True)
        try:
            self.recommended_checkbox.setChecked(mode == "recommended")
            self.professional_checkbox.setChecked(mode == "professional")
            self.select_all_checkbox.setChecked(mode == "all")
        finally:
            for checkbox in checkbox_map.values():
                checkbox.blockSignals(False)

    @staticmethod
    def is_scan_only_item(item):
        """截图补充路径中不少条目只能统计，不能直接清理。"""
        return bool(item.get("scan_only"))

    def allow_item_cleaning(self, item):
        mode = self.current_clean_mode()
        if mode == "all":
            return True
        if mode == "professional":
            return self.is_scan_only_item(item)
        return not self.is_scan_only_item(item)

    def is_cleanable_item(self, item):
        return self.allow_item_cleaning(item)

    def on_clean_mode_changed(self, _state):
        """推荐/专业模式切换后，重新计算可清理项和勾选状态。"""
        sender = self.sender()
        if sender is self.professional_checkbox and self.professional_checkbox.isChecked():
            self.set_clean_mode("professional")
        elif sender is self.recommended_checkbox and self.recommended_checkbox.isChecked():
            self.set_clean_mode("recommended")
        elif not self.recommended_checkbox.isChecked() and not self.professional_checkbox.isChecked():
            self.set_clean_mode("recommended")

        if self.scan_results:
            self.refresh_cleanable_totals()
            self.update_result_tree_cleanability()
            self.select_all_checkbox.setEnabled(bool(self.scan_results))
            self.clean_all_button.setEnabled(bool(self.cleanable_items))
            self.uncheck_items_outside_current_mode()
            self.update_selected_items()

    def refresh_cleanable_totals(self):
        total_items = sum(len(items) for items in self.scan_results.values())
        total_size = sum(item['size'] for category in self.scan_results.values() for item in category)
        self.cleanable_items = [
            item
            for category in self.scan_results.values()
            for item in category
            if self.is_cleanable_item(item)
        ]
        cleanable_size = sum(item['size'] for item in self.cleanable_items)
        category_count = sum(1 for items in self.scan_results.values() if items)
        mode_name = self.clean_mode_name()
        self.cleanable_value_label.setText(self.format_size(cleanable_size))
        self.result_summary_label.setText(
            f"{mode_name}模式 / {category_count} 类 / {total_items} 项 / 统计 {self.format_size(total_size)} / 可清理 {self.format_size(cleanable_size)}"
        )
        if total_items:
            self.status_label.setText(
                f"扫描完成，统计空间 {self.format_size(total_size)}，{mode_name}可释放 {self.format_size(cleanable_size)}"
            )
        return total_items

    def category_icon_for_name(self, name):
        """按目标名称/路径尽量取系统真实图标，失败时回退到应用图标。"""
        value = (name or "").lower()
        candidates = []
        if name and os.path.exists(str(name)):
            candidates.append(str(name))
        if "edgecore" in value or "edge" in value or "msedge" in value:
            candidates.extend([
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ])
        if "chrome" in value or "chromium" in value:
            candidates.extend([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ])
        if "internet explorer" in value or value == "ie" or "inetcpl" in value:
            candidates.append(r"C:\Program Files\Internet Explorer\iexplore.exe")
        if "defender" in value or "mpcmd" in value or "security" in value:
            candidates.extend([
                r"C:\Program Files\Windows Defender\MSASCui.exe",
                r"C:\ProgramData\Microsoft\Windows Defender",
            ])
        if "onedrive" in value:
            candidates.append(r"C:\Program Files\Microsoft OneDrive\OneDrive.exe")
        if "todesk" in value:
            candidates.extend([
                r"C:\Program Files\ToDesk\ToDesk.exe",
                r"C:\Program Files (x86)\ToDesk\ToDesk.exe",
            ])
        if "uu" in value:
            candidates.append(r"C:\Program Files (x86)\Netease\UU\uu.exe")
        if "nvidia" in value:
            candidates.append(r"C:\Program Files\NVIDIA Corporation")
        if "intel" in value:
            candidates.append(r"C:\Intel")
        if "drvpath" in value or "driver" in value:
            candidates.append(r"C:\DrvPath")
        if "win" in value or "system" in value or "registry" in value or "update" in value:
            candidates.extend([
                r"C:\Windows\explorer.exe",
                r"C:\Windows\System32\shell32.dll",
                r"C:\Windows",
            ])

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return self.icon_provider.icon(QFileInfo(candidate))
        return self.app_icon

    def target_icon_for_item(self, item):
        path = item.get("path", "")
        if path and os.path.exists(path):
            return self.icon_provider.icon(QFileInfo(path))
        return self.category_icon_for_name(
            item.get("type") or item.get("category") or path
        )

    def item_display_text(self, item):
        item_name = self.display_name_from_path(item.get('path', ''))
        if self.is_scan_only_item(item) and self.is_cleanable_item(item):
            return f"{item_name} [专业]"
        if self.is_scan_only_item(item):
            return f"{item_name} [仅统计]"
        return item_name

    def update_result_child_cleanability(self, child_item):
        item = child_item.data(0, Qt.UserRole) or {}
        cleanable = self.is_cleanable_item(item)
        scan_only = self.is_scan_only_item(item)
        mode = self.current_clean_mode()

        child_item.setText(0, self.item_display_text(item))
        child_item.setDisabled(not cleanable)
        if not cleanable:
            child_item.setCheckState(0, Qt.Unchecked)
            if mode == "professional":
                child_item.setToolTip(0, "推荐项，请切换到推荐或全选模式清理")
            else:
                child_item.setToolTip(0, "专业项，请切换到专业或全选模式清理")
        elif scan_only:
            child_item.setToolTip(0, "专业清理项")
        else:
            child_item.setToolTip(0, "推荐清理项")
        return cleanable

    def update_result_tree_cleanability(self):
        self.results_tree.setUpdatesEnabled(False)
        self.results_tree.blockSignals(True)
        try:
            for i in range(self.results_tree.topLevelItemCount()):
                category_item = self.results_tree.topLevelItem(i)
                cleanable_count = 0
                category_size = 0
                category_cleanable_size = 0

                for j in range(category_item.childCount()):
                    child_item = category_item.child(j)
                    item = child_item.data(0, Qt.UserRole) or {}
                    item_size = item.get('size', 0)
                    category_size += item_size
                    if self.update_result_child_cleanability(child_item):
                        cleanable_count += 1
                        category_cleanable_size += item_size

                total_count = category_item.childCount()
                if cleanable_count:
                    category_item.setDisabled(False)
                    category_item.setText(
                        2,
                        f"{cleanable_count} 项可清理 / {total_count - cleanable_count} 项仅统计",
                    )
                else:
                    category_item.setDisabled(True)
                    category_item.setCheckState(0, Qt.Unchecked)
                    category_item.setText(2, f"{total_count} 项路径 / 仅统计")
                category_item.setToolTip(
                    1,
                    f"统计 {self.format_size(category_size)}，可清理 {self.format_size(category_cleanable_size)}",
                )
        finally:
            self.results_tree.blockSignals(False)
            self.results_tree.setUpdatesEnabled(True)

    def populate_results_tree(self, results):
        """填充结果树"""
        self.results_tree.setUpdatesEnabled(False)
        self.results_tree.blockSignals(True)
        self.results_tree.clear()
        category_font = QFont()
        category_font.setBold(True)

        for category, items in results.items():
            if not items:
                continue

            category_size = sum(item['size'] for item in items)
            category_cleanable = [item for item in items if self.is_cleanable_item(item)]
            category_cleanable_size = sum(item['size'] for item in category_cleanable)
            category_name = category_tree_label(category)

            category_item = QTreeWidgetItem(self.results_tree)
            category_item.setText(0, category_name)
            category_item.setText(1, self.format_size(category_size))
            if category_cleanable:
                category_item.setText(
                    2,
                    f"{len(category_cleanable)} 项可清理 / {len(items) - len(category_cleanable)} 项仅统计",
                )
            else:
                category_item.setText(2, f"{len(items)} 项路径 / 仅统计")
            category_item.setFont(0, category_font)
            category_item.setFont(1, category_font)
            category_icon = self.category_icon_for_name(category_name)
            if not category_icon.isNull():
                category_item.setIcon(0, category_icon)
            category_item.setFlags(category_item.flags() | Qt.ItemIsUserCheckable)
            category_item.setCheckState(0, Qt.Unchecked)
            if not category_cleanable:
                category_item.setDisabled(True)
            category_item.setToolTip(
                1,
                f"统计 {self.format_size(category_size)}，可清理 {self.format_size(category_cleanable_size)}",
            )

            for item in items:
                item_path = item['path']
                cleanable = self.is_cleanable_item(item)
                file_item = QTreeWidgetItem(category_item)
                file_item.setText(0, self.item_display_text(item))
                file_item.setText(1, self.format_size(item['size']))
                file_item.setText(2, item_path)
                file_item.setIcon(0, self.target_icon_for_item(item))
                file_item.setToolTip(2, item_path)
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Unchecked)
                file_item.setData(0, Qt.UserRole, item)
                self.update_result_child_cleanability(file_item)

        self.results_tree.expandAll()
        self.results_tree.blockSignals(False)
        self.results_tree.setUpdatesEnabled(True)

    def uncheck_items_outside_current_mode(self):
        self.results_tree.setUpdatesEnabled(False)
        self.results_tree.blockSignals(True)
        try:
            for i in range(self.results_tree.topLevelItemCount()):
                category_item = self.results_tree.topLevelItem(i)
                checked_children = 0
                cleanable_children = 0
                for j in range(category_item.childCount()):
                    child_item = category_item.child(j)
                    item_data = child_item.data(0, Qt.UserRole) or {}
                    if not self.is_cleanable_item(item_data):
                        child_item.setCheckState(0, Qt.Unchecked)
                    else:
                        cleanable_children += 1
                        if child_item.checkState(0) == Qt.Checked:
                            checked_children += 1

                if checked_children and checked_children == cleanable_children:
                    category_item.setCheckState(0, Qt.Checked)
                elif checked_children:
                    category_item.setCheckState(0, Qt.PartiallyChecked)
                else:
                    category_item.setCheckState(0, Qt.Unchecked)
        finally:
            self.results_tree.blockSignals(False)
            self.results_tree.setUpdatesEnabled(True)

    def on_select_all_changed(self, state):
        """顶部“全选”模式：勾选推荐项和专业项。"""
        if state == Qt.Checked:
            self.set_clean_mode("all")
            if self.scan_results:
                self.refresh_cleanable_totals()
                self.update_result_tree_cleanability()
        elif not self.recommended_checkbox.isChecked() and not self.professional_checkbox.isChecked():
            self.set_clean_mode("recommended")
            if self.scan_results:
                self.refresh_cleanable_totals()
                self.update_result_tree_cleanability()

        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        self.results_tree.setUpdatesEnabled(False)
        self.results_tree.blockSignals(True)
        try:
            for i in range(self.results_tree.topLevelItemCount()):
                category_item = self.results_tree.topLevelItem(i)
                if category_item.isDisabled():
                    category_item.setCheckState(0, Qt.Unchecked)
                    continue
                category_item.setCheckState(0, check_state)
                for j in range(category_item.childCount()):
                    child_item = category_item.child(j)
                    item_data = child_item.data(0, Qt.UserRole) or {}
                    if child_item.isDisabled() or not self.is_cleanable_item(item_data):
                        child_item.setCheckState(0, Qt.Unchecked)
                        continue
                    child_item.setCheckState(0, check_state)
        finally:
            self.results_tree.blockSignals(False)
            self.results_tree.setUpdatesEnabled(True)
        self.update_selected_items()

    def on_item_changed(self, item, column):
        """处理项目选择状态变化"""
        if column != 0:
            return

        # 如果是类别项，同步所有子项
        if item.parent() is None:
            check_state = item.checkState(0)
            self.results_tree.setUpdatesEnabled(False)
            self.results_tree.blockSignals(True)
            try:
                for i in range(item.childCount()):
                    child_item = item.child(i)
                    item_data = child_item.data(0, Qt.UserRole) or {}
                    if child_item.isDisabled() or not self.is_cleanable_item(item_data):
                        child_item.setCheckState(0, Qt.Unchecked)
                        continue
                    child_item.setCheckState(0, check_state)
            finally:
                self.results_tree.blockSignals(False)
                self.results_tree.setUpdatesEnabled(True)

        # 更新选中项列表
        self.update_selected_items()

    def update_selected_items(self):
        """更新选中的项目列表"""
        self.selected_items = []

        for i in range(self.results_tree.topLevelItemCount()):
            category_item = self.results_tree.topLevelItem(i)

            for j in range(category_item.childCount()):
                child_item = category_item.child(j)
                if child_item.checkState(0) == Qt.Checked:
                    item_data = child_item.data(0, Qt.UserRole)
                    if item_data and self.is_cleanable_item(item_data):
                        self.selected_items.append(item_data)

        selected_size = sum(item['size'] for item in self.selected_items)
        self.selected_summary_label.setText(
            f"已选 {len(self.selected_items)} 项 / {self.format_size(selected_size)}"
        )
        self.clean_button.setEnabled(len(self.selected_items) > 0)
        self.clean_all_button.setEnabled(len(self.cleanable_items) > 0)

    def start_clean(self):
        """开始清理选中的项目"""
        if not self.selected_items:
            return
        self.start_clean_items(self.selected_items, "清理选中")

    def start_clean_all(self):
        """一键清理当前模式下的全部可清理项目。"""
        if not self.cleanable_items:
            QMessageBox.information(self, "一键清理", "当前模式没有可清理项目。")
            return
        self.start_clean_items(self.cleanable_items, "一键清理")

    def start_clean_items(self, items, action_label):
        """启动清理线程，items 必须已经过滤为当前模式可清理项。"""
        clean_items = [item for item in items if self.is_cleanable_item(item)]
        if not clean_items:
            QMessageBox.information(self, action_label, "没有可清理项目")
            return

        total_size = sum(item['size'] for item in clean_items)
        professional_items = [item for item in clean_items if self.is_scan_only_item(item)]
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(f"确认{action_label}")

        if self.simulate_checkbox.isChecked():
            msg.setText(
                f"您选择了模拟模式，将会模拟{action_label} {len(clean_items)} 个项目，"
                f"总计 {self.format_size(total_size)}。"
            )
        else:
            msg.setText(
                f"您确定要{action_label} {len(clean_items)} 个项目，"
                f"总计 {self.format_size(total_size)} 吗？"
            )
            if professional_items:
                msg.setInformativeText(
                    f"其中包含 {len(professional_items)} 个专业清理项。"
                    "这些路径可能属于 WinSxS、WindowsApps、Defender、EdgeCore 或系统组件缓存，"
                    "删除后可能影响系统更新、应用恢复或安全记录。此操作无法撤销！"
                )
            else:
                msg.setInformativeText("此操作无法撤销！")

        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec_() != QMessageBox.Yes:
            return

        # 设置清理选项
        self.cleaner.set_options({
            'simulate': self.simulate_checkbox.isChecked(),
            'backup': self.backup_checkbox.isChecked(),
            'backup_dir': self.cleaner.backup_dir,
            'allow_scan_only_clean': self.current_clean_mode() in {"professional", "all"},
        })

        # 开始清理
        self.scan_button.setEnabled(False)
        self.clean_all_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.clean_all_button.setText("清理中...")
        self.clean_button.setText("清理中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, len(clean_items))
        self.status_label.setText("正在清理文件，请稍候...")
        self.animate_status_pulse(self.status_label)

        # 启动清理线程
        self.clean_thread = CleanThread(self.cleaner, list(clean_items))
        self.clean_thread.update_signal.connect(self.on_clean_progress)
        self.clean_thread.finished_signal.connect(self.on_clean_finished)
        self.clean_thread.error_signal.connect(self.on_clean_error)
        self.clean_thread.start()

    def on_clean_progress(self, file_path, progress):
        """清理进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"正在清理: {self.display_name_from_path(file_path)}")

    def on_clean_finished(self, results):
        """清理完成后的处理"""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self.scan_button.setText("重新扫描")
        self.clean_all_button.setText("一键清理")
        self.clean_button.setText("清理选中")

        freed_space = results.get('freed_space', 0)
        errors = results.get('errors', [])

        if self.simulate_checkbox.isChecked():
            message = f"模拟清理完成，可释放空间: {self.format_size(freed_space)}"
        else:
            message = f"清理完成，已释放空间: {self.format_size(freed_space)}"

        if errors:
            message += f"，{len(errors)} 个错误"

        self.status_label.setText(message)
        self.animate_status_pulse(self.status_label)
        self.update_selected_items()

        # 如果有错误，显示错误日志
        if errors:
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("清理错误")
            error_msg.setText(f"清理过程中发生 {len(errors)} 个错误")
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            error_msg.setDetailedText(error_details)
            error_msg.exec_()

        # 更新磁盘信息；真实清理后重新扫描，避免树里残留已删除路径。
        self.update_disk_info()
        if not self.simulate_checkbox.isChecked():
            self.status_label.setText(f"{message}，正在重新扫描...")
            self.start_scan()

    def on_clean_error(self, message):
        """清理线程异常回传。"""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self.scan_button.setText("重新扫描")
        self.clean_all_button.setText("一键清理")
        self.clean_button.setText("清理选中")
        self.update_selected_items()
        self.status_label.setText(f"清理失败: {message}")
        QMessageBox.warning(self, "清理错误", f"清理过程中出错:\n{message}")

    @staticmethod
    def format_size(size_bytes):
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"


def main():
    """Qt应用入口，用于源码运行和PyInstaller打包。"""
    app = QApplication(sys.argv)
    window = CleanerMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
