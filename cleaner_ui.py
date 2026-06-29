#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 用户界面
"""

import os
import sys
import subprocess
import hashlib
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
                            QFileIconProvider)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QFileInfo
from PyQt5.QtGui import QIcon, QFont, QPixmap

from cleaner_logic import CleanerLogic
from category_display import category_tree_label
from config import APP_NAME
from qt_backup_manager import QtBackupManagerDialog


APP_DISPLAY_NAME = "C盘清理精灵"


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

QTableWidget#optimizerTable,
QTableWidget#uninstallTable {
    background: #FFFFFF;
    border: 1px solid #D6E8E4;
    border-radius: 8px;
    color: #1C2C26;
    gridline-color: #E3EFEC;
    outline: 0;
    selection-background-color: #CCEFE8;
    selection-color: #15241C;
}

QTableWidget#optimizerTable::item,
QTableWidget#uninstallTable::item {
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


# 侧边栏导航项：(标签, 页面构建方法名)
NAV_ITEMS = [
    ("C盘清理", "_build_clean_page"),
    ("系统优化", "_build_optimize_page"),
    ("软件卸载", "_build_uninstall_page"),
    ("文件管理", "_build_file_page"),
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
        return button

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(168)

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
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setObjectName(
                "sidebarButtonActive" if i == index else "sidebarButton"
            )
            # 重新应用样式表，让 objectName 变化即时生效
            button.style().unpolish(button)
            button.style().polish(button)

    # ------------------------------------------------------------------
    # 通用小组件
    # ------------------------------------------------------------------
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
        self.setMinimumSize(960, 660)
        self.resize(1020, 700)
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
        self.professional_checkbox.setToolTip("专业模式允许清理 WinSxS、WindowsApps、Defender、EdgeCore 等高风险扫描项")
        self.professional_checkbox.stateChanged.connect(self.on_clean_mode_changed)

        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.setToolTip("勾选/取消勾选当前模式下的全部可清理项")
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

        return page

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
        reload_button.clicked.connect(lambda: self.load_installed_apps(show_message=True))
        uninstall_button = QPushButton("卸载选中")
        uninstall_button.setObjectName("scanPrimaryButton")
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
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        outer.addWidget(self.uninstall_table, 1)

        self.uninstall_status_label = QLabel("正在读取软件列表...")
        self.uninstall_status_label.setObjectName("statusLabel")
        outer.addWidget(self.uninstall_status_label)

        self.load_installed_apps(show_message=False)
        return page

    def _make_optimizer_table(self, headers):
        table = QTableWidget()
        table.setObjectName("optimizerTable")
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setIconSize(QSize(20, 20))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeToContents)
        return table

    def _populate_optimizer_table(self, table, rows):
        table.setRowCount(0)
        for row_index, payload in enumerate(rows):
            table.insertRow(row_index)
            columns = payload.get("columns", [])
            for column_index in range(table.columnCount() - 1):
                text = columns[column_index] if column_index < len(columns) else ""
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column_index == 0:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked if payload.get("recommended", True) else Qt.Unchecked)
                    item.setData(Qt.UserRole, payload)
                    icon = self.category_icon_for_name(payload.get("icon_hint") or text)
                    if not icon.isNull():
                        item.setIcon(icon)
                table.setItem(row_index, column_index, item)

            action_button = QPushButton(payload.get("action", "处理"))
            action_button.setObjectName("miniActionButton")
            action_button.setCursor(Qt.PointingHandCursor)
            action_button.clicked.connect(
                lambda _checked=False, row=dict(payload): self.run_optimizer_row_action(row)
            )
            table.setCellWidget(row_index, table.columnCount() - 1, action_button)
            table.setRowHeight(row_index, 34)

    def _fallback_startup_rows(self):
        return [
            {
                "columns": ["Windows Security notification icon", "系统通知启动项"],
                "icon_hint": "defender",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Microsoft OneDrive", "用户启动项"],
                "icon_hint": "onedrive",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
            {
                "columns": ["Microsoft Edge", "更新/浏览器启动项"],
                "icon_hint": "edge",
                "action": "查看",
                "command": "taskmgr",
                "action_type": "command",
            },
        ]

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

        return rows or self._fallback_startup_rows()

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

        if rows:
            return rows

        return [
            {
                "columns": ["C盘清理精灵.exe", "--", "--"],
                "icon_hint": "cleaner",
                "action": "刷新",
                "action_type": "command",
                "command": "taskmgr",
                "recommended": False,
            }
        ]

    def populate_optimization_items(self):
        return [
            {
                "columns": ["刷新 DNS 解析缓存"],
                "icon_hint": "windows",
                "action": "执行",
                "action_type": "command",
                "command": "ipconfig /flushdns",
            },
            {
                "columns": ["执行系统空闲任务整理"],
                "icon_hint": "windows",
                "action": "执行",
                "action_type": "command",
                "command": "rundll32.exe advapi32.dll,ProcessIdleTasks",
            },
            {
                "columns": ["关闭“使用 Windows 时获取技巧和建议”"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v SubscribedContent-338389Enabled /t REG_DWORD /d 0 /f',
            },
            {
                "columns": ["关闭开始菜单建议广告"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v SystemPaneSuggestionsEnabled /t REG_DWORD /d 0 /f',
            },
            {
                "columns": ["关闭锁屏界面内容广告"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v RotatingLockScreenOverlayEnabled /t REG_DWORD /d 0 /f',
            },
            {
                "columns": ["禁用自动更新地图"],
                "icon_hint": "windows",
                "action": "优化",
                "action_type": "command",
                "command": r'reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\Maps" /v AutoDownloadAndUpdateMapData /t REG_DWORD /d 0 /f',
                "recommended": False,
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
            },
            {
                "columns": ["开始菜单运行记录"],
                "icon_hint": "windows",
                "action": "清理",
                "action_type": "command",
                "command": r'reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /f',
            },
            {
                "columns": ["Internet Explorer 上网痕迹"],
                "icon_hint": "ie",
                "action": "清理",
                "action_type": "command",
                "command": "RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess 255",
            },
            {
                "columns": ["系统通知区及图标缓存"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            },
            {
                "columns": ["快速访问的缓存数据存储"],
                "icon_hint": "windows",
                "action": "检查",
                "action_type": None,
                "recommended": False,
            },
            {
                "columns": ["IE 浏览器自动完成"],
                "icon_hint": "ie",
                "action": "检查",
                "action_type": None,
            },
        ]

    def populate_registry_items(self):
        return [
            {"columns": ["缺失的共享 DLL"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["未使用的文件扩展名"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["无效的默认图标"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["应用程序打开方式文件问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["CLSID 问题"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["应用程序卸载残留"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["无效的防火墙规则"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["Windows 兼容性助手功能的记忆库"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
            {"columns": ["统计和管理用户界面交互行为"], "icon_hint": "registry", "action": "检查", "action_type": None, "recommended": False},
        ]

    def set_current_optimizer_checked(self, state):
        table = self.optimizer_tabs.currentWidget()
        if not table:
            return
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                item.setCheckState(check_state)

    def apply_optimizer_recommended_filter(self, state):
        table = self.optimizer_tabs.currentWidget()
        if not table or state != Qt.Checked:
            return
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            payload = item.data(Qt.UserRole) if item else {}
            if item:
                item.setCheckState(Qt.Checked if payload.get("recommended", True) else Qt.Unchecked)

    def selected_optimizer_rows(self):
        table = self.optimizer_tabs.currentWidget()
        if not table:
            return []
        rows = []
        for row_index in range(table.rowCount()):
            item = table.item(row_index, 0)
            if item and item.checkState() == Qt.Checked:
                payload = item.data(Qt.UserRole)
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

        risky_tabs = {"开机加速", "运行内存"}
        if tab_name in risky_tabs:
            answer = QMessageBox.question(
                self,
                "一键优化",
                f"将处理 {len(rows)} 个“{tab_name}”项目，是否继续？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        executed = 0
        skipped = 0
        for row in rows:
            if self.run_optimizer_row_action(row, confirm=False, quiet=True):
                executed += 1
            else:
                skipped += 1

        QMessageBox.information(
            self,
            "一键优化",
            f"{tab_name} 已处理 {executed} 项，保留/需人工复核 {skipped} 项。",
        )
        self.refresh_optimizer_tab()

    def run_optimizer_row_action(self, row, confirm=True, quiet=False):
        action_type = row.get("action_type")
        if action_type == "disable_startup":
            return self.disable_startup_item(row, confirm=confirm)
        if action_type == "kill_process":
            return self.kill_process_item(row, confirm=confirm)
        if action_type == "command" and row.get("command"):
            self._run_shell_command(row.get("columns", ["系统优化"])[0], row["command"], quiet=quiet)
            return True

        if not quiet:
            QMessageBox.information(
                self,
                "系统优化",
                "此项目属于高风险或需人工确认项，已保留在列表中供检查，不会静默修改系统。",
            )
        return False

    def _run_shell_command(self, label, command, quiet=False):
        if sys.platform.startswith("win"):
            try:
                subprocess.Popen(command, shell=True)
                return
            except Exception as exc:  # pragma: no cover - Windows shell dependent
                QMessageBox.warning(self, label, f"执行失败: {exc}")
                return
        if not quiet:
            QMessageBox.information(self, label, f"该操作将在 Windows 上执行:\n{command}")

    def disable_startup_item(self, row, confirm=True):
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

    def kill_process_item(self, row, confirm=True):
        pid = row.get("pid")
        process_name = row.get("columns", ["进程"])[0]
        if not pid:
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
            if psutil is not None:
                psutil.Process(pid).terminate()
            elif sys.platform.startswith("win"):
                subprocess.Popen(f"taskkill /PID {pid} /F", shell=True)
            else:
                return False
            return True
        except Exception as exc:  # pragma: no cover - process state dependent
            QMessageBox.warning(self, "结束进程", f"结束失败: {exc}")
            return False

    def _build_file_page(self):
        return self._build_feature_page(
            "文件管理",
            "定位大文件、管理磁盘占用，把扫描到的可清理路径交给 C盘清理处理。",
            [
                ("大文件扫描", "C盘清理已包含 >100MB 大文件扫描，点此前往查看结果。",
                 "开始大文件扫描", self.scan_large_files),
                ("重复文件扫描", "选择一个目录，按大小和哈希找出重复文件。",
                 "扫描重复文件", self.scan_duplicate_files),
                ("打开此电脑", "在资源管理器中查看各磁盘占用情况。",
                 "打开此电脑", lambda: self.run_system_action("此电脑", "explorer")),
                ("存储使用情况", "打开 Windows 存储设置，按类别查看占用。",
                 "打开存储设置", lambda: self.run_system_action("存储设置", "ms-settings:storagesense")),
                ("磁盘清理", "调用 Windows 自带磁盘清理工具。",
                 "打开磁盘清理", lambda: self.run_system_action("磁盘清理", "cleanmgr")),
            ],
        )

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
        self._select_page(2)
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
            self.uninstall_status_label.setText(f"已启动卸载程序: {app.get('name', '')}")
        except Exception as exc:  # pragma: no cover - Windows shell dependent
            QMessageBox.warning(self, "软件卸载", f"启动卸载失败: {exc}")

    @staticmethod
    def normalize_uninstall_command(command):
        lowered = command.lower()
        if "msiexec" in lowered and " /i" in lowered:
            command = command.replace(" /I", " /X").replace(" /i", " /X")
        return command

    def scan_large_files(self):
        """切回 C 盘清理并执行包含大文件项的一键扫描。"""
        self._select_page(0)
        if self.scan_button.isEnabled():
            self.start_scan()
        else:
            self.status_label.setText("扫描正在进行中...")

    def scan_duplicate_files(self):
        """选择目录并按大小+SHA256 查找重复文件。"""
        root_dir = QFileDialog.getExistingDirectory(self, "选择重复文件扫描目录", os.path.expanduser("~"))
        if not root_dir:
            return

        self.status_label.setText(f"正在扫描重复文件: {root_dir}")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            duplicates = self._find_duplicate_files(root_dir)
        finally:
            QApplication.restoreOverrideCursor()

        if not duplicates:
            self.status_label.setText("重复文件扫描完成，未发现重复文件")
            QMessageBox.information(self, "重复文件扫描", "未发现重复文件。")
            return

        lines = []
        total_waste = 0
        for size, paths in duplicates[:12]:
            total_waste += size * (len(paths) - 1)
            lines.append(f"{self.format_size(size)} x {len(paths)}")
            lines.extend(f"  {path}" for path in paths[:4])
            if len(paths) > 4:
                lines.append(f"  ... 还有 {len(paths) - 4} 个")

        self.status_label.setText(
            f"重复文件扫描完成，发现 {len(duplicates)} 组，约可处理 {self.format_size(total_waste)}"
        )
        QMessageBox.information(self, "重复文件扫描", "\n".join(lines)[:7000])

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

        total_items = self.refresh_cleanable_totals()

        if not results or total_items == 0:
            self.status_label.setText("扫描完成，未发现可清理项目")
            self.update_selected_items()
            return

        # 填充结果树
        self.populate_results_tree(results)
        self.select_all_checkbox.setEnabled(bool(self.cleanable_items))
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
        return hasattr(self, "professional_checkbox") and self.professional_checkbox.isChecked()

    @staticmethod
    def is_scan_only_item(item):
        """截图补充路径中不少条目只能统计，不能直接清理。"""
        return bool(item.get("scan_only"))

    def allow_item_cleaning(self, item):
        return not self.is_scan_only_item(item) or self.professional_mode_enabled()

    def is_cleanable_item(self, item):
        return self.allow_item_cleaning(item)

    def on_clean_mode_changed(self, _state):
        """推荐/专业模式切换后，重新计算可清理项和勾选状态。"""
        sender = self.sender()
        if sender is self.professional_checkbox and self.professional_checkbox.isChecked():
            self.recommended_checkbox.blockSignals(True)
            self.recommended_checkbox.setChecked(False)
            self.recommended_checkbox.blockSignals(False)
        elif sender is self.recommended_checkbox and self.recommended_checkbox.isChecked():
            self.professional_checkbox.blockSignals(True)
            self.professional_checkbox.setChecked(False)
            self.professional_checkbox.blockSignals(False)
        elif not self.recommended_checkbox.isChecked() and not self.professional_checkbox.isChecked():
            self.recommended_checkbox.blockSignals(True)
            self.recommended_checkbox.setChecked(True)
            self.recommended_checkbox.blockSignals(False)

        if self.scan_results:
            self.refresh_cleanable_totals()
            self.populate_results_tree(self.scan_results)
            self.select_all_checkbox.setEnabled(bool(self.cleanable_items))
            self.clean_all_button.setEnabled(bool(self.cleanable_items))
            if self.select_all_checkbox.isChecked():
                self.on_select_all_changed(Qt.Checked)
            else:
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
        mode_name = "专业" if self.professional_mode_enabled() else "推荐"
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

    def populate_results_tree(self, results):
        """填充结果树"""
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
                scan_only = self.is_scan_only_item(item)
                cleanable = self.is_cleanable_item(item)
                file_item = QTreeWidgetItem(category_item)
                item_name = self.display_name_from_path(item_path)
                if scan_only and cleanable:
                    file_item.setText(0, f"{item_name} [专业]")
                elif scan_only:
                    file_item.setText(0, f"{item_name} [仅统计]")
                else:
                    file_item.setText(0, item_name)
                file_item.setText(1, self.format_size(item['size']))
                file_item.setText(2, item_path)
                file_item.setIcon(0, self.target_icon_for_item(item))
                if scan_only and cleanable:
                    file_item.setToolTip(0, "专业清理项，确认后可清理")
                elif scan_only:
                    file_item.setToolTip(0, "仅统计路径，不会直接清理")
                file_item.setToolTip(2, item_path)
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Unchecked)
                file_item.setData(0, Qt.UserRole, item)
                if not cleanable:
                    file_item.setDisabled(True)

        self.results_tree.expandAll()

    def on_select_all_changed(self, state):
        """顶部“全选”勾选框：勾选/取消所有类别。"""
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        self.results_tree.blockSignals(True)
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
        self.results_tree.blockSignals(False)
        self.update_selected_items()

    def on_item_changed(self, item, column):
        """处理项目选择状态变化"""
        if column != 0:
            return

        # 如果是类别项，同步所有子项
        if item.parent() is None:
            check_state = item.checkState(0)
            self.results_tree.blockSignals(True)
            for i in range(item.childCount()):
                child_item = item.child(i)
                item_data = child_item.data(0, Qt.UserRole) or {}
                if child_item.isDisabled() or not self.is_cleanable_item(item_data):
                    child_item.setCheckState(0, Qt.Unchecked)
                    continue
                child_item.setCheckState(0, check_state)
            self.results_tree.blockSignals(False)

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
            'allow_scan_only_clean': self.professional_mode_enabled(),
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
