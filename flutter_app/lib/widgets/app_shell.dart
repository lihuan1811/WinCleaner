import 'package:flutter/material.dart';

import '../screens/dashboard_screen.dart';
import '../screens/uninstaller_screen.dart';
import '../services/installed_apps_service.dart';
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
      subtitle: '广告 hosts 屏蔽、磁盘分析和碎片整理集中处理。',
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
  ];

  @override
  Widget build(BuildContext context) {
    final selected = _items[_selectedIndex];
    final content = switch (_selectedIndex) {
      0 => const DashboardScreen(),
      1 => const SystemOptimizationScreen(),
      2 => UninstallerScreen(installedAppsService: widget.installedAppsService),
      3 => const FileManagementScreen(),
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
                      padding: const EdgeInsets.fromLTRB(18, 16, 18, 0),
                      child: Column(
                        children: [
                          _CommerceStyleHeader(
                            selectedIndex: _selectedIndex,
                            selected: selected,
                            items: _items,
                            onSelect: (index) =>
                                setState(() => _selectedIndex = index),
                            onAbout: _showAboutDialog,
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
          'WinCleaner 集成系统清理、系统优化、软件卸载和文件管理功能。'
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

class _CommerceStyleHeader extends StatelessWidget {
  const _CommerceStyleHeader({
    required this.selectedIndex,
    required this.selected,
    required this.items,
    required this.onSelect,
    required this.onAbout,
    required this.onSettings,
    required this.onSearch,
    required this.onAccount,
    required this.onNotifications,
  });

  final int selectedIndex;
  final _ShellItem selected;
  final List<_ShellItem> items;
  final ValueChanged<int> onSelect;
  final VoidCallback onAbout;
  final VoidCallback onSettings;
  final VoidCallback onSearch;
  final VoidCallback onAccount;
  final VoidCallback onNotifications;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      radius: 20,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      color: AppColors.glass,
      child: Row(
        children: [
          const _BrandMark(),
          const SizedBox(width: 18),
          Container(width: 1, height: 34, color: AppColors.hairline),
          const SizedBox(width: 14),
          for (var i = 0; i < items.length; i++) ...[
            _NavPill(
              item: items[i],
              selected: selectedIndex == i,
              onTap: () => onSelect(i),
            ),
            if (i != items.length - 1) const SizedBox(width: 6),
          ],
          const SizedBox(width: 18),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '当前模块: ${selected.label}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.text,
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  selected.subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: AppColors.muted, fontSize: 12),
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
          const SizedBox(width: 10),
          TextButton(onPressed: onAbout, child: const Text('关于我们')),
          const SizedBox(width: 10),
          Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(999),
            child: InkWell(
              borderRadius: BorderRadius.circular(999),
              onTap: onAccount,
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
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.primary, AppColors.primaryDark],
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Icon(Icons.cleaning_services, color: Colors.white),
        ),
        const SizedBox(width: 12),
        const Text(
          'WinCleaner',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w900,
            color: AppColors.text,
          ),
        ),
      ],
    );
  }
}

class _NavPill extends StatelessWidget {
  const _NavPill({
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
      color: selected ? AppColors.primary : Colors.transparent,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          height: 44,
          padding: const EdgeInsets.symmetric(horizontal: 13),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected ? const Color(0x66FFFFFF) : Colors.transparent,
            ),
          ),
          child: Row(
            children: [
              Icon(
                item.icon,
                size: 18,
                color: selected ? Colors.white : AppColors.muted,
              ),
              const SizedBox(width: 8),
              Text(
                item.label,
                style: TextStyle(
                  color: selected ? Colors.white : AppColors.text,
                  fontWeight: selected ? FontWeight.w900 : FontWeight.w700,
                ),
              ),
            ],
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
  });

  final IconData icon;
  final String label;
  final String title;
  final String subtitle;
}
