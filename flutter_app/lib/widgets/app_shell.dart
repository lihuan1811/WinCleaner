import 'package:flutter/material.dart';

import '../screens/dashboard_screen.dart';
import '../screens/system_repair_screen.dart';
import '../screens/uninstaller_screen.dart';
import '../services/global_restore_service.dart';
import '../services/installed_apps_service.dart';
import '../services/operation_log_service.dart';
import '../theme/app_theme.dart';

class AppShell extends StatefulWidget {
  const AppShell({
    super.key,
    this.installedAppsService = const InstalledAppsService(),
  });

  final InstalledAppsService installedAppsService;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;
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
      icon: Icons.speed_outlined,
      label: '系统优化',
      title: '系统优化中心',
      subtitle: 'Windows 设置、广告屏蔽、右键菜单和计划任务集中处理。',
    ),
    _ShellItem(
      icon: Icons.delete_outline,
      label: '软件卸载',
      title: '软件卸载中心',
      subtitle: '读取 Windows 卸载注册表，启动官方卸载程序或 BCU。',
    ),
    _ShellItem(
      icon: Icons.folder_outlined,
      label: '文件管理',
      title: '文件管理中心',
      subtitle: '查找重复文件和超大文件，辅助释放磁盘空间。',
    ),
    _ShellItem(
      icon: Icons.construction_outlined,
      label: '系统修复',
      title: 'CMD 系统修复工具箱',
      subtitle: 'SFC、DISM、CHKDSK、网络和更新组件修复。',
    ),
  ];

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
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFF8FBFF),
              AppColors.background,
              AppColors.backgroundDeep,
            ],
          ),
        ),
        child: Stack(
          children: [
            const Positioned.fill(child: CustomPaint(painter: _DesktopGrid())),
            LayoutBuilder(
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
                            onSelect: (index) =>
                                setState(() => _selectedIndex = index),
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
                                  onSettings: _showSettingsDialog,
                                  onSearch: _showSearchDialog,
                                  onAccount: _showAccountDialog,
                                  onNotifications: _showNotifications,
                                ),
                                const SizedBox(height: 14),
                                Expanded(
                                  child: AnimatedSwitcher(
                                    duration: const Duration(milliseconds: 220),
                                    switchInCurve: Curves.easeOutCubic,
                                    switchOutCurve: Curves.easeInCubic,
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
          ],
        ),
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
                    setState(() => _selectedIndex = i);
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

  Future<void> _showAccountDialog() {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('账户'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _DialogLine(icon: Icons.person_outline, text: 'Administrator'),
            SizedBox(height: 12),
            _DialogLine(icon: Icons.security_outlined, text: '高级授权用户'),
            SizedBox(height: 12),
            _DialogLine(icon: Icons.window_outlined, text: 'Windows 清理工具模式'),
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
    required this.onSelect,
    required this.onAbout,
    required this.onStats,
    required this.onRestore,
    required this.onLogs,
  });

  final int selectedIndex;
  final List<_ShellItem> items;
  final ValueChanged<int> onSelect;
  final VoidCallback onAbout;
  final VoidCallback onStats;
  final VoidCallback onRestore;
  final VoidCallback onLogs;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      width: 286,
      height: double.infinity,
      radius: 24,
      padding: const EdgeInsets.all(18),
      color: AppColors.sidebar,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BrandMark(),
          const SizedBox(height: 28),
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
              onTap: () => onSelect(index),
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
    required this.onSettings,
    required this.onSearch,
    required this.onAccount,
    required this.onNotifications,
  });

  final _ShellItem selected;
  final VoidCallback onSettings;
  final VoidCallback onSearch;
  final VoidCallback onAccount;
  final VoidCallback onNotifications;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      radius: 20,
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
          _UserChip(onTap: onAccount),
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

class _DesktopGrid extends CustomPainter {
  const _DesktopGrid();

  @override
  void paint(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = const Color(0x21AFC1D4)
      ..strokeWidth = 1;
    const step = 48.0;
    for (var x = 0.0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), linePaint);
    }
    for (var y = 0.0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);
    }

    final washPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0xB8FFFFFF), Color(0x00FFFFFF)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height * .45));
    canvas.drawRect(
        Rect.fromLTWH(0, 0, size.width, size.height * .45), washPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
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
    required this.onTap,
  });

  final _ShellItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? AppColors.primaryDark : Colors.transparent,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          height: 58,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: selected ? null : AppColors.glassMuted,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: selected ? const Color(0x66FFFFFF) : AppColors.border,
            ),
          ),
          child: Row(
            children: [
              FeatureIcon(
                icon: item.icon,
                size: 34,
                iconSize: 17,
                primary: selected ? AppColors.primaryDark : AppColors.primary,
                secondary: selected ? AppColors.primary : AppColors.accent,
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
                            ? const Color(0xDDEAF2FF)
                            : AppColors.muted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
            ],
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
      child: Material(
        color: AppColors.glassMuted,
        borderRadius: BorderRadius.circular(13),
        child: InkWell(
          borderRadius: BorderRadius.circular(13),
          onTap: onTap,
          child: Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(13),
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
    );
  }
}

class _UserChip extends StatelessWidget {
  const _UserChip({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
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
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Administrator',
                style: TextStyle(
                  color: AppColors.text,
                  fontWeight: FontWeight.w800,
                ),
              ),
              SizedBox(width: 10),
              CircleAvatar(
                radius: 18,
                backgroundColor: AppColors.paleBlue,
                child: Icon(Icons.person_outline, size: 18),
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
      child: TextButton.icon(
        onPressed: onTap,
        icon: Icon(icon, size: 18),
        label: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
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
  });

  final IconData icon;
  final String label;
  final String title;
  final String subtitle;
}
