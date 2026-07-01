#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 用户界面
"""

import os
import sys
import subprocess
import shutil
import hashlib
import datetime
import re
import csv
import webbrowser
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
                            QTextEdit, QAbstractButton, QStyledItemDelegate, QStyle,
                            QMenu, QDialog, QDialogButtonBox, QInputDialog, QFormLayout)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QFileInfo, QPropertyAnimation, QEasingCurve,
    QTimer, QRect
)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPainter

from cleaner_logic import CleanerLogic
from category_display import category_tree_label
from file_migration import FileMigrationService, MigrationError
from folder_hints import folder_tooltip
from config import APP_NAME, ACCOUNT_API_BASE_URL, USE_REMOTE_ACCOUNT
from local_account_service import AccountError, LocalAccountService
from remote_account_service import RemoteAccountService
from qt_backup_manager import QtBackupManagerDialog
from registry_cleaner import RegistryCleanerService
from system_repair import SystemRepairService, decode_console_output


APP_DISPLAY_NAME = "C盘清理精灵"


class BXToggleSwitch(QAbstractButton):
    """BoosterX 风格的滑动开关：开=蓝色(向右)，关=红色(向左)。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(48, 26)

    def sizeHint(self):
        return QSize(48, 26)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2
        track = QColor("#2F6BFF") if self.isChecked() else QColor("#E5484D")
        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(rect, radius, radius)

        diameter = rect.height() - 6
        knob_x = rect.right() - diameter - 3 if self.isChecked() else rect.left() + 3
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob_x, rect.top() + 3, diameter, diameter)


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


def _windows_volume_label(root):
    """获取 Windows 卷标（如“软件”“文档”），失败返回空串。"""
    if not sys.platform.startswith("win"):
        return ""
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(261)
        fs = ctypes.create_unicode_buffer(261)
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            buf,
            len(buf),
            None,
            None,
            None,
            fs,
            len(fs),
        )
        return buf.value or ""
    except Exception:
        return ""


def list_system_drives():
    """列出磁盘分区及容量信息，用于目录选择对话框。

    返回列表，元素为 {device, label, mountpoint, total, used, free, percent}。
    """
    drives = []
    seen = set()

    def add(mountpoint):
        try:
            root = os.path.abspath(mountpoint)
        except Exception:
            return
        if root in seen or not os.path.exists(root):
            return
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            return
        seen.add(root)
        total = usage.total
        used = usage.used
        free = usage.free
        percent = (used / total * 100) if total else 0
        label = _windows_volume_label(root)
        drives.append(
            {
                "device": root,
                "label": label,
                "mountpoint": root,
                "total": total,
                "used": used,
                "free": free,
                "percent": percent,
            }
        )

    if psutil is not None:
        try:
            for part in psutil.disk_partitions(all=False):
                add(part.mountpoint)
        except Exception:
            pass

    if not drives:
        if sys.platform.startswith("win"):
            try:
                import ctypes

                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for i in range(26):
                    if bitmask & (1 << i):
                        add(f"{chr(65 + i)}:\\")
            except Exception:
                pass
        else:
            add("/")

    return drives


def _format_capacity(num_bytes):
    value = float(num_bytes or 0)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if value < 1024 or unit == "PB":
            return f"{value:.1f} {unit}" if unit not in ("B", "KB") else f"{value:.0f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


class DriveSelectDialog(QDialog):
    """磁盘/目录选择对话框：列出各盘符的名称、总计、可用、已用占比。"""

    def __init__(self, parent=None, current=""):
        super().__init__(parent)
        self.setWindowTitle("选择磁盘 / 目录")
        self.resize(560, 360)
        self.selected_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        tip = QLabel("选择要扫描的磁盘（双击直接进入），或点击“浏览文件夹”选择具体目录。")
        tip.setObjectName("pageSubtitle")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("appTable")
        self.table.setHorizontalHeaderLabels(["名称", "总计", "可用", "已用 / 总计"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 150)
        self.table.setItemDelegateForColumn(3, UsageBarDelegate(self.table))
        self.table.doubleClicked.connect(self._accept_selection)
        layout.addWidget(self.table, 1)

        self._populate(current)

        button_row = QHBoxLayout()
        browse_button = QPushButton("浏览文件夹…")
        browse_button.setObjectName("cleanSecondaryButton")
        browse_button.clicked.connect(self._browse_folder)
        button_row.addWidget(browse_button)
        button_row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        button_row.addWidget(buttons)
        layout.addLayout(button_row)

    def _populate(self, current):
        drives = list_system_drives()
        self.table.setRowCount(0)
        for drive in drives:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = drive["label"]
            device = drive["device"].rstrip("\\/")
            display = f"{name} ({device})" if name else device
            name_item = QTableWidgetItem(display)
            name_item.setData(Qt.UserRole, drive["device"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(_format_capacity(drive["total"])))
            self.table.setItem(row, 2, QTableWidgetItem(_format_capacity(drive["free"])))
            pct_item = QTableWidgetItem(f"{drive['percent']:.1f}%")
            pct_item.setData(BAR_FRAC_ROLE, drive["percent"] / 100.0)
            pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, pct_item)
            if current and os.path.abspath(current).startswith(os.path.abspath(drive["device"])):
                self.table.selectRow(row)
        if self.table.currentRow() < 0 and self.table.rowCount():
            self.table.selectRow(0)

    def _accept_selection(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item:
            self.selected_path = item.data(Qt.UserRole)
            self.accept()

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if directory:
            self.selected_path = directory
            self.accept()


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

QTreeWidget#folderUsageTree {
    background: #FFFFFF;
    border: 1px solid #D6E8E4;
    border-radius: 8px;
    color: #1C2C26;
    alternate-background-color: #F5FBF9;
    outline: 0;
    selection-background-color: #CCEFE8;
    selection-color: #15241C;
}

QTreeWidget#folderUsageTree::item {
    min-height: 28px;
    padding: 3px 4px;
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
    min-width: 52px;
    padding: 0 10px;
}

QPushButton#miniActionButton:hover {
    background: #E7F7F4;
}

QPushButton#miniActionButton:disabled {
    border-color: #C7DDD8;
    color: #9DB3AD;
    background: #F4F8F7;
}

QPushButton#dangerActionButton {
    background: #FFFFFF;
    border: 1px solid #E5897F;
    border-radius: 12px;
    color: #C0392B;
    font-size: 12px;
    font-weight: 700;
    min-height: 24px;
    min-width: 52px;
    padding: 0 10px;
}

QPushButton#dangerActionButton:hover {
    background: #FCEDEA;
}

QPushButton#dangerActionButton:disabled {
    border-color: #E3D6D4;
    color: #B7A6A3;
    background: #F7F3F2;
}

QScrollArea#pageScroll {
    background: transparent;
    border: none;
}

QWidget#pageScrollInner {
    background: transparent;
}

QWidget#bxTabContainer {
    background: #F4FAF9;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
}

QScrollArea#bxCategoryScroll,
QWidget#bxCategoryInner {
    background: transparent;
    border: none;
}

QPushButton#bxCategory,
QPushButton#bxCategoryActive {
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    padding: 0 12px;
    text-align: left;
}

QPushButton#bxCategory {
    background: transparent;
    color: #2C4A43;
}

QPushButton#bxCategory:hover {
    background: #E7F7F4;
    color: #0D7E72;
}

QPushButton#bxCategoryActive {
    background: #14B8A6;
    color: #FFFFFF;
}

QScrollArea#bxScrollArea {
    background: transparent;
    border: none;
}

QWidget#bxListContainer {
    background: transparent;
}

QFrame#bxCard {
    background: #FFFFFF;
    border: 1px solid #D7E6E2;
    border-radius: 12px;
}

QFrame#bxCard:hover {
    border: 1px solid #14B8A6;
}

QLabel#bxCardTitle {
    color: #0F2E2A;
    font-size: 14px;
    font-weight: 600;
}

QPushButton#bxCardTitleButton {
    color: #0F2E2A;
    font-size: 14px;
    font-weight: 600;
    background: transparent;
    border: none;
    padding: 2px 0;
    text-align: left;
}

QPushButton#bxCardTitleButton:hover {
    color: #0D9488;
}

QPushButton#bxCardTitleButton:checked {
    color: #0D9488;
}

QLabel#bxCardWarning {
    color: #B8860B;
    font-size: 11px;
}

QLabel#bxStateLabel {
    font-size: 12px;
    min-width: 64px;
}

QWidget#bxDetailBox {
    background: transparent;
}

QLabel#bxDetailDesc {
    color: #4A5B57;
    font-size: 12px;
}

QFrame#bxRecommendBox {
    background: #F1FAF8;
    border: 1px solid #CDE9E3;
    border-radius: 8px;
}

QLabel#bxRecommendTitle {
    color: #0D9488;
    font-size: 12px;
    font-weight: 700;
}

QLabel#bxRecommendText {
    color: #3C4D49;
    font-size: 12px;
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
    """文件管理扫描线程，避免大文件/重复文件/文件夹统计扫描阻塞 UI。"""
    file_scan_finished_signal = pyqtSignal(str, object)
    file_scan_error_signal = pyqtSignal(str, str)
    file_scan_progress_signal = pyqtSignal(str, str)

    # 扫描时跳过的重解析点 / 系统 / 超大低价值目录，避免遍历过慢或死循环
    SKIP_DIR_NAMES = {
        "$recycle.bin",
        "system volume information",
        "windowsapps",
        "winsxs",
        "$windows.~ws",
        "$windows.~bt",
        "config.msi",
        "driverstore",
    }

    def __init__(self, mode, root_dir, min_size=100 * 1024 * 1024, max_files=5000):
        super().__init__()
        self.mode = mode
        self.root_dir = root_dir
        self.min_size = min_size
        self.max_files = max_files

    def run(self):
        try:
            if self.mode == "large":
                payload = self.find_large_files(
                    self.root_dir, self.min_size, self.max_files, self._emit_progress
                )
            elif self.mode == "duplicates":
                payload = self.find_duplicate_files(
                    self.root_dir, self.max_files, self._emit_progress
                )
            elif self.mode == "folders":
                payload = self.scan_folder_sizes(self.root_dir, self._emit_progress)
            else:
                raise ValueError(f"未知文件扫描类型: {self.mode}")
            self.file_scan_finished_signal.emit(self.mode, payload)
        except Exception as exc:  # pragma: no cover - depends on host filesystem
            self.file_scan_error_signal.emit(self.mode, str(exc))

    def _emit_progress(self, text):
        self.file_scan_progress_signal.emit(self.mode, text)

    @staticmethod
    def scan_folder_sizes(root_dir, progress=None):
        """统计目录树中每个文件夹的实际占用大小（递归汇总，类似 WinDirStat）。

        返回结构::

            {
                "root": 根目录,
                "total": {目录: 递归总大小},
                "own": {目录: 该目录内文件的大小（不含子目录）},
                "count": {目录: 递归文件总数},
                "children": {目录: [按大小降序排列的直接子目录, ...]},
            }
        """
        dir_own = {}
        dir_own_count = {}
        children = {}
        order = []
        count = 0
        for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True,
                                                     onerror=lambda _e: None):
            # 不进入符号链接/连接点，避免死循环与重复统计。
            dirnames[:] = [
                d for d in dirnames
                if not FileScanThread._is_link_safe(os.path.join(dirpath, d))
            ]
            order.append(dirpath)
            count += 1
            if progress is not None and count % 300 == 0:
                progress(f"正在统计文件夹占用: 已扫描 {count} 个目录 ...")

            own = 0
            own_count = 0
            for file_name in filenames:
                file_path = os.path.join(dirpath, file_name)
                try:
                    if os.path.islink(file_path):
                        continue
                    own += os.path.getsize(file_path)
                    own_count += 1
                except OSError:
                    continue
            dir_own[dirpath] = own
            dir_own_count[dirpath] = own_count

            kids = []
            for dir_name in dirnames:
                child_path = os.path.join(dirpath, dir_name)
                # 跳过符号链接/重解析点，避免重复计算与死循环。
                try:
                    if os.path.islink(child_path):
                        continue
                except OSError:
                    continue
                kids.append(child_path)
            children[dirpath] = kids

        # os.walk 自上而下，反向遍历即可保证子目录先于父目录累加。
        total = {}
        total_count = {}
        for dirpath in reversed(order):
            acc = dir_own.get(dirpath, 0)
            acc_count = dir_own_count.get(dirpath, 0)
            for child in children.get(dirpath, []):
                acc += total.get(child, 0)
                acc_count += total_count.get(child, 0)
            total[dirpath] = acc
            total_count[dirpath] = acc_count

        for dirpath, kids in children.items():
            kids.sort(key=lambda c: total.get(c, 0), reverse=True)

        return {
            "root": root_dir,
            "total": total,
            "own": dir_own,
            "count": total_count,
            "children": children,
        }

    @staticmethod
    def _is_link_safe(path):
        try:
            return os.path.islink(path)
        except OSError:
            return True

    @classmethod
    def _prune_dirs(cls, root, dirs):
        """就地修改 os.walk 的目录列表：跳过连接点/符号链接与系统重目录，避免遍历过慢或死循环。"""
        kept = []
        for name in dirs:
            full = os.path.join(root, name)
            try:
                if os.path.islink(full):
                    continue
            except OSError:
                continue
            if name.lower() in cls.SKIP_DIR_NAMES:
                continue
            kept.append(name)
        dirs[:] = kept

    @classmethod
    def find_large_files(cls, root_dir, min_size=100 * 1024 * 1024, max_files=5000, progress=None):
        large_files = []
        scanned = 0
        for root, dirs, files in os.walk(root_dir, topdown=True, onerror=lambda _e: None):
            cls._prune_dirs(root, dirs)
            for file_name in files:
                if scanned >= max_files:
                    break
                path = os.path.join(root, file_name)
                try:
                    if os.path.islink(path) or not os.path.isfile(path):
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
            if progress is not None and scanned and scanned % 1000 == 0:
                progress(f"正在扫描大文件: 已检查 {scanned} 个文件 ...")
            if scanned >= max_files:
                break
        large_files.sort(key=lambda item: item["size"], reverse=True)
        return large_files[:200]

    @classmethod
    def find_duplicate_files(cls, root_dir, max_files=5000, progress=None):
        by_size = {}
        scanned = 0
        stop = False
        for root, dirs, files in os.walk(root_dir, topdown=True, onerror=lambda _e: None):
            cls._prune_dirs(root, dirs)
            for file_name in files:
                if scanned >= max_files:
                    stop = True
                    break
                path = os.path.join(root, file_name)
                try:
                    if os.path.islink(path) or not os.path.isfile(path):
                        continue
                    size = os.path.getsize(path)
                    if size <= 0:
                        continue
                    by_size.setdefault(size, []).append(path)
                    scanned += 1
                except (OSError, PermissionError):
                    continue
            if progress is not None and scanned and scanned % 500 == 0:
                progress(f"正在收集文件: 已扫描 {scanned} 个 ...")
            if stop:
                break

        # 仅对“大小相同”的候选做哈希；先用部分哈希（头部 64KB）预筛，
        # 再对通过预筛的做完整哈希，避免对大量大文件做全量 SHA256 造成卡顿。
        candidates = [(size, paths) for size, paths in by_size.items() if len(paths) >= 2]
        duplicates = []
        total_groups = len(candidates)
        for index, (size, paths) in enumerate(candidates, start=1):
            if progress is not None and (index == 1 or index % 20 == 0 or index == total_groups):
                progress(f"正在比对重复文件: {index}/{total_groups} 组 ...")
            by_partial = {}
            for path in paths:
                partial = cls.file_digest(path, partial=True)
                if partial:
                    by_partial.setdefault(partial, []).append(path)
            for partial_group in by_partial.values():
                if len(partial_group) < 2:
                    continue
                by_full = {}
                for path in partial_group:
                    full = cls.file_digest(path)
                    if full:
                        by_full.setdefault(full, []).append(path)
                for full_group in by_full.values():
                    if len(full_group) > 1:
                        duplicates.append((size, full_group))

        duplicates.sort(key=lambda group: group[0] * (len(group[1]) - 1), reverse=True)
        return duplicates

    @staticmethod
    def file_digest(path, partial=False, partial_bytes=64 * 1024):
        digest = hashlib.sha256()
        try:
            with open(path, "rb") as handle:
                if partial:
                    digest.update(handle.read(partial_bytes))
                else:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
            return digest.hexdigest()
        except (OSError, PermissionError):
            return None


# 占用条委托读取的“比例”自定义角色（0~1），与用于排序的 Qt.UserRole 区分开。
BAR_FRAC_ROLE = int(Qt.UserRole) + 1


class UsageBarDelegate(QStyledItemDelegate):
    """在单元格内绘制一条青色占用条 + 原始文字（WinDirStat 风格）。

    - 比例从 ``BAR_FRAC_ROLE``（0~1）读取；无该数据时退回默认绘制。
    - 叠加的文字取单元格的 DisplayRole（如 “35.2%” 或 “1.2 GB”）。
    """

    def __init__(self, parent=None, align=Qt.AlignCenter):
        super().__init__(parent)
        self._align = align

    def paint(self, painter, option, index):
        frac = index.data(BAR_FRAC_ROLE)
        if frac is None:
            super().paint(painter, option, index)
            return
        try:
            frac = float(frac)
        except (TypeError, ValueError):
            super().paint(painter, option, index)
            return

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        bar_rect = option.rect.adjusted(6, 5, -6, -5)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)

        painter.setBrush(QColor("#E3EFEC"))
        painter.drawRoundedRect(bar_rect, 4, 4)

        frac = max(0.0, min(1.0, frac))
        fill_width = int(bar_rect.width() * frac)
        if fill_width > 0:
            fill_rect = QRect(bar_rect)
            fill_rect.setWidth(fill_width)
            # 占用越大颜色越深，给出直观的冷暖提示。
            if frac >= 0.5:
                painter.setBrush(QColor("#0D9488"))
            elif frac >= 0.15:
                painter.setBrush(QColor("#14B8A6"))
            else:
                painter.setBrush(QColor("#5EEAD4"))
            painter.drawRoundedRect(fill_rect, 4, 4)

        text = index.data(Qt.DisplayRole)
        if text:
            painter.setPen(QColor("#15241C"))
            painter.drawText(option.rect.adjusted(9, 0, -9, 0),
                             int(self._align | Qt.AlignVCenter), str(text))
        painter.restore()


class MigrationScanThread(QThread):
    """后台统计个人文件夹当前占用与迁移状态。"""
    scan_finished_signal = pyqtSignal(list)
    scan_error_signal = pyqtSignal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        try:
            folders = self.service.list_folders(with_size=True)
            self.scan_finished_signal.emit(folders)
        except Exception as exc:  # pragma: no cover - 依赖运行环境
            self.scan_error_signal.emit(str(exc))


class MigrationThread(QThread):
    """执行个人文件夹迁移 / 还原。"""
    progress_signal = pyqtSignal(str)
    item_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(str, dict)
    error_signal = pyqtSignal(str)

    def __init__(self, service, mode, keys, target_root="", move_files=True):
        super().__init__()
        self.service = service
        self.mode = mode  # "migrate" | "restore"
        self.keys = list(keys)
        self.target_root = target_root
        self.move_files = move_files

    def run(self):
        summary = {"done": 0, "failed": 0, "errors": []}
        try:
            for key in self.keys:
                try:
                    if self.mode == "migrate":
                        info = self.service.migrate_folder(
                            key, self.target_root, move_files=self.move_files
                        )
                        self.progress_signal.emit(f"已迁移: {info['name']} → {info['dst']}")
                    else:
                        info = self.service.restore_folder(key)
                        self.progress_signal.emit(f"已还原: {info['name']}")
                    summary["done"] += 1
                    self.item_signal.emit({"key": key, "ok": True})
                except MigrationError as exc:
                    summary["failed"] += 1
                    summary["errors"].append(str(exc))
                    self.progress_signal.emit(f"跳过: {exc}")
                    self.item_signal.emit({"key": key, "ok": False, "error": str(exc)})
                except Exception as exc:  # pragma: no cover - 运行环境相关
                    summary["failed"] += 1
                    summary["errors"].append(str(exc))
                    self.item_signal.emit({"key": key, "ok": False, "error": str(exc)})
            self.finished_signal.emit(self.mode, summary)
        except Exception as exc:  # pragma: no cover
            self.error_signal.emit(str(exc))


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
                stdin=subprocess.DEVNULL,
                timeout=60 * 60,
                **hidden_windows_subprocess_kwargs(),
            )
            output = "\n".join(
                part.strip()
                for part in (
                    decode_console_output(result.stdout),
                    decode_console_output(result.stderr),
                )
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
                    timeout=120,
                    **hidden_windows_subprocess_kwargs(),
                )
                output = "\n".join(
                    part.strip()
                    for part in (
                        decode_console_output(result.stdout),
                        decode_console_output(result.stderr),
                    )
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
    ("软件卸载", "_build_uninstall_page"),
    ("文件管理", "_build_file_page"),
    ("系统修复", "_build_repair_page"),
    ("账号会员", "_build_account_page"),
]


class AccountAuthDialog(QDialog):
    """独立登录/注册窗口，避免与会员中心挤在同一页。"""

    def __init__(self, parent, initial_tab=0):
        super().__init__(parent)
        self.setWindowTitle("登录 / 注册")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("accountAuthDialog")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(14)

        title = QLabel("账号登录")
        title.setObjectName("pageTitle")
        subtitle = QLabel("登录或注册后兑换会员卡；新用户注册即赠送体验卡。")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("accountAuthTabs")

        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        login_layout.setContentsMargins(12, 16, 12, 12)
        login_layout.setSpacing(10)
        self.account_email_input = QLineEdit()
        self.account_email_input.setPlaceholderText("名称")
        self.account_password_input = QLineEdit()
        self.account_password_input.setPlaceholderText("密码，至少 6 位")
        self.account_password_input.setEchoMode(QLineEdit.Password)
        login_button = QPushButton("登录")
        login_button.setObjectName("scanPrimaryButton")
        login_button.setMinimumHeight(36)
        login_button.clicked.connect(parent.login_account)
        login_layout.addWidget(self.account_email_input)
        login_layout.addWidget(self.account_password_input)
        login_layout.addWidget(login_button)
        login_layout.addStretch(1)

        register_tab = QWidget()
        register_layout = QVBoxLayout(register_tab)
        register_layout.setContentsMargins(12, 16, 12, 12)
        register_layout.setSpacing(10)
        self.register_name_input = QLineEdit()
        self.register_name_input.setPlaceholderText("名称（至少 6 位，不能含中文）")
        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText("密码，至少 6 位")
        self.register_password_input.setEchoMode(QLineEdit.Password)
        register_hint = QLabel("名称需 6 位及以上、不能包含中文，且不能与已注册名称重复。")
        register_hint.setObjectName("statusLabel")
        register_hint.setWordWrap(True)
        register_button = QPushButton("注册并登录")
        register_button.setObjectName("scanPrimaryButton")
        register_button.setMinimumHeight(36)
        register_button.clicked.connect(parent.register_account_from_dialog)
        register_layout.addWidget(self.register_name_input)
        register_layout.addWidget(self.register_password_input)
        register_layout.addWidget(register_hint)
        register_layout.addWidget(register_button)
        register_layout.addStretch(1)

        self.tabs.addTab(login_tab, "登录")
        self.tabs.addTab(register_tab, "注册")
        outer.addWidget(self.tabs)

        self.message_label = QLabel("")
        self.message_label.setObjectName("statusLabel")
        self.message_label.setWordWrap(True)
        outer.addWidget(self.message_label)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("关闭")
        close_button.setObjectName("cleanSecondaryButton")
        close_button.clicked.connect(self.reject)
        close_row.addWidget(close_button)
        outer.addLayout(close_row)

        if 0 <= initial_tab < self.tabs.count():
            self.tabs.setCurrentIndex(initial_tab)

    def set_message(self, text):
        self.message_label.setText(text or "")

    def login_credentials(self):
        return (
            self.account_email_input.text().strip(),
            self.account_password_input.text(),
            "",
        )

    def register_credentials(self):
        name = self.register_name_input.text().strip()
        return (
            name,
            self.register_password_input.text(),
            name,
        )


class CleanerMainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.cleaner = CleanerLogic()
        self.registry_cleaner = RegistryCleanerService()
        self.scan_results = {}
        self.selected_items = []
        self.cleanable_items = []
        self.app_icon = self._load_app_icon()
        self.icon_provider = QFileIconProvider()
        self.nav_buttons = []
        self.optimizer_tables = {}
        self.optimizer_handled_keys = set()
        self.uninstall_apps = []
        self.uninstall_sort_column = None
        self.uninstall_sort_ascending = True
        self.hidden_uninstall_keys = set()
        self.file_scan_root = ""
        self.file_large_items = []
        self.file_duplicate_groups = []
        self.folder_scan_data = None
        self.folder_scan_done_root = None
        self.file_scan_thread = None
        self.defrag_thread = None
        self.migration_service = FileMigrationService()
        self.migration_scan_thread = None
        self.migration_thread = None
        self.migration_loaded = False
        self.migration_rows = {}
        self.fragment_grid_cells = []
        self.bx_mode = "basic"
        self.bx_active_category = "基础"
        self.bx_category_buttons = {}
        self.bx_thread = None
        self.bx_item_states = {}
        self.bx_rows = []
        self._prime_process_cpu()
        self.active_animations = []
        self.account_service = self._build_account_service()
        self.account_state = self.account_service.current_state()
        self.account_auth_dialog = None
        
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

        layout.addSpacing(6)
        self.account_sidebar_button = QPushButton("登录 / 注册")
        self.account_sidebar_button.setObjectName("sidebarButton")
        self.account_sidebar_button.setCursor(Qt.PointingHandCursor)
        self.account_sidebar_button.setMinimumWidth(148)
        self.account_sidebar_button.clicked.connect(self.on_account_sidebar_clicked)
        layout.addWidget(self.account_sidebar_button)

        layout.addStretch(1)

        self.sidebar_footer_label = QLabel("等待扫描…")
        self.sidebar_footer_label.setObjectName("sidebarFooter")
        self.sidebar_footer_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.sidebar_footer_label.setWordWrap(True)
        layout.addWidget(self.sidebar_footer_label)
        self.update_sidebar_footer()

        return sidebar

    def update_sidebar_footer(self):
        """用真实数据刷新侧边栏底部：清理模式 + 上次扫描可清理项/大小。"""
        if not hasattr(self, "sidebar_footer_label"):
            return
        recommended = True
        if hasattr(self, "recommended_checkbox"):
            recommended = self.recommended_checkbox.isChecked()
        mode_text = "推荐模式" if recommended else "全面模式"

        count = len(getattr(self, "cleanable_items", []) or [])
        total_bytes = 0
        for item in getattr(self, "cleanable_items", []) or []:
            if isinstance(item, dict):
                total_bytes += item.get("size", 0) or 0
        if count:
            stats_text = f"可清理 {count} 项 / {self.format_size(total_bytes)}"
        else:
            stats_text = "路径统计：暂未扫描"
        self.sidebar_footer_label.setText(f"{mode_text}\n{stats_text}")

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
            # 文件管理页不再自动扫描，改为用户点击“扫描文件夹”后再统计，避免打开卡顿。

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

        self.backup_checkbox = QCheckBox("删除前备份")
        self.backup_checkbox.setToolTip("删除前自动备份，可在“备份管理”中恢复")
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
        page_subtitle = QLabel("开机启动、运行内存、系统优化(含 BX 一键优化)、隐私清理、N卡/A卡一键调优都在软件内查看和处理。")
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
            ("系统优化", None, None),  # BX 卡片式一键优化界面
            ("隐私清理", ["电脑隐私记录", "操作"], self.populate_privacy_items()),
            ("N卡一键调优", ["NVIDIA 优化项", "操作"], self.populate_nvidia_items()),
            ("A卡一键调优", ["AMD 优化项", "操作"], self.populate_amd_items()),
        ]

        self.optimizer_bx_tab_index = -1
        for tab_name, headers, rows in tab_specs:
            if tab_name == "系统优化":
                bx_widget = self._build_bx_widget()
                self.optimizer_bx_tab_index = self.optimizer_tabs.addTab(bx_widget, tab_name)
                continue
            table = self._make_optimizer_table(headers)
            self.optimizer_tables[tab_name] = table
            self._populate_optimizer_table(table, rows)
            self.optimizer_tabs.addTab(table, tab_name)

        self.optimizer_tabs.currentChanged.connect(self.on_optimizer_tab_changed)
        outer.addWidget(self.optimizer_tabs, 1)

        self.optimizer_action_bar = QWidget()
        action_bar = QHBoxLayout(self.optimizer_action_bar)
        action_bar.setContentsMargins(0, 0, 0, 0)
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
        outer.addWidget(self.optimizer_action_bar)

        self.optimizer_status_label = QLabel("准备处理系统优化项。")
        self.optimizer_status_label.setObjectName("statusLabel")
        outer.addWidget(self.optimizer_status_label)

        self.on_optimizer_tab_changed(self.optimizer_tabs.currentIndex())
        return page

    def on_optimizer_tab_changed(self, index):
        """切到「系统优化」(BX 卡片界面)时隐藏共享操作栏，BX 有自己的预设与应用按钮。"""
        if not hasattr(self, "optimizer_action_bar"):
            return
        is_bx = index == getattr(self, "optimizer_bx_tab_index", -1)
        self.optimizer_action_bar.setVisible(not is_bx)
        if hasattr(self, "optimizer_status_label"):
            self.optimizer_status_label.setVisible(not is_bx)

    def _build_bx_widget(self):
        container = QWidget()
        container.setObjectName("bxTabContainer")
        body = QHBoxLayout(container)
        body.setContentsMargins(14, 14, 14, 14)
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

        category_scroll = QScrollArea()
        category_scroll.setObjectName("bxCategoryScroll")
        category_scroll.setWidgetResizable(True)
        category_scroll.setFrameShape(QFrame.NoFrame)
        category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        category_inner = QWidget()
        category_inner.setObjectName("bxCategoryInner")
        category_inner_layout = QVBoxLayout(category_inner)
        category_inner_layout.setContentsMargins(0, 0, 0, 0)
        category_inner_layout.setSpacing(4)

        self.bx_category_buttons = {}
        for category in self.bx_visible_categories():
            button = QPushButton(category)
            button.setObjectName("bxCategoryActive" if category == self.bx_active_category else "bxCategory")
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(36)
            button.clicked.connect(lambda _checked=False, target=category: self.select_bx_category(target))
            category_inner_layout.addWidget(button)
            self.bx_category_buttons[category] = button
        category_inner_layout.addStretch(1)
        category_scroll.setWidget(category_inner)
        category_layout.addWidget(category_scroll, 1)

        category_layout.addSpacing(12)
        quick_title = QLabel("快速方法")
        quick_title.setObjectName("featureCardTitle")
        category_layout.addWidget(quick_title)

        self.bx_basic_button = QPushButton("基本优化")
        self.bx_basic_button.setObjectName("scanPrimaryButton")
        self.bx_basic_button.setMinimumHeight(34)
        self.bx_basic_button.clicked.connect(lambda: self.select_bx_mode("basic"))
        self.bx_best_button = QPushButton("最佳优化")
        self.bx_best_button.setObjectName("cleanSecondaryButton")
        self.bx_best_button.setMinimumHeight(34)
        self.bx_best_button.clicked.connect(lambda: self.select_bx_mode("best"))
        category_layout.addWidget(self.bx_basic_button)
        category_layout.addWidget(self.bx_best_button)

        self.bx_apply_button = QPushButton("✓ 应用")
        self.bx_apply_button.setObjectName("scanPrimaryButton")
        self.bx_apply_button.setMinimumHeight(40)
        self.bx_apply_button.clicked.connect(self.apply_bx_optimization)
        category_layout.addWidget(self.bx_apply_button)

        main_panel = QVBoxLayout()
        main_panel.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("featureCard")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        toolbar_title = QLabel("基础设置")
        toolbar_title.setObjectName("featureCardTitle")
        bx_refresh_button = QPushButton("更新")
        bx_refresh_button.setObjectName("cleanSecondaryButton")
        bx_refresh_button.setMinimumWidth(88)
        bx_refresh_button.clicked.connect(self.refresh_bx_page)

        toolbar_layout.addWidget(toolbar_title)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(bx_refresh_button)
        main_panel.addWidget(toolbar)

        self.bx_scroll = QScrollArea()
        self.bx_scroll.setObjectName("bxScrollArea")
        self.bx_scroll.setWidgetResizable(True)
        self.bx_scroll.setFrameShape(QFrame.NoFrame)
        self.bx_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.bx_list_container = QWidget()
        self.bx_list_container.setObjectName("bxListContainer")
        self.bx_list_layout = QVBoxLayout(self.bx_list_container)
        self.bx_list_layout.setContentsMargins(2, 2, 2, 2)
        self.bx_list_layout.setSpacing(10)
        self.bx_list_layout.addStretch(1)
        self.bx_scroll.setWidget(self.bx_list_container)
        main_panel.addWidget(self.bx_scroll, 1)

        self.bx_status_label = QLabel("基本模式已就绪。")
        self.bx_status_label.setObjectName("statusLabel")
        main_panel.addWidget(self.bx_status_label)

        body.addWidget(category_panel)
        body.addLayout(main_panel, 1)

        self.update_bx_mode_buttons()
        self.apply_bx_preset(self.bx_mode, refresh_only=False)
        return container

    def bx_category_order(self):
        return [
            "我的调整",
            "基础",
            "系统维护",
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
        return self._bx_base_catalog() + self._bx_system_maintenance_items()

    def _bx_system_maintenance_items(self):
        """把原「系统优化」标签里的命令项合并成 BX 卡片，统一在系统优化里展示。"""
        cached = getattr(self, "_bx_maintenance_cache", None)
        if cached is not None:
            return cached

        items = []
        seen_titles = set()
        for row in self.populate_optimization_items():
            command = row.get("command")
            if not command:
                continue
            title = (row.get("columns") or ["系统优化项"])[0]
            if title in seen_titles:
                continue
            seen_titles.add(title)
            action = row.get("action", "优化")
            target_state = "将被执行" if action == "执行" else "将被调整"
            detail = ""
            children = row.get("children") or []
            if children:
                detail_cols = children[0].get("columns") or []
                if detail_cols:
                    detail = str(detail_cols[0])
            items.append({
                "category": "系统维护",
                "title": title,
                "target_state": target_state,
                "risk": "基础" if row.get("recommended", True) else "谨慎",
                "description": detail or f"{title}。",
                "command": command,
                "icon_hint": row.get("icon_hint", "windows"),
                "basic": bool(row.get("recommended", True)),
                "best": True,
            })

        self._bx_maintenance_cache = items
        return items

    def _bx_base_catalog(self):
        return [
            {
                "category": "基础",
                "title": "鼠标加速",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "移除鼠标指针的加速，保持严格的线性 1:1 鼠标移动。",
                "recommend": "在任何竞技游戏中禁用；如果主要使用触控板，则保持默认。",
                "command": (
                    r'reg add "HKCU\Control Panel\Mouse" /v MouseSpeed /t REG_SZ /d 0 /f & '
                    r'reg add "HKCU\Control Panel\Mouse" /v MouseThreshold1 /t REG_SZ /d 0 /f & '
                    r'reg add "HKCU\Control Panel\Mouse" /v MouseThreshold2 /t REG_SZ /d 0 /f'
                ),
                "icon_hint": "windows",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "系统启动时自动更新驱动程序",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "禁止 Windows 通过更新自动安装新版本的驱动程序。",
                "recommend": "如果手动安装驱动程序或固定一个版本，请禁用；可避免更新有争议的驱动后的“突然”重启，并节省每月约 200MB 流量。",
                "command": r'reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching" /v SearchOrderConfig /t REG_DWORD /d 0 /f',
                "icon_hint": "driver",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "全局通知",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "关闭操作中心 Toast 通知，减少打扰。",
                "command": r'reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications" /v ToastEnabled /t REG_DWORD /d 0 /f',
                "icon_hint": "windows",
                "basic": True,
                "best": True,
            },
            {
                "category": "基础",
                "title": "UWP应用程序在后台运行",
                "target_state": "将被禁用",
                "risk": "基础",
                "description": "禁止 UWP/商店应用在后台运行，节省内存与电量。",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications" /v GlobalUserDisabled /t REG_DWORD /d 1 /f',
                "icon_hint": "windows",
                "basic": True,
                "best": True,
            },
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
                "warning": "禁用时将无法工作: 快速ALT+TAB",
                "command": r'reg add "HKCU\System\GameConfigStore" /v GameDVR_FSEBehaviorMode /t REG_DWORD /d 2 /f',
                "icon_hint": "game",
                "basic": False,
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
                "warning": "禁用时将无法工作: LastActivityView",
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
                "warning": "禁用时将无法工作: 打印机",
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
                "warning": "禁用时将无法工作: 任务管理器中的网络使用, 网络设置中的网络使用情况",
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

    def bx_item_id(self, item):
        return f"{item.get('category', '')}::{item.get('title', '')}"

    def bx_visible_categories(self):
        """只显示真正含有优化项的分类，避免左侧出现一堆空分类把面板挤爆。"""
        present = {item.get("category") for item in self.bx_catalog()}
        categories = ["我的调整"]
        for category in self.bx_category_order():
            if category == "我的调整":
                continue
            if category in present:
                categories.append(category)
        return categories

    def bx_category_items(self, category=None):
        category = category or self.bx_active_category
        if category == "我的调整":
            return list(self.bx_catalog())
        return [item for item in self.bx_catalog() if item.get("category") == category]

    def bx_preset_default_on(self, item, preset):
        """某个预设下该项是否默认开启。"""
        if not item.get("command"):
            return False
        if preset == "default":
            return False
        if preset == "max":
            return True
        if preset == "best":
            return bool(item.get("best"))
        return bool(item.get("basic"))

    def apply_bx_preset(self, preset, refresh_only=False):
        """按预设(默认/基本/最佳/最大)重置全部开关状态。"""
        if preset in ("basic", "best"):
            self.bx_mode = preset
        else:
            self.bx_mode = preset
        self.bx_item_states = {}
        for item in self.bx_catalog():
            self.bx_item_states[self.bx_item_id(item)] = self.bx_preset_default_on(item, preset)
        self.update_bx_mode_buttons()
        self.populate_bx_categories()
        self.populate_bx_items()
        if not refresh_only and hasattr(self, "bx_status_label"):
            preset_name = {"default": "默认", "basic": "基本", "best": "最佳", "max": "最大"}.get(preset, preset)
            self.bx_status_label.setText(f"已套用「{preset_name}」预设，可逐项微调后点击应用。")
            self.animate_status_pulse(self.bx_status_label)

    def populate_bx_categories(self):
        if not self.bx_category_buttons:
            return
        for category, button in self.bx_category_buttons.items():
            items = self.bx_category_items(category)
            count = sum(1 for item in items if self.bx_item_states.get(self.bx_item_id(item)))
            button.setText(f"{category}    {count}" if count else category)
            button.setObjectName("bxCategoryActive" if category == self.bx_active_category else "bxCategory")
            button.style().unpolish(button)
            button.style().polish(button)

    def select_bx_category(self, category):
        self.bx_active_category = category
        self.populate_bx_categories()
        self.populate_bx_items()

    def update_bx_mode_buttons(self):
        if not hasattr(self, "bx_basic_button"):
            return
        mode_buttons = {
            "basic": self.bx_basic_button,
            "best": self.bx_best_button,
        }
        for mode, button in mode_buttons.items():
            if button is None:
                continue
            button.setObjectName("scanPrimaryButton" if self.bx_mode == mode else "cleanSecondaryButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def select_bx_mode(self, mode):
        if mode not in ("basic", "best", "max"):
            mode = "basic"
        self.bx_mode = mode
        self.apply_bx_preset(self.bx_mode)

    def refresh_bx_page(self):
        self.populate_bx_categories()
        self.populate_bx_items()
        if hasattr(self, "bx_status_label"):
            self.bx_status_label.setText("BX(优化) 项目已刷新。")
            self.animate_status_pulse(self.bx_status_label)

    def _bx_off_label(self, item):
        mapping = {
            "将被禁用": "已启用",
            "将被启用": "已禁用",
            "将被调整": "默认",
            "将被限制": "未限制",
            "仅检查": "仅检查",
            "仅展示": "仅展示",
        }
        return mapping.get(item.get("target_state", ""), "未更改")

    def _bx_apply_row_visual(self, item, toggle, state_label):
        is_on = bool(self.bx_item_states.get(self.bx_item_id(item)))
        if is_on:
            state_label.setText(item.get("target_state", "将被禁用"))
            state_label.setStyleSheet("color: #2F6BFF; font-weight: 600;")
        else:
            state_label.setText(self._bx_off_label(item))
            state_label.setStyleSheet("color: #E5484D; font-weight: 600;")
        if toggle.isChecked() != is_on:
            toggle.blockSignals(True)
            toggle.setChecked(is_on)
            toggle.blockSignals(False)

    def _on_bx_toggle(self, item, toggle, state_label, checked):
        self.bx_item_states[self.bx_item_id(item)] = bool(checked)
        self._bx_apply_row_visual(item, toggle, state_label)
        self.populate_bx_categories()
        self.update_bx_status()

    def bx_item_recommend(self, item):
        """返回展开卡片时显示的“推荐”文字：优先用条目自带，否则按风险生成默认。"""
        if item.get("recommend"):
            return item["recommend"]
        if not item.get("command"):
            return "安全相关项目，默认仅检查、不自动更改，避免降低系统防护。"
        if item.get("risk") == "谨慎":
            return "如无相关需求可开启；若你依赖该功能，请保持默认（关闭）。"
        return "推荐在所选预设下开启；如遇到异常，可在此处关闭。"

    def _make_bx_card(self, item):
        card = QFrame()
        card.setObjectName("bxCard")
        card_v = QVBoxLayout(card)
        card_v.setContentsMargins(16, 10, 16, 10)
        card_v.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(12)

        icon_label = QLabel()
        icon = self.category_icon_for_name(item.get("icon_hint") or item["title"])
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(22, 22))
        icon_label.setFixedWidth(26)
        header.addWidget(icon_label, 0, Qt.AlignVCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        # 用可点击按钮做标题，点击展开/收起详情。
        title_button = QPushButton(f"{item['title']}  ⌄")
        title_button.setObjectName("bxCardTitleButton")
        title_button.setCursor(Qt.PointingHandCursor)
        title_button.setCheckable(True)
        title_button.setFlat(True)
        text_box.addWidget(title_button, 0, Qt.AlignLeft)
        if item.get("warning"):
            warning_label = QLabel(f"⚠ {item['warning']}")
            warning_label.setObjectName("bxCardWarning")
            warning_label.setWordWrap(True)
            text_box.addWidget(warning_label)
        header.addLayout(text_box, 1)

        state_label = QLabel()
        state_label.setObjectName("bxStateLabel")
        state_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(state_label, 0, Qt.AlignVCenter)

        toggle = BXToggleSwitch()
        has_command = bool(item.get("command"))
        toggle.setEnabled(has_command)
        toggle.toggled.connect(
            lambda checked, it=item, tg=toggle, sl=state_label: self._on_bx_toggle(it, tg, sl, checked)
        )
        header.addWidget(toggle, 0, Qt.AlignVCenter)
        card_v.addLayout(header)

        # 展开详情区域：详细描述 + 推荐。
        detail = QWidget()
        detail.setObjectName("bxDetailBox")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(38, 8, 4, 4)
        detail_layout.setSpacing(8)

        desc_label = QLabel(item.get("description", ""))
        desc_label.setObjectName("bxDetailDesc")
        desc_label.setWordWrap(True)
        detail_layout.addWidget(desc_label)

        recommend_box = QFrame()
        recommend_box.setObjectName("bxRecommendBox")
        recommend_layout = QVBoxLayout(recommend_box)
        recommend_layout.setContentsMargins(12, 8, 12, 8)
        recommend_layout.setSpacing(3)
        recommend_title = QLabel("推荐")
        recommend_title.setObjectName("bxRecommendTitle")
        recommend_text = QLabel(self.bx_item_recommend(item))
        recommend_text.setObjectName("bxRecommendText")
        recommend_text.setWordWrap(True)
        recommend_layout.addWidget(recommend_title)
        recommend_layout.addWidget(recommend_text)
        detail_layout.addWidget(recommend_box)

        detail.setVisible(False)
        card_v.addWidget(detail)

        def _toggle_detail(checked, btn=title_button, dt=detail, it=item):
            dt.setVisible(checked)
            btn.setText(f"{it['title']}  {'⌃' if checked else '⌄'}")

        title_button.toggled.connect(_toggle_detail)

        self._bx_apply_row_visual(item, toggle, state_label)
        self.bx_rows.append({"item": item, "toggle": toggle, "state_label": state_label})
        return card

    def populate_bx_items(self):
        if not hasattr(self, "bx_list_layout"):
            return
        self.bx_rows = []
        while self.bx_list_layout.count():
            child = self.bx_list_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
        for item in self.bx_category_items():
            self.bx_list_layout.addWidget(self._make_bx_card(item))
        self.bx_list_layout.addStretch(1)
        self.update_bx_status()

    def selected_bx_items(self):
        return [
            item
            for item in self.bx_catalog()
            if item.get("command") and self.bx_item_states.get(self.bx_item_id(item))
        ]

    def update_bx_status(self):
        if not hasattr(self, "bx_status_label"):
            return
        selected_count = len(self.selected_bx_items())
        total_count = sum(1 for item in self.bx_catalog() if item.get("command"))
        mode_name = {"default": "默认", "basic": "基本", "best": "最佳", "max": "最大"}.get(self.bx_mode, self.bx_mode)
        self.bx_status_label.setText(
            f"{mode_name}预设 / {self.bx_active_category} / 已开启 {selected_count} 项 / 可优化 {total_count} 项"
        )

    def apply_bx_optimization(self):
        if self.bx_thread and self.bx_thread.isRunning():
            self.bx_status_label.setText("BX(优化) 正在执行，请稍后。")
            self.animate_status_pulse(self.bx_status_label)
            return

        if not self.require_membership("系统优化"):
            return

        items = self.selected_bx_items()
        if not items:
            self.bx_status_label.setText("请先开启需要应用的 BX 优化项（蓝色开关）。")
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
            self.bx_apply_button.setText("应用中..." if busy else "✓ 应用")
        if hasattr(self, "bx_scroll"):
            self.bx_scroll.setEnabled(not busy)
        if hasattr(self, "bx_basic_button"):
            self.bx_basic_button.setEnabled(not busy)
            self.bx_best_button.setEnabled(not busy)
        for button in getattr(self, "bx_category_buttons", {}).values():
            button.setEnabled(not busy)

    def on_bx_progress(self, message):
        self.bx_status_label.setText(message)

    def on_bx_item_finished(self, title, success, message):
        for row in getattr(self, "bx_rows", []):
            if row["item"].get("title") == title:
                state_label = row["state_label"]
                state_label.setText("已应用" if success else "跳过/失败")
                state_label.setStyleSheet(
                    "color: #0D9488; font-weight: 600;" if success else "color: #E5484D; font-weight: 600;"
                )
                state_label.setToolTip(message)
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
        self.uninstall_select_all = QCheckBox("全选")
        self.uninstall_select_all.stateChanged.connect(self.toggle_all_uninstall_checks)
        reload_button = QPushButton("刷新列表")
        reload_button.setObjectName("cleanSecondaryButton")
        reload_button.setMinimumWidth(96)
        reload_button.clicked.connect(lambda: self.load_installed_apps(show_message=True))
        uninstall_button = QPushButton("卸载选中")
        uninstall_button.setObjectName("scanPrimaryButton")
        uninstall_button.setMinimumWidth(96)
        uninstall_button.clicked.connect(self.uninstall_selected_app)
        toolbar.addWidget(self.uninstall_select_all)
        toolbar.addStretch(1)
        toolbar.addWidget(reload_button)
        toolbar.addWidget(uninstall_button)
        outer.addLayout(toolbar)

        self.uninstall_table = QTableWidget()
        self.uninstall_table.setObjectName("uninstallTable")
        self.uninstall_table.setColumnCount(8)
        self.uninstall_table.setHorizontalHeaderLabels(
            ["选择", "软件名称", "发布者", "版本", "安装日期", "大小", "安装位置", "操作"]
        )
        self.uninstall_table.verticalHeader().setVisible(False)
        self.uninstall_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.uninstall_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.uninstall_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.uninstall_table.setAlternatingRowColors(True)
        self.uninstall_table.setIconSize(QSize(20, 20))
        self.uninstall_table.setSortingEnabled(False)
        self.uninstall_table.itemChanged.connect(self.on_uninstall_item_changed)
        header_view = self.uninstall_table.horizontalHeader()
        header_view.setMinimumSectionSize(46)
        header_view.setSortIndicatorShown(True)
        header_view.setSectionsClickable(True)
        header_view.sectionClicked.connect(self.on_uninstall_header_clicked)
        header_view.setSectionResizeMode(0, QHeaderView.Fixed)
        header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.Stretch)
        header_view.setSectionResizeMode(7, QHeaderView.Fixed)
        self.uninstall_table.setColumnWidth(0, 52)
        self.uninstall_table.setColumnWidth(7, 96)
        self.uninstall_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.uninstall_table.customContextMenuRequested.connect(self.show_uninstall_context_menu)
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
        page_subtitle = QLabel("会员中心：查看权益、兑换激活码；登录与注册请使用侧边栏「登录 / 注册」按钮。")
        page_subtitle.setObjectName("pageSubtitle")
        page_subtitle.setWordWrap(True)
        header.addWidget(page_title)
        header.addWidget(page_subtitle)
        outer.addLayout(header)

        status_card = QFrame()
        status_card.setObjectName("featureCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(18, 16, 18, 16)
        status_layout.setSpacing(8)

        self.account_status_title = QLabel("未登录")
        self.account_status_title.setObjectName("featureCardTitle")
        self.account_status_detail = QLabel("请先登录或注册账户，再兑换会员卡。")
        self.account_status_detail.setObjectName("featureCardDesc")
        self.account_status_detail.setWordWrap(True)
        self.account_plan_label = QLabel("当前权益: Guest")
        self.account_plan_label.setObjectName("statusLabel")
        self.account_plan_label.setWordWrap(True)

        auth_actions = QHBoxLayout()
        auth_actions.setSpacing(10)
        self.account_open_auth_button = QPushButton("登录 / 注册")
        self.account_open_auth_button.setObjectName("scanPrimaryButton")
        self.account_open_auth_button.setMinimumWidth(120)
        self.account_open_auth_button.clicked.connect(lambda: self.show_account_auth_dialog(0))
        self.account_logout_button = QPushButton("退出登录")
        self.account_logout_button.setObjectName("cleanSecondaryButton")
        self.account_logout_button.setMinimumWidth(96)
        self.account_logout_button.clicked.connect(self.logout_account)
        auth_actions.addWidget(self.account_open_auth_button)
        auth_actions.addWidget(self.account_logout_button)
        auth_actions.addStretch(1)

        status_layout.addWidget(self.account_status_title)
        status_layout.addWidget(self.account_status_detail)
        status_layout.addWidget(self.account_plan_label)
        status_layout.addLayout(auth_actions)
        outer.addWidget(status_card)

        card_box = QFrame()
        card_box.setObjectName("featureCard")
        card_layout = QVBoxLayout(card_box)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(9)

        card_title = QLabel("激活码兑换")
        card_title.setObjectName("featureCardTitle")
        card_desc = QLabel("新账号注册即赠送一次体验卡；体验到期后，请输入激活码开通会员（体验卡 / 周卡 / 月卡 / 季卡 / 年卡）。")
        card_desc.setObjectName("featureCardDesc")
        card_desc.setWordWrap(True)

        card_row = QHBoxLayout()
        card_row.setSpacing(10)
        self.card_code_input = QLineEdit()
        self.card_code_input.setPlaceholderText("输入激活码，例如 WINCLEANER-XXXX-XXXX-XXXX")
        redeem_button = QPushButton("兑换卡密")
        redeem_button.setObjectName("scanPrimaryButton")
        redeem_button.setMinimumWidth(112)
        redeem_button.clicked.connect(self.redeem_account_card)
        card_row.addWidget(self.card_code_input, 1)
        card_row.addWidget(redeem_button)

        self.account_message_label = QLabel("已连接服务器授权：注册送体验卡，到期后用激活码续期。")
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

        if not self.require_membership("系统修复"):
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

            if self._optimizer_row_key(payload) in self.optimizer_handled_keys:
                self._mark_optimizer_item_done(item, action_button)

    @staticmethod
    def _optimizer_row_key(row):
        """为优化项生成稳定标识，用于记录是否已处理。"""
        columns = row.get("columns", [])
        return (
            "|".join(str(value).strip().lower() for value in columns[:2]),
            str(row.get("command", "")).strip().lower(),
            str(row.get("action_type", "")),
        )

    def _mark_optimizer_item_done(self, item, action_button):
        """把已执行的优化项渲染成“已处理”，给用户明确反馈。"""
        base_text = item.text(0)
        if not base_text.startswith("✓"):
            item.setText(0, f"✓ {base_text}")
        if item.flags() & Qt.ItemIsUserCheckable:
            item.setCheckState(0, Qt.Unchecked)
        item.setForeground(0, QColor("#0D9488"))
        if action_button is not None:
            action_button.setText("已处理")
            action_button.setEnabled(False)

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
                        "action": "禁用",
                        "action_type": "disable_service",
                        "service_name": service_name,
                        "command": "services.msc",
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
        # 仅在真实枚举不到任何启动项时才回退到示例数据，避免把假项混进真实列表
        if not rows:
            rows = self._fallback_startup_rows()
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

    def _prime_process_cpu(self):
        """初始化 psutil 每进程 CPU 采样基线，使后续刷新得到真实 CPU 占用。"""
        if psutil is None:
            return
        try:
            for _process in psutil.process_iter(["cpu_percent"]):
                pass
        except Exception:
            pass

    def _windows_tasklist_rows(self):
        """psutil 不可用时，用 Windows 自带 tasklist 枚举真实进程，保证“结束”能直接关掉。"""
        if not sys.platform.startswith("win"):
            return []
        try:
            result = subprocess.run(
                "tasklist /FO CSV /NH",
                shell=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=20,
                **hidden_windows_subprocess_kwargs(),
            )
        except Exception:
            return []

        import csv
        import io

        text = decode_console_output(result.stdout)
        entries = []
        for parts in csv.reader(io.StringIO(text)):
            if len(parts) < 5:
                continue
            name = parts[0].strip()
            try:
                pid = int(parts[1])
            except (ValueError, IndexError):
                continue
            digits = "".join(ch for ch in parts[4] if ch.isdigit())
            rss = int(digits) * 1024 if digits else 0
            entries.append((rss, name, pid))

        entries.sort(reverse=True)
        rows = []
        for rss, name, pid in entries[:60]:
            current = pid == os.getpid()
            rows.append({
                "columns": [
                    f"{name}  (PID {pid})",
                    self.format_size(rss) if rss else "--",
                    "--",
                ],
                "icon_hint": name,
                "action": "保留" if current else "结束",
                "action_type": None if current else "kill_process",
                "pid": pid,
                "process_name": name,
                "recommended": False,
            })
        return rows

    def populate_memory_items(self):
        rows = []
        if psutil is not None:
            try:
                total_memory = max(psutil.virtual_memory().total, 1)
                cpu_cores = max(psutil.cpu_count() or 1, 1)
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
                    cpu_percent = (info.get("cpu_percent") or 0.0) / cpu_cores
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

        if not rows:
            rows.extend(self._windows_tasklist_rows())

        # 仅在既没有 psutil 也没有 tasklist（基本只会发生在非 Windows）时才用示例数据
        if not rows:
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
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v LargeSystemCache /t REG_DWORD /d 1 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\LargeSystemCache = 1"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["禁止系统内核与驱动程序分页到硬盘"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v DisablePagingExecutive /t REG_DWORD /d 1 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\DisablePagingExecutive = 1"],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["系统自动管理文件管理系统缓存"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v LargeSystemCache /t REG_DWORD /d 0 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\LargeSystemCache = 0"],
                    2,
                    icon_hint="registry",
                ),
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
                "action": "优化",
                "action_type": "command",
                "command": (
                    r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" '
                    r'/v FeatureSettingsOverride /t REG_DWORD /d 3 /f & '
                    r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" '
                    r'/v FeatureSettingsOverrideMask /t REG_DWORD /d 3 /f'
                ),
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [
                        r"HKLM\...\Memory Management\FeatureSettingsOverride = 3",
                        r"HKLM\...\Memory Management\FeatureSettingsOverrideMask = 3",
                    ],
                    2,
                    icon_hint="registry",
                ),
            },
            {
                "columns": ["关闭TSX漏洞补丁"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Kernel" /v DisableTsx /t REG_DWORD /d 0 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Kernel\DisableTsx = 0"],
                    2,
                    icon_hint="registry",
                ),
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
                "action": "清理",
                "action_type": "command",
                "recommended": False,
                "command": (
                    r'reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v IconStreams /f & '
                    r'reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v PastIconsStream /f'
                ),
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
                "action": "清理",
                "action_type": "command",
                "recommended": False,
                "command": (
                    r'cmd /c del /f /q "%LOCALAPPDATA%\IconCache.db" '
                    r'"%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*" '
                    r'"%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*"'
                ),
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
                "action": "清理",
                "action_type": "command",
                "command": (
                    r'cmd /c del /f /q "%SystemRoot%\Panther\*.log" '
                    r'"%SystemRoot%\INF\setupapi.dev.log" "%SystemRoot%\setupact.log"'
                ),
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
                "action": "清理",
                "action_type": "command",
                "recommended": False,
                "command": (
                    r'cmd /c del /f /q "%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations\*" '
                    r'"%APPDATA%\Microsoft\Windows\Recent\CustomDestinations\*"'
                ),
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
                "action": "清理",
                "action_type": "command",
                "command": (
                    r'reg delete "HKCU\Software\Microsoft\Internet Explorer\TypedURLs" /f & '
                    r'reg delete "HKCU\Software\Microsoft\Internet Explorer\IntelliForms\Storage1" /f & '
                    r'reg delete "HKCU\Software\Microsoft\Internet Explorer\IntelliForms\Storage2" /f & '
                    r"RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess 16"
                ),
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
        rows = []

        # 真实扫描：缺失的共享 DLL、应用程序卸载残留（可一键安全清理，删除前自动备份）
        try:
            issues = self.registry_cleaner.scan()
        except Exception:  # pragma: no cover - 注册表访问异常兜底
            issues = []
        for issue in issues:
            rows.append({
                "columns": [f"[{issue['category']}] {issue['detail']}"],
                "icon_hint": "registry",
                "action": "清理",
                "action_type": "registry_delete",
                "registry": issue,
                "recommended": True,
                "children": self.optimizer_detail_children(
                    [self.registry_cleaner.issue_location(issue)], 2, icon_hint="registry"
                ),
            })

        # 高风险类别不自动删除，点击「检查」直接打开注册表编辑器人工核对
        rows.extend(self._registry_inspect_catalog())

        if not rows:
            rows = [{
                "columns": ["未发现可自动清理的注册表无效项"],
                "icon_hint": "registry",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            }]
        return rows

    def _registry_inspect_catalog(self):
        catalog = [
            ("未使用的文件扩展名", r"HKEY_CLASSES_ROOT"),
            ("无效的默认图标", r"HKEY_CLASSES_ROOT\*\DefaultIcon"),
            ("应用程序打开方式文件问题", r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts"),
            ("CLSID问题", r"HKEY_CLASSES_ROOT\CLSID"),
            ("CLSID问题", r"HKEY_CLASSES_ROOT\Wow6432Node\CLSID"),
            ("CLSID问题", r"HKEY_CLASSES_ROOT\Interface"),
            ("CLSID问题", r"HKEY_CLASSES_ROOT\TypeLib"),
            ("CLSID问题", r"HKEY_CLASSES_ROOT\AppID"),
            ("无效的防火墙规则", r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules"),
            ("Windows 兼容性助手功能的记忆库", r"HKEY_CURRENT_USER\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store"),
            ("统计和管理用户界面交互行为", r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"),
        ]
        rows = []
        for name, reg_path in catalog:
            rows.append({
                "columns": [name],
                "icon_hint": "registry",
                "action": "检查",
                "action_type": "open_regedit",
                "reg_path": reg_path,
                "recommended": False,
                "children": self.optimizer_detail_children([reg_path], 2, icon_hint="registry"),
            })
        return rows

    def current_optimizer_table(self):
        """返回当前标签页对应的表格；BX 卡片界面没有表格时返回 None。"""
        widget = self.optimizer_tabs.currentWidget()
        if widget in self.optimizer_tables.values():
            return widget
        return None

    def set_current_optimizer_checked(self, state):
        table = self.current_optimizer_table()
        if not table:
            return
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for item in self.optimizer_top_level_items(table):
            if item:
                item.setCheckState(0, check_state)

    def apply_optimizer_recommended_filter(self, state):
        table = self.current_optimizer_table()
        if not table or state != Qt.Checked:
            return
        for item in self.optimizer_top_level_items(table):
            payload = item.data(0, Qt.UserRole) if item else {}
            if item:
                item.setCheckState(0, Qt.Checked if payload.get("recommended", True) else Qt.Unchecked)

    def selected_optimizer_rows(self):
        table = self.current_optimizer_table()
        if not table:
            return []
        rows = []
        for item in self.optimizer_top_level_items(table):
            if item and item.checkState(0) == Qt.Checked:
                payload = item.data(0, Qt.UserRole)
                if payload:
                    rows.append(payload)
        return rows

    def _gpu_common_tuning_rows(self):
        """N/A 卡通用的游戏向优化项（对两家显卡都适用且相对安全）。"""
        return [
            {
                "columns": ["启用硬件加速 GPU 调度 (HAGS)"],
                "icon_hint": "nvidia",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f',
                "recommended": True,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\HwSchMode = 2", "重启后生效"],
                    2, icon_hint="registry",
                ),
            },
            {
                "columns": ["关闭全屏优化 (FSO)"],
                "icon_hint": "game",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\System\GameConfigStore" /v GameDVR_FSEBehaviorMode /t REG_DWORD /d 2 /f',
                "recommended": True,
                "children": self.optimizer_detail_children(
                    [r"HKCU\System\GameConfigStore\GameDVR_FSEBehaviorMode = 2"],
                    2, icon_hint="registry",
                ),
            },
            {
                "columns": ["关闭 Game DVR 后台录制"],
                "icon_hint": "game",
                "action": "优化",
                "action_type": "command",
                "command": (
                    r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR" /v AppCaptureEnabled /t REG_DWORD /d 0 /f & '
                    r'reg add "HKCU\System\GameConfigStore" /v GameDVR_Enabled /t REG_DWORD /d 0 /f'
                ),
                "recommended": True,
                "children": self.optimizer_detail_children(
                    ["GameDVR\\AppCaptureEnabled = 0", "GameConfigStore\\GameDVR_Enabled = 0"],
                    2, icon_hint="registry",
                ),
            },
            {
                "columns": ["开启 Windows 游戏模式"],
                "icon_hint": "game",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\GameBar" /v AutoGameModeEnabled /t REG_DWORD /d 1 /f',
                "recommended": True,
                "children": self.optimizer_detail_children(
                    [r"HKCU\Software\Microsoft\GameBar\AutoGameModeEnabled = 1"],
                    2, icon_hint="registry",
                ),
            },
            {
                "columns": ["增大显卡驱动超时时间 (TdrDelay)"],
                "icon_hint": "nvidia",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v TdrDelay /t REG_DWORD /d 10 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\TdrDelay = 10", "减少高负载下的驱动重置"],
                    2, icon_hint="registry",
                ),
            },
        ]

    def populate_nvidia_items(self):
        """N卡一键调优：NVIDIA 专属 + 通用游戏向优化项（Windows 上真实执行）。"""
        rows = [
            {
                "columns": ["禁用 NVIDIA 遥测服务"],
                "icon_hint": "nvidia",
                "action": "优化",
                "action_type": "command",
                "command": r'cmd /c "sc stop NvTelemetryContainer & sc config NvTelemetryContainer start= disabled"',
                "recommended": True,
                "children": self.optimizer_detail_children(
                    ["sc stop NvTelemetryContainer", "sc config NvTelemetryContainer start= disabled"],
                    2, icon_hint="cmd",
                ),
            },
            {
                "columns": ["禁用 NVIDIA 遥测计划任务"],
                "icon_hint": "nvidia",
                "action": "优化",
                "action_type": "command",
                "command": (
                    r'cmd /c "schtasks /Change /DISABLE /TN NvTmRep_CrashReport1_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8} & '
                    r'schtasks /Change /DISABLE /TN NvTmRep_CrashReport2_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8} & '
                    r'schtasks /Change /DISABLE /TN NvTmRep_CrashReport3_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8} & '
                    r'schtasks /Change /DISABLE /TN NvTmRep_CrashReport4_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8}"'
                ),
                "recommended": True,
                "children": self.optimizer_detail_children(
                    ["schtasks /Change /DISABLE /TN NvTmRep_CrashReport*"],
                    2, icon_hint="cmd",
                ),
            },
            {
                "columns": ["NVIDIA 电源管理设为最高性能"],
                "icon_hint": "nvidia",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Services\nvlddmkm\Global\NVTweak" /v DisplayPowerSaving /t REG_DWORD /d 0 /f',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    [r"nvlddmkm\Global\NVTweak\DisplayPowerSaving = 0", "关闭显卡节能，偏向性能"],
                    2, icon_hint="registry",
                ),
            },
        ]
        rows.extend(self._gpu_common_tuning_rows())
        return rows

    def populate_amd_items(self):
        """A卡一键调优：AMD 专属 + 通用游戏向优化项（Windows 上真实执行）。"""
        rows = [
            {
                "columns": ["禁用 AMD ULPS 超低功耗状态"],
                "icon_hint": "driver",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000" /v EnableUlps /t REG_DWORD /d 0 /f',
                "recommended": True,
                "children": self.optimizer_detail_children(
                    [r"Class\{4d36e968-...}\0000\EnableUlps = 0", "减少显卡频繁降频，提升稳定性"],
                    2, icon_hint="registry",
                ),
            },
            {
                "columns": ["禁用 AMD 用户体验遥测计划任务"],
                "icon_hint": "driver",
                "action": "优化",
                "action_type": "command",
                "command": r'cmd /c "schtasks /Change /DISABLE /TN \"StartCN\" & schtasks /Change /DISABLE /TN \"AMD Notifications\ SoftwareUpdate\""',
                "recommended": False,
                "children": self.optimizer_detail_children(
                    ["schtasks /Change /DISABLE /TN StartCN", "schtasks /Change /DISABLE /TN 'AMD Notifications SoftwareUpdate'"],
                    2, icon_hint="cmd",
                ),
            },
        ]
        rows.extend(self._gpu_common_tuning_rows())
        return rows

    def refresh_optimizer_tab(self):
        tab_name = self.optimizer_tabs.tabText(self.optimizer_tabs.currentIndex())
        loaders = {
            "开机加速": self.populate_startup_items,
            "运行内存": self.populate_memory_items,
            "系统优化": self.populate_optimization_items,
            "隐私清理": self.populate_privacy_items,
            "N卡一键调优": self.populate_nvidia_items,
            "A卡一键调优": self.populate_amd_items,
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
        if not self.require_membership(tab_name or "系统优化"):
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
        if not self.require_membership(label or "系统优化"):
            return False
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
        handled = False
        if action_type == "disable_startup":
            handled = self.disable_startup_item(row, confirm=confirm)
        elif action_type == "disable_service":
            handled = self.disable_service_item(row, confirm=confirm)
        elif action_type == "registry_delete" and row.get("registry"):
            handled = self.delete_registry_issue(row, confirm=confirm)
        elif action_type == "open_regedit" and row.get("reg_path"):
            if quiet:
                # 批量「一键优化」不应弹出注册表编辑器，仅供单项点击时查看
                return False
            handled = self.open_registry_editor(row["reg_path"], quiet=quiet)
        elif action_type in {"kill_process", "kill_process_by_name"}:
            handled = self.kill_process_item(row, confirm=confirm)
        elif action_type == "command" and row.get("command"):
            self._run_shell_command(row.get("columns", ["系统优化"])[0], row["command"], quiet=quiet)
            handled = True
        else:
            if not quiet and hasattr(self, "optimizer_status_label"):
                self.optimizer_status_label.setText("该项目仅展示或检查，不需要执行处理。")
                self.animate_status_pulse(self.optimizer_status_label)
            return False

        if handled and action_type != "open_regedit":
            self.optimizer_handled_keys.add(self._optimizer_row_key(row))
        return handled

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

    def disable_service_item(self, row, confirm=False):
        service = row.get("service_name")
        display = row.get("columns", ["服务"])[0]
        if not service:
            return False
        if not sys.platform.startswith("win"):
            QMessageBox.information(self, "系统服务", "禁用服务功能将在 Windows 上执行。")
            return False
        if confirm:
            answer = QMessageBox.question(
                self,
                "禁用服务",
                f"确定禁用并停止服务“{display}”吗？\n\n部分系统服务被禁用后可能影响相关功能，"
                f"如需恢复可在“服务”中将启动类型改回自动/手动。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
        try:
            subprocess.run(
                f'sc stop "{service}"',
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **hidden_windows_subprocess_kwargs(),
            )
            result = subprocess.run(
                f'sc config "{service}" start= disabled',
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **hidden_windows_subprocess_kwargs(),
            )
            if result.returncode != 0:
                QMessageBox.warning(self, "禁用服务", "禁用失败，请用管理员身份运行后重试。")
                return False
            return True
        except Exception as exc:  # pragma: no cover - Windows service dependent
            QMessageBox.warning(self, "禁用服务", f"禁用失败: {exc}")
            return False

    def delete_registry_issue(self, row, confirm=False):
        issue = row.get("registry")
        if not issue:
            return False
        if not self.registry_cleaner.available():
            if not sys.platform.startswith("win"):
                QMessageBox.information(self, "注册表清理", "注册表清理功能将在 Windows 上执行。")
            return False
        if confirm:
            answer = QMessageBox.question(
                self,
                "注册表清理",
                f"确定清理该注册表无效项吗？\n\n{self.registry_cleaner.issue_location(issue)}\n\n"
                f"删除前会自动导出 .reg 备份到备份目录，可随时双击还原。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
        backup_dir = os.path.join(self.cleaner.backup_dir, "registry_backup")
        self.registry_cleaner.export_backup(issue, backup_dir)
        if self.registry_cleaner.delete_issue(issue):
            return True
        QMessageBox.warning(self, "注册表清理", "清理失败，请用管理员身份运行后重试。")
        return False

    def open_registry_editor(self, reg_path, quiet=False):
        if not sys.platform.startswith("win"):
            if not quiet:
                QMessageBox.information(self, "注册表", f"将在 Windows 上打开注册表编辑器并定位:\n{reg_path}")
            return True
        try:
            import winreg
            last_key = reg_path if reg_path.lower().startswith("computer\\") else f"计算机\\{reg_path}"
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Applets\Regedit",
            ) as key:
                winreg.SetValueEx(key, "LastKey", 0, winreg.REG_SZ, last_key)
        except Exception:  # pragma: no cover - 定位失败时仍打开编辑器
            pass
        try:
            subprocess.Popen("regedit", shell=True)
            return True
        except Exception as exc:  # pragma: no cover - Windows shell dependent
            if not quiet:
                QMessageBox.warning(self, "注册表", f"打开注册表编辑器失败: {exc}")
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
        page_subtitle = QLabel("直接列出所有文件夹并按实际占用大小排名，也可扫描大文件、重复文件。")
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

        self.scan_folders_button = QPushButton("扫描文件夹")
        self.scan_folders_button.setObjectName("scanPrimaryButton")
        self.scan_folders_button.setMinimumWidth(112)
        self.scan_folders_button.clicked.connect(self.scan_folder_usage)

        self.scan_large_button = QPushButton("扫描大文件")
        self.scan_large_button.setObjectName("cleanSecondaryButton")
        self.scan_large_button.setMinimumWidth(112)
        self.scan_large_button.clicked.connect(self.scan_large_files)

        self.scan_duplicate_button = QPushButton("扫描重复文件")
        self.scan_duplicate_button.setObjectName("cleanSecondaryButton")
        self.scan_duplicate_button.setMinimumWidth(128)
        self.scan_duplicate_button.clicked.connect(self.scan_duplicate_files)

        self.file_select_all = QCheckBox("全选")
        self.file_select_all.setToolTip("勾选/取消当前列表内所有文件")
        self.file_select_all.stateChanged.connect(self.toggle_all_file_checks)

        self.delete_selected_file_button = QPushButton("删除选中文件")
        self.delete_selected_file_button.setObjectName("cleanSecondaryButton")
        self.delete_selected_file_button.setMinimumWidth(128)
        self.delete_selected_file_button.setToolTip("删除已勾选文件到回收站（可从系统回收站恢复）")
        self.delete_selected_file_button.clicked.connect(self.delete_selected_files)

        self.delete_duplicate_copies_button = QPushButton("彻底删除文件")
        self.delete_duplicate_copies_button.setObjectName("dangerActionButton")
        self.delete_duplicate_copies_button.setMinimumWidth(128)
        self.delete_duplicate_copies_button.setToolTip("彻底删除已勾选文件（不备份、不可恢复）")
        self.delete_duplicate_copies_button.clicked.connect(self.permanently_delete_selected_files)

        toolbar.addWidget(choose_dir_button)
        toolbar.addWidget(self.scan_folders_button)
        toolbar.addWidget(self.scan_large_button)
        toolbar.addWidget(self.scan_duplicate_button)
        toolbar.addWidget(self.file_select_all)
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

        self.folder_tree = self._make_folder_tree()
        self.file_large_table = self._make_file_manage_table(["选择", "文件名", "大小", "路径", "操作"])
        # 大文件“大小”列绘制占用条（相对最大文件）。
        self.file_large_table.setItemDelegateForColumn(2, UsageBarDelegate(self.file_large_table))
        self.file_duplicate_table = self._make_file_manage_table(["选择", "文件名", "大小", "重复组", "路径", "操作"])
        self.fragment_page = self._build_fragment_page()
        self.migration_page = self._build_migration_page()
        self.file_tabs.addTab(self.folder_tree, "文件夹占用")
        self.file_tabs.addTab(self.file_large_table, "大文件")
        self.file_tabs.addTab(self.file_duplicate_table, "重复文件")
        # 碎片整理标签已隐藏（页面仍构建以保留相关引用），不再作为标签展示。
        self.file_tabs.addTab(self.migration_page, "文件迁移")
        self.file_tabs.currentChanged.connect(self.on_file_tab_changed)
        outer.addWidget(self.file_tabs, 1)

        self.file_status_label = QLabel("点击“扫描文件夹”开始统计当前目录占用（可先用“选择目录”切换磁盘）。")
        self.file_status_label.setObjectName("statusLabel")
        outer.addWidget(self.file_status_label)

        return page

    FOLDER_PLACEHOLDER = "__folder_placeholder__"

    def _make_folder_tree(self):
        tree = QTreeWidget()
        tree.setObjectName("folderUsageTree")
        tree.setColumnCount(4)
        tree.setHeaderLabels(["文件夹", "占用大小", "文件数", "占比"])
        tree.setAlternatingRowColors(True)
        tree.setUniformRowHeights(True)
        tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tree.setIconSize(QSize(18, 18))
        tree.setSortingEnabled(False)
        tree.itemExpanded.connect(self.on_folder_item_expanded)
        tree.setItemDelegateForColumn(3, UsageBarDelegate(tree))
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.on_folder_context_menu)

        header_view = tree.header()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Fixed)
        tree.setColumnWidth(1, 110)
        tree.setColumnWidth(2, 80)
        tree.setColumnWidth(3, 160)
        return tree

    def _make_folder_item(self, dir_path, size, file_count, root_total):
        name = os.path.basename(dir_path.rstrip("\\/")) or dir_path
        item = QTreeWidgetItem()
        item.setText(0, name)
        item.setText(1, self.format_size(size))
        item.setText(2, f"{file_count:,}")
        pct = (size / root_total * 100) if root_total else 0
        item.setText(3, f"{pct:.1f}%")
        item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
        item.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
        item.setData(0, Qt.UserRole, dir_path)
        item.setData(3, BAR_FRAC_ROLE, pct / 100.0)  # 供占用条委托绘制
        # 悬停提示：中文名 + 用途 + 是否可清理建议
        tooltip = folder_tooltip(dir_path)
        for column in range(4):
            item.setToolTip(column, tooltip)
        try:
            item.setIcon(0, self.icon_provider.icon(QFileInfo(dir_path)))
        except Exception:
            pass
        # 有子目录时挂一个占位子节点，展开时再懒加载，避免一次性构建整棵树。
        if self.folder_scan_data and self.folder_scan_data["children"].get(dir_path):
            placeholder = QTreeWidgetItem()
            placeholder.setData(0, Qt.UserRole, self.FOLDER_PLACEHOLDER)
            item.addChild(placeholder)
        return item

    def populate_folder_tree(self, payload):
        self.folder_scan_data = payload
        tree = self.folder_tree
        tree.clear()
        root = payload["root"]
        root_total = payload["total"].get(root, 0) or 1
        counts = payload.get("count", {})
        top_items = []
        for child in payload["children"].get(root, []):
            item = self._make_folder_item(
                child, payload["total"].get(child, 0), counts.get(child, 0), root_total
            )
            tree.addTopLevelItem(item)
            top_items.append(item)
        # 默认展开两层：展开顶层项会触发懒加载填充其直接子目录。
        for item in top_items:
            tree.expandItem(item)

    def on_folder_item_expanded(self, item):
        if item.childCount() != 1:
            return
        only_child = item.child(0)
        if only_child.data(0, Qt.UserRole) != self.FOLDER_PLACEHOLDER:
            return
        item.removeChild(only_child)
        dir_path = item.data(0, Qt.UserRole)
        data = self.folder_scan_data or {}
        root_total = data.get("total", {}).get(data.get("root"), 0) or 1
        counts = data.get("count", {})
        for child in data.get("children", {}).get(dir_path, []):
            item.addChild(
                self._make_folder_item(
                    child, data["total"].get(child, 0), counts.get(child, 0), root_total
                )
            )

    def on_folder_context_menu(self, pos):
        item = self.folder_tree.itemAt(pos)
        if item is None:
            return
        path = item.data(0, Qt.UserRole)
        if not path or path == self.FOLDER_PLACEHOLDER:
            return

        menu = QMenu(self.folder_tree)
        act_open = menu.addAction("在资源管理器中打开")
        act_copy = menu.addAction("复制路径")
        menu.addSeparator()
        act_delete = menu.addAction("删除该文件夹…")

        chosen = menu.exec_(self.folder_tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_open:
            self.open_file_location(path)
        elif chosen == act_copy:
            QApplication.clipboard().setText(path)
            self.file_status_label.setText(f"已复制路径: {path}")
            self.animate_status_pulse(self.file_status_label)
        elif chosen == act_delete:
            self.delete_folder_from_tree(path)

    def is_protected_directory(self, path):
        """判断文件夹是否属于禁止删除的系统关键位置或程序自身目录。"""
        if not path:
            return True
        try:
            normalized = os.path.abspath(path).replace("/", "\\").rstrip("\\").lower()
        except Exception:
            return True
        # 盘符根目录，如 c: / c:\
        if len(normalized) <= 2 or normalized.endswith(":"):
            return True
        critical = {
            "c:\\windows", "c:\\program files", "c:\\program files (x86)",
            "c:\\users", "c:\\programdata",
            "c:\\windows\\system32", "c:\\windows\\syswow64", "c:\\windows\\winsxs",
        }
        if normalized in critical:
            return True
        for root in ("c:\\windows\\system32\\", "c:\\windows\\syswow64\\", "c:\\windows\\winsxs\\"):
            if (normalized + "\\").startswith(root):
                return True
        try:
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0])).replace("/", "\\").rstrip("\\").lower()
        except Exception:
            app_dir = ""
        # 程序自身所在目录及其任一祖先目录都不允许删除。
        if app_dir and (app_dir == normalized or app_dir.startswith(normalized + "\\")):
            return True
        return False

    def delete_folder_from_tree(self, path):
        """右键“删除该文件夹”：强保护 + 确认后删除到回收站（可恢复）。"""
        if not path or not os.path.isdir(path):
            QMessageBox.information(self, "删除文件夹", "该文件夹不存在或已被删除。")
            return
        if self.is_protected_directory(path):
            QMessageBox.warning(
                self,
                "删除文件夹",
                "该文件夹属于系统关键位置或程序自身，禁止删除以保证系统稳定。",
            )
            return

        size = 0
        count = 0
        if self.folder_scan_data:
            size = self.folder_scan_data.get("total", {}).get(path, 0)
            count = self.folder_scan_data.get("count", {}).get(path, 0)

        soft_warn = ""
        if self.is_soft_protected_file(path + "\\"):
            soft_warn = "\n注意：该文件夹位于系统或程序目录，删除可能影响已安装程序！"

        prompt = (
            f"确定删除整个文件夹吗？\n{path}\n\n"
            f"占用约 {self.format_size(size)}，包含 {count:,} 个文件，将连同其中所有内容一并删除。\n"
            "删除到回收站（可从回收站恢复）。"
            f"{soft_warn}"
        )
        if QMessageBox.question(
            self, "删除文件夹", prompt,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        ok, err = self.move_path_to_recycle_bin(path)
        if ok:
            self.file_status_label.setText(
                f"已删除文件夹到回收站: {path}（释放约 {self.format_size(size)}）"
            )
            self.animate_status_pulse(self.file_status_label)
            self.update_disk_info()
            # 重新统计占用，刷新树。
            self.folder_scan_done_root = None
            self.scan_folder_usage()
        else:
            QMessageBox.warning(self, "删除文件夹", f"删除失败: {err}")

    def move_path_to_recycle_bin(self, path):
        """将文件或文件夹移动到回收站。返回 (成功, 错误信息)。"""
        if not sys.platform.startswith("win"):
            return False, "仅支持 Windows 回收站删除。"
        try:
            import ctypes
            from ctypes import windll
            from ctypes.wintypes import HWND, UINT, LPCWSTR, BOOL

            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", HWND),
                    ("wFunc", UINT),
                    ("pFrom", LPCWSTR),
                    ("pTo", LPCWSTR),
                    ("fFlags", UINT),
                    ("fAnyOperationsAborted", BOOL),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", LPCWSTR),
                ]

            FO_DELETE = 3
            FOF_ALLOWUNDO = 0x40
            FOF_NOCONFIRMATION = 0x10
            FOF_SILENT = 0x04

            fileop = SHFILEOPSTRUCTW(
                None, FO_DELETE, path + "\0\0", None,
                FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT,
                None, None, None,
            )
            result = windll.shell32.SHFileOperationW(ctypes.byref(fileop))
            if result == 0 and not fileop.fAnyOperationsAborted:
                return True, ""
            return False, f"Shell 操作返回代码 {result}"
        except Exception as exc:  # pragma: no cover - Windows shell dependent
            return False, str(exc)

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
        table.itemChanged.connect(self.on_file_check_item_changed)

        header_view = table.horizontalHeader()
        header_view.setMinimumSectionSize(46)
        for index, name in enumerate(headers):
            if name == "选择":
                header_view.setSectionResizeMode(index, QHeaderView.Fixed)
                table.setColumnWidth(index, 52)
            elif name in ("文件名", "路径"):
                header_view.setSectionResizeMode(index, QHeaderView.Stretch)
            elif name == "操作":
                header_view.setSectionResizeMode(index, QHeaderView.Fixed)
                table.setColumnWidth(index, 150)
            else:
                header_view.setSectionResizeMode(index, QHeaderView.ResizeToContents)
        return table

    @staticmethod
    def _make_file_check_item(payload):
        """文件管理表格第一列的多选复选框，UserRole 存放该行 payload。"""
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setCheckState(Qt.Unchecked)
        item.setTextAlignment(Qt.AlignCenter)
        item.setData(Qt.UserRole, payload)
        return item

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

    def _build_migration_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        tip = QLabel(
            "将桌面、文档、下载、图片等个人文件夹迁移到其它磁盘以释放 C 盘空间。"
            "迁移后会在原位置创建连接点，程序与系统仍按原路径访问，数据实际存放在目标磁盘。"
        )
        tip.setObjectName("pageSubtitle")
        tip.setWordWrap(True)
        outer.addWidget(tip)

        target_row = QHBoxLayout()
        target_row.setSpacing(8)
        target_label = QLabel("目标文件夹:")
        target_label.setObjectName("statusLabel")
        self.migration_target_input = QLineEdit()
        self.migration_target_input.setPlaceholderText("例如 D:\\Personal")
        self.migration_target_input.setText("D:\\Personal")
        browse_button = QPushButton("浏览")
        browse_button.setObjectName("cleanSecondaryButton")
        browse_button.clicked.connect(self.select_migration_target)
        self.migration_move_checkbox = QCheckBox("转移已有文件")
        self.migration_move_checkbox.setChecked(True)
        target_row.addWidget(target_label)
        target_row.addWidget(self.migration_target_input, 1)
        target_row.addWidget(browse_button)
        target_row.addWidget(self.migration_move_checkbox)
        outer.addLayout(target_row)

        self.migration_table = QTableWidget(0, 5)
        self.migration_table.setObjectName("appTable")
        self.migration_table.setHorizontalHeaderLabels(["选择", "文件夹", "当前路径", "占用大小", "状态"])
        self.migration_table.verticalHeader().setVisible(False)
        self.migration_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.migration_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header_view = self.migration_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        outer.addWidget(self.migration_table, 1)

        self.migration_progress = QProgressBar()
        self.migration_progress.setRange(0, 100)
        self.migration_progress.setValue(0)
        self.migration_progress.setTextVisible(False)
        outer.addWidget(self.migration_progress)

        actions = QHBoxLayout()
        mode_label = QLabel("快速选择:")
        mode_label.setObjectName("statusLabel")
        self.migration_default_button = QPushButton("默认模式")
        self.migration_default_button.setObjectName("cleanSecondaryButton")
        self.migration_default_button.setToolTip("勾选：文档、下载、图片、视频、音乐")
        self.migration_default_button.clicked.connect(lambda: self.select_migration_mode("default"))
        self.migration_all_button = QPushButton("全选模式")
        self.migration_all_button.setObjectName("cleanSecondaryButton")
        self.migration_all_button.setToolTip("勾选全部个人文件夹")
        self.migration_all_button.clicked.connect(lambda: self.select_migration_mode("all"))
        actions.addWidget(mode_label)
        actions.addWidget(self.migration_default_button)
        actions.addWidget(self.migration_all_button)
        actions.addStretch(1)
        self.migration_refresh_button = QPushButton("刷新")
        self.migration_refresh_button.setObjectName("cleanSecondaryButton")
        self.migration_refresh_button.clicked.connect(self.refresh_migration_folders)
        self.migration_migrate_button = QPushButton("开始迁移")
        self.migration_migrate_button.setObjectName("scanPrimaryButton")
        self.migration_migrate_button.setMinimumWidth(112)
        self.migration_migrate_button.clicked.connect(self.start_migration)
        self.migration_restore_button = QPushButton("还原选中")
        self.migration_restore_button.setObjectName("cleanSecondaryButton")
        self.migration_restore_button.clicked.connect(self.restore_migration)
        actions.addWidget(self.migration_refresh_button)
        actions.addWidget(self.migration_migrate_button)
        actions.addWidget(self.migration_restore_button)
        outer.addLayout(actions)

        self.migration_status_label = QLabel("点击“刷新”列出可迁移的个人文件夹。")
        self.migration_status_label.setObjectName("statusLabel")
        self.migration_status_label.setWordWrap(True)
        outer.addWidget(self.migration_status_label)

        return page

    def select_migration_target(self):
        directory = QFileDialog.getExistingDirectory(self, "选择目标文件夹", "")
        if directory:
            self.migration_target_input.setText(os.path.normpath(directory))

    # 默认模式勾选的文件夹：文档、下载、图片、视频、音乐
    DEFAULT_MIGRATION_KEYS = {"documents", "downloads", "pictures", "videos", "music"}

    def select_migration_mode(self, mode):
        """默认模式=文档/下载/图片/视频/音乐；全选模式=全部文件夹。"""
        for row in range(self.migration_table.rowCount()):
            item = self.migration_table.item(row, 0)
            if not item or not (item.flags() & Qt.ItemIsUserCheckable):
                continue
            key = item.data(Qt.UserRole)
            if mode == "all":
                checked = True
            else:
                checked = key in self.DEFAULT_MIGRATION_KEYS
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        if hasattr(self, "migration_status_label"):
            label = "全选模式：已勾选全部文件夹。" if mode == "all" else "默认模式：已勾选 文档 / 下载 / 图片 / 视频 / 音乐。"
            self.migration_status_label.setText(label)

    def refresh_migration_folders(self):
        if self.migration_scan_thread and self.migration_scan_thread.isRunning():
            return
        self.migration_status_label.setText("正在统计个人文件夹占用，请稍候...")
        self.animate_status_pulse(self.migration_status_label)
        self.migration_progress.setRange(0, 0)
        self.migration_refresh_button.setEnabled(False)
        self.migration_scan_thread = MigrationScanThread(self.migration_service)
        self.migration_scan_thread.scan_finished_signal.connect(self.on_migration_scan_finished)
        self.migration_scan_thread.scan_error_signal.connect(self.on_migration_scan_error)
        self.migration_scan_thread.start()

    def on_migration_scan_finished(self, folders):
        self.migration_loaded = True
        self.migration_progress.setRange(0, 100)
        self.migration_progress.setValue(0)
        self.migration_refresh_button.setEnabled(True)
        self.migration_rows = {}
        table = self.migration_table
        table.setRowCount(0)
        migrated = 0
        for folder in folders:
            row = table.rowCount()
            table.insertRow(row)
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            # 默认模式：预勾选 文档/下载/图片/视频/音乐（且存在、未迁移）
            default_checked = (
                folder["key"] in self.DEFAULT_MIGRATION_KEYS
                and folder["exists"]
                and not folder["migrated"]
            )
            check_item.setCheckState(Qt.Checked if default_checked else Qt.Unchecked)
            check_item.setData(Qt.UserRole, folder["key"])
            table.setItem(row, 0, check_item)
            table.setItem(row, 1, QTableWidgetItem(folder["name"]))
            path_text = folder["path"]
            if folder["migrated"] and folder.get("target"):
                path_text = f"{folder['path']}  →  {folder['target']}"
            table.setItem(row, 2, QTableWidgetItem(path_text))
            size_text = self.format_size(folder["size"]) if folder["exists"] else "不存在"
            table.setItem(row, 3, QTableWidgetItem(size_text))
            if folder["migrated"]:
                status = "已迁移"
                migrated += 1
            elif not folder["exists"]:
                status = "不存在"
            else:
                status = "未迁移"
            table.setItem(row, 4, QTableWidgetItem(status))
            self.migration_rows[folder["key"]] = folder
        self.migration_status_label.setText(
            f"共 {len(folders)} 个个人文件夹，其中 {migrated} 个已迁移。勾选后可迁移或还原。"
        )

    def on_migration_scan_error(self, message):
        self.migration_progress.setRange(0, 100)
        self.migration_refresh_button.setEnabled(True)
        self.migration_status_label.setText(f"统计失败: {message}")

    def checked_migration_keys(self):
        keys = []
        for row in range(self.migration_table.rowCount()):
            item = self.migration_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                keys.append(item.data(Qt.UserRole))
        return keys

    def set_migration_busy(self, busy):
        self.migration_migrate_button.setEnabled(not busy)
        self.migration_restore_button.setEnabled(not busy)
        self.migration_refresh_button.setEnabled(not busy)
        self.migration_progress.setRange(0, 0 if busy else 100)
        if not busy:
            self.migration_progress.setValue(100)

    def start_migration(self):
        if not self.require_membership("文件迁移"):
            return
        keys = self.checked_migration_keys()
        if not keys:
            QMessageBox.information(self, "文件迁移", "请先勾选需要迁移的文件夹。")
            return
        target_root = self.migration_target_input.text().strip()
        if not target_root:
            QMessageBox.information(self, "文件迁移", "请先填写目标文件夹。")
            return

        pending = [k for k in keys if not (self.migration_rows.get(k, {}).get("migrated"))]
        if not pending:
            QMessageBox.information(self, "文件迁移", "所选文件夹均已迁移。")
            return

        drive = os.path.splitdrive(os.path.abspath(target_root))[0].upper()
        warn = ""
        if drive in ("", "C:"):
            warn = "\n\n注意：目标位于系统盘（C:），迁移后并不会释放 C 盘空间。"
        answer = QMessageBox.question(
            self,
            "确认迁移",
            f"将把选中的 {len(pending)} 个文件夹迁移到:\n{target_root}\n\n"
            "原位置会保留连接点，程序仍可正常访问。此操作会移动真实文件。" + warn,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.set_migration_busy(True)
        self.migration_status_label.setText("正在迁移，请勿关闭软件...")
        self.animate_status_pulse(self.migration_status_label)
        self.migration_thread = MigrationThread(
            self.migration_service,
            "migrate",
            pending,
            target_root=target_root,
            move_files=self.migration_move_checkbox.isChecked(),
        )
        self.migration_thread.progress_signal.connect(self.on_migration_progress)
        self.migration_thread.finished_signal.connect(self.on_migration_finished)
        self.migration_thread.error_signal.connect(self.on_migration_error)
        self.migration_thread.finished.connect(self.migration_thread.deleteLater)
        self.migration_thread.start()

    def restore_migration(self):
        if not self.require_membership("文件迁移"):
            return
        keys = self.checked_migration_keys()
        if not keys:
            QMessageBox.information(self, "文件迁移", "请先勾选需要还原的文件夹。")
            return
        pending = [k for k in keys if self.migration_rows.get(k, {}).get("migrated")]
        if not pending:
            QMessageBox.information(self, "文件迁移", "所选文件夹均未处于迁移状态。")
            return

        answer = QMessageBox.question(
            self,
            "确认还原",
            f"将把选中的 {len(pending)} 个文件夹的数据移回原位置并删除连接点。是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.set_migration_busy(True)
        self.migration_status_label.setText("正在还原，请勿关闭软件...")
        self.animate_status_pulse(self.migration_status_label)
        self.migration_thread = MigrationThread(self.migration_service, "restore", pending)
        self.migration_thread.progress_signal.connect(self.on_migration_progress)
        self.migration_thread.finished_signal.connect(self.on_migration_finished)
        self.migration_thread.error_signal.connect(self.on_migration_error)
        self.migration_thread.finished.connect(self.migration_thread.deleteLater)
        self.migration_thread.start()

    def on_migration_progress(self, message):
        self.migration_status_label.setText(message)

    def on_migration_finished(self, mode, summary):
        self.set_migration_busy(False)
        action = "迁移" if mode == "migrate" else "还原"
        text = f"{action}完成：成功 {summary.get('done', 0)} 个"
        if summary.get("failed"):
            text += f"，失败 {summary['failed']} 个"
        self.migration_status_label.setText(text)
        if summary.get("errors"):
            QMessageBox.warning(
                self, f"文件{action}", "部分项目未完成：\n\n" + "\n".join(summary["errors"][:10])
            )
        self.refresh_migration_folders()

    def on_migration_error(self, message):
        self.set_migration_busy(False)
        self.migration_status_label.setText(f"操作失败: {message}")

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
        if not self.require_membership("磁盘碎片整理"):
            return
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
        if self.hidden_uninstall_keys:
            apps = [a for a in apps if self._app_identity(a) not in self.hidden_uninstall_keys]
        self.uninstall_apps = apps
        if not hasattr(self, "uninstall_table"):
            return
        if self.uninstall_sort_column is not None:
            self._sort_uninstall_apps()
        self.render_uninstall_table(self.uninstall_apps)

        if apps:
            hidden_note = f"（已隐藏 {len(self.hidden_uninstall_keys)} 项）" if self.hidden_uninstall_keys else ""
            self.uninstall_status_label.setText(
                f"已读取 {len(apps)} 个已安装软件{hidden_note}。右键可查看更多操作，点击表头可排序。"
            )
        else:
            message = "当前环境未读取到软件列表；Windows 上会读取卸载注册表。"
            self.uninstall_status_label.setText(message)
            if show_message:
                QMessageBox.information(self, "软件卸载", message)

    def render_uninstall_table(self, apps):
        if not hasattr(self, "uninstall_table"):
            return

        self.uninstall_table.blockSignals(True)
        self.uninstall_table.setRowCount(0)
        for row_index, app in enumerate(apps):
            self.uninstall_table.insertRow(row_index)

            check_item = QTableWidgetItem()
            check_item.setFlags(
                (Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            )
            check_item.setCheckState(Qt.Unchecked)
            check_item.setTextAlignment(Qt.AlignCenter)
            check_item.setData(Qt.UserRole, app)
            self.uninstall_table.setItem(row_index, 0, check_item)

            name_item = QTableWidgetItem(app.get("name", ""))
            icon = self.icon_for_installed_app(app)
            if not icon.isNull():
                name_item.setIcon(icon)
            name_item.setData(Qt.UserRole, app)
            self.uninstall_table.setItem(row_index, 1, name_item)
            self.uninstall_table.setItem(row_index, 2, QTableWidgetItem(app.get("publisher", "")))
            self.uninstall_table.setItem(row_index, 3, QTableWidgetItem(app.get("version", "")))

            date_item = QTableWidgetItem(app.get("install_date", ""))
            date_item.setData(Qt.UserRole, app.get("install_date_sort", 0))
            self.uninstall_table.setItem(row_index, 4, date_item)

            size_bytes = app.get("size_bytes", 0)
            size_item = QTableWidgetItem(self.format_size(size_bytes) if size_bytes else "-")
            size_item.setData(Qt.UserRole, size_bytes)
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.uninstall_table.setItem(row_index, 5, size_item)

            self.uninstall_table.setItem(row_index, 6, QTableWidgetItem(app.get("install_location", "")))

            uninstall_button = QPushButton("卸载")
            uninstall_button.setObjectName("miniActionButton")
            uninstall_button.setCursor(Qt.PointingHandCursor)
            uninstall_button.setMinimumWidth(72)
            uninstall_button.clicked.connect(
                lambda _checked=False, target=dict(app): self.run_uninstall_command(target)
            )
            self.uninstall_table.setCellWidget(row_index, 7, uninstall_button)
            self.uninstall_table.setRowHeight(row_index, 34)

        self.uninstall_table.blockSignals(False)
        if hasattr(self, "uninstall_select_all"):
            self.uninstall_select_all.blockSignals(True)
            self.uninstall_select_all.setChecked(False)
            self.uninstall_select_all.blockSignals(False)

        if self.uninstall_sort_column is not None:
            order = Qt.AscendingOrder if self.uninstall_sort_ascending else Qt.DescendingOrder
            self.uninstall_table.horizontalHeader().setSortIndicator(
                self.uninstall_sort_column, order
            )

    def on_uninstall_header_clicked(self, column):
        if column in (0, 7):
            return
        if self.uninstall_sort_column == column:
            self.uninstall_sort_ascending = not self.uninstall_sort_ascending
        else:
            self.uninstall_sort_column = column
            self.uninstall_sort_ascending = True
        self._sort_uninstall_apps()
        self.render_uninstall_table(self.uninstall_apps)

    def _uninstall_sort_key(self, app):
        column = self.uninstall_sort_column
        if column == 1:
            return app.get("name", "").lower()
        if column == 2:
            return app.get("publisher", "").lower()
        if column == 3:
            return app.get("version", "").lower()
        if column == 4:
            return app.get("install_date_sort", 0)
        if column == 5:
            return app.get("size_bytes", 0)
        if column == 6:
            return app.get("install_location", "").lower()
        return app.get("name", "").lower()

    def _sort_uninstall_apps(self):
        if self.uninstall_sort_column is None:
            return
        self.uninstall_apps.sort(
            key=self._uninstall_sort_key,
            reverse=not self.uninstall_sort_ascending,
        )

    def installed_apps_from_registry(self):
        if not sys.platform.startswith("win"):
            return []

        try:
            import winreg
        except ImportError:
            return []

        locations = [
            (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE",
             r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE",
             r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, "HKEY_CURRENT_USER",
             r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        apps = []
        seen = set()
        for root, root_name, subkey in locations:
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
                        app["reg_hive"] = root
                        app["reg_hive_name"] = root_name
                        app["reg_subkey"] = subkey
                        app["reg_child"] = child_name
                        app["reg_path"] = f"{root_name}\\{subkey}\\{child_name}"
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
        install_date_raw = self._registry_value(key, "InstallDate")
        size_kb = self._registry_int(key, "EstimatedSize")
        size_bytes = size_kb * 1024 if size_kb > 0 else 0
        website = (
            self._registry_value(key, "URLInfoAbout")
            or self._registry_value(key, "HelpLink")
            or self._registry_value(key, "URLUpdateInfo")
        )
        return {
            "name": self._registry_value(key, "DisplayName"),
            "publisher": self._registry_value(key, "Publisher"),
            "version": self._registry_value(key, "DisplayVersion"),
            "install_location": self._registry_value(key, "InstallLocation"),
            "install_date": self._format_install_date(install_date_raw),
            "install_date_sort": self._install_date_sort_key(install_date_raw),
            "size_bytes": size_bytes,
            "website": website,
            "uninstall": self._registry_value(key, "UninstallString"),
            "quiet_uninstall": self._registry_value(key, "QuietUninstallString"),
        }

    @staticmethod
    def _registry_int(key, name):
        try:
            import winreg
            value, _value_type = winreg.QueryValueEx(key, name)
            return int(value)
        except (OSError, ValueError, TypeError):
            return 0

    @staticmethod
    def _format_install_date(raw):
        text = str(raw or "").strip()
        if len(text) == 8 and text.isdigit():
            try:
                parsed = datetime.datetime.strptime(text, "%Y%m%d")
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return text

    @staticmethod
    def _install_date_sort_key(raw):
        text = str(raw or "").strip()
        if len(text) == 8 and text.isdigit():
            try:
                return int(datetime.datetime.strptime(text, "%Y%m%d").timestamp())
            except ValueError:
                pass
        return 0

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

    def toggle_all_uninstall_checks(self, state):
        """顶部“全选”联动整张卸载列表的复选框。"""
        if not hasattr(self, "uninstall_table"):
            return
        target = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        self.uninstall_table.blockSignals(True)
        for row in range(self.uninstall_table.rowCount()):
            check_item = self.uninstall_table.item(row, 0)
            if check_item is not None:
                check_item.setCheckState(target)
        self.uninstall_table.blockSignals(False)
        self.update_uninstall_selection_status()

    def on_uninstall_item_changed(self, item):
        if item is None or item.column() != 0:
            return
        self.sync_uninstall_select_all()
        self.update_uninstall_selection_status()

    def sync_uninstall_select_all(self):
        """根据每行勾选状态回写顶部“全选”复选框（不触发联动）。"""
        if not hasattr(self, "uninstall_select_all"):
            return
        total = self.uninstall_table.rowCount()
        checked = len(self.checked_uninstall_apps())
        self.uninstall_select_all.blockSignals(True)
        self.uninstall_select_all.setChecked(total > 0 and checked == total)
        self.uninstall_select_all.blockSignals(False)

    def checked_uninstall_apps(self):
        apps = []
        if not hasattr(self, "uninstall_table"):
            return apps
        for row in range(self.uninstall_table.rowCount()):
            check_item = self.uninstall_table.item(row, 0)
            if check_item is not None and check_item.checkState() == Qt.Checked:
                app = check_item.data(Qt.UserRole)
                if app:
                    apps.append(app)
        return apps

    def update_uninstall_selection_status(self):
        if not hasattr(self, "uninstall_status_label"):
            return
        count = len(self.checked_uninstall_apps())
        if count:
            self.uninstall_status_label.setText(f"已勾选 {count} 个软件，点击“卸载选中”批量卸载。")

    def uninstall_selected_app(self):
        if not self.require_membership("软件卸载"):
            return
        apps = self.checked_uninstall_apps()
        if not apps:
            row = self.uninstall_table.currentRow()
            if row >= 0:
                item = self.uninstall_table.item(row, 1) or self.uninstall_table.item(row, 0)
                app = item.data(Qt.UserRole) if item else None
                if app:
                    apps = [app]
        if not apps:
            QMessageBox.information(self, "软件卸载", "请先勾选需要卸载的软件。")
            return

        if len(apps) == 1:
            self.run_uninstall_command(apps[0])
            return

        names = "\n".join(f"· {app.get('name', '')}" for app in apps)
        answer = QMessageBox.question(
            self,
            "批量卸载",
            f"确定依次卸载以下 {len(apps)} 个软件吗？\n\n{names}\n\n将逐个调用各自的卸载程序。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        launched = 0
        skipped = []
        for app in apps:
            if self._launch_uninstall(app):
                launched += 1
            else:
                skipped.append(app.get("name", ""))

        if not sys.platform.startswith("win"):
            QMessageBox.information(self, "软件卸载", f"以下命令将在 Windows 上依次执行，共 {len(apps)} 个。")
            return

        message = f"已启动 {launched} 个卸载程序，完成后将自动刷新列表。"
        if skipped:
            message += f" 跳过 {len(skipped)} 个（无可用卸载命令）。"
        self.uninstall_status_label.setText(message)
        QTimer.singleShot(4000, lambda: self.load_installed_apps(show_message=False))
        QTimer.singleShot(12000, lambda: self.load_installed_apps(show_message=False))

    def _launch_uninstall(self, app):
        """执行单个软件的卸载命令（不再单独确认，供批量卸载复用）。"""
        command = app.get("quiet_uninstall") or app.get("uninstall")
        if not command:
            return False
        command = self.normalize_uninstall_command(command)
        if not sys.platform.startswith("win"):
            return True
        try:
            subprocess.Popen(command, shell=True, **hidden_windows_subprocess_kwargs())
            return True
        except Exception:  # pragma: no cover - Windows shell dependent
            return False

    def run_uninstall_command(self, app):
        if not self.require_membership("软件卸载"):
            return
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
            subprocess.Popen(command, shell=True, **hidden_windows_subprocess_kwargs())
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

    # ------------------------------------------------------------------
    # 软件卸载：右键菜单
    # ------------------------------------------------------------------
    @staticmethod
    def _app_identity(app):
        """软件的稳定标识，用于隐藏名单等去重。"""
        if not app:
            return ""
        return app.get("reg_path") or "|".join(
            (app.get("name", ""), app.get("publisher", ""), app.get("version", ""))
        )

    def _app_at_row(self, row):
        if row is None or row < 0:
            return None
        item = self.uninstall_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def show_uninstall_context_menu(self, pos):
        if not hasattr(self, "uninstall_table"):
            return
        row = self.uninstall_table.rowAt(pos.y())
        app = self._app_at_row(row)
        if app is not None:
            self.uninstall_table.selectRow(row)

        menu = QMenu(self)
        has_app = app is not None

        act_uninstall = menu.addAction("卸载")
        act_uninstall.setEnabled(has_app)
        act_force = menu.addAction("强制删除")
        act_force.setEnabled(has_app)
        act_del_entry = menu.addAction("删除条目")
        act_del_entry.setEnabled(has_app)
        act_edit = menu.addAction("编辑信息")
        act_edit.setEnabled(has_app)
        act_hide = menu.addAction("从列表中隐藏")
        act_hide.setEnabled(has_app)

        menu.addSeparator()
        act_select_all = menu.addAction("全选")
        act_refresh = menu.addAction("刷新")
        view_menu = menu.addMenu("查看方式")
        act_view_name = view_menu.addAction("按名称排序")
        act_view_size = view_menu.addAction("按大小排序")
        act_view_date = view_menu.addAction("按安装日期排序")
        act_view_publisher = view_menu.addAction("按发布者排序")

        menu.addSeparator()
        act_open_reg = menu.addAction("打开注册表项")
        act_open_reg.setEnabled(has_app)
        act_open_folder = menu.addAction("安装文件夹")
        act_open_folder.setEnabled(has_app and bool(app.get("install_location")))
        act_website = menu.addAction("程序网站")
        act_website.setEnabled(has_app and bool(app.get("website")))
        act_search = menu.addAction("在线搜索")
        act_search.setEnabled(has_app)
        act_copy = menu.addAction("将名称复制到剪贴板")
        act_copy.setEnabled(has_app)

        menu.addSeparator()
        act_export = menu.addAction("导出列表到…")

        chosen = menu.exec_(self.uninstall_table.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        if chosen is act_uninstall:
            self.run_uninstall_command(app)
        elif chosen is act_force:
            self.force_delete_app(app)
        elif chosen is act_del_entry:
            self.delete_uninstall_entry(app)
        elif chosen is act_edit:
            self.edit_uninstall_entry(app)
        elif chosen is act_hide:
            self.hide_uninstall_app(app)
        elif chosen is act_select_all:
            self.toggle_all_uninstall_checks(Qt.Checked)
            if hasattr(self, "uninstall_select_all"):
                self.uninstall_select_all.setChecked(True)
        elif chosen is act_refresh:
            self.load_installed_apps(show_message=False)
        elif chosen is act_view_name:
            self._apply_uninstall_sort(1)
        elif chosen is act_view_size:
            self._apply_uninstall_sort(5)
        elif chosen is act_view_date:
            self._apply_uninstall_sort(4)
        elif chosen is act_view_publisher:
            self._apply_uninstall_sort(2)
        elif chosen is act_open_reg:
            self.open_app_registry_key(app)
        elif chosen is act_open_folder:
            self.open_app_install_folder(app)
        elif chosen is act_website:
            self.open_app_website(app)
        elif chosen is act_search:
            self.search_app_online(app)
        elif chosen is act_copy:
            self.copy_app_name(app)
        elif chosen is act_export:
            self.export_uninstall_list()

    def _apply_uninstall_sort(self, column):
        self.uninstall_sort_column = column
        self.uninstall_sort_ascending = column not in (4, 5)  # 大小/日期默认降序
        self._sort_uninstall_apps()
        self.render_uninstall_table(self.uninstall_apps)

    def hide_uninstall_app(self, app):
        self.hidden_uninstall_keys.add(self._app_identity(app))
        self.load_installed_apps(show_message=False)

    def copy_app_name(self, app):
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(app.get("name", ""))
            self.uninstall_status_label.setText(f"已复制软件名称: {app.get('name', '')}")

    def search_app_online(self, app):
        name = app.get("name", "").strip()
        if not name:
            return
        query = name
        publisher = app.get("publisher", "").strip()
        if publisher:
            query = f"{name} {publisher}"
        from urllib.parse import quote_plus
        webbrowser.open(f"https://www.bing.com/search?q={quote_plus(query)}")

    def open_app_website(self, app):
        url = app.get("website", "").strip()
        if not url:
            QMessageBox.information(self, "软件卸载", "该软件未在注册表中登记官网地址。")
            return
        if not url.lower().startswith(("http://", "https://")):
            url = "http://" + url
        webbrowser.open(url)

    def open_app_install_folder(self, app):
        location = app.get("install_location", "").strip()
        if not location:
            location = os.path.dirname(self.executable_path_from_command(app.get("uninstall", "")))
        if not location or not os.path.isdir(location):
            QMessageBox.information(self, "软件卸载", "未找到有效的安装文件夹。")
            return
        if sys.platform.startswith("win"):
            try:
                os.startfile(location)  # noqa: for Windows explorer
            except OSError as exc:
                QMessageBox.warning(self, "软件卸载", f"无法打开文件夹: {exc}")
        else:
            self.uninstall_status_label.setText(f"安装文件夹: {location}")

    def open_app_registry_key(self, app):
        reg_path = app.get("reg_path", "")
        if not reg_path:
            QMessageBox.information(self, "软件卸载", "未获取到该软件的注册表项路径。")
            return
        if not sys.platform.startswith("win"):
            self.uninstall_status_label.setText(f"注册表项: {reg_path}")
            return
        try:
            import winreg
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Applets\Regedit",
            ) as key:
                winreg.SetValueEx(key, "LastKey", 0, winreg.REG_SZ, "计算机\\" + reg_path)
            subprocess.Popen(["regedit.exe"], **hidden_windows_subprocess_kwargs())
        except Exception as exc:  # pragma: no cover - Windows dependent
            QMessageBox.warning(self, "软件卸载", f"无法打开注册表编辑器: {exc}")

    def edit_uninstall_entry(self, app):
        if not sys.platform.startswith("win"):
            QMessageBox.information(self, "软件卸载", "编辑注册表信息仅在 Windows 上可用。")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑软件信息")
        dialog.setMinimumWidth(380)
        form = QFormLayout(dialog)
        name_edit = QLineEdit(app.get("name", ""))
        publisher_edit = QLineEdit(app.get("publisher", ""))
        version_edit = QLineEdit(app.get("version", ""))
        form.addRow("显示名称", name_edit)
        form.addRow("发布者", publisher_edit)
        form.addRow("版本", version_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec_() != QDialog.Accepted:
            return

        updates = {
            "DisplayName": name_edit.text().strip(),
            "Publisher": publisher_edit.text().strip(),
            "DisplayVersion": version_edit.text().strip(),
        }
        try:
            import winreg
            full_sub = app["reg_subkey"] + "\\" + app["reg_child"]
            with winreg.OpenKey(
                app["reg_hive"], full_sub, 0, winreg.KEY_SET_VALUE
            ) as key:
                for value_name, value in updates.items():
                    winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value)
            self.uninstall_status_label.setText(f"已更新注册表信息: {updates['DisplayName']}")
            self.load_installed_apps(show_message=False)
        except (OSError, KeyError, PermissionError) as exc:
            QMessageBox.warning(
                self, "软件卸载",
                f"写入注册表失败（可能需要管理员权限）:\n{exc}",
            )

    def delete_uninstall_entry(self, app):
        answer = QMessageBox.question(
            self,
            "删除条目",
            f"确定从注册表中删除“{app.get('name', '')}”的卸载条目吗？\n\n"
            "这只会让它从列表中消失，不会删除程序文件；如果程序仍在，可能无法再从这里卸载。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if self._delete_registry_entry(app):
            self.uninstall_status_label.setText(f"已删除注册表条目: {app.get('name', '')}")
            self.load_installed_apps(show_message=False)

    def force_delete_app(self, app):
        location = app.get("install_location", "").strip()
        detail = f"注册表条目：{app.get('reg_path', '')}"
        if location:
            detail += f"\n安装目录：{location}"
        answer = QMessageBox.warning(
            self,
            "强制删除",
            f"【危险操作】确定强制删除“{app.get('name', '')}”吗？\n\n"
            f"{detail}\n\n"
            "将删除其注册表卸载条目，并尝试删除安装目录中的所有文件。\n"
            "此操作不可恢复，且不会调用官方卸载程序，可能残留启动项或服务。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        removed_folder = False
        if location and os.path.isdir(location) and self._is_safe_to_force_delete(location):
            try:
                shutil.rmtree(location, ignore_errors=True)
                removed_folder = not os.path.isdir(location)
            except OSError:
                removed_folder = False
        self._delete_registry_entry(app)
        self.load_installed_apps(show_message=False)
        msg = f"已强制删除“{app.get('name', '')}”的注册表条目"
        msg += "，并删除了安装目录。" if removed_folder else "。安装目录未删除或不存在。"
        self.uninstall_status_label.setText(msg)

    @staticmethod
    def _is_safe_to_force_delete(location):
        """避免误删系统关键目录。"""
        normalized = os.path.normpath(location).lower().rstrip("\\/")
        if len(normalized) < 4:  # 例如 c:\
            return False
        unsafe = {
            "c:\\windows", "c:\\program files", "c:\\program files (x86)",
            "c:\\programdata", "c:\\users", "c:\\",
        }
        if normalized in unsafe:
            return False
        return True

    def _delete_registry_entry(self, app):
        if not sys.platform.startswith("win"):
            QMessageBox.information(self, "软件卸载", "删除注册表条目仅在 Windows 上可用。")
            return False
        try:
            import winreg
            with winreg.OpenKey(
                app["reg_hive"], app["reg_subkey"], 0,
                winreg.KEY_ALL_ACCESS,
            ) as parent:
                winreg.DeleteKey(parent, app["reg_child"])
            return True
        except (OSError, KeyError, PermissionError) as exc:
            QMessageBox.warning(
                self, "软件卸载",
                f"删除注册表条目失败（可能需要管理员权限）:\n{exc}",
            )
            return False

    def export_uninstall_list(self):
        if not self.uninstall_apps:
            QMessageBox.information(self, "软件卸载", "当前列表为空，没有可导出的内容。")
            return
        default_name = f"installed_apps_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _filter = QFileDialog.getSaveFileName(
            self, "导出软件列表", default_name,
            "CSV 文件 (*.csv);;文本文件 (*.txt)",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["软件名称", "发布者", "版本", "安装日期", "大小", "安装位置"])
                for app in self.uninstall_apps:
                    size_bytes = app.get("size_bytes", 0)
                    writer.writerow([
                        app.get("name", ""),
                        app.get("publisher", ""),
                        app.get("version", ""),
                        app.get("install_date", ""),
                        self.format_size(size_bytes) if size_bytes else "",
                        app.get("install_location", ""),
                    ])
            self.uninstall_status_label.setText(f"已导出 {len(self.uninstall_apps)} 条记录到: {path}")
        except OSError as exc:
            QMessageBox.warning(self, "软件卸载", f"导出失败: {exc}")

    def _build_account_service(self):
        """根据配置选择远程或本地账号服务；远程不可用时回退到本地。"""
        if USE_REMOTE_ACCOUNT and ACCOUNT_API_BASE_URL:
            try:
                return RemoteAccountService(ACCOUNT_API_BASE_URL)
            except Exception:
                pass
        return LocalAccountService()

    def navigate_to_account_page(self):
        """切换到“账号会员”页面；未登录时先弹出独立登录窗口。"""
        if not (getattr(self, "account_state", None) or {}).get("user"):
            self.show_account_auth_dialog(0)
        for index, (label, _method) in enumerate(NAV_ITEMS):
            if label == "账号会员":
                self._select_page(index)
                return

    def on_account_sidebar_clicked(self):
        user = (getattr(self, "account_state", None) or {}).get("user")
        if user:
            self.navigate_to_account_page()
        else:
            self.show_account_auth_dialog(0)

    def show_account_auth_dialog(self, initial_tab=0):
        dialog = AccountAuthDialog(self, initial_tab=initial_tab)
        self.account_auth_dialog = dialog
        dialog.exec_()
        self.account_auth_dialog = None

    def is_membership_active(self):
        """当前账号是否为有效会员（含未过期的体验卡）。"""
        state = getattr(self, "account_state", None) or {}
        user = state.get("user")
        return bool(user and user.get("isPremium"))

    def _refresh_account_state_quiet(self):
        """静默刷新账号状态；离线且此前已登录时保留旧状态，避免误判为未激活。"""
        try:
            new_state = self.account_service.current_state()
        except Exception:
            return
        if not new_state:
            return
        if new_state.get("offline") and (getattr(self, "account_state", None) or {}).get("user"):
            return
        self.account_state = new_state

    def require_membership(self, feature="该功能"):
        """核心功能前置校验：无有效会员时提示激活并返回 False。"""
        self._refresh_account_state_quiet()
        if self.is_membership_active():
            return True

        user = (getattr(self, "account_state", None) or {}).get("user")
        if user:
            text = (
                f"{feature}需要有效会员。\n\n"
                "你的体验卡 / 会员已到期，请输入激活码开通后再使用。"
            )
        else:
            text = (
                f"{feature}需要登录并激活会员后使用。\n\n"
                "新账号注册即赠送一次体验卡，体验到期后可用激活码开通。"
            )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("需要会员")
        box.setText(text)
        go_button = box.addButton("前往激活", QMessageBox.AcceptRole)
        box.addButton("取消", QMessageBox.RejectRole)
        box.exec_()
        if box.clickedButton() is go_button:
            if not user:
                self.show_account_auth_dialog(0)
            else:
                self.navigate_to_account_page()
        return False

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

        if hasattr(self, "account_open_auth_button"):
            self.account_open_auth_button.setVisible(not bool(user))
        if hasattr(self, "account_logout_button"):
            self.account_logout_button.setVisible(bool(user))
        if hasattr(self, "account_sidebar_button"):
            self.account_sidebar_button.setText("账号中心" if user else "登录 / 注册")

        if message:
            self.account_message_label.setText(message)
            self.animate_status_pulse(self.account_message_label)

    def account_credentials(self):
        dialog = getattr(self, "account_auth_dialog", None)
        if dialog is not None and dialog.tabs.currentIndex() == 1:
            return dialog.register_credentials()
        if dialog is not None:
            return dialog.login_credentials()
        return ("", "", "")

    @staticmethod
    def validate_account_name_input(name):
        """客户端即时校验账号名称：≥6 位、不含中文（限 ASCII）。返回错误信息或空串。"""
        value = (name or "").strip()
        if len(value) < 6:
            return "名称至少需要 6 位。"
        if not value.isascii():
            return "名称不能包含中文字符，请使用字母或数字。"
        return ""

    def register_account_from_dialog(self):
        dialog = getattr(self, "account_auth_dialog", None)
        if dialog is None:
            return
        name, password, display_name = dialog.register_credentials()
        name_error = self.validate_account_name_input(name)
        if name_error:
            dialog.set_message(name_error)
            return
        if len(password or "") < 6:
            dialog.set_message("密码至少需要 6 位。")
            return
        try:
            self.account_service.register(name, password, display_name)
            dialog.register_password_input.clear()
            self.refresh_account_state("注册并登录成功。")
            dialog.set_message("注册并登录成功。")
            dialog.accept()
        except AccountError as exc:
            dialog.set_message(str(exc))

    def register_account(self):
        self.register_account_from_dialog()

    def login_account(self):
        name, password, _display_name = self.account_credentials()
        dialog = getattr(self, "account_auth_dialog", None)
        name_error = self.validate_account_name_input(name)
        if name_error:
            if dialog is not None:
                dialog.set_message(name_error)
            else:
                self.refresh_account_state(name_error)
            return
        try:
            self.account_service.login(name, password)
            if dialog is not None:
                dialog.account_password_input.clear()
                dialog.set_message("登录成功。")
                dialog.accept()
            self.refresh_account_state("登录成功。")
        except AccountError as exc:
            if dialog is not None:
                dialog.set_message(str(exc))
            else:
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

    def scan_folder_usage(self):
        """扫描当前目录下所有文件夹并按实际占用大小排名（类似 WinDirStat）。"""
        root_dir = self.current_file_scan_root()
        if hasattr(self, "file_tabs"):
            self.file_tabs.setCurrentWidget(self.folder_tree)
        self.file_status_label.setText(f"正在统计文件夹占用: {root_dir}（大目录可能需要较久）...")
        self.start_file_scan_thread("folders", root_dir)

    def on_file_tab_changed(self, _index):
        """切换标签时不自动扫描文件；但首次进入“文件迁移”会自动列出个人文件夹。"""
        self.sync_file_select_all()
        if (
            hasattr(self, "migration_page")
            and self.file_tabs.currentWidget() is self.migration_page
            and not self.migration_loaded
            and not (self.migration_scan_thread and self.migration_scan_thread.isRunning())
        ):
            self.refresh_migration_folders()
        return

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
        for button_name in ("scan_folders_button", "scan_large_button", "scan_duplicate_button"):
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
        thread.file_scan_progress_signal.connect(self.on_file_scan_progress)
        thread.finished.connect(lambda: self.set_file_scan_controls_enabled(True))
        thread.finished.connect(lambda: setattr(self, "file_scan_thread", None))
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: QApplication.restoreOverrideCursor())
        thread.start()

    def on_file_scan_progress(self, _mode, text):
        if hasattr(self, "file_status_label"):
            self.file_status_label.setText(text)

    def on_file_scan_finished(self, mode, payload):
        if mode == "folders":
            self.populate_folder_tree(payload)
            self.folder_scan_done_root = payload.get("root")
            root = payload.get("root")
            root_total = payload.get("total", {}).get(root, 0)
            folder_count = max(len(payload.get("total", {})) - 1, 0)
            self.file_status_label.setText(
                f"文件夹统计完成: 共 {folder_count} 个文件夹，合计 {self.format_size(root_total)}"
            )
            self.animate_status_pulse(self.file_status_label)
            return

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
            "folders": "文件夹统计",
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
        dialog = DriveSelectDialog(self, current=self.current_file_scan_root())
        if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
            selected = dialog.selected_path
            self.file_scan_root = selected
            self.file_root_label.setText(f"扫描目录: {selected}")
            # 选择目录后自动开始扫描（文件夹占用统计）。
            self.scan_folder_usage()

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
        self.file_large_table.blockSignals(True)
        self.file_large_table.setSortingEnabled(False)
        self.file_large_table.setRowCount(0)
        max_size = max((item["size"] for item in items), default=0) or 1
        for row_index, item in enumerate(items):
            self.file_large_table.insertRow(row_index)
            path = item["path"]
            payload = {"path": path, "size": item["size"], "mode": "large"}

            self.file_large_table.setItem(row_index, 0, self._make_file_check_item(payload))

            name_item = QTableWidgetItem(os.path.basename(path) or path)
            if os.path.exists(path):
                name_item.setIcon(self.icon_provider.icon(QFileInfo(path)))
            name_item.setToolTip(path)
            self.file_large_table.setItem(row_index, 1, name_item)

            size_item = QTableWidgetItem(self.format_size(item["size"]))
            size_item.setData(Qt.UserRole, item["size"])
            size_item.setData(BAR_FRAC_ROLE, item["size"] / max_size)
            self.file_large_table.setItem(row_index, 2, size_item)

            path_item = QTableWidgetItem(path)
            path_item.setToolTip(path)
            path_item.setData(Qt.UserRole, payload)
            self.file_large_table.setItem(row_index, 3, path_item)

            self.file_large_table.setCellWidget(
                row_index,
                4,
                self._make_file_action_widget(payload),
            )
            self.file_large_table.setRowHeight(row_index, 34)
        self.file_large_table.setSortingEnabled(True)
        self.file_large_table.blockSignals(False)
        self.sync_file_select_all()

    def populate_duplicate_files_table(self, duplicates):
        if not hasattr(self, "file_duplicate_table"):
            return
        self.file_duplicate_table.blockSignals(True)
        self.file_duplicate_table.setSortingEnabled(False)
        self.file_duplicate_table.setRowCount(0)
        row_index = 0
        for group_index, (size, paths) in enumerate(duplicates, start=1):
            for path_offset, path in enumerate(paths):
                self.file_duplicate_table.insertRow(row_index)
                action_payload = {
                    "path": path,
                    "size": size,
                    "mode": "duplicate",
                    "group": group_index,
                    "keep": path_offset == 0,
                }
                # 复选框用于批量删除，允许勾选任意副本（包括第一份）。
                check_payload = {
                    "path": path,
                    "size": size,
                    "mode": "duplicate",
                    "group": group_index,
                }
                self.file_duplicate_table.setItem(row_index, 0, self._make_file_check_item(check_payload))

                name_item = QTableWidgetItem(os.path.basename(path) or path)
                if os.path.exists(path):
                    name_item.setIcon(self.icon_provider.icon(QFileInfo(path)))
                name_item.setToolTip(path)
                self.file_duplicate_table.setItem(row_index, 1, name_item)

                size_item = QTableWidgetItem(self.format_size(size))
                size_item.setData(Qt.UserRole, size)
                self.file_duplicate_table.setItem(row_index, 2, size_item)
                self.file_duplicate_table.setItem(row_index, 3, QTableWidgetItem(f"第 {group_index} 组"))

                path_item = QTableWidgetItem(path)
                path_item.setToolTip(path)
                path_item.setData(Qt.UserRole, action_payload)
                self.file_duplicate_table.setItem(row_index, 4, path_item)

                self.file_duplicate_table.setCellWidget(
                    row_index,
                    5,
                    self._make_file_action_widget(action_payload),
                )
                self.file_duplicate_table.setRowHeight(row_index, 34)
                row_index += 1
        self.file_duplicate_table.setSortingEnabled(True)
        self.file_duplicate_table.blockSignals(False)
        self.sync_file_select_all()

    def _make_file_action_widget(self, payload):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 6, 2)
        layout.setSpacing(6)

        keep = payload.get("keep", False)

        open_button = QPushButton("打开")
        open_button.setObjectName("miniActionButton")
        open_button.setCursor(Qt.PointingHandCursor)
        open_button.setFixedWidth(54)
        open_button.setToolTip("在资源管理器中打开所在目录")
        open_button.clicked.connect(lambda _checked=False, target=payload["path"]: self.open_file_location(target))

        delete_button = QPushButton("保留" if keep else "删除")
        delete_button.setObjectName("miniActionButton" if keep else "dangerActionButton")
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setFixedWidth(54)
        delete_button.setEnabled(not keep)
        if keep:
            delete_button.setToolTip("重复组内保留的文件，不会被删除")
        else:
            delete_button.setToolTip("删除该文件（删除前自动备份，可在备份管理中恢复）")
            delete_button.clicked.connect(
                lambda _checked=False, target=dict(payload): self.request_delete_payload(target)
            )

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
            return self.file_duplicate_table, 4, "duplicate"
        return self.file_large_table, 3, "large"

    def _active_file_table(self):
        """当前处于大文件/重复文件标签时返回对应表格，否则 None。"""
        if not hasattr(self, "file_tabs") or not hasattr(self, "file_large_table"):
            return None
        current = self.file_tabs.currentWidget()
        if current in (self.file_large_table, self.file_duplicate_table):
            return current
        return None

    def toggle_all_file_checks(self, state):
        """顶部“全选”联动当前文件表格内所有复选框。"""
        table = self._active_file_table()
        if table is None:
            return
        target = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        table.blockSignals(True)
        for row in range(table.rowCount()):
            check_item = table.item(row, 0)
            if check_item is not None:
                check_item.setCheckState(target)
        table.blockSignals(False)
        self.update_file_selection_status()

    def on_file_check_item_changed(self, item):
        if item is None or item.column() != 0:
            return
        self.sync_file_select_all()
        self.update_file_selection_status()

    def sync_file_select_all(self):
        """根据当前表格勾选状态回写顶部“全选”复选框。"""
        if not hasattr(self, "file_select_all"):
            return
        table = self._active_file_table()
        self.file_select_all.blockSignals(True)
        if table is None:
            self.file_select_all.setChecked(False)
        else:
            total = table.rowCount()
            checked = len(self.checked_file_payloads())
            self.file_select_all.setChecked(total > 0 and checked == total)
        self.file_select_all.blockSignals(False)

    def update_file_selection_status(self):
        if not hasattr(self, "file_status_label"):
            return
        count = len(self.checked_file_payloads())
        if count:
            self.file_status_label.setText(
                f"已勾选 {count} 个文件：可“删除选中文件”（进回收站）或“彻底删除文件”（永久）。"
            )

    def checked_file_payloads(self):
        """当前表格中被勾选的文件 payload 列表。"""
        table = self._active_file_table()
        payloads = []
        if table is None:
            return payloads
        for row in range(table.rowCount()):
            check_item = table.item(row, 0)
            if check_item is not None and check_item.checkState() == Qt.Checked:
                payload = check_item.data(Qt.UserRole)
                if payload:
                    payloads.append(payload)
        return payloads

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

    def files_to_delete(self):
        """优先使用勾选的文件；没有勾选时回退到选中行。"""
        return self.checked_file_payloads() or self.selected_file_payloads()

    def delete_selected_files(self):
        """删除选中文件 → 移动到回收站（可从回收站恢复）。"""
        payloads = self.files_to_delete()
        if not payloads:
            self.file_status_label.setText("请先勾选需要删除的文件。")
            self.animate_status_pulse(self.file_status_label)
            return
        answer = QMessageBox.question(
            self,
            "删除选中文件",
            f"确定将勾选的 {len(payloads)} 个文件删除到回收站吗？\n\n（可从系统回收站恢复）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.delete_file_payloads(payloads, to_recycle_bin=True)

    def permanently_delete_selected_files(self):
        """彻底删除文件 → 永久删除，不进回收站、不可恢复。"""
        payloads = self.files_to_delete()
        if not payloads:
            self.file_status_label.setText("请先勾选需要彻底删除的文件。")
            self.animate_status_pulse(self.file_status_label)
            return
        answer = QMessageBox.warning(
            self,
            "彻底删除文件",
            f"【危险操作】确定彻底删除勾选的 {len(payloads)} 个文件吗？\n\n"
            "文件将被永久删除，不进回收站、无法恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.delete_file_payloads(payloads, force=True, permanent=True)

    def request_delete_payload(self, payload):
        """单行“删除”按钮：带确认与受保护提示，确认后强制删除（仍跳过系统关键文件）。"""
        path = payload.get("path")
        if payload.get("keep"):
            return
        if not path or not os.path.isfile(path):
            QMessageBox.information(self, "删除文件", "该文件不存在或已被删除。")
            self.refresh_file_tables_after_delete()
            return
        if self.is_hard_protected_file(path):
            QMessageBox.warning(
                self,
                "删除文件",
                "该文件属于系统关键位置或程序自身，禁止删除以保证系统稳定。",
            )
            return

        if self.is_soft_protected_file(path):
            prompt = (
                "该文件位于系统或程序目录：\n"
                f"{path}\n\n"
                "删除可能影响已安装程序运行。已开启“删除前备份”，可在备份管理中恢复。\n"
                "确定仍要删除吗？"
            )
        else:
            prompt = (
                f"确定删除该文件吗？\n{path}\n\n"
                "（已开启“删除前备份”，可在备份管理中恢复）"
            )

        if QMessageBox.question(
            self,
            "删除文件",
            prompt,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        self.delete_file_payloads([payload], force=True)

    def delete_file_payloads(self, payloads, force=False, to_recycle_bin=False, permanent=False):
        # 回收站模式不需要备份（可从回收站恢复）；永久删除模式明确不备份。
        if to_recycle_bin or permanent:
            backup_dir = None
        else:
            backup_dir = self.file_delete_backup_dir() if self.cleaner.options.get("backup", True) else None
        deleted_count = 0
        skipped_protected = 0
        skipped_keep = 0
        freed_bytes = 0
        errors = []

        for payload in payloads:
            path = payload.get("path")
            if payload.get("keep"):
                skipped_keep += 1
                continue
            if not path or not os.path.isfile(path):
                continue
            if self.is_hard_protected_file(path):
                skipped_protected += 1
                continue
            if not force and not self.is_user_deletable_file(path):
                skipped_protected += 1
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                size = payload.get("size", 0)
            try:
                if to_recycle_bin:
                    ok, err = self.move_path_to_recycle_bin(path)
                    if not ok:
                        errors.append(f"{path}: {err}")
                        continue
                    freed_bytes += size
                elif permanent:
                    # 永久删除：直接 os.remove，绝不进回收站、不可恢复。
                    os.remove(path)
                    freed_bytes += size
                else:
                    freed_bytes += self.delete_file_path(path, backup_dir=backup_dir)
                deleted_count += 1
            except Exception as exc:  # pragma: no cover - filesystem dependent
                errors.append(f"{path}: {exc}")

        self.refresh_file_tables_after_delete()

        skipped_total = skipped_protected + skipped_keep
        verb = "删除到回收站" if to_recycle_bin else ("彻底删除" if permanent else "删除")
        status = f"已{verb} {deleted_count} 个文件，释放 {self.format_size(freed_bytes)}"
        if skipped_total:
            status += f"，跳过 {skipped_total} 个受保护/保留项"
        if errors:
            status += f"，失败 {len(errors)} 个"
        self.file_status_label.setText(status)
        self.animate_status_pulse(self.file_status_label)

        # 批量操作时，如果全部被系统/程序目录保护而未删除，给出明确弹窗说明，避免“点了没反应”的困惑。
        if deleted_count == 0 and skipped_protected and not errors:
            QMessageBox.information(
                self,
                "未删除文件",
                f"有 {skipped_protected} 个文件位于受保护的系统/程序目录，已自动跳过。\n\n"
                "如确实需要删除其中某个文件，请点击该行右侧的“删除”按钮单独确认。",
            )

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
        if self.is_hard_protected_file(path):
            return False
        return not self.is_soft_protected_file(path)

    def is_hard_protected_file(self, path):
        """系统关键文件 / 程序自身：任何情况下都不允许删除。"""
        if not path:
            return True
        file_name = os.path.basename(path).lower()
        if file_name in {"pagefile.sys", "hiberfil.sys", "swapfile.sys", "ntldr", "bootmgr"}:
            return True
        normalized = path.replace("/", "\\").lower()
        hard_roots = (
            "c:\\windows\\system32\\",
            "c:\\windows\\syswow64\\",
            "c:\\windows\\winsxs\\",
        )
        if any(normalized.startswith(root) for root in hard_roots):
            return True
        try:
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0])).replace("/", "\\").lower()
        except Exception:
            app_dir = ""
        if app_dir and normalized.startswith(app_dir + "\\"):
            return True
        return False

    def is_soft_protected_file(self, path):
        """系统或程序目录：默认跳过，但用户单行确认后可强制删除。"""
        normalized = (path or "").replace("/", "\\").lower()
        soft_roots = (
            "c:\\windows\\",
            "c:\\program files\\",
            "c:\\program files (x86)\\",
        )
        return any(normalized.startswith(root) for root in soft_roots)

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
        self.update_sidebar_footer()

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
        self.update_sidebar_footer()
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

    def remove_cleaned_items_from_tree(self, cleaned_paths):
        """清理后不再整棵重新扫描，只把已清理/已消失的行从树里去掉。"""
        if not hasattr(self, "results_tree"):
            return
        cleaned = set()
        for path in cleaned_paths or []:
            try:
                cleaned.add(os.path.normcase(os.path.abspath(path)))
            except Exception:
                pass

        self.results_tree.setUpdatesEnabled(False)
        self.results_tree.blockSignals(True)
        try:
            for i in range(self.results_tree.topLevelItemCount() - 1, -1, -1):
                category_item = self.results_tree.topLevelItem(i)
                for j in range(category_item.childCount() - 1, -1, -1):
                    child = category_item.child(j)
                    data = child.data(0, Qt.UserRole) or {}
                    path = data.get("path", "")
                    if not path:
                        continue
                    try:
                        norm = os.path.normcase(os.path.abspath(path))
                    except Exception:
                        norm = ""
                    if norm in cleaned or not os.path.exists(path):
                        category_item.removeChild(child)
                if category_item.childCount() == 0:
                    self.results_tree.takeTopLevelItem(i)
        finally:
            self.results_tree.blockSignals(False)
            self.results_tree.setUpdatesEnabled(True)
        self.update_selected_items()

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
        if not self.require_membership("文件清理"):
            return
        clean_items = [item for item in items if self.is_cleanable_item(item)]
        if not clean_items:
            QMessageBox.information(self, action_label, "没有可清理项目")
            return

        total_size = sum(item['size'] for item in clean_items)
        professional_items = [item for item in clean_items if self.is_scan_only_item(item)]
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(f"确认{action_label}")

        msg.setText(
            f"您确定要{action_label} {len(clean_items)} 个项目，"
            f"总计 {self.format_size(total_size)} 吗？（将真实删除）"
        )
        if professional_items:
            msg.setInformativeText(
                f"其中包含 {len(professional_items)} 个专业清理项。"
                "这些路径可能属于 WinSxS、WindowsApps、Defender、EdgeCore 或系统组件缓存，"
                "删除后可能影响系统更新、应用恢复或安全记录。此操作无法撤销！"
            )
        else:
            msg.setInformativeText("文件将被真实删除，此操作无法撤销！")
        
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        if msg.exec_() != QMessageBox.Yes:
            return
        
        # 设置清理选项：始终真实删除，备份开启时可在“备份管理”中恢复
        self.cleaner.set_options({
            'simulate': False,
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
        skipped = results.get('skipped', [])

        message = f"清理完成，已释放空间: {self.format_size(freed_space)}"

        if skipped:
            message += f"，跳过 {len(skipped)} 个被占用文件"
        if errors:
            message += f"，{len(errors)} 个错误"

        self.status_label.setText(message)
        self.animate_status_pulse(self.status_label)
        self.update_selected_items()

        # 只有真正的清理失败才弹窗提醒；被占用/受保护的文件属于正常跳过，不算错误。
        if errors:
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("清理错误")
            error_msg.setText(f"清理过程中发生 {len(errors)} 个错误")
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            if skipped:
                error_details += (
                    f"\n\n另有 {len(skipped)} 个文件正被其它程序占用，已自动跳过（属正常情况）。"
                )
            error_msg.setDetailedText(error_details)
            error_msg.exec_()
        
        # 只更新磁盘信息，不自动重新扫描（用户如需刷新可手动点“重新扫描”）。
        self.update_disk_info()
        self.remove_cleaned_items_from_tree(results.get("cleaned_items", []))

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
