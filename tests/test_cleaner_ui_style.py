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


def test_qt_ui_has_recommended_professional_and_select_all_modes():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "self.recommended_checkbox = QCheckBox(\"推荐\")" in source
    assert "self.professional_checkbox = QCheckBox(\"专业\")" in source
    assert "self.select_all_checkbox = QCheckBox(\"全选\")" in source
    assert "def current_clean_mode" in source
    assert "allow_scan_only_clean" in source
    assert "def professional_mode_enabled" in source
    assert "def on_clean_mode_changed" in source
    assert "def allow_item_cleaning" in source


def test_qt_professional_mode_is_not_select_all_mode():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    allow_logic = source.split("def allow_item_cleaning", 1)[1].split("def is_cleanable_item", 1)[0]
    select_all_logic = source.split("def on_select_all_changed", 1)[1].split("def on_item_changed", 1)[0]

    assert 'if mode == "all":' in allow_logic
    assert "return True" in allow_logic
    assert 'if mode == "professional":' in allow_logic
    assert "return self.is_scan_only_item(item)" in allow_logic
    assert "return not self.is_scan_only_item(item)" in allow_logic
    assert 'self.set_clean_mode("all")' in select_all_logic
    assert 'self.set_clean_mode("recommended")' in select_all_logic
    assert 'self.current_clean_mode() in {"professional", "all"}' in source


def test_qt_cleanup_mode_switch_updates_existing_tree_without_rebuilding():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    mode_handler = source.split("def on_clean_mode_changed", 1)[1].split("def refresh_cleanable_totals", 1)[0]

    assert "update_result_tree_cleanability" in source
    assert "populate_results_tree" not in mode_handler
    assert "setUpdatesEnabled(False)" in source


def test_qt_bulk_selection_pauses_tree_repaints():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    select_all_handler = source.split("def on_select_all_changed", 1)[1].split("def on_item_changed", 1)[0]
    item_changed_handler = source.split("def on_item_changed", 1)[1].split("def update_selected_items", 1)[0]

    assert "setUpdatesEnabled(False)" in select_all_handler
    assert "setUpdatesEnabled(True)" in select_all_handler
    assert "setUpdatesEnabled(False)" in item_changed_handler
    assert "setUpdatesEnabled(True)" in item_changed_handler


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


def test_qt_scan_results_use_target_icons():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "QFileIconProvider" in source
    assert "category_icon_for_name" in source
    assert "target_icon_for_item" in source
    assert "file_item.setIcon(0, self.target_icon_for_item(item))" in source


def test_qt_system_optimizer_matches_tabbed_internal_tooling():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "self.optimizer_tabs" in source
    assert "开机加速" in source
    assert "运行内存" in source
    assert "系统优化" in source
    assert "隐私清理" in source
    assert "注册表清理" in source
    assert "populate_startup_items" in source
    assert "populate_memory_items" in source
    assert "populate_optimization_items" in source
    assert "populate_privacy_items" in source
    assert "populate_registry_items" in source
    assert "一键优化" in source


def test_qt_uninstaller_is_in_app_table():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "self.uninstall_table" in source
    assert "load_installed_apps" in source
    assert "uninstall_selected_app" in source
    assert "QuietUninstallString" in source
    assert "UninstallString" in source
    assert "QTableWidget" in source


def test_qt_file_manager_uses_in_app_tables():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    file_page = source.split("def _build_file_page", 1)[1].split("def _open_system_tool", 1)[0]
    large_scan = source.split("def scan_large_files", 1)[1].split("def scan_duplicate_files", 1)[0]
    duplicate_scan = source.split("def scan_duplicate_files", 1)[1].split("def set_file_scan_controls_enabled", 1)[0]

    assert "self.file_tabs = QTabWidget()" in file_page
    assert "self.file_large_table" in file_page
    assert "self.file_duplicate_table" in file_page
    assert "populate_large_files_table" in source
    assert "populate_duplicate_files_table" in source
    assert "_select_page(0)" not in large_scan
    assert "QMessageBox.information" not in duplicate_scan


def test_qt_labels_have_room_for_chinese_actions():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "sidebar.setFixedWidth(196)" in source
    assert "button.setMinimumWidth(148)" in source
    assert "uninstall_button.setMinimumWidth(96)" in source
    assert "header_view.setMinimumSectionSize(86)" in source


def test_qt_uses_lightweight_opacity_animations():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "QPropertyAnimation" in source
    assert "QGraphicsOpacityEffect" in source
    assert "QEasingCurve.OutCubic" in source
    assert "def animate_page_transition" in source
    assert "def animate_status_pulse" in source
    page_animation = source.split("def animate_page_transition", 1)[1].split("def animate_status_pulse", 1)[0]
    assert 'b"opacity"' in source
    assert "animation.setDuration(duration)" in source
    assert "0.62, 1.0, 160" in page_animation
    assert "geometry" not in page_animation
    assert "resize" not in page_animation


def test_qt_has_in_app_account_login_register_and_card_redeem():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert '("账号会员", "_build_account_page")' in source
    assert "LocalAccountService" in source
    assert "self.account_email_input" in source
    assert "self.account_password_input" in source
    assert "self.card_code_input" in source
    assert "register_account" in source
    assert "login_account" in source
    assert "redeem_account_card" in source
    assert "WINCLEANER-VIP-30D" in source
    assert "登录" in source
    assert "注册" in source
    assert "兑换卡密" in source


def test_qt_file_manager_scans_run_in_worker_thread():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    large_scan = source.split("def scan_large_files", 1)[1].split("def scan_duplicate_files", 1)[0]
    duplicate_scan = source.split("def scan_duplicate_files", 1)[1].split("def on_file_scan_finished", 1)[0]

    assert "class FileScanThread(QThread)" in source
    assert "file_scan_finished_signal" in source
    assert 'self.start_file_scan_thread("large", root_dir)' in large_scan
    assert 'self.start_file_scan_thread("duplicates", root_dir)' in duplicate_scan
    assert "thread = FileScanThread(mode, root_dir)" in source
    assert "self.find_large_files(root_dir)" not in large_scan
    assert "self._find_duplicate_files(root_dir)" not in duplicate_scan


def test_qt_optimizer_pages_have_expanded_catalogs():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "populate_startup_service_items" in source
    assert "startup_folder_items" in source
    assert "Windows Security notification icon" in source
    assert "Realtek高清晰音频管理器" in source
    assert "Microsoft Edge Update Service (edgeupdate)" in source
    assert "GameViewerService" in source
    assert "NVIDIA Display Container LS" in source
    assert "Microsoft PC Manager Service" in source
    assert "ToDesk Service" in source
    assert "Windows 启动优化功能（碎片整理预取）" in source
    assert "禁用Windows预安装和应用推荐功能" in source
    assert "登录缓存配置文件" in source
    assert "程序安装信息" in source
    assert "CLSID问题" in source


def test_qt_uninstaller_refreshes_after_uninstall_command():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    run_uninstall = source.split("def run_uninstall_command", 1)[1].split("def normalize_uninstall_command", 1)[0]

    assert "QTimer.singleShot" in run_uninstall
    assert "load_installed_apps(show_message=False)" in run_uninstall


def test_qt_optimizer_actions_run_without_manual_confirmations():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    populate_table = source.split("def _populate_optimizer_table", 1)[1].split("def _dedupe_optimizer_rows", 1)[0]
    apply_tab = source.split("def apply_current_optimization_tab", 1)[1].split("def run_optimizer_row_action", 1)[0]
    run_action_signature = source.split("def run_optimizer_row_action", 1)[1].split(":", 1)[0]
    kill_process = source.split("def kill_process_item", 1)[1].split("def _build_file_page", 1)[0]

    assert "confirm=False" in populate_table
    assert "QMessageBox.question" not in apply_tab
    assert "QMessageBox.information(\n            self,\n            \"一键优化\"" not in apply_tab
    assert "confirm=False" in run_action_signature
    assert "kill_process_by_name" in source
    assert "process_name" in kill_process
    assert "taskkill /IM" in kill_process
