#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 用户界面
"""

import os
import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QProgressBar, QCheckBox,
                            QTreeWidget, QTreeWidgetItem, QMessageBox,
                            QFrame, QGridLayout, QStackedWidget, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap

from cleaner_logic import CleanerLogic
from category_display import category_tree_label
from config import APP_NAME


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
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)

    def __init__(self, cleaner):
        super().__init__()
        self.cleaner = cleaner

    def run(self):
        """运行扫描过程"""
        results = self.cleaner.scan_system()
        self.finished_signal.emit(results)


class CleanThread(QThread):
    """清理线程，避免UI冻结"""
    update_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(dict)

    def __init__(self, cleaner, selected_items):
        super().__init__()
        self.cleaner = cleaner
        self.selected_items = selected_items

    def run(self):
        """运行清理过程"""
        results = self.cleaner.clean_selected(self.selected_items, self.update_signal)
        self.finished_signal.emit(results)


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
        self.app_icon = self._load_app_icon()
        self.nav_buttons = []

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

        self.clean_button = QPushButton("一键清理")
        self.clean_button.setObjectName("cleanSecondaryButton")
        self.clean_button.setCursor(Qt.PointingHandCursor)
        self.clean_button.setToolTip("清理当前勾选的扫描结果")
        self.clean_button.setEnabled(False)
        self.clean_button.clicked.connect(self.start_clean)

        action_layout.addWidget(self.scan_button)
        action_layout.addWidget(self.clean_button)
        action_layout.addStretch(1)
        hero_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("scanProgress")
        self.progress_bar.setVisible(False)

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

        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.setToolTip("勾选/取消勾选全部扫描结果")
        self.select_all_checkbox.setEnabled(False)
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)

        self.simulate_checkbox = QCheckBox("模拟模式")
        self.simulate_checkbox.setToolTip("默认不实际删除文件")
        self.simulate_checkbox.setChecked(True)

        self.backup_checkbox = QCheckBox("删除前备份")
        self.backup_checkbox.setChecked(True)

        result_header.addWidget(self.select_all_checkbox)
        result_header.addWidget(self.simulate_checkbox)
        result_header.addWidget(self.backup_checkbox)
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
        return self._build_feature_page(
            "系统优化",
            "调用 Windows 内置工具优化启动项、服务、磁盘和电源策略（在 Windows 系统上生效）。",
            [
                ("启动项管理", "打开任务管理器，禁用拖慢开机的自启动程序。",
                 "打开任务管理器", lambda: self._open_system_tool("任务管理器", "taskmgr")),
                ("系统服务", "打开服务管理器，按需调整后台服务启动类型。",
                 "打开服务", lambda: self._open_system_tool("服务管理器", "services.msc")),
                ("磁盘碎片整理", "调用 Windows 磁盘优化工具整理/优化驱动器。",
                 "打开磁盘优化", lambda: self._open_system_tool("磁盘优化", "dfrgui")),
                ("电源选项", "切换高性能/节能电源计划。",
                 "打开电源选项", lambda: self._open_system_tool("电源选项", "powercfg.cpl")),
            ],
        )

    def _build_uninstall_page(self):
        return self._build_feature_page(
            "软件卸载",
            "通过 Windows 程序和功能管理已安装软件，彻底卸载不需要的程序。",
            [
                ("程序和功能", "打开经典的“程序和功能”卸载列表。",
                 "打开卸载列表", lambda: self._open_system_tool("程序和功能", "appwiz.cpl")),
                ("应用和功能", "打开 Windows 设置中的应用管理页。",
                 "打开应用设置", lambda: self._open_system_tool("应用和功能", "ms-settings:appsfeatures")),
                ("已安装更新", "查看并卸载已安装的系统/软件更新。",
                 "查看更新", lambda: self._open_system_tool("已安装更新", "appwiz.cpl")),
                ("存储感知", "打开存储设置，按使用情况清理应用。",
                 "打开存储设置", lambda: self._open_system_tool("存储感知", "ms-settings:storagesense")),
            ],
        )

    def _build_file_page(self):
        return self._build_feature_page(
            "文件管理",
            "定位大文件、管理磁盘占用，把扫描到的可清理路径交给 C盘清理处理。",
            [
                ("大文件扫描", "C盘清理已包含 >100MB 大文件扫描，点此前往查看结果。",
                 "前往C盘清理", lambda: self._select_page(0)),
                ("打开此电脑", "在资源管理器中查看各磁盘占用情况。",
                 "打开此电脑", lambda: self._open_system_tool("此电脑", "explorer")),
                ("存储使用情况", "打开 Windows 存储设置，按类别查看占用。",
                 "打开存储设置", lambda: self._open_system_tool("存储设置", "ms-settings:storagesense")),
                ("磁盘清理", "调用 Windows 自带磁盘清理工具。",
                 "打开磁盘清理", lambda: self._open_system_tool("磁盘清理", "cleanmgr")),
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
        self.clean_button.setEnabled(False)
        self.select_all_checkbox.setEnabled(False)
        self.results_tree.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.cleanable_value_label.setText("0 B")
        self.result_summary_label.setText("扫描进行中")
        self.selected_summary_label.setText("已选 0 项 / 0 B")
        self.status_label.setText("正在扫描系统，请稍候...")

        # 启动扫描线程
        self.scan_thread = ScanThread(self.cleaner)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.start()

    def on_scan_finished(self, results):
        """扫描完成后的处理"""
        self.scan_results = results
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self.scan_button.setText("重新扫描")

        total_items = sum(len(items) for items in results.values())
        total_size = sum(item['size'] for category in results.values() for item in category)
        category_count = sum(1 for items in results.values() if items)
        self.cleanable_value_label.setText(self.format_size(total_size))
        self.result_summary_label.setText(
            f"{category_count} 类 / {total_items} 项 / {self.format_size(total_size)}"
        )

        if not results or total_items == 0:
            self.status_label.setText("扫描完成，未发现可清理项目")
            self.update_selected_items()
            return

        self.status_label.setText(f"扫描完成，发现可释放空间: {self.format_size(total_size)}")

        # 填充结果树
        self.populate_results_tree(results)
        self.select_all_checkbox.setEnabled(True)
        self.update_selected_items()

        # 更新磁盘信息
        self.update_disk_info()

    @staticmethod
    def display_name_from_path(path):
        """从 Windows 或 POSIX 路径中提取用于树节点的短名称。"""
        normalized = path.rstrip("\\/")
        if not normalized:
            return path
        return normalized.replace("\\", "/").rsplit("/", 1)[-1] or normalized

    def populate_results_tree(self, results):
        """填充结果树"""
        self.results_tree.clear()
        category_font = QFont()
        category_font.setBold(True)

        for category, items in results.items():
            if not items:
                continue

            category_size = sum(item['size'] for item in items)
            category_name = category_tree_label(category)

            category_item = QTreeWidgetItem(self.results_tree)
            category_item.setText(0, category_name)
            category_item.setText(1, self.format_size(category_size))
            category_item.setText(2, f"{len(items)} 项路径")
            category_item.setFont(0, category_font)
            category_item.setFont(1, category_font)
            if not self.app_icon.isNull():
                category_item.setIcon(0, self.app_icon)
            category_item.setFlags(category_item.flags() | Qt.ItemIsUserCheckable)
            category_item.setCheckState(0, Qt.Unchecked)

            for item in items:
                item_path = item['path']
                file_item = QTreeWidgetItem(category_item)
                file_item.setText(0, self.display_name_from_path(item_path))
                file_item.setText(1, self.format_size(item['size']))
                file_item.setText(2, item_path)
                file_item.setToolTip(2, item_path)
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Unchecked)
                file_item.setData(0, Qt.UserRole, item)

        self.results_tree.expandAll()

    def on_select_all_changed(self, state):
        """顶部“全选”勾选框：勾选/取消所有类别。"""
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        self.results_tree.blockSignals(True)
        for i in range(self.results_tree.topLevelItemCount()):
            category_item = self.results_tree.topLevelItem(i)
            category_item.setCheckState(0, check_state)
            for j in range(category_item.childCount()):
                category_item.child(j).setCheckState(0, check_state)
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
                item.child(i).setCheckState(0, check_state)
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
                    if item_data:
                        self.selected_items.append(item_data)

        selected_size = sum(item['size'] for item in self.selected_items)
        self.selected_summary_label.setText(
            f"已选 {len(self.selected_items)} 项 / {self.format_size(selected_size)}"
        )
        self.clean_button.setEnabled(len(self.selected_items) > 0)

    def start_clean(self):
        """开始清理选中的项目"""
        if not self.selected_items:
            return

        # 确认对话框
        total_size = sum(item['size'] for item in self.selected_items)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("确认清理")

        if self.simulate_checkbox.isChecked():
            msg.setText(f"您选择了模拟模式，将会模拟清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)}。")
        else:
            msg.setText(f"您确定要清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)} 吗？")
            msg.setInformativeText("此操作无法撤销！")

        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec_() != QMessageBox.Yes:
            return

        # 设置清理选项
        self.cleaner.set_options({
            'simulate': self.simulate_checkbox.isChecked(),
            'backup': self.backup_checkbox.isChecked()
        })

        # 开始清理
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.clean_button.setText("清理中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, len(self.selected_items))
        self.status_label.setText("正在清理文件，请稍候...")

        # 启动清理线程
        self.clean_thread = CleanThread(self.cleaner, self.selected_items)
        self.clean_thread.update_signal.connect(self.on_clean_progress)
        self.clean_thread.finished_signal.connect(self.on_clean_finished)
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
        self.clean_button.setText("一键清理")

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

        # 更新磁盘信息
        self.update_disk_info()

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
