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
      body: LayoutBuilder(
        builder: (context, constraints) {
          final shellWidth =
              constraints.maxWidth < 1280 ? 1280.0 : constraints.maxWidth;
          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SizedBox(
              width: shellWidth,
              height: constraints.maxHeight,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(22, 20, 22, 0),
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
                    const SizedBox(height: 18),
                    Expanded(
                      child: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 220),
                        switchInCurve: Curves.easeOut,
                        switchOutCurve: Curves.easeIn,
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
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceTint,
        borderRadius: BorderRadius.circular(30),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 860,
                padding: const EdgeInsets.all(14),
                decoration: const BoxDecoration(
                  color: AppColors.warmSurface,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(30),
                    bottomRight: Radius.circular(30),
                  ),
                ),
                child: Row(
                  children: [
                    const _BrandMark(),
                    const SizedBox(width: 18),
                    for (var i = 0; i < items.length; i++) ...[
                      _NavPill(
                        item: items[i],
                        selected: selectedIndex == i,
                        onTap: () => onSelect(i),
                      ),
                      if (i != items.length - 1) const SizedBox(width: 4),
                    ],
                    const SizedBox(width: 8),
                    IconButton(
                      tooltip: '搜索',
                      onPressed: onSearch,
                      icon: const Icon(Icons.search),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              IconButton(
                tooltip: '通知',
                onPressed: onNotifications,
                icon: const Icon(Icons.notifications_none_outlined),
              ),
              const SizedBox(width: 8),
              IconButton(
                tooltip: '设置',
                onPressed: onSettings,
                icon: const Icon(Icons.settings_outlined),
              ),
              const SizedBox(width: 18),
              TextButton(
                onPressed: onAbout,
                child: const Text('关于我们'),
              ),
              const SizedBox(width: 18),
              Padding(
                padding: const EdgeInsets.only(right: 18),
                child: Material(
                  color: Colors.transparent,
                  borderRadius: BorderRadius.circular(999),
                  child: Ink(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(999),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x14000000),
                          blurRadius: 18,
                          offset: Offset(0, 8),
                        ),
                      ],
                    ),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(999),
                      onTap: onAccount,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Padding(
                            padding: EdgeInsets.only(left: 18),
                            child: Text(
                              'Administrator',
                              style: TextStyle(fontWeight: FontWeight.w800),
                            ),
                          ),
                          Container(
                            width: 42,
                            height: 42,
                            margin: const EdgeInsets.all(4),
                            decoration: const BoxDecoration(
                              color: AppColors.background,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(Icons.north_east, size: 20),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(34, 34, 34, 38),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const _GradientText('系统性能工作台'),
                      const SizedBox(height: 12),
                      Text(
                        selected.subtitle,
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontSize: 16,
                          height: 1.5,
                        ),
                      ),
                    ],
                  ),
                ),
                _HeroMetric(
                  icon: selected.icon,
                  label: '当前模块',
                  value: '功能已接入',
                ),
                const SizedBox(width: 16),
                const _HeroMetric(
                  icon: Icons.security_outlined,
                  label: '保护策略',
                  value: '确认后执行',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
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
          'WinCleaner_',
          style: TextStyle(
            fontSize: 21,
            fontWeight: FontWeight.w900,
            color: AppColors.primaryDark,
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
    return TextButton.icon(
      onPressed: onTap,
      icon: Icon(item.icon, size: 18),
      label: Text(item.label),
      style: TextButton.styleFrom(
        foregroundColor: selected ? Colors.white : AppColors.text,
        backgroundColor: selected ? AppColors.primary : Colors.transparent,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      ),
    );
  }
}

class _GradientText extends StatelessWidget {
  const _GradientText(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return ShaderMask(
      blendMode: BlendMode.srcIn,
      shaderCallback: (bounds) => const LinearGradient(
        colors: [AppColors.primaryDark, AppColors.primary],
      ).createShader(bounds),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 52,
          height: 1.05,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 210,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xC7FFFFFF),
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: const Color(0xCCFFFFFF)),
      ),
      child: Row(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: const BoxDecoration(
              color: AppColors.background,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: AppColors.primary),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: AppColors.muted, fontSize: 12),
                ),
                const SizedBox(height: 4),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
              ],
            ),
          ),
        ],
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
