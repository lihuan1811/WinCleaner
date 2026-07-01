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
    assert "系统修复" in source


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
    assert "QTreeWidget" in source
    assert "QTreeWidgetItem" in source
    assert "children" in source
    assert "addChild" in source
    assert "setExpanded" in source
    assert "开机加速" in source
    assert "运行内存" in source
    assert "系统优化" in source
    assert "隐私清理" in source
    assert "N卡一键调优" in source
    assert "A卡一键调优" in source
    assert "populate_startup_items" in source
    assert "populate_memory_items" in source
    assert "populate_optimization_items" in source
    assert "populate_privacy_items" in source
    assert "populate_nvidia_items" in source
    assert "populate_amd_items" in source
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
    assert "self.fragment_page" in file_page
    assert "碎片整理" in file_page
    assert "populate_large_files_table" in source
    assert "populate_duplicate_files_table" in source
    assert "删除选中文件" in file_page
    assert "删除重复副本" in file_page
    assert "_make_file_action_widget" in source
    assert "delete_selected_files" in source
    assert "delete_duplicate_copies" in source
    assert "delete_file_path" in source
    assert "_select_page(0)" not in large_scan
    assert "QMessageBox.information" not in duplicate_scan


def test_qt_file_manager_has_fragment_cleanup_tab():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "class DefragThread(QThread)" in source
    assert "scan_fragments" in source
    assert "optimize_fragments" in source
    assert "defrag C: /A /V" in source
    assert "defrag C: /U /V" in source
    assert "fragment_grid_cells" in source
    assert "碎片数" in source
    assert "碎片文件" in source
    assert "碎片率" in source
    assert "扫描碎片" in source
    assert "整理碎片" in source
    assert "hidden_windows_subprocess_kwargs" in source


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


def test_qt_sidebar_has_bx_optimization_module():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    # BX 优化已合并进「系统优化」页的「系统优化」标签，不再是独立侧边栏页
    assert '("BX(优化)", "_build_bx_page")' not in source
    assert "def _build_bx_widget" in source
    assert "self.optimizer_bx_tab_index" in source
    assert "self.bx_mode" in source
    assert "self.bx_active_category" in source
    assert "def page_index_for_label" in source
    show_apps = source.split("def show_installed_apps", 1)[1].split("def load_installed_apps", 1)[0]
    assert 'self.page_index_for_label("软件卸载")' in show_apps
    assert "self._select_page(2)" not in show_apps


def test_qt_bx_module_has_basic_and_best_modes():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "BX(优化)" in source
    assert "基础设置" in source
    assert "self.bx_basic_button = QPushButton(\"基本\")" in source
    assert "self.bx_best_button = QPushButton(\"最佳\")" in source
    assert "def select_bx_mode" in source
    assert 'self.bx_mode = "basic"' in source
    assert 'self.bx_mode = "best"' in source
    assert "应用" in source


def test_qt_bx_module_contains_boosterx_like_items():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    for label in [
        "自动更新地图",
        "商店应用程序的自动更新",
        "全局全屏优化（FSO）",
        "游戏栏",
        "索引",
        "SysMain（预取、Superfetch...）",
        "打印服务",
        "诊断驱动程序",
        "暂停 Windows 更新",
        "交付优化",
        "加速 Microsoft Edge 启动和后台运行",
        "OneDrive",
        "HAGS",
    ]:
        assert label in source

    assert "basic" in source
    assert "best" in source


def test_qt_bx_module_uses_toggle_card_layout_and_presets():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    # 开关卡片式 UI
    assert "class BXToggleSwitch(QAbstractButton)" in source
    assert "def _make_bx_card" in source
    assert "self.bx_item_states" in source
    assert "bxCard" in source

    # 默认/基本/最佳/最大 预设
    assert "def apply_bx_preset" in source
    for preset in ['"default"', '"basic"', '"best"', '"max"']:
        assert preset in source

    # 参考图新增项与警告行
    for label in ["鼠标加速", "系统启动时自动更新驱动程序", "全局通知", "UWP应用程序在后台运行"]:
        assert label in source
    for warning in ["禁用时将无法工作: 打印机", "禁用时将无法工作: 快速ALT+TAB"]:
        assert warning in source


def test_qt_bx_best_preset_is_superset_of_basic():
    """最佳预设应覆盖基本预设的全部项（best ⊇ basic）。"""
    import ast

    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    catalog_fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_bx_base_catalog"
    )
    list_node = next(
        stmt.value for stmt in catalog_fn.body if isinstance(stmt, ast.Return)
    )
    items = [ast.literal_eval(element) for element in list_node.elts]

    assert items, "_bx_base_catalog 不应为空"
    for item in items:
        if item.get("basic"):
            assert item.get("best"), f"基本项 {item['title']} 必须也属于最佳预设"


def test_qt_bx_module_runs_without_blocking_or_manual_confirmation():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    apply_logic = source.split("def apply_bx_optimization", 1)[1].split("def set_bx_busy", 1)[0]

    assert "class BXOptimizationThread(QThread)" in source
    assert "bx_progress_signal" in source
    assert "bx_item_finished_signal" in source
    assert "bx_finished_signal" in source
    assert "hidden_windows_subprocess_kwargs" in source
    assert "subprocess.run" in source
    assert "QMessageBox.question" not in apply_logic


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


def test_qt_has_system_repair_module_page():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")
    repair_source = Path("system_repair.py").read_text(encoding="utf-8")

    assert '("系统修复", "_build_repair_page")' in source
    assert "SystemRepairService" in source
    assert "SystemRepairThread" in source
    assert "CMD 系统修复工具箱" in source
    assert "推荐安全修复" in source
    assert "深度系统修复" in source
    assert "一键执行选中修复" in source
    assert "SFC 系统文件修复" in repair_source
    assert "DISM 系统镜像修复" in repair_source
    assert "repair_log_output" in source


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
    assert "run_optimizer_row_action_from_button" in source
    assert "QTimer.singleShot(650, self.refresh_optimizer_tab)" in source
    assert "kill_process_by_name" in source
    assert "process_name" in kill_process
    assert "taskkill" in kill_process
    assert "/F /T" in kill_process
    assert "wait(1.5)" in kill_process
