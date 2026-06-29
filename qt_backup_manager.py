#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Qt backup management dialog for C盘清理精灵."""

import os
import shutil

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class QtBackupManagerDialog(QDialog):
    """Manage cleanup backups without falling back to the legacy Tk window."""

    def __init__(self, parent, cleaner, format_size):
        super().__init__(parent)
        self.cleaner = cleaner
        self.format_size = format_size

        self.setWindowTitle("备份管理")
        self.setMinimumSize(760, 520)
        self._build_ui()
        self.refresh_backup_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.backup_dir_label = QLabel("备份目录: --")
        self.backup_count_label = QLabel("备份数量: --")
        self.backup_size_label = QLabel("备份总大小: --")
        layout.addWidget(self.backup_dir_label)
        layout.addWidget(self.backup_count_label)
        layout.addWidget(self.backup_size_label)

        dir_row = QHBoxLayout()
        self.backup_dir_edit = QLineEdit()
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_backup_dir)
        apply_dir_button = QPushButton("应用目录")
        apply_dir_button.clicked.connect(self.apply_backup_dir)
        dir_row.addWidget(QLabel("备份目录:"))
        dir_row.addWidget(self.backup_dir_edit, 1)
        dir_row.addWidget(browse_button)
        dir_row.addWidget(apply_dir_button)
        layout.addLayout(dir_row)

        limit_row = QHBoxLayout()
        self.max_backups_edit = QLineEdit()
        self.max_backups_edit.setFixedWidth(70)
        self.max_backup_size_edit = QLineEdit()
        self.max_backup_size_edit.setFixedWidth(90)
        apply_limits_button = QPushButton("应用限制")
        apply_limits_button.clicked.connect(self.apply_backup_limits)
        limit_row.addWidget(QLabel("最大备份数量:"))
        limit_row.addWidget(self.max_backups_edit)
        limit_row.addWidget(QLabel("最大备份大小(MB):"))
        limit_row.addWidget(self.max_backup_size_edit)
        limit_row.addWidget(apply_limits_button)
        limit_row.addStretch(1)
        layout.addLayout(limit_row)

        self.backup_table = QTableWidget(0, 3)
        self.backup_table.setHorizontalHeaderLabels(["备份名称", "备份时间", "大小"])
        self.backup_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.backup_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.backup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backup_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.backup_table, 1)

        button_row = QHBoxLayout()
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_backup_list)
        restore_button = QPushButton("恢复选中的备份")
        restore_button.clicked.connect(self.restore_backup)
        delete_button = QPushButton("删除选中的备份")
        delete_button.clicked.connect(self.delete_backup)
        clean_button = QPushButton("清理旧备份")
        clean_button.clicked.connect(self.clean_old_backups)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)

        button_row.addWidget(refresh_button)
        button_row.addWidget(restore_button)
        button_row.addWidget(delete_button)
        button_row.addWidget(clean_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def refresh_backup_list(self):
        info = self.cleaner.get_backup_info()
        self.backup_dir_label.setText(f"备份目录: {info['backup_dir']}")
        self.backup_count_label.setText(f"备份数量: {info['backup_count']}")
        self.backup_size_label.setText(f"备份总大小: {self.format_size(info['total_size'])}")
        self.backup_dir_edit.setText(info["backup_dir"])
        self.max_backups_edit.setText(str(self.cleaner.max_backups))
        self.max_backup_size_edit.setText(str(int(self.cleaner.max_backup_size / (1024 * 1024))))

        self.backup_table.setRowCount(0)
        for backup in info["backups"]:
            row = self.backup_table.rowCount()
            self.backup_table.insertRow(row)
            name_item = QTableWidgetItem(backup["name"])
            name_item.setData(Qt.UserRole, backup["path"])
            self.backup_table.setItem(row, 0, name_item)
            self.backup_table.setItem(row, 1, QTableWidgetItem(backup["time"]))
            self.backup_table.setItem(row, 2, QTableWidgetItem(self.format_size(backup["size"])))

    def browse_backup_dir(self):
        selected = QFileDialog.getExistingDirectory(
            self,
            "选择备份目录",
            self.backup_dir_edit.text() or self.cleaner.backup_dir,
        )
        if selected:
            self.backup_dir_edit.setText(selected)

    def apply_backup_dir(self):
        backup_dir = self.backup_dir_edit.text().strip()
        if not backup_dir:
            QMessageBox.warning(self, "备份目录", "备份目录不能为空")
            return
        try:
            os.makedirs(backup_dir, exist_ok=True)
            self.cleaner.set_options({"backup_dir": backup_dir})
            self.refresh_backup_list()
        except Exception as exc:
            QMessageBox.warning(self, "备份目录", f"设置备份目录失败: {exc}")

    def apply_backup_limits(self):
        try:
            max_backups = int(self.max_backups_edit.text().strip())
            max_backup_size_mb = int(self.max_backup_size_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "备份限制", "请输入有效数字")
            return

        if max_backups <= 0 or max_backup_size_mb <= 0:
            QMessageBox.warning(self, "备份限制", "备份数量和大小必须大于 0")
            return

        self.cleaner.set_options({
            "max_backups": max_backups,
            "max_backup_size": max_backup_size_mb * 1024 * 1024,
        })
        self.refresh_backup_list()

    def selected_backup_path(self):
        rows = self.backup_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.backup_table.item(rows[0].row(), 0)
        return item.data(Qt.UserRole) if item else None

    def restore_backup(self):
        backup_path = self.selected_backup_path()
        if not backup_path:
            QMessageBox.information(self, "备份恢复", "请先选择要恢复的备份")
            return
        if QMessageBox.question(
            self,
            "确认恢复",
            "恢复备份将覆盖当前文件，确定要继续吗？",
        ) != QMessageBox.Yes:
            return
        if self.cleaner.restore_backup(backup_path):
            QMessageBox.information(self, "备份恢复", "备份恢复成功")
        else:
            QMessageBox.warning(self, "备份恢复", "备份恢复失败")

    def delete_backup(self):
        backup_path = self.selected_backup_path()
        if not backup_path:
            QMessageBox.information(self, "删除备份", "请先选择要删除的备份")
            return
        if QMessageBox.question(
            self,
            "确认删除",
            "确定要删除选中的备份吗？此操作无法撤销！",
        ) != QMessageBox.Yes:
            return
        try:
            shutil.rmtree(backup_path)
            self.refresh_backup_list()
        except Exception as exc:
            QMessageBox.warning(self, "删除备份", f"删除备份失败: {exc}")

    def clean_old_backups(self):
        if QMessageBox.question(
            self,
            "清理旧备份",
            "确定按当前限制清理旧备份吗？",
        ) != QMessageBox.Yes:
            return
        if self.cleaner.clean_old_backups():
            self.refresh_backup_list()
        else:
            QMessageBox.warning(self, "清理旧备份", "旧备份清理失败")
