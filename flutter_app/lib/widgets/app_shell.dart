import 'package:flutter/material.dart';

import '../screens/dashboard_screen.dart';
import '../screens/uninstaller_screen.dart';
import '../theme/app_theme.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;

  static const _items = [
    _NavItem(icon: Icons.cleaning_services_outlined, label: 'C盘清理'),
    _NavItem(icon: Icons.speed_outlined, label: '系统优化'),
    _NavItem(icon: Icons.delete_outline, label: '软件卸载'),
    _NavItem(icon: Icons.folder_outlined, label: '文件管理'),
  ];

  @override
  Widget build(BuildContext context) {
    final content = switch (_selectedIndex) {
      2 => const UninstallerScreen(),
      _ => const DashboardScreen(),
    };

    return Scaffold(
      body: Row(
        children: [
          _Sidebar(
            selectedIndex: _selectedIndex,
            onSelect: (index) => setState(() => _selectedIndex = index),
          ),
          Expanded(
            child: Column(
              children: [
                _TopBar(title: _selectedIndex == 2 ? '软件卸载中心' : '系统清理大师'),
                Expanded(child: content),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.selectedIndex, required this.onSelect});

  final int selectedIndex;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 260,
      color: AppColors.sidebar,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 22, 16, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _Brand(),
            const SizedBox(height: 48),
            for (var i = 0; i < _AppShellState._items.length; i++)
              _NavButton(
                item: _AppShellState._items[i],
                selected: selectedIndex == i,
                onTap: () => onSelect(i),
              ),
            const Spacer(),
            const Divider(color: AppColors.border),
            const SizedBox(height: 16),
            const Row(
              children: [
                Icon(Icons.info_outline, color: Color(0xFF475569)),
                SizedBox(width: 14),
                Text(
                  '关于我们',
                  style: TextStyle(color: Color(0xFF475569), fontSize: 14),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Brand extends StatelessWidget {
  const _Brand();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Icon(Icons.cleaning_services, color: Colors.white),
        ),
        const SizedBox(width: 14),
        const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'WinCleaner',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w900,
                color: AppColors.primaryDark,
              ),
            ),
            SizedBox(height: 3),
            Text(
              '系统清理与卸载管家',
              style: TextStyle(fontSize: 12, color: AppColors.muted),
            ),
          ],
        ),
      ],
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final _NavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Material(
        color: selected ? AppColors.primary : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onTap,
          child: SizedBox(
            height: 58,
            child: Row(
              children: [
                const SizedBox(width: 22),
                Icon(
                  item.icon,
                  color: selected ? Colors.white : const Color(0xFF475569),
                ),
                const SizedBox(width: 18),
                Text(
                  item.label,
                  style: TextStyle(
                    color: selected ? Colors.white : const Color(0xFF475569),
                    fontWeight: FontWeight.w600,
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

class _TopBar extends StatelessWidget {
  const _TopBar({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 80,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          Text(title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(width: 24),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: BoxDecoration(
              color: const Color(0xFFD8E7FF),
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Text(
              'PREVIEW',
              style: TextStyle(
                color: AppColors.primaryDark,
                fontWeight: FontWeight.w800,
                fontSize: 12,
              ),
            ),
          ),
          const Spacer(),
          const Icon(Icons.notifications_none, color: AppColors.text),
          const SizedBox(width: 28),
          const Icon(Icons.settings_outlined, color: AppColors.text),
          const SizedBox(width: 28),
          const VerticalDivider(color: AppColors.border),
          const SizedBox(width: 18),
          const Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                'Administrator',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  color: AppColors.text,
                ),
              ),
              SizedBox(height: 3),
              Text(
                '高级授权用户',
                style: TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(width: 14),
          const CircleAvatar(
            radius: 22,
            backgroundColor: AppColors.paleBlue,
            child: Icon(Icons.person, color: AppColors.primary),
          ),
        ],
      ),
    );
  }
}

class _NavItem {
  const _NavItem({required this.icon, required this.label});

  final IconData icon;
  final String label;
}
