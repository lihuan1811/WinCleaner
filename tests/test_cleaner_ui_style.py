from pathlib import Path


def test_qt_ui_uses_cleaner_spirit_layout():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "APP_QSS" in source
    assert "sidebar" in source
    assert "heroPanel" in source
    assert "resultCard" in source
    assert "resultTree" in source
    assert "scanPrimaryButton" in source


def test_qt_ui_keeps_screenshot_like_teal_shell():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "#14B8A6" in source
    assert "一键扫描" in source
    assert "一键清理" in source
    assert "扫描结果" in source
    assert "C盘清理精灵" in source


def test_qt_ui_sidebar_navigation_is_wired():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "QStackedWidget" in source
    assert "_select_page" in source
    assert "系统优化" in source
    assert "软件卸载" in source
    assert "文件管理" in source


def test_qt_ui_separates_clean_all_from_selected_clean():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "self.clean_all_button = QPushButton(\"一键清理\")" in source
    assert "self.clean_button = QPushButton(\"清理选中\")" in source
    assert "def start_clean_all" in source
    assert "self.cleanable_items" in source
    assert "start_clean_items" in source


def test_qt_ui_marks_statistics_only_items_as_not_cleanable():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "is_scan_only_item" in source
    assert "仅统计" in source
    assert "setDisabled(True)" in source
    assert "cleanable_size" in source
    assert "scan_only" in source


def test_qt_ui_has_backup_management_and_thread_error_recovery():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "QtBackupManagerDialog" in source
    assert "browse_backup_dir" in source
    assert "restore_backup" in Path("qt_backup_manager.py").read_text(encoding="utf-8")
    assert "error_signal" in source
    assert "on_scan_error" in source
    assert "on_clean_error" in source


def test_qt_feature_pages_have_native_actions_not_only_shortcuts():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "run_system_action" in source
    assert "show_installed_apps" in source
    assert "scan_large_files" in source
    assert "scan_duplicate_files" in source
