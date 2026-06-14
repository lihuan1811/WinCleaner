import 'package:flutter/material.dart';

import '../models/installed_app.dart';
import '../services/bcu_service.dart';
import '../services/installed_apps_service.dart';
import '../services/uninstall_service.dart';
import '../theme/app_theme.dart';

class UninstallerScreen extends StatefulWidget {
  const UninstallerScreen({
    super.key,
    this.bcuService,
    this.installedAppsService = const InstalledAppsService(),
    this.uninstallService,
  });

  final BcuService? bcuService;
  final InstalledAppsService installedAppsService;
  final UninstallService? uninstallService;

  @override
  State<UninstallerScreen> createState() => _UninstallerScreenState();
}

class _UninstallerScreenState extends State<UninstallerScreen> {
  late final BcuService _bcuService;
  late final UninstallService _uninstallService;
  late List<InstalledApp> _apps;
  String _query = '';
  bool _isLoading = true;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _bcuService = widget.bcuService ?? BcuService();
    _uninstallService = widget.uninstallService ?? UninstallService();
    _apps = const [];
    _loadInstalledApps();
  }

  @override
  Widget build(BuildContext context) {
    final selectedApps = _apps.where((app) => app.isSelected).toList();
    final selectedCount = selectedApps.length;
    final status = _bcuService.locate();
    final filteredApps = _apps.where((app) {
      final query = _query.trim().toLowerCase();
      if (query.isEmpty) {
        return true;
      }
      return app.name.toLowerCase().contains(query) ||
          app.publisher.toLowerCase().contains(query);
    }).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: _SummaryCard(
                  title: '已安装软件',
                  value: _isLoading ? '...' : '${_apps.length}',
                  subtitle: '来自 Windows 卸载注册表',
                ),
              ),
              const SizedBox(width: 24),
              const Expanded(
                child: _SummaryCard(
                  title: '建议复查',
                  value: '1',
                  subtitle: '未知发布者或旧版本',
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: _BcuStatusCard(status: status, onLaunch: _launchBcu),
              ),
            ],
          ),
          const SizedBox(height: 30),
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('软件卸载', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 4),
                  const Text(
                    '通过 BCUninstaller 后端执行卸载，危险操作需二次确认',
                    style: TextStyle(color: AppColors.muted),
                  ),
                ],
              ),
              const Spacer(),
              SizedBox(
                width: 310,
                child: TextField(
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.search),
                    hintText: '搜索软件或发布者',
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: AppColors.border),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: AppColors.border),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Row(
                    children: [
                      Text(
                        '软件列表',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 5,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.paleBlue,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '$selectedCount 已选择',
                          style: const TextStyle(
                            color: AppColors.primaryDark,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: _isLoading ? null : _loadInstalledApps,
                        icon: const Icon(Icons.refresh),
                        label: const Text('刷新'),
                      ),
                      const SizedBox(width: 12),
                      OutlinedButton.icon(
                        onPressed: selectedCount == 0
                            ? null
                            : () => _confirmUninstall(selectedApps),
                        icon: const Icon(Icons.delete_outline),
                        label: const Text('卸载选中项'),
                      ),
                      const SizedBox(width: 12),
                      FilledButton.icon(
                        onPressed: status.isAvailable ? _launchBcu : null,
                        icon: const Icon(Icons.open_in_new),
                        label: const Text('打开 BCU'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  if (_isLoading)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 54),
                      child: Center(child: CircularProgressIndicator()),
                    )
                  else if (_loadError != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 42),
                      child: Text(_loadError!,
                          style: const TextStyle(color: Colors.red)),
                    )
                  else
                    _AppTable(
                      apps: filteredApps,
                      onChanged: (app, selected) {
                        setState(() {
                          _apps = [
                            for (final current in _apps)
                              if (current.name == app.name &&
                                  current.uninstallCommand ==
                                      app.uninstallCommand)
                                current.copyWith(isSelected: selected)
                              else
                                current,
                          ];
                        });
                      },
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _launchBcu() async {
    try {
      await _bcuService.launch();
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('已启动 BCUninstaller')));
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    }
  }

  Future<void> _loadInstalledApps() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });

    try {
      final apps = await widget.installedAppsService.loadInstalledApps();
      if (!mounted) {
        return;
      }
      setState(() {
        _apps = apps;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _apps = sampleInstalledApps;
        _isLoading = false;
        _loadError = '读取软件列表失败，已显示示例数据：$error';
      });
    }
  }

  Future<void> _confirmUninstall(List<InstalledApp> selectedApps) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('确认卸载'),
          content: Text(
            '将启动 ${selectedApps.length} 个软件的官方卸载程序。'
            '不会静默卸载，也不会自动清理残留。继续前请保存工作。',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('启动卸载'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    var launched = 0;
    for (final app in selectedApps) {
      if (app.uninstallCommand.trim().isEmpty) {
        continue;
      }
      try {
        await _uninstallService.launch(app.uninstallCommand);
        launched++;
      } catch (error) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('${app.name} 启动卸载失败：$error')),
          );
        }
      }
    }

    if (mounted && launched > 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已启动 $launched 个卸载程序')),
      );
    }
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.title,
    required this.value,
    required this.subtitle,
  });

  final String title;
  final String value;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            Container(
              width: 54,
              height: 54,
              decoration: BoxDecoration(
                color: AppColors.paleBlue,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.apps_outlined, color: AppColors.primary),
            ),
            const SizedBox(width: 18),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: AppColors.muted)),
                const SizedBox(height: 5),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                    color: AppColors.primaryDark,
                  ),
                ),
                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 12, color: AppColors.muted),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _BcuStatusCard extends StatelessWidget {
  const _BcuStatusCard({required this.status, required this.onLaunch});

  final BcuStatus status;
  final VoidCallback onLaunch;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            CircleAvatar(
              radius: 27,
              backgroundColor: status.isAvailable
                  ? const Color(0xFFD8FBE4)
                  : const Color(0xFFFFF1C7),
              child: Icon(
                status.isAvailable ? Icons.check : Icons.priority_high,
                color:
                    status.isAvailable ? AppColors.success : AppColors.warning,
              ),
            ),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    status.isAvailable ? 'BCU 后端可用' : 'BCU 后端未配置',
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                      color: AppColors.text,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    status.message,
                    style: const TextStyle(
                      color: AppColors.muted,
                      fontSize: 12,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: status.isAvailable ? onLaunch : null,
              icon: const Icon(Icons.open_in_new),
            ),
          ],
        ),
      ),
    );
  }
}

class _AppTable extends StatelessWidget {
  const _AppTable({required this.apps, required this.onChanged});

  final List<InstalledApp> apps;
  final void Function(InstalledApp app, bool selected) onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const _TableHeader(),
        const Divider(color: AppColors.border),
        for (final app in apps) _AppRow(app: app, onChanged: onChanged),
      ],
    );
  }
}

class _TableHeader extends StatelessWidget {
  const _TableHeader();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          SizedBox(width: 48),
          Expanded(
            flex: 3,
            child: Text('软件名称', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
          Expanded(
            flex: 2,
            child: Text('发布者', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
          Expanded(
            child: Text('版本', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
          Expanded(
            child: Text('大小', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
          Expanded(
            child: Text('安装日期', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
          Expanded(
            child: Text('来源', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
        ],
      ),
    );
  }
}

class _AppRow extends StatelessWidget {
  const _AppRow({required this.app, required this.onChanged});

  final InstalledApp app;
  final void Function(InstalledApp app, bool selected) onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Row(
          children: [
            SizedBox(
              width: 48,
              child: Checkbox(
                value: app.isSelected,
                onChanged: (value) => onChanged(app, value ?? false),
              ),
            ),
            Expanded(
              flex: 3,
              child: Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: AppColors.paleBlue,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.apps,
                      color: AppColors.primary,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Flexible(
                    child: Text(
                      app.name,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              flex: 2,
              child: Text(app.publisher, overflow: TextOverflow.ellipsis),
            ),
            Expanded(child: Text(app.version, overflow: TextOverflow.ellipsis)),
            Expanded(child: Text(app.sizeLabel)),
            Expanded(child: Text(app.installDate)),
            Expanded(
              child: Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 9,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.paleBlue,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    app.source,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: AppColors.primaryDark,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
