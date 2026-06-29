import 'package:flutter/material.dart';

import '../screens/dashboard_screen.dart';
import '../screens/system_repair_screen.dart';
import '../screens/uninstaller_screen.dart';
import '../services/global_restore_service.dart';
import '../services/installed_apps_service.dart';
import '../services/local_account_service.dart';
import '../services/operation_log_service.dart';
import '../theme/app_theme.dart';

class AppShell extends StatefulWidget {
  const AppShell({
    super.key,
    this.installedAppsService = const InstalledAppsService(),
    this.accountService,
  });

  final InstalledAppsService installedAppsService;
  final LocalAccountService? accountService;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;
  late final LocalAccountService _accountService;
  LocalAccountState _accountState = LocalAccountState.empty();
  bool _loadingAccount = true;
  final GlobalRestoreService _globalRestoreService = GlobalRestoreService();
  final OperationLogService _operationLogService = OperationLogService();

  static const _items = [
    _ShellItem(
      icon: Icons.cleaning_services_outlined,
      label: 'C盘清理',
      title: 'C盘清理工作台',
      subtitle: '扫描并清理临时文件、缓存、日志和更新残留。',
    ),
    _ShellItem(
      icon: Icons.tune_outlined,
      label: '系统优化',
      title: '系统优化中心',
      subtitle: 'Windows 设置、广告屏蔽、右键菜单和计划任务集中处理。',
      requiresPremium: false,
    ),
    _ShellItem(
      icon: Icons.inventory_2_outlined,
      label: '软件卸载',
      title: '软件卸载中心',
      subtitle: '读取 Windows 卸载注册表，启动官方卸载程序或 BCU。',
      requiresPremium: false,
    ),
    _ShellItem(
      icon: Icons.folder_copy_outlined,
      label: '文件管理',
      title: '文件管理中心',
      subtitle: '查找重复文件和超大文件，辅助释放磁盘空间。',
      requiresPremium: false,
    ),
    _ShellItem(
      icon: Icons.health_and_safety_outlined,
      label: '系统修复',
      title: 'CMD 系统修复工具箱',
      subtitle: 'SFC、DISM、CHKDSK、网络和更新组件修复。',
      requiresPremium: false,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _accountService = widget.accountService ?? LocalAccountService();
    _loadAccountState();
  }

  Future<void> _loadAccountState() async {
    final state = await _accountService.loadState();
    if (!mounted) {
      return;
    }
    setState(() {
      _accountState = state;
      _loadingAccount = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final selected = _items[_selectedIndex];
    final content = switch (_selectedIndex) {
      0 => const DashboardScreen(),
      1 => const SystemOptimizationScreen(),
      2 => UninstallerScreen(installedAppsService: widget.installedAppsService),
      3 => const FileManagementScreen(),
      4 => const SystemRepairScreen(),
      _ => const DashboardScreen(),
    };

    return Scaffold(
      body: ColoredBox(
        color: AppColors.background,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final shellWidth =
                constraints.maxWidth < 1280 ? 1280.0 : constraints.maxWidth;
            return SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SizedBox(
                width: shellWidth,
                height: constraints.maxHeight,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
                  child: Row(
                    children: [
                      _DesktopSidebar(
                        selectedIndex: _selectedIndex,
                        items: _items,
                        hasPremium: _accountState.isPremium,
                        onSelect: _selectNavigationIndex,
                        onPremiumRequired: _showPremiumRequiredDialog,
                        onAbout: _showAboutDialog,
                        onStats: _showStatsDialog,
                        onRestore: _showGlobalRestoreDialog,
                        onLogs: _showOperationLogDialog,
                      ),
                      const SizedBox(width: 18),
                      Expanded(
                        child: Column(
                          children: [
                            _DesktopHeader(
                              selected: selected,
                              accountState: _accountState,
                              loadingAccount: _loadingAccount,
                              onSettings: _showSettingsDialog,
                              onSearch: _showSearchDialog,
                              onAccount: _showAccountDialog,
                              onNotifications: _showNotifications,
                            ),
                            const SizedBox(height: 14),
                            Expanded(
                              child: AnimatedSwitcher(
                                duration: const Duration(milliseconds: 180),
                                switchInCurve: Curves.easeOutCubic,
                                switchOutCurve: Curves.easeInCubic,
                                layoutBuilder:
                                    (currentChild, previousChildren) {
                                  return Stack(
                                    fit: StackFit.expand,
                                    alignment: Alignment.topLeft,
                                    children: [
                                      for (final child in previousChildren)
                                        Positioned.fill(child: child),
                                      if (currentChild != null)
                                        Positioned.fill(child: currentChild),
                                    ],
                                  );
                                },
                                transitionBuilder: (child, animation) {
                                  final curved = CurvedAnimation(
                                    parent: animation,
                                    curve: Curves.easeOutCubic,
                                  );
                                  return FadeTransition(
                                    opacity: curved,
                                    child: SlideTransition(
                                      position: Tween<Offset>(
                                        begin: const Offset(0, .018),
                                        end: Offset.zero,
                                      ).animate(curved),
                                      child: child,
                                    ),
                                  );
                                },
                                child: KeyedSubtree(
                                  key: ValueKey(selected.label),
                                  child: content,
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            _BottomCommandBar(
                              onStats: _showStatsDialog,
                              onRestore: _showGlobalRestoreDialog,
                              onLogs: _showOperationLogDialog,
                              onAbout: _showAboutDialog,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  void _selectNavigationIndex(int index) {
    final item = _items[index];
    if (item.requiresPremium && !_accountState.isPremium) {
      _showPremiumRequiredDialog(item.label);
      return;
    }
    setState(() => _selectedIndex = index);
  }

  Future<void> _showPremiumRequiredDialog(String featureName) {
    return showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('需要会员'),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _DialogLine(
                icon: Icons.lock_outline,
                text: '$featureName 属于会员功能。',
              ),
              const SizedBox(height: 12),
              const _DialogLine(
                icon: Icons.card_membership_outlined,
                text: '请先登录并兑换会员卡，开通后可使用系统优化、软件卸载、文件管理和系统修复。',
              ),
              const SizedBox(height: 12),
              const _DialogLine(
                icon: Icons.shield_outlined,
                text: '当前版本为本地演示授权，后续可替换为服务器校验。',
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('稍后'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              _showAccountDialog(initialMessage: '开通会员后即可使用 $featureName。');
            },
            child: const Text('去开通'),
          ),
        ],
      ),
    );
  }

  void _showNotifications() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('暂无新的系统通知')),
    );
  }

  Future<void> _showSettingsDialog() {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('设置'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _DialogLine(
                icon: Icons.verified_user_outlined, text: '危险操作前保持二次确认'),
            SizedBox(height: 12),
            _DialogLine(
                icon: Icons.admin_panel_settings_outlined,
                text: '建议以管理员身份运行以获得完整权限'),
            SizedBox(height: 12),
            _DialogLine(
                icon: Icons.folder_copy_outlined, text: '下载目录默认只扫描不自动清理'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  Future<void> _showStatsDialog() {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('本次操作数据统计'),
        content: const SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _DialogLine(
                  icon: Icons.cleaning_services_outlined, text: '清理任务：等待扫描'),
              SizedBox(height: 12),
              _DialogLine(icon: Icons.tune_outlined, text: '优化任务：按需执行，支持单项回退'),
              SizedBox(height: 12),
              _DialogLine(
                  icon: Icons.restore_outlined, text: '迁移/注册表类操作：保留确认与还原入口'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  Future<void> _showGlobalRestoreDialog() {
    return showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('全局一键还原所有修改'),
        content: const Text(
          '将尝试恢复 hosts 广告屏蔽、所有带恢复命令的 Windows 优化项，'
          '并按 AppData 迁移历史执行还原。该操作会真实调用系统命令。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('关闭'),
          ),
          FilledButton(
            onPressed: () async {
              Navigator.of(dialogContext).pop();
              await _runGlobalRestore();
            },
            child: const Text('执行全局还原'),
          ),
        ],
      ),
    );
  }

  Future<void> _runGlobalRestore() async {
    final result = await _globalRestoreService.restoreAll();
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(result.success ? '全局还原完成' : '全局还原完成但存在失败项'),
        content: SizedBox(
          width: 640,
          child: SingleChildScrollView(child: SelectableText(result.output)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  Future<void> _showOperationLogDialog() async {
    final entries = await _operationLogService.read(limit: 50);
    if (!mounted) {
      return;
    }
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('查看全部操作日志'),
        content: SizedBox(
          width: 460,
          child: entries.isEmpty
              ? const Text('暂无操作日志', style: TextStyle(color: AppColors.muted))
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (final entry in entries)
                      ListTile(
                        leading: const Icon(Icons.receipt_long_outlined),
                        title: Text('${entry.module} · ${entry.action}'),
                        subtitle: Text(
                          '${entry.timestamp}\n${entry.detail}',
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  Future<void> _showSearchDialog() {
    return showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('搜索工具'),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (var i = 0; i < _items.length; i++)
                ListTile(
                  leading: Icon(_items[i].icon, color: AppColors.primary),
                  title: Text(_items[i].title),
                  subtitle: Text(_items[i].label),
                  trailing: const Icon(Icons.north_east),
                  onTap: () {
                    Navigator.of(dialogContext).pop();
                    _selectNavigationIndex(i);
                  },
                ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  Future<void> _showAccountDialog({String? initialMessage}) async {
    final state = await showDialog<LocalAccountState>(
      context: context,
      builder: (context) => _AccountMembershipDialog(
        service: _accountService,
        initialState: _accountState,
        initialMessage: initialMessage,
      ),
    );
    if (state != null && mounted) {
      setState(() => _accountState = state);
    }
  }

  Future<void> _showAboutDialog() {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('关于 WinCleaner'),
        content: const Text(
          'WinCleaner 集成系统清理、系统优化、软件卸载、文件管理和系统修复功能。'
          '所有会修改系统或删除文件的操作都会保留确认步骤。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }
}

class _DesktopSidebar extends StatelessWidget {
  const _DesktopSidebar({
    required this.selectedIndex,
    required this.items,
    required this.hasPremium,
    required this.onSelect,
    required this.onPremiumRequired,
    required this.onAbout,
    required this.onStats,
    required this.onRestore,
    required this.onLogs,
  });

  final int selectedIndex;
  final List<_ShellItem> items;
  final bool hasPremium;
  final ValueChanged<int> onSelect;
  final ValueChanged<String> onPremiumRequired;
  final VoidCallback onAbout;
  final VoidCallback onStats;
  final VoidCallback onRestore;
  final VoidCallback onLogs;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      width: 286,
      height: double.infinity,
      radius: 16,
      padding: const EdgeInsets.all(16),
      color: AppColors.sidebar,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BrandMark(),
          const SizedBox(height: 24),
          const Text(
            '功能导航',
            style: TextStyle(
              color: AppColors.muted,
              fontSize: 12,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          for (var index = 0; index < items.length; index++) ...[
            _SidebarNavButton(
              item: items[index],
              selected: selectedIndex == index,
              locked: items[index].requiresPremium && !hasPremium,
              onTap: () {
                if (items[index].requiresPremium && !hasPremium) {
                  onPremiumRequired(items[index].label);
                  return;
                }
                onSelect(index);
              },
            ),
            const SizedBox(height: 8),
          ],
          const Spacer(),
          const Divider(color: AppColors.hairline),
          const SizedBox(height: 10),
          _QuickActionTile(
            icon: Icons.insights_outlined,
            title: '本次操作数据统计',
            onTap: onStats,
          ),
          _QuickActionTile(
            icon: Icons.restore_outlined,
            title: '全局一键还原所有修改',
            onTap: onRestore,
          ),
          _QuickActionTile(
            icon: Icons.receipt_long_outlined,
            title: '查看全部操作日志',
            onTap: onLogs,
          ),
          const SizedBox(height: 10),
          TextButton.icon(
            onPressed: onAbout,
            icon: const Icon(Icons.info_outline),
            label: const Text('关于我们'),
          ),
        ],
      ),
    );
  }
}

class _DesktopHeader extends StatelessWidget {
  const _DesktopHeader({
    required this.selected,
    required this.accountState,
    required this.loadingAccount,
    required this.onSettings,
    required this.onSearch,
    required this.onAccount,
    required this.onNotifications,
  });

  final _ShellItem selected;
  final LocalAccountState accountState;
  final bool loadingAccount;
  final VoidCallback onSettings;
  final VoidCallback onSearch;
  final VoidCallback onAccount;
  final VoidCallback onNotifications;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      radius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      color: AppColors.glass,
      child: Row(
        children: [
          FeatureIcon(
            icon: selected.icon,
            size: 48,
            iconSize: 23,
            selected: true,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '当前模块：${selected.label}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 3),
                Text(
                  selected.subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: AppColors.muted, fontSize: 13),
                ),
              ],
            ),
          ),
          _HeaderIconButton(
            tooltip: '搜索',
            onPressed: onSearch,
            icon: Icons.search,
          ),
          const SizedBox(width: 8),
          _HeaderIconButton(
            tooltip: '通知',
            onPressed: onNotifications,
            icon: Icons.notifications_none_outlined,
          ),
          const SizedBox(width: 8),
          _HeaderIconButton(
            tooltip: '设置',
            onPressed: onSettings,
            icon: Icons.settings_outlined,
          ),
          const SizedBox(width: 12),
          _UserChip(
            state: accountState,
            loading: loadingAccount,
            onTap: onAccount,
          ),
        ],
      ),
    );
  }
}

class _HeaderIconButton extends StatelessWidget {
  const _HeaderIconButton({
    required this.tooltip,
    required this.onPressed,
    required this.icon,
  });

  final String tooltip;
  final VoidCallback onPressed;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      tooltip: tooltip,
      onPressed: onPressed,
      style: IconButton.styleFrom(
        backgroundColor: AppColors.glassStrong,
        foregroundColor: AppColors.text,
        minimumSize: const Size(44, 44),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
      icon: Icon(icon, size: 20),
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        FeatureIcon(
          icon: Icons.cleaning_services,
          size: 48,
          iconSize: 22,
          selected: true,
        ),
        SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'WinCleaner',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 21,
                  fontWeight: FontWeight.w900,
                  color: AppColors.text,
                ),
              ),
              SizedBox(height: 2),
              Text(
                'Windows 系统清理管家',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SidebarNavButton extends StatelessWidget {
  const _SidebarNavButton({
    required this.item,
    required this.selected,
    required this.locked,
    required this.onTap,
  });

  final _ShellItem item;
  final bool selected;
  final bool locked;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: locked ? '${item.label}，会员功能' : item.label,
      hint: locked ? '打开会员开通提示' : '打开${item.title}',
      child: Material(
        color: selected ? AppColors.primaryDark : Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            curve: Curves.easeOutCubic,
            height: 58,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: selected
                  ? null
                  : locked
                      ? AppColors.glassMuted.withValues(alpha: .62)
                      : AppColors.glassMuted,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: selected ? const Color(0x66FFFFFF) : AppColors.border,
              ),
            ),
            child: Row(
              children: [
                FeatureIcon(
                  icon: locked ? Icons.lock_outline : item.icon,
                  size: 34,
                  iconSize: 17,
                  primary: selected ? AppColors.primaryDark : AppColors.primary,
                  selected: selected,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: selected ? Colors.white : AppColors.text,
                          fontWeight:
                              selected ? FontWeight.w900 : FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        item.subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: selected
                              ? const Color(0xFFEAF2FF)
                              : AppColors.muted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                if (locked) ...[
                  const SizedBox(width: 8),
                  const Icon(
                    Icons.workspace_premium_outlined,
                    color: AppColors.primary,
                    size: 18,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _QuickActionTile extends StatelessWidget {
  const _QuickActionTile({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Semantics(
        button: true,
        label: title,
        child: Material(
          color: AppColors.glassMuted,
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: onTap,
            child: Container(
              height: 44,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.border),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(icon, color: AppColors.primary, size: 19),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.text,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _UserChip extends StatelessWidget {
  const _UserChip({
    required this.state,
    required this.loading,
    required this.onTap,
  });

  final LocalAccountState state;
  final bool loading;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final title = loading ? '加载中' : state.displayName;
    final badge = loading
        ? 'Account'
        : state.isPremium
            ? state.planLabel
            : state.isSignedIn
                ? 'Free'
                : '登录/注册';
    final icon = state.isPremium
        ? Icons.workspace_premium_outlined
        : state.isSignedIn
            ? Icons.person_outline
            : Icons.login_outlined;
    return Semantics(
      button: true,
      label: '账户与会员，$title，$badge',
      hint: '打开账户与会员设置',
      child: Tooltip(
        message: '账户与会员设置',
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(999),
          child: InkWell(
            borderRadius: BorderRadius.circular(999),
            onTap: onTap,
            child: Container(
              height: 44,
              padding: const EdgeInsets.only(left: 14, right: 4),
              decoration: BoxDecoration(
                color: AppColors.glassStrong,
                border: Border.all(color: AppColors.border),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 150),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.text,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          badge,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: state.isPremium
                                ? AppColors.primary
                                : AppColors.muted,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  CircleAvatar(
                    radius: 18,
                    backgroundColor: AppColors.paleBlue,
                    child: ExcludeSemantics(child: Icon(icon, size: 18)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _AccountMembershipDialog extends StatefulWidget {
  const _AccountMembershipDialog({
    required this.service,
    required this.initialState,
    this.initialMessage,
  });

  final LocalAccountService service;
  final LocalAccountState initialState;
  final String? initialMessage;

  @override
  State<_AccountMembershipDialog> createState() =>
      _AccountMembershipDialogState();
}

class _AccountMembershipDialogState extends State<_AccountMembershipDialog> {
  late LocalAccountState _state;
  late String? _message;
  bool _registerMode = false;
  bool _busy = false;
  String? _error;

  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _cardController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _state = widget.initialState;
    _message = widget.initialMessage;
    if (_state.isSignedIn) {
      _emailController.text = _state.email;
      _nameController.text = _state.displayName;
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _cardController.dispose();
    super.dispose();
  }

  Future<void> _submitAuth() async {
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final next = _registerMode
          ? await widget.service.register(
              email: _emailController.text,
              password: _passwordController.text,
              displayName: _nameController.text,
            )
          : await widget.service.login(
              email: _emailController.text,
              password: _passwordController.text,
            );
      if (!mounted) {
        return;
      }
      setState(() {
        _state = next;
        _message = _registerMode ? '注册并登录成功。' : '登录成功。';
        _passwordController.clear();
      });
    } on AccountException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
      }
    } catch (error) {
      if (mounted) {
        setState(() => _error = '操作失败：$error');
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _redeemCard() async {
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final result = await widget.service.redeemCard(_cardController.text);
      if (!mounted) {
        return;
      }
      setState(() {
        _state = result.state;
        _message = result.message;
        _cardController.clear();
      });
    } on AccountException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
      }
    } catch (error) {
      if (mounted) {
        setState(() => _error = '兑换失败：$error');
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _logout() async {
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final next = await widget.service.logout();
      if (!mounted) {
        return;
      }
      setState(() {
        _state = next;
        _message = '已退出登录。';
        _passwordController.clear();
      });
    } catch (error) {
      if (mounted) {
        setState(() => _error = '退出失败：$error');
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: [
          const FeatureIcon(
            icon: Icons.workspace_premium_outlined,
            size: 42,
            iconSize: 20,
            selected: true,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              '账户与会员',
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: 620,
        child: AnimatedSize(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StatusMessage(error: _error, message: _message),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 180),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  final curved = CurvedAnimation(
                    parent: animation,
                    curve: Curves.easeOutCubic,
                  );
                  return FadeTransition(
                    opacity: curved,
                    child: SlideTransition(
                      position: Tween<Offset>(
                        begin: const Offset(0, .03),
                        end: Offset.zero,
                      ).animate(curved),
                      child: child,
                    ),
                  );
                },
                child: _state.isSignedIn
                    ? _buildMemberPanel(key: const ValueKey('member'))
                    : _buildAuthPanel(key: const ValueKey('auth')),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(_state),
          child: const Text('关闭'),
        ),
      ],
    );
  }

  Widget _buildAuthPanel({required Key key}) {
    return Column(
      key: key,
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SegmentedButton<bool>(
          showSelectedIcon: false,
          segments: const [
            ButtonSegment(value: false, label: Text('登录')),
            ButtonSegment(value: true, label: Text('注册')),
          ],
          selected: {_registerMode},
          onSelectionChanged: _busy
              ? null
              : (values) {
                  setState(() {
                    _registerMode = values.first;
                    _error = null;
                    _message = null;
                  });
                },
        ),
        const SizedBox(height: 16),
        if (_registerMode) ...[
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: '用户名',
              prefixIcon: Icon(Icons.badge_outlined),
            ),
          ),
          const SizedBox(height: 12),
        ],
        TextField(
          controller: _emailController,
          decoration: const InputDecoration(
            labelText: '邮箱',
            prefixIcon: Icon(Icons.mail_outline),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _passwordController,
          obscureText: true,
          decoration: const InputDecoration(
            labelText: '密码',
            prefixIcon: Icon(Icons.lock_outline),
            helperText: '至少 6 位，本地演示版会保存加密摘要。',
          ),
          onSubmitted: (_) => _busy ? null : _submitAuth(),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: Text(
                _registerMode ? '注册后可继续兑换会员卡。' : '已注册用户可直接登录，未注册请切换到注册。',
                style: const TextStyle(color: AppColors.muted, fontSize: 13),
              ),
            ),
            FilledButton.icon(
              onPressed: _busy ? null : _submitAuth,
              icon: _busy
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(_registerMode
                      ? Icons.person_add_alt_1_outlined
                      : Icons.login_outlined),
              label: Text(_registerMode ? '注册' : '登录'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMemberPanel({required Key key}) {
    final expiresAt = _state.expiresAt;
    return Column(
      key: key,
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GlassPanel(
          padding: const EdgeInsets.all(16),
          radius: 14,
          shadow: false,
          color: AppColors.glassMuted,
          child: Row(
            children: [
              FeatureIcon(
                icon: _state.isPremium
                    ? Icons.verified_outlined
                    : Icons.person_outline,
                size: 46,
                iconSize: 22,
                selected: _state.isPremium,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '当前会员状态',
                      style: TextStyle(
                        color: AppColors.text,
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _state.isPremium
                          ? '${_state.planLabel} · 剩余 ${_state.remainingDays} 天'
                          : '免费用户 · 会员模块暂未解锁',
                      style: TextStyle(
                        color: _state.isPremium
                            ? AppColors.primary
                            : AppColors.muted,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_state.email} · 设备码 ${_state.deviceId}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style:
                          const TextStyle(color: AppColors.muted, fontSize: 12),
                    ),
                  ],
                ),
              ),
              Text(
                expiresAt == null ? '未开通' : _formatDate(expiresAt),
                style: const TextStyle(
                  color: AppColors.text,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _cardController,
          textCapitalization: TextCapitalization.characters,
          decoration: const InputDecoration(
            labelText: '输入会员卡密',
            prefixIcon: Icon(Icons.card_membership_outlined),
            helperText: '本地演示卡密，后续可替换为服务端兑换接口。',
          ),
          onSubmitted: (_) => _busy ? null : _redeemCard(),
        ),
        const SizedBox(height: 10),
        SelectableText(
          '可测试卡密：${LocalAccountService.demoCardCodes.join(' / ')}',
          style: const TextStyle(color: AppColors.muted, fontSize: 12),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            OutlinedButton.icon(
              onPressed: _busy ? null : _logout,
              icon: const Icon(Icons.logout_outlined),
              label: const Text('退出登录'),
            ),
            const Spacer(),
            FilledButton.icon(
              onPressed: _busy ? null : _redeemCard,
              icon: _busy
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.redeem_outlined),
              label: const Text('兑换会员卡'),
            ),
          ],
        ),
      ],
    );
  }

  static String _formatDate(DateTime value) {
    final local = value.toLocal();
    final month = local.month.toString().padLeft(2, '0');
    final day = local.day.toString().padLeft(2, '0');
    return '${local.year}-$month-$day';
  }
}

class _StatusMessage extends StatelessWidget {
  const _StatusMessage({required this.error, required this.message});

  final String? error;
  final String? message;

  @override
  Widget build(BuildContext context) {
    final text = error ?? message;
    if (text == null) {
      return const SizedBox.shrink();
    }
    final isError = error != null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Semantics(
        liveRegion: true,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: isError
                ? AppColors.danger.withValues(alpha: .08)
                : AppColors.success.withValues(alpha: .08),
            border: Border.all(
              color: isError
                  ? AppColors.danger.withValues(alpha: .25)
                  : AppColors.success.withValues(alpha: .25),
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Icon(
                isError ? Icons.error_outline : Icons.check_circle_outline,
                color: isError ? AppColors.danger : AppColors.success,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  text,
                  style: TextStyle(
                    color: isError ? AppColors.danger : AppColors.success,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BottomCommandBar extends StatelessWidget {
  const _BottomCommandBar({
    required this.onStats,
    required this.onRestore,
    required this.onLogs,
    required this.onAbout,
  });

  final VoidCallback onStats;
  final VoidCallback onRestore;
  final VoidCallback onLogs;
  final VoidCallback onAbout;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      radius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      shadow: false,
      child: Row(
        children: [
          _BottomAction(
            icon: Icons.insights_outlined,
            label: '本次操作数据统计',
            onTap: onStats,
          ),
          _BottomAction(
            icon: Icons.restore_outlined,
            label: '全局一键还原所有修改',
            onTap: onRestore,
          ),
          _BottomAction(
            icon: Icons.receipt_long_outlined,
            label: '查看全部操作日志',
            onTap: onLogs,
          ),
          _BottomAction(
            icon: Icons.info_outline,
            label: '关于软件',
            onTap: onAbout,
          ),
        ],
      ),
    );
  }
}

class _BottomAction extends StatelessWidget {
  const _BottomAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Semantics(
        button: true,
        label: label,
        child: TextButton.icon(
          onPressed: onTap,
          icon: Icon(icon, size: 18),
          label: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ),
    );
  }
}

class _DialogLine extends StatelessWidget {
  const _DialogLine({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: AppColors.primary),
        const SizedBox(width: 10),
        Expanded(child: Text(text)),
      ],
    );
  }
}

class _ShellItem {
  const _ShellItem({
    required this.icon,
    required this.label,
    required this.title,
    required this.subtitle,
    this.requiresPremium = false,
  });

  final IconData icon;
  final String label;
  final String title;
  final String subtitle;
  final bool requiresPremium;
}
