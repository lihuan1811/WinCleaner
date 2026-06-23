import 'dart:io';

import 'package:flutter/material.dart';

import '../services/ad_block_service.dart';
import '../services/app_data_migration_service.dart';
import '../services/disk_optimization_service.dart';
import '../services/drive_status_service.dart';
import '../services/duplicate_files_service.dart';
import '../services/empty_folder_service.dart';
import '../services/large_files_service.dart';
import '../services/rule_store_service.dart';
import '../services/system_cleanup_scan_service.dart';
import '../services/windows_maintenance_service.dart';
import '../services/windows_optimization_service.dart';
import '../theme/app_theme.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    this.adBlockService,
    this.duplicateFilesService,
    this.largeFilesService,
    this.diskOptimizationService,
    this.windowsOptimizationService,
    this.driveStatusService,
    this.cleanupScanService,
    this.appDataMigrationService,
  });

  final AdBlockService? adBlockService;
  final DuplicateFilesService? duplicateFilesService;
  final LargeFilesService? largeFilesService;
  final DiskOptimizationService? diskOptimizationService;
  final WindowsOptimizationService? windowsOptimizationService;
  final DriveStatusService? driveStatusService;
  final SystemCleanupScanService? cleanupScanService;
  final AppDataMigrationService? appDataMigrationService;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late final AdBlockService _adBlockService;
  late final DuplicateFilesService _duplicateFilesService;
  late final LargeFilesService _largeFilesService;
  late final DiskOptimizationService _diskOptimizationService;
  late final WindowsOptimizationService _windowsOptimizationService;
  late final DriveStatusService _driveStatusService;
  late final SystemCleanupScanService _cleanupScanService;
  late final AppDataMigrationService _appDataMigrationService;
  DriveStatus? _driveStatus;
  CleanupScanResult? _scanResult;
  bool _loadingDriveStatus = true;
  bool _scanningSystem = false;
  bool _cleaningSystem = false;
  String? _dashboardMessage;
  final List<int> _scanTrendBytes = [];
  final List<_ActivityLogEntry> _activities = [
    const _ActivityLogEntry(
      icon: Icons.info_outline,
      color: Color(0xFFDDEBFF),
      title: '等待首次扫描',
      subtitle: '点击一键开始扫描',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _adBlockService = widget.adBlockService ?? AdBlockService();
    _duplicateFilesService =
        widget.duplicateFilesService ?? DuplicateFilesService();
    _largeFilesService = widget.largeFilesService ?? LargeFilesService();
    _diskOptimizationService =
        widget.diskOptimizationService ?? DiskOptimizationService();
    _windowsOptimizationService =
        widget.windowsOptimizationService ?? WindowsOptimizationService();
    _driveStatusService = widget.driveStatusService ?? DriveStatusService();
    _cleanupScanService =
        widget.cleanupScanService ?? SystemCleanupScanService();
    _appDataMigrationService =
        widget.appDataMigrationService ?? AppDataMigrationService();
    _loadDriveStatus();
  }

  Future<void> _loadDriveStatus() async {
    setState(() {
      _loadingDriveStatus = true;
      _dashboardMessage = null;
    });
    try {
      final status = await _driveStatusService.loadDrive('C');
      if (!mounted) {
        return;
      }
      setState(() {
        _driveStatus = status;
        _loadingDriveStatus = false;
        _activities
          ..removeWhere((entry) => entry.title == '等待首次扫描')
          ..insert(
            0,
            _ActivityLogEntry(
              icon: Icons.storage_outlined,
              color: const Color(0xFFDDEBFF),
              title: status.isSupported ? '磁盘状态已刷新' : '磁盘状态不可用',
              subtitle: status.healthMessage,
            ),
          );
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loadingDriveStatus = false;
        _dashboardMessage = '读取磁盘状态失败：$error';
        _activities.insert(
          0,
          _ActivityLogEntry(
            icon: Icons.warning_amber,
            color: const Color(0xFFFFF1C7),
            title: '磁盘状态读取失败',
            subtitle: error.toString(),
          ),
        );
      });
    }
  }

  Future<void> _startSystemScan() async {
    setState(() {
      _scanningSystem = true;
      _dashboardMessage = '正在扫描系统可清理项目...';
    });
    try {
      final result = await _cleanupScanService.scan();
      if (!mounted) {
        return;
      }
      setState(() {
        _scanResult = result;
        _scanningSystem = false;
        _dashboardMessage = '发现 ${result.itemCount} 个可清理项目';
        _scanTrendBytes
          ..add(result.totalBytes)
          ..removeRange(
              0, _scanTrendBytes.length > 7 ? _scanTrendBytes.length - 7 : 0);
        _activities
          ..removeWhere((entry) => entry.title == '等待首次扫描')
          ..insert(
            0,
            _ActivityLogEntry(
              icon: Icons.done_all,
              color: const Color(0xFFD8FBE4),
              title: '扫描完成 ${_formatBytes(result.totalBytes)}',
              subtitle:
                  '${result.itemCount} 个项目 · ${_formatClock(result.completedAt)}',
            ),
          );
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _scanningSystem = false;
        _dashboardMessage = '扫描失败：$error';
        _activities.insert(
          0,
          _ActivityLogEntry(
            icon: Icons.warning_amber,
            color: const Color(0xFFFFF1C7),
            title: '扫描失败',
            subtitle: error.toString(),
          ),
        );
      });
    }
  }

  Future<void> _startSystemClean() async {
    final scanResult = _scanResult;
    if (scanResult == null || scanResult.totalBytes == 0) {
      setState(() {
        _dashboardMessage = '请先扫描可清理项目';
      });
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认清理'),
        content: Text(
          '将清理已扫描到的临时文件、缓存、日志等安全目标，'
          '下载目录会保持只扫描不自动删除。\n\n预计可清理 ${_formatBytes(scanResult.totalBytes)}。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('开始清理'),
          ),
        ],
      ),
    );

    if (confirmed != true) {
      return;
    }

    setState(() {
      _cleaningSystem = true;
      _dashboardMessage = '正在清理安全目标...';
    });

    try {
      final result = await _cleanupScanService.clean();
      if (!mounted) {
        return;
      }
      setState(() {
        _cleaningSystem = false;
        _scanResult = null;
        _dashboardMessage =
            '已清理 ${result.deletedCount} 个文件，释放 ${_formatBytes(result.freedBytes)}';
        _scanTrendBytes
          ..add(result.freedBytes)
          ..removeRange(
              0, _scanTrendBytes.length > 7 ? _scanTrendBytes.length - 7 : 0);
        _activities
          ..removeWhere((entry) => entry.title == '等待首次扫描')
          ..insert(
            0,
            _ActivityLogEntry(
              icon: Icons.cleaning_services_outlined,
              color: const Color(0xFFD8FBE4),
              title: '清理完成 ${_formatBytes(result.freedBytes)}',
              subtitle:
                  '${result.deletedCount} 个文件 · 跳过 ${result.skippedCategories.length} 类保护目标',
            ),
          );
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _cleaningSystem = false;
        _dashboardMessage = '清理失败：$error';
        _activities.insert(
          0,
          _ActivityLogEntry(
            icon: Icons.warning_amber,
            color: const Color(0xFFFFF1C7),
            title: '清理失败',
            subtitle: error.toString(),
          ),
        );
      });
    }
  }

  Future<void> _openScanReport() {
    return showDialog<void>(
      context: context,
      builder: (context) => _ScanReportDialog(result: _scanResult),
    );
  }

  String get _defaultScanPath {
    return _defaultUserScanPath();
  }

  Future<void> _openAdBlockTool() {
    return showDialog<void>(
      context: context,
      builder: (context) => _AdBlockDialog(service: _adBlockService),
    );
  }

  Future<void> _openDuplicateTool() {
    return showDialog<void>(
      context: context,
      builder: (context) => _DuplicateFilesDialog(
        service: _duplicateFilesService,
        initialPath: _defaultScanPath,
      ),
    );
  }

  Future<void> _openLargeFilesTool() {
    return showDialog<void>(
      context: context,
      builder: (context) => _LargeFilesDialog(
        service: _largeFilesService,
        initialPath: _defaultScanPath,
      ),
    );
  }

  Future<void> _openAppDataMigrationTool() {
    return showDialog<void>(
      context: context,
      builder: (context) => _AppDataMigrationDialog(
        service: _appDataMigrationService,
      ),
    );
  }

  Future<void> _openDiskOptimizationTool() {
    return showDialog<void>(
      context: context,
      builder: (context) =>
          _DiskOptimizationDialog(service: _diskOptimizationService),
    );
  }

  Future<void> _openWindowsOptimizationTool() {
    return showDialog<void>(
      context: context,
      builder: (context) =>
          _WindowsOptimizationDialog(service: _windowsOptimizationService),
    );
  }

  Future<void> _openAllTools() {
    return showDialog<void>(
      context: context,
      builder: (context) => _AllToolsDialog(
        onOpenAdBlock: () {
          Navigator.of(context).pop();
          _openAdBlockTool();
        },
        onOpenDuplicateFiles: () {
          Navigator.of(context).pop();
          _openDuplicateTool();
        },
        onOpenLargeFiles: () {
          Navigator.of(context).pop();
          _openLargeFilesTool();
        },
        onOpenAppDataMigration: () {
          Navigator.of(context).pop();
          _openAppDataMigrationTool();
        },
        onOpenDiskOptimization: () {
          Navigator.of(context).pop();
          _openDiskOptimizationTool();
        },
        onOpenWindowsOptimization: () {
          Navigator.of(context).pop();
          _openWindowsOptimizationTool();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionHeader(
            title: 'C盘清理工作台',
            subtitle: '先扫描可清理空间，再确认执行清理，下载目录默认保护。',
          ),
          const SizedBox(height: 24),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: _StorageCard(
                  status: _driveStatus,
                  scanResult: _scanResult,
                  loading: _loadingDriveStatus,
                  scanning: _scanningSystem,
                  cleaning: _cleaningSystem,
                  message: _dashboardMessage,
                  onScan: _startSystemScan,
                  onClean: _startSystemClean,
                  onReport: _openScanReport,
                ),
              ),
              const SizedBox(width: 32),
              Expanded(
                child: _HealthCard(
                  status: _driveStatus,
                  scanResult: _scanResult,
                ),
              ),
            ],
          ),
          const SizedBox(height: 34),
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('高级工具箱', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 4),
                  const Text(
                    '深层优化您的电脑性能',
                    style: TextStyle(color: AppColors.muted),
                  ),
                ],
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: _openAllTools,
                label: const Text('查看全部工具'),
                icon: const Icon(Icons.chevron_right),
                iconAlignment: IconAlignment.end,
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: _ToolCard(
                  icon: Icons.block_outlined,
                  title: '广告清理',
                  subtitle: '写入 hosts 屏蔽广告域名',
                  onTap: _openAdBlockTool,
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: _ToolCard(
                  icon: Icons.copy_outlined,
                  title: '重复文件',
                  subtitle: '按 SHA-256 识别重复文件',
                  onTap: _openDuplicateTool,
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: _ToolCard(
                  icon: Icons.sd_storage_outlined,
                  title: '超大文件',
                  subtitle: '扫描目录中的大体积文件',
                  onTap: _openLargeFilesTool,
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: _ToolCard(
                  icon: Icons.grid_view_outlined,
                  title: '碎片整理',
                  subtitle: '调用 Windows 磁盘优化',
                  onTap: _openDiskOptimizationTool,
                ),
              ),
            ],
          ),
          const SizedBox(height: 32),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 2,
                child: _TrendCard(valuesBytes: _scanTrendBytes),
              ),
              const SizedBox(width: 32),
              Expanded(
                child: _ActivityCard(entries: _activities.take(4).toList()),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class SystemOptimizationScreen extends StatelessWidget {
  const SystemOptimizationScreen({
    super.key,
    this.adBlockService,
    this.diskOptimizationService,
    this.windowsOptimizationService,
    this.maintenanceService,
    this.ruleStoreService = const RuleStoreService(),
  });

  final AdBlockService? adBlockService;
  final DiskOptimizationService? diskOptimizationService;
  final WindowsOptimizationService? windowsOptimizationService;
  final WindowsMaintenanceService? maintenanceService;
  final RuleStoreService ruleStoreService;

  Future<void> _openAdBlockTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) =>
          _AdBlockDialog(service: adBlockService ?? AdBlockService()),
    );
  }

  Future<void> _openDiskOptimizationTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _DiskOptimizationDialog(
        service: diskOptimizationService ?? DiskOptimizationService(),
      ),
    );
  }

  Future<void> _openWindowsOptimizationTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _WindowsOptimizationDialog(
        service: windowsOptimizationService ?? WindowsOptimizationService(),
      ),
    );
  }

  Future<void> _openInvalidShortcutTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _InvalidShortcutDialog(
        service: maintenanceService ?? WindowsMaintenanceService(),
      ),
    );
  }

  Future<void> _openContextMenuTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _RegistryMaintenanceDialog(
        title: '右键菜单清理',
        icon: Icons.menu_open_outlined,
        scanLabel: '扫描右键菜单',
        emptyText: '未发现右键菜单扩展项',
        scan: () => (maintenanceService ?? WindowsMaintenanceService())
            .scanContextMenuEntries(),
        deleteEntry: (path) =>
            (maintenanceService ?? WindowsMaintenanceService())
                .deleteRegistryEntry(path),
      ),
    );
  }

  Future<void> _openUninstallRegistryTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _RegistryMaintenanceDialog(
        title: '卸载残留注册表',
        icon: Icons.app_blocking_outlined,
        scanLabel: '扫描卸载残留',
        emptyText: '未发现无效卸载注册表项',
        scan: () => (maintenanceService ?? WindowsMaintenanceService())
            .scanInvalidUninstallEntries(),
        deleteEntry: (path) =>
            (maintenanceService ?? WindowsMaintenanceService())
                .deleteRegistryEntry(path),
      ),
    );
  }

  Future<void> _openScheduledTaskTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _ScheduledCleanupDialog(
        service: maintenanceService ?? WindowsMaintenanceService(),
      ),
    );
  }

  Future<void> _openRuleStore(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _RuleStoreDialog(service: ruleStoreService),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _FeatureCenterScaffold(
      title: '系统优化中心',
      subtitle: '集中处理 Windows 设置、广告屏蔽、右键菜单、快捷方式和计划任务。',
      children: [
        _ToolCard(
          icon: Icons.tune_outlined,
          title: 'Windows 设置优化',
          subtitle: '执行 powercfg、netsh、ipconfig、注册表和资源管理器修复',
          onTap: () => _openWindowsOptimizationTool(context),
        ),
        _ToolCard(
          icon: Icons.block_outlined,
          title: '广告清理',
          subtitle: '写入 hosts 规则，屏蔽常见广告域名',
          onTap: () => _openAdBlockTool(context),
        ),
        _ToolCard(
          icon: Icons.grid_view_outlined,
          title: '碎片整理',
          subtitle: '调用 Windows defrag 分析和优化磁盘',
          onTap: () => _openDiskOptimizationTool(context),
        ),
        _ToolCard(
          icon: Icons.link_off_outlined,
          title: '无效快捷方式',
          subtitle: '扫描桌面、开始菜单和任务栏失效 .lnk',
          onTap: () => _openInvalidShortcutTool(context),
        ),
        _ToolCard(
          icon: Icons.menu_open_outlined,
          title: '右键菜单清理',
          subtitle: '扫描 Directory、Folder、Drive 和文件右键扩展',
          onTap: () => _openContextMenuTool(context),
        ),
        _ToolCard(
          icon: Icons.app_blocking_outlined,
          title: '卸载残留注册表',
          subtitle: '发现安装目录已丢失的卸载注册表项',
          onTap: () => _openUninstallRegistryTool(context),
        ),
        _ToolCard(
          icon: Icons.event_repeat_outlined,
          title: '定时任务',
          subtitle: '通过 schtasks 创建高权限清理计划',
          onTap: () => _openScheduledTaskTool(context),
        ),
        _ToolCard(
          icon: Icons.storefront_outlined,
          title: '规则商店',
          subtitle: '下载 c_cleaner_plus 清理规则包 JSON',
          onTap: () => _openRuleStore(context),
        ),
      ],
    );
  }
}

class FileManagementScreen extends StatelessWidget {
  const FileManagementScreen({
    super.key,
    this.duplicateFilesService,
    this.largeFilesService,
    this.emptyFolderService,
    this.appDataMigrationService,
  });

  final DuplicateFilesService? duplicateFilesService;
  final LargeFilesService? largeFilesService;
  final EmptyFolderService? emptyFolderService;
  final AppDataMigrationService? appDataMigrationService;

  Future<void> _openDuplicateTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _DuplicateFilesDialog(
        service: duplicateFilesService ?? DuplicateFilesService(),
        initialPath: _defaultUserScanPath(),
      ),
    );
  }

  Future<void> _openLargeFilesTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _LargeFilesDialog(
        service: largeFilesService ?? LargeFilesService(),
        initialPath: _defaultUserScanPath(),
      ),
    );
  }

  Future<void> _openEmptyFoldersTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _EmptyFoldersDialog(
        service: emptyFolderService ?? EmptyFolderService(),
        initialPath: _defaultUserScanPath(),
      ),
    );
  }

  Future<void> _openAppDataMigrationTool(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (context) => _AppDataMigrationDialog(
        service: appDataMigrationService ?? AppDataMigrationService(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _FeatureCenterScaffold(
      title: '文件管理中心',
      subtitle: '发现重复文件和大体积文件，先定位再处理。',
      children: [
        _ToolCard(
          icon: Icons.copy_outlined,
          title: '重复文件',
          subtitle: '按文件大小和 SHA-256 查找重复副本',
          onTap: () => _openDuplicateTool(context),
        ),
        _ToolCard(
          icon: Icons.sd_storage_outlined,
          title: '超大文件',
          subtitle: '扫描目录中的大文件并按大小排序',
          onTap: () => _openLargeFilesTool(context),
        ),
        _ToolCard(
          icon: Icons.folder_delete_outlined,
          title: '空文件夹',
          subtitle: '按最深路径优先扫描和删除空目录',
          onTap: () => _openEmptyFoldersTool(context),
        ),
        _ToolCard(
          icon: Icons.drive_file_move_outline,
          title: 'C盘瘦身',
          subtitle: '迁移 AppData 大目录到其他盘并保留原路径',
          onTap: () => _openAppDataMigrationTool(context),
        ),
      ],
    );
  }
}

class _FeatureCenterScaffold extends StatelessWidget {
  const _FeatureCenterScaffold({
    required this.title,
    required this.subtitle,
    required this.children,
  });

  final String title;
  final String subtitle;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(title: title, subtitle: subtitle),
          const SizedBox(height: 24),
          LayoutBuilder(
            builder: (context, constraints) {
              const gap = 24.0;
              final columns = constraints.maxWidth < 760 ? 1 : 2;
              final tileWidth =
                  (constraints.maxWidth - gap * (columns - 1)) / columns;
              return Wrap(
                spacing: gap,
                runSpacing: gap,
                children: [
                  for (final child in children)
                    SizedBox(width: tileWidth, child: child),
                ],
              );
            },
          ),
          const SizedBox(height: 28),
          const _GuidanceCard(),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 8),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: AppColors.muted,
                    fontSize: 15,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
          const FeatureIcon(
            icon: Icons.north_east,
            size: 54,
            iconSize: 22,
            selected: true,
          ),
        ],
      ),
    );
  }
}

class _GuidanceCard extends StatelessWidget {
  const _GuidanceCard();

  @override
  Widget build(BuildContext context) {
    return const GlassPanel(
      padding: EdgeInsets.all(20),
      radius: 16,
      child: Row(
        children: [
          Icon(Icons.verified_user_outlined, color: AppColors.primary),
          SizedBox(width: 14),
          Expanded(
            child: Text(
              '会修改系统或删除文件的操作都需要确认。建议在 Windows 上以管理员身份运行。',
              style: TextStyle(color: AppColors.muted, height: 1.5),
            ),
          ),
        ],
      ),
    );
  }
}

class _StorageCard extends StatelessWidget {
  const _StorageCard({
    required this.status,
    required this.scanResult,
    required this.loading,
    required this.scanning,
    required this.cleaning,
    required this.message,
    required this.onScan,
    required this.onClean,
    required this.onReport,
  });

  final DriveStatus? status;
  final CleanupScanResult? scanResult;
  final bool loading;
  final bool scanning;
  final bool cleaning;
  final String? message;
  final VoidCallback onScan;
  final VoidCallback onClean;
  final VoidCallback onReport;

  @override
  Widget build(BuildContext context) {
    final currentStatus = status;
    final used = currentStatus == null || !currentStatus.isSupported
        ? '--'
        : _formatBytes(currentStatus.usedBytes);
    final free = currentStatus == null || !currentStatus.isSupported
        ? '--'
        : _formatBytes(currentStatus.freeBytes);
    final percent = currentStatus == null ? 0.0 : currentStatus.usagePercent;
    final scannedBytes = scanResult == null
        ? '尚未扫描'
        : '本次可清理 ${_formatBytes(scanResult!.totalBytes)}';

    return GlassPanel(
      padding: const EdgeInsets.all(28),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '系统存储监控',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 10),
                Text(
                  loading
                      ? '正在读取驱动器 C: 的实时状态'
                      : currentStatus?.healthMessage ?? '等待读取驱动器 C:',
                  style: const TextStyle(color: AppColors.muted),
                ),
                const SizedBox(height: 34),
                Wrap(
                  spacing: 30,
                  runSpacing: 16,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    _Metric(label: '已用空间', value: used),
                    const SizedBox(
                      height: 52,
                      child: VerticalDivider(color: AppColors.border),
                    ),
                    _Metric(label: '剩余空间', value: free, dark: true),
                    const SizedBox(
                      height: 52,
                      child: VerticalDivider(color: AppColors.border),
                    ),
                    _Metric(label: '扫描结果', value: scannedBytes, dark: true),
                  ],
                ),
                if (message != null) ...[
                  const SizedBox(height: 18),
                  Text(
                    message!,
                    style: const TextStyle(color: AppColors.muted),
                  ),
                ],
                if (scanning || cleaning) ...[
                  const SizedBox(height: 16),
                  const LinearProgressIndicator(minHeight: 4),
                ],
                const SizedBox(height: 28),
                Wrap(
                  spacing: 18,
                  runSpacing: 12,
                  children: [
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                        fixedSize: const Size(220, 62),
                        backgroundColor: AppColors.primaryDark,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      onPressed: scanning || cleaning ? null : onScan,
                      icon: const Icon(Icons.search),
                      label: const Text(
                        '一键开始扫描',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                    const SizedBox(width: 18),
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                        fixedSize: const Size(150, 62),
                        foregroundColor: AppColors.primaryDark,
                        backgroundColor: AppColors.paleBlue,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      onPressed: scanning ||
                              cleaning ||
                              scanResult == null ||
                              scanResult!.totalBytes == 0
                          ? null
                          : onClean,
                      icon: const Icon(Icons.cleaning_services_outlined),
                      label: Text(cleaning ? '清理中' : '一键清理'),
                    ),
                    const SizedBox(width: 18),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        fixedSize: const Size(150, 62),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      onPressed: scanning || cleaning ? null : onReport,
                      child: const Text(
                        '详细报告',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 30),
          SizedBox(
            width: 230,
            height: 230,
            child: _PercentRing(percent: percent),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, this.dark = false});

  final String label;
  final String value;
  final bool dark;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: AppColors.muted)),
        const SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(
            fontSize: 30,
            fontWeight: FontWeight.w900,
            color: dark ? AppColors.text : AppColors.primaryDark,
          ),
        ),
      ],
    );
  }
}

class _PercentRing extends StatelessWidget {
  const _PercentRing({required this.percent});

  final double percent;

  @override
  Widget build(BuildContext context) {
    final normalized = (percent / 100).clamp(0.0, 1.0).toDouble();
    return Stack(
      alignment: Alignment.center,
      children: [
        SizedBox(
          width: 210,
          height: 210,
          child: CircularProgressIndicator(
            value: normalized,
            strokeWidth: 22,
            backgroundColor: const Color(0xFFE5EBF4),
            color: AppColors.primary,
            strokeCap: StrokeCap.butt,
          ),
        ),
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${percent.round()}%',
              style: const TextStyle(
                fontSize: 52,
                fontWeight: FontWeight.w900,
                color: AppColors.primaryDark,
              ),
            ),
            const Text(
              '占用率',
              style: TextStyle(
                color: AppColors.muted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _HealthCard extends StatelessWidget {
  const _HealthCard({required this.status, required this.scanResult});

  final DriveStatus? status;
  final CleanupScanResult? scanResult;

  @override
  Widget build(BuildContext context) {
    final currentStatus = status;
    final healthLabel = currentStatus?.healthLabel ?? '读取中';
    final lastScan = scanResult == null
        ? '上次检查: 尚未扫描'
        : '上次检查: ${_formatClock(scanResult!.completedAt)}';
    final diskPercent =
        currentStatus == null ? 0.0 : currentStatus.usagePercent;
    final cleanableBytes = scanResult?.totalBytes ?? 0;
    final cleanablePercent =
        (cleanableBytes / (10 * 1024 * 1024 * 1024)).clamp(0.0, 1.0).toDouble();

    return GlassPanel(
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('系统健康状态', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 28),
          Row(
            children: [
              const CircleAvatar(
                radius: 42,
                backgroundColor: Color(0xFFE6ECF5),
                child: Icon(
                  Icons.shield_outlined,
                  color: AppColors.primary,
                  size: 40,
                ),
              ),
              const SizedBox(width: 22),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      healthLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primaryDark,
                      ),
                    ),
                    Text(
                      lastScan,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: AppColors.muted),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 36),
          _HealthLine(
            label: '系统盘占用',
            value: '${diskPercent.round()}%',
            percent: (diskPercent / 100).clamp(0.0, 1.0).toDouble(),
          ),
          const SizedBox(height: 26),
          _HealthLine(
            label: '可清理空间',
            value: cleanableBytes == 0 ? '待扫描' : _formatBytes(cleanableBytes),
            percent: cleanablePercent,
          ),
        ],
      ),
    );
  }
}

class _HealthLine extends StatelessWidget {
  const _HealthLine({
    required this.label,
    required this.value,
    required this.percent,
  });

  final String label;
  final String value;
  final double percent;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppColors.muted),
              ),
            ),
            const Spacer(),
            Flexible(
              child: Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.end,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        LinearProgressIndicator(
          value: percent,
          minHeight: 6,
          borderRadius: BorderRadius.circular(4),
        ),
      ],
    );
  }
}

class _ToolCard extends StatelessWidget {
  const _ToolCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      radius: 16,
      padding: EdgeInsets.zero,
      color: AppColors.glassMuted,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: SizedBox(
            height: 156,
            child: Padding(
              padding: const EdgeInsets.all(22),
              child: Row(
                children: [
                  FeatureIcon(icon: icon),
                  const SizedBox(width: 18),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          subtitle,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.muted,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.north_east,
                      color: Colors.white,
                      size: 18,
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

class _AllToolsDialog extends StatelessWidget {
  const _AllToolsDialog({
    required this.onOpenAdBlock,
    required this.onOpenDuplicateFiles,
    required this.onOpenLargeFiles,
    required this.onOpenAppDataMigration,
    required this.onOpenDiskOptimization,
    required this.onOpenWindowsOptimization,
  });

  final VoidCallback onOpenAdBlock;
  final VoidCallback onOpenDuplicateFiles;
  final VoidCallback onOpenLargeFiles;
  final VoidCallback onOpenAppDataMigration;
  final VoidCallback onOpenDiskOptimization;
  final VoidCallback onOpenWindowsOptimization;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('全部工具'),
      content: SizedBox(
        width: 520,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _ToolListTile(
              icon: Icons.block_outlined,
              title: '广告清理',
              subtitle: '写入 hosts 屏蔽广告域名',
              onTap: onOpenAdBlock,
            ),
            _ToolListTile(
              icon: Icons.copy_outlined,
              title: '重复文件',
              subtitle: '按 SHA-256 识别重复文件',
              onTap: onOpenDuplicateFiles,
            ),
            _ToolListTile(
              icon: Icons.sd_storage_outlined,
              title: '超大文件',
              subtitle: '扫描目录中的大体积文件',
              onTap: onOpenLargeFiles,
            ),
            _ToolListTile(
              icon: Icons.drive_file_move_outline,
              title: 'C盘瘦身',
              subtitle: '迁移 AppData 大目录并创建 Junction',
              onTap: onOpenAppDataMigration,
            ),
            _ToolListTile(
              icon: Icons.tune_outlined,
              title: 'Windows 设置优化',
              subtitle: '执行 powercfg、netsh、ipconfig 和注册表优化',
              onTap: onOpenWindowsOptimization,
            ),
            _ToolListTile(
              icon: Icons.grid_view_outlined,
              title: '碎片整理',
              subtitle: '调用 Windows 磁盘优化',
              onTap: onOpenDiskOptimization,
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
    );
  }
}

class _ToolListTile extends StatelessWidget {
  const _ToolListTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: FeatureIcon(icon: icon, size: 42, iconSize: 20),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}

class _AdBlockDialog extends StatefulWidget {
  const _AdBlockDialog({required this.service});

  final AdBlockService service;

  @override
  State<_AdBlockDialog> createState() => _AdBlockDialogState();
}

class _AdBlockDialogState extends State<_AdBlockDialog> {
  AdBlockStatus? _status;
  bool _busy = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadStatus();
  }

  Future<void> _loadStatus() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final status = await widget.service.status();
      if (!mounted) {
        return;
      }
      setState(() {
        _status = status;
        _busy = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _enable() async {
    await _run(() => widget.service.enable());
  }

  Future<void> _disable() async {
    await _run(() => widget.service.disable());
  }

  Future<void> _run(Future<AdBlockStatus> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final status = await action();
      if (!mounted) {
        return;
      }
      setState(() {
        _status = status;
        _busy = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _error = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final status = _status;
    return _ToolDialogFrame(
      title: '广告清理',
      icon: Icons.block_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_busy) const LinearProgressIndicator(minHeight: 4),
          const SizedBox(height: 18),
          _StatusLine(
            label: '状态',
            value: status == null
                ? '读取中'
                : status.enabled
                    ? '已启用'
                    : '未启用',
          ),
          const SizedBox(height: 10),
          _StatusLine(label: 'hosts', value: status?.hostsPath ?? '-'),
          const SizedBox(height: 10),
          _StatusLine(label: '规则数', value: '${status?.blockedDomains ?? 0}'),
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 22),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : _enable,
                icon: const Icon(Icons.shield_outlined),
                label: const Text('启用屏蔽'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _busy ? null : _disable,
                icon: const Icon(Icons.restore),
                label: const Text('恢复 hosts'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DuplicateFilesDialog extends StatefulWidget {
  const _DuplicateFilesDialog({
    required this.service,
    required this.initialPath,
  });

  final DuplicateFilesService service;
  final String initialPath;

  @override
  State<_DuplicateFilesDialog> createState() => _DuplicateFilesDialogState();
}

class _DuplicateFilesDialogState extends State<_DuplicateFilesDialog> {
  late final TextEditingController _pathController;
  DuplicateScanResult? _result;
  bool _busy = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _pathController = TextEditingController(text: widget.initialPath);
  }

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final result = await widget.service.scanDirectory(
        _pathController.text,
        minBytes: 1024,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
        _busy = false;
        _message = '发现 ${result.groups.length} 组重复文件';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = error.toString();
      });
    }
  }

  Future<void> _deleteCopies() async {
    final groups = _result?.groups ?? const <DuplicateFileGroup>[];
    if (groups.isEmpty) {
      return;
    }

    setState(() {
      _busy = true;
      _message = null;
    });
    final result = await widget.service.deleteDuplicateCopies(groups);
    if (!mounted) {
      return;
    }
    setState(() {
      _busy = false;
      _message =
          '已删除 ${result.deletedCount} 个副本，释放 ${_formatBytes(result.freedBytes)}';
      _result = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return _ToolDialogFrame(
      title: '重复文件',
      icon: Icons.copy_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PathInput(controller: _pathController),
          const SizedBox(height: 14),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : _scan,
                icon: const Icon(Icons.search),
                label: const Text('扫描重复文件'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _busy || result == null || result.groups.isEmpty
                    ? null
                    : _deleteCopies,
                icon: const Icon(Icons.delete_outline),
                label: const Text('删除副本'),
              ),
            ],
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_message != null) ...[
            const SizedBox(height: 16),
            Text(_message!, style: const TextStyle(color: AppColors.muted)),
          ],
          if (result != null) ...[
            const SizedBox(height: 16),
            _StatusLine(
                label: '可释放', value: _formatBytes(result.duplicateBytes)),
            const SizedBox(height: 14),
            _DuplicateGroupList(groups: result.groups),
          ],
        ],
      ),
    );
  }
}

class _LargeFilesDialog extends StatefulWidget {
  const _LargeFilesDialog({required this.service, required this.initialPath});

  final LargeFilesService service;
  final String initialPath;

  @override
  State<_LargeFilesDialog> createState() => _LargeFilesDialogState();
}

class _LargeFilesDialogState extends State<_LargeFilesDialog> {
  late final TextEditingController _pathController;
  LargeFileScanResult? _result;
  bool _busy = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _pathController = TextEditingController(text: widget.initialPath);
  }

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final result = await widget.service.scanDirectory(
        _pathController.text,
        minBytes: 100 * 1024 * 1024,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
        _busy = false;
        _message = '发现 ${result.files.length} 个超大文件';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return _ToolDialogFrame(
      title: '超大文件',
      icon: Icons.sd_storage_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PathInput(controller: _pathController),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _busy ? null : _scan,
            icon: const Icon(Icons.search),
            label: const Text('扫描超大文件'),
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_message != null) ...[
            const SizedBox(height: 16),
            Text(_message!, style: const TextStyle(color: AppColors.muted)),
          ],
          if (result != null) ...[
            const SizedBox(height: 16),
            _StatusLine(label: '总大小', value: _formatBytes(result.totalBytes)),
            const SizedBox(height: 14),
            _LargeFileList(files: result.files),
          ],
        ],
      ),
    );
  }
}

class _EmptyFoldersDialog extends StatefulWidget {
  const _EmptyFoldersDialog({
    required this.service,
    required this.initialPath,
  });

  final EmptyFolderService service;
  final String initialPath;

  @override
  State<_EmptyFoldersDialog> createState() => _EmptyFoldersDialogState();
}

class _EmptyFoldersDialogState extends State<_EmptyFoldersDialog> {
  late final TextEditingController _pathController;
  EmptyFolderScanResult? _result;
  bool _busy = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _pathController = TextEditingController(text: widget.initialPath);
  }

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final result = await widget.service.scan(_pathController.text);
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _result = result;
        _message = '发现 ${result.folders.length} 个空文件夹';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = error.toString();
      });
    }
  }

  Future<void> _delete() async {
    final folders = _result?.folders ?? const <EmptyFolderEntry>[];
    if (folders.isEmpty) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除空文件夹'),
        content: Text('将删除 ${folders.length} 个仍为空的文件夹。非空目录会自动跳过。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }

    setState(() {
      _busy = true;
      _message = null;
    });
    final result = await widget.service.deleteFolders(folders);
    if (!mounted) {
      return;
    }
    setState(() {
      _busy = false;
      _result = null;
      _message =
          '已删除 ${result.deletedCount} 个空文件夹，跳过 ${result.skippedPaths.length} 个';
    });
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return _ToolDialogFrame(
      title: '空文件夹',
      icon: Icons.folder_delete_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PathInput(controller: _pathController),
          const SizedBox(height: 14),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : _scan,
                icon: const Icon(Icons.search),
                label: const Text('扫描空文件夹'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _busy || result == null || result.folders.isEmpty
                    ? null
                    : _delete,
                icon: const Icon(Icons.delete_outline),
                label: const Text('删除空文件夹'),
              ),
            ],
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_message != null) ...[
            const SizedBox(height: 16),
            Text(_message!, style: const TextStyle(color: AppColors.muted)),
          ],
          if (result != null) ...[
            const SizedBox(height: 14),
            _PathList(
              emptyText: '未发现空文件夹',
              paths: result.folders.map((folder) => folder.path).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _AppDataMigrationDialog extends StatefulWidget {
  const _AppDataMigrationDialog({required this.service});

  final AppDataMigrationService service;

  @override
  State<_AppDataMigrationDialog> createState() =>
      _AppDataMigrationDialogState();
}

class _AppDataMigrationDialogState extends State<_AppDataMigrationDialog> {
  late final TextEditingController _targetController;
  late List<AppDataScanSource> _sources;
  AppDataMigrationScanResult? _result;
  List<AppDataMigrationRecord> _history = const [];
  final Set<int> _selectedFolders = {};
  bool _busy = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _targetController = TextEditingController(
      text: AppDataMigrationService.defaultTargetRoot(),
    );
    _sources = AppDataMigrationService.defaultScanSources();
    if (_sources.isEmpty) {
      _sources = [
        AppDataScanSource(
          label: '当前用户目录',
          path: _defaultUserScanPath(),
          targetSubdir: 'Custom',
        ),
      ];
    }
    _history = widget.service.loadHistory();
  }

  @override
  void dispose() {
    _targetController.dispose();
    super.dispose();
  }

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _message = null;
      _selectedFolders.clear();
    });
    try {
      final result = await widget.service.scanLargeFolders(_sources);
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _result = result;
        _selectedFolders.addAll(
          List<int>.generate(result.folders.length, (index) => index),
        );
        _message =
            '发现 ${result.folders.length} 个可迁移目录，总计 ${_formatBytes(result.totalBytes)}';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = error.toString();
      });
    }
  }

  Future<void> _migrateSelected() async {
    final result = _result;
    if (result == null || _selectedFolders.isEmpty) {
      setState(() => _message = '请先扫描并勾选需要迁移的目录');
      return;
    }

    final folders = _selectedFolders
        .where((index) => index >= 0 && index < result.folders.length)
        .map((index) => result.folders[index])
        .toList();
    final totalBytes =
        folders.fold<int>(0, (total, folder) => total + folder.sizeBytes);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认迁移 AppData 目录'),
        content: Text(
          '将移动 ${folders.length} 个目录到：\n${_targetController.text}\n\n'
          '移动后会在原路径创建 Junction。建议关闭相关软件，并以管理员身份运行。\n'
          '预计释放 C 盘 ${_formatBytes(totalBytes)}。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('执行迁移'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }

    setState(() {
      _busy = true;
      _message = '正在迁移 ${folders.length} 个目录...';
    });

    final batchId = DateTime.now().microsecondsSinceEpoch.toString();
    var successCount = 0;
    final outputs = <String>[];
    for (final folder in folders) {
      final operation = await widget.service.migrateFolder(
        folder,
        _targetController.text,
        batchId: batchId,
      );
      if (operation.success) {
        successCount++;
      }
      outputs.add('${folder.name}: ${operation.output}');
    }

    if (!mounted) {
      return;
    }
    setState(() {
      _busy = false;
      _history = widget.service.loadHistory();
      _selectedFolders.clear();
      _result = null;
      _message = '迁移完成 $successCount/${folders.length}\n${outputs.join('\n')}';
    });
  }

  Future<void> _restore(AppDataMigrationRecord record) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认还原'),
        content: Text('将把 ${record.name} 从目标目录移回原路径：\n${record.sourcePath}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('还原'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }

    setState(() {
      _busy = true;
      _message = '正在还原 ${record.name}...';
    });
    final result = await widget.service.restoreMigration(record);
    if (!mounted) {
      return;
    }
    setState(() {
      _busy = false;
      _history = widget.service.loadHistory();
      _message = result.output;
    });
  }

  @override
  Widget build(BuildContext context) {
    final scanResult = _result;
    return _ToolDialogFrame(
      title: 'AppData 迁移瘦身',
      icon: Icons.drive_file_move_outline,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _targetController,
            decoration: const InputDecoration(
              labelText: '目标根目录',
              prefixIcon: Icon(Icons.drive_folder_upload_outlined),
              helperText: '建议选择 D/E 盘，例如 D:\\Yugongyipan',
            ),
          ),
          const SizedBox(height: 14),
          const Text(
            '扫描来源',
            style: TextStyle(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 4),
          const Text(
            '默认只扫描用户 AppData，并跳过 WindowsApps、Packages、Microsoft、ProgramData 等受保护目录。',
            style: TextStyle(color: AppColors.muted, height: 1.45),
          ),
          const SizedBox(height: 8),
          _ScanSourceSelector(
            sources: _sources,
            busy: _busy,
            onChanged: (index, enabled) {
              setState(() {
                final source = _sources[index];
                _sources[index] = AppDataScanSource(
                  label: source.label,
                  path: source.path,
                  targetSubdir: source.targetSubdir,
                  enabled: enabled,
                );
              });
            },
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 10,
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : _scan,
                icon: const Icon(Icons.search),
                label: const Text('扫描大目录'),
              ),
              OutlinedButton.icon(
                onPressed:
                    _busy || scanResult == null || _selectedFolders.isEmpty
                        ? null
                        : _migrateSelected,
                icon: const Icon(Icons.drive_file_move_outline),
                label: const Text('执行迁移'),
              ),
              OutlinedButton.icon(
                onPressed: _busy
                    ? null
                    : () => setState(() {
                          _history = widget.service.loadHistory();
                          _message = '迁移记录已刷新';
                        }),
                icon: const Icon(Icons.history),
                label: const Text('刷新记录'),
              ),
            ],
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_message != null) ...[
            const SizedBox(height: 16),
            _CommandOutput(output: _message!),
          ],
          if (scanResult != null) ...[
            const SizedBox(height: 16),
            _StatusLine(
              label: '可迁移',
              value:
                  '${scanResult.folders.length} 个目录 · ${_formatBytes(scanResult.totalBytes)}',
            ),
            const SizedBox(height: 12),
            _MigrationFolderList(
              folders: scanResult.folders,
              selected: _selectedFolders,
              onChanged: _busy
                  ? null
                  : (index, selected) {
                      setState(() {
                        if (selected) {
                          _selectedFolders.add(index);
                        } else {
                          _selectedFolders.remove(index);
                        }
                      });
                    },
            ),
          ],
          const SizedBox(height: 18),
          const Text(
            '迁移记录',
            style: TextStyle(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          _MigrationHistoryList(
            records: _history,
            onRestore: _busy ? null : _restore,
          ),
        ],
      ),
    );
  }
}

class _ScanSourceSelector extends StatelessWidget {
  const _ScanSourceSelector({
    required this.sources,
    required this.busy,
    required this.onChanged,
  });

  final List<AppDataScanSource> sources;
  final bool busy;
  final void Function(int index, bool enabled) onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 150,
      child: ListView.separated(
        itemCount: sources.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) {
          final source = sources[index];
          return CheckboxListTile(
            dense: true,
            value: source.enabled,
            onChanged:
                busy ? null : (value) => onChanged(index, value ?? false),
            title: Text(
              source.label,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Text(source.path, overflow: TextOverflow.ellipsis),
            controlAffinity: ListTileControlAffinity.leading,
          );
        },
      ),
    );
  }
}

class _MigrationFolderList extends StatelessWidget {
  const _MigrationFolderList({
    required this.folders,
    required this.selected,
    required this.onChanged,
  });

  final List<AppDataMigrationFolder> folders;
  final Set<int> selected;
  final void Function(int index, bool selected)? onChanged;

  @override
  Widget build(BuildContext context) {
    if (folders.isEmpty) {
      return const Text('未发现占比较高的大目录',
          style: TextStyle(color: AppColors.muted));
    }

    return SizedBox(
      height: 300,
      child: ListView.separated(
        itemCount: folders.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) {
          final folder = folders[index];
          final ratio = folder.parentTotalBytes == 0
              ? 0
              : (folder.sizeBytes / folder.parentTotalBytes * 100).round();
          return CheckboxListTile(
            dense: true,
            value: selected.contains(index),
            onChanged: onChanged == null
                ? null
                : (value) => onChanged!(index, value ?? false),
            title: Text(
              '${folder.name} · ${_formatBytes(folder.sizeBytes)}',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Text(
              '${folder.sourceLabel} · 占父目录 $ratio%\n${folder.path}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            secondary: const FeatureIcon(
              icon: Icons.folder_copy_outlined,
              size: 38,
              iconSize: 18,
            ),
          );
        },
      ),
    );
  }
}

class _MigrationHistoryList extends StatelessWidget {
  const _MigrationHistoryList({
    required this.records,
    required this.onRestore,
  });

  final List<AppDataMigrationRecord> records;
  final ValueChanged<AppDataMigrationRecord>? onRestore;

  @override
  Widget build(BuildContext context) {
    if (records.isEmpty) {
      return const Text('暂无迁移记录', style: TextStyle(color: AppColors.muted));
    }

    return SizedBox(
      height: 240,
      child: ListView.separated(
        itemCount: records.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) {
          final record = records[index];
          final createdAt =
              DateTime.fromMillisecondsSinceEpoch(record.createdAtMillis);
          return ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const FeatureIcon(
              icon: Icons.history_outlined,
              size: 38,
              iconSize: 18,
            ),
            title: Text(
              '${record.name} · ${_formatBytes(record.sizeBytes)}',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Text(
              '${_formatClock(createdAt)}\n${record.sourcePath} -> ${record.targetPath}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            trailing: OutlinedButton(
              onPressed: onRestore == null ? null : () => onRestore!(record),
              child: const Text('还原'),
            ),
          );
        },
      ),
    );
  }
}

class _InvalidShortcutDialog extends StatefulWidget {
  const _InvalidShortcutDialog({required this.service});

  final WindowsMaintenanceService service;

  @override
  State<_InvalidShortcutDialog> createState() => _InvalidShortcutDialogState();
}

class _InvalidShortcutDialogState extends State<_InvalidShortcutDialog> {
  List<ShortcutIssue> _issues = const [];
  bool _busy = false;
  String? _message;

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final issues = await widget.service.scanInvalidShortcuts(
        _defaultShortcutRoots(),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _issues = issues;
        _message = '发现 ${issues.length} 个无效快捷方式';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = error.toString();
      });
    }
  }

  Future<void> _deleteAll() async {
    if (_issues.isEmpty) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除快捷方式'),
        content: Text('将删除 ${_issues.length} 个无效 .lnk 文件，不会删除目标程序。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }

    var deleted = 0;
    final failed = <String>[];
    for (final issue in _issues) {
      try {
        final file = File(issue.path);
        if (await file.exists()) {
          await file.delete();
          deleted++;
        }
      } on FileSystemException catch (error) {
        failed.add('${issue.path}: ${error.message}');
      }
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _issues = const [];
      _message = '已删除 $deleted 个快捷方式，失败 ${failed.length} 个';
    });
  }

  @override
  Widget build(BuildContext context) {
    return _ToolDialogFrame(
      title: '无效快捷方式',
      icon: Icons.link_off_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '扫描桌面、公共桌面、开始菜单和任务栏固定项，使用 Windows WScript 解析 .lnk 目标。',
            style: TextStyle(color: AppColors.muted, height: 1.5),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : _scan,
                icon: const Icon(Icons.search),
                label: const Text('扫描快捷方式'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _busy || _issues.isEmpty ? null : _deleteAll,
                icon: const Icon(Icons.delete_outline),
                label: const Text('删除无效项'),
              ),
            ],
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_message != null) ...[
            const SizedBox(height: 16),
            Text(_message!, style: const TextStyle(color: AppColors.muted)),
          ],
          const SizedBox(height: 14),
          _ShortcutIssueList(issues: _issues),
        ],
      ),
    );
  }
}

class _RegistryMaintenanceDialog extends StatefulWidget {
  const _RegistryMaintenanceDialog({
    required this.title,
    required this.icon,
    required this.scanLabel,
    required this.emptyText,
    required this.scan,
    required this.deleteEntry,
  });

  final String title;
  final IconData icon;
  final String scanLabel;
  final String emptyText;
  final Future<List<MaintenanceRegistryEntry>> Function() scan;
  final Future<MaintenanceResult> Function(String path) deleteEntry;

  @override
  State<_RegistryMaintenanceDialog> createState() =>
      _RegistryMaintenanceDialogState();
}

class _RegistryMaintenanceDialogState
    extends State<_RegistryMaintenanceDialog> {
  List<MaintenanceRegistryEntry> _entries = const [];
  bool _busy = false;
  String? _message;

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final entries = await widget.scan();
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _entries = entries;
        _message = '发现 ${entries.length} 项';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = error.toString();
      });
    }
  }

  Future<void> _delete(MaintenanceRegistryEntry entry) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除注册表项'),
        content: SelectableText(entry.path),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('删除'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }

    setState(() {
      _busy = true;
      _message = null;
    });
    final result = await widget.deleteEntry(entry.path);
    if (!mounted) {
      return;
    }
    setState(() {
      _busy = false;
      _message = result.success ? '已删除 ${entry.name}' : result.output;
      if (result.success) {
        _entries = _entries.where((item) => item.path != entry.path).toList();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return _ToolDialogFrame(
      title: widget.title,
      icon: widget.icon,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          FilledButton.icon(
            onPressed: _busy ? null : _scan,
            icon: const Icon(Icons.search),
            label: Text(widget.scanLabel),
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_message != null) ...[
            const SizedBox(height: 16),
            Text(_message!, style: const TextStyle(color: AppColors.muted)),
          ],
          const SizedBox(height: 14),
          _RegistryEntryList(
            entries: _entries,
            emptyText: widget.emptyText,
            onDelete: _busy ? null : _delete,
          ),
        ],
      ),
    );
  }
}

class _ScheduledCleanupDialog extends StatefulWidget {
  const _ScheduledCleanupDialog({required this.service});

  final WindowsMaintenanceService service;

  @override
  State<_ScheduledCleanupDialog> createState() =>
      _ScheduledCleanupDialogState();
}

class _ScheduledCleanupDialogState extends State<_ScheduledCleanupDialog> {
  final _nameController = TextEditingController(text: 'DailyClean');
  final _timeController = TextEditingController(text: '09:00');
  String? _output;
  bool _busy = false;

  @override
  void dispose() {
    _nameController.dispose();
    _timeController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<MaintenanceResult> Function() action) async {
    setState(() {
      _busy = true;
      _output = null;
    });
    try {
      final result = await action();
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _output = '退出码 ${result.exitCode}\n${result.output}';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _output = error.toString();
      });
    }
  }

  Future<void> _createDaily() {
    return _run(
      () => widget.service.createScheduledCleanupTask(
        taskName: _nameController.text,
        executablePath: Platform.resolvedExecutable,
        schedule: MaintenanceSchedule.daily,
        time: _timeController.text,
      ),
    );
  }

  Future<void> _deleteTask() {
    return _run(
      () => widget.service.deleteScheduledTask(_nameController.text),
    );
  }

  Future<void> _runTask() {
    return _run(
      () => widget.service.runScheduledTask(_nameController.text),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _ToolDialogFrame(
      title: '定时任务',
      icon: Icons.event_repeat_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '使用 Windows schtasks 创建高权限清理计划。默认每天执行一次当前 WinCleaner 程序。',
            style: TextStyle(color: AppColors.muted, height: 1.5),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: '任务名称'),
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 140,
                child: TextField(
                  controller: _timeController,
                  decoration: const InputDecoration(labelText: '时间 HH:mm'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : _createDaily,
                icon: const Icon(Icons.add_task_outlined),
                label: const Text('创建每日任务'),
              ),
              OutlinedButton.icon(
                onPressed: _busy ? null : _runTask,
                icon: const Icon(Icons.play_arrow_outlined),
                label: const Text('立即运行'),
              ),
              OutlinedButton.icon(
                onPressed: _busy ? null : _deleteTask,
                icon: const Icon(Icons.delete_outline),
                label: const Text('删除任务'),
              ),
            ],
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_output != null) ...[
            const SizedBox(height: 16),
            _CommandOutput(output: _output!),
          ],
        ],
      ),
    );
  }
}

class _RuleStoreDialog extends StatefulWidget {
  const _RuleStoreDialog({required this.service});

  final RuleStoreService service;

  @override
  State<_RuleStoreDialog> createState() => _RuleStoreDialogState();
}

class _RuleStoreDialogState extends State<_RuleStoreDialog> {
  bool _busy = false;
  String? _message;

  Future<void> _download(RulePack pack) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final result = await widget.service.downloadRulePack(
        pack,
        _defaultRulePackDirectory(),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = '已下载 ${pack.name}: ${result.file.path}';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final packs = widget.service.packs;
    return _ToolDialogFrame(
      title: '规则商店',
      icon: Icons.storefront_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '规则来源为 Kiowx/c_cleaner_plus 的 config 目录。下载后保存在本机 WinCleaner rules 目录，后续可继续接入自定义规则扫描。',
            style: TextStyle(color: AppColors.muted, height: 1.5),
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_message != null) ...[
            const SizedBox(height: 16),
            SelectableText(
              _message!,
              style: const TextStyle(color: AppColors.muted),
            ),
          ],
          const SizedBox(height: 14),
          SizedBox(
            height: 360,
            child: ListView.separated(
              itemCount: packs.length,
              separatorBuilder: (_, __) =>
                  const Divider(color: AppColors.border),
              itemBuilder: (context, index) {
                final pack = packs[index];
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const FeatureIcon(
                    icon: Icons.description_outlined,
                    size: 42,
                    iconSize: 20,
                  ),
                  title: Text(
                    pack.name,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    '${pack.category} · ${pack.description}\n${pack.fileName}',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: OutlinedButton(
                    onPressed: _busy ? null : () => _download(pack),
                    child: const Text('下载'),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _DiskOptimizationDialog extends StatefulWidget {
  const _DiskOptimizationDialog({required this.service});

  final DiskOptimizationService service;

  @override
  State<_DiskOptimizationDialog> createState() =>
      _DiskOptimizationDialogState();
}

class _DiskOptimizationDialogState extends State<_DiskOptimizationDialog> {
  final _driveController = TextEditingController(text: 'C');
  bool _busy = false;
  String? _output;

  @override
  void dispose() {
    _driveController.dispose();
    super.dispose();
  }

  Future<void> _analyze() async {
    await _run(() => widget.service.analyze(_driveController.text));
  }

  Future<void> _optimize() async {
    await _run(() => widget.service.optimize(_driveController.text));
  }

  Future<void> _run(Future<DiskOptimizationResult> Function() action) async {
    setState(() {
      _busy = true;
      _output = null;
    });
    try {
      final result = await action();
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _output =
            '退出码 ${result.exitCode}\n${result.output.isEmpty ? '命令无输出' : result.output}';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _output = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return _ToolDialogFrame(
      title: '碎片整理',
      icon: Icons.grid_view_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 160,
            child: TextField(
              controller: _driveController,
              decoration: const InputDecoration(labelText: '盘符'),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _busy ? null : _analyze,
                icon: const Icon(Icons.analytics_outlined),
                label: const Text('分析'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _busy ? null : _optimize,
                icon: const Icon(Icons.speed_outlined),
                label: const Text('优化'),
              ),
            ],
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_output != null) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                border: Border.all(color: AppColors.border),
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                _output!,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _WindowsOptimizationDialog extends StatefulWidget {
  const _WindowsOptimizationDialog({required this.service});

  final WindowsOptimizationService service;

  @override
  State<_WindowsOptimizationDialog> createState() =>
      _WindowsOptimizationDialogState();
}

class _WindowsOptimizationDialogState
    extends State<_WindowsOptimizationDialog> {
  bool _busy = false;
  String? _activeActionId;
  String? _output;

  Future<void> _apply(WindowsOptimizationAction action) async {
    final confirmed = await _confirm(action, revert: false);
    if (confirmed != true) {
      return;
    }
    await _run(action, () => widget.service.apply(action.id));
  }

  Future<void> _revert(WindowsOptimizationAction action) async {
    final confirmed = await _confirm(action, revert: true);
    if (confirmed != true) {
      return;
    }
    await _run(action, () => widget.service.revert(action.id));
  }

  Future<bool?> _confirm(
    WindowsOptimizationAction action, {
    required bool revert,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(revert ? '确认恢复默认' : '确认执行优化'),
        content: Text(
          '${action.title}\n\n${action.description}\n\n'
          '风险: ${action.riskLabel}'
          '${action.requiresAdmin ? '\n需要管理员权限。' : ''}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(revert ? '恢复默认' : '执行优化'),
          ),
        ],
      ),
    );
  }

  Future<void> _run(
    WindowsOptimizationAction action,
    Future<WindowsOptimizationResult> Function() runner,
  ) async {
    setState(() {
      _busy = true;
      _activeActionId = action.id;
      _output = null;
    });

    try {
      final result = await runner();
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _activeActionId = null;
        _output = result.output;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _activeActionId = null;
        _output = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return _ToolDialogFrame(
      title: 'Windows 设置优化',
      icon: Icons.tune_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '这些操作会真实调用 Windows 命令；请在 Windows 上以管理员身份运行以获得完整权限。',
            style: TextStyle(color: AppColors.muted, height: 1.5),
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 380,
            child: ListView.separated(
              itemCount: widget.service.actions.length,
              separatorBuilder: (_, __) =>
                  const Divider(color: AppColors.border),
              itemBuilder: (context, index) {
                final action = widget.service.actions[index];
                final active = _busy && _activeActionId == action.id;
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: FeatureIcon(
                    icon: _optimizationIcon(action.category),
                    size: 44,
                    iconSize: 20,
                  ),
                  title: Text(
                    action.title,
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                  subtitle: Text(
                    '${action.category} · ${action.riskLabel}'
                    '${action.requiresAdmin ? ' · 需要管理员' : ''}\n'
                    '${action.description}\n'
                    '${action.commands.map((c) => c.commandLine).join('\n')}',
                  ),
                  trailing: Wrap(
                    spacing: 8,
                    children: [
                      FilledButton(
                        onPressed: _busy ? null : () => _apply(action),
                        child: Text(active ? '执行中' : '执行优化'),
                      ),
                      OutlinedButton(
                        onPressed: _busy || !action.canRevert
                            ? null
                            : () => _revert(action),
                        child: const Text('恢复默认'),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
          if (_busy) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(minHeight: 4),
          ],
          if (_output != null) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                border: Border.all(color: AppColors.border),
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                _output!,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ),
          ],
        ],
      ),
    );
  }

  IconData _optimizationIcon(String category) {
    return switch (category) {
      '网络' => Icons.wifi_tethering_outlined,
      '性能' => Icons.speed_outlined,
      '存储' => Icons.sd_storage_outlined,
      '启动' => Icons.rocket_launch_outlined,
      '视觉' => Icons.auto_awesome_motion_outlined,
      '隐私' => Icons.visibility_off_outlined,
      '修复' => Icons.construction_outlined,
      _ => Icons.tune_outlined,
    };
  }
}

class _ScanReportDialog extends StatelessWidget {
  const _ScanReportDialog({required this.result});

  final CleanupScanResult? result;

  @override
  Widget build(BuildContext context) {
    final scanResult = result;
    return _ToolDialogFrame(
      title: '扫描详细报告',
      icon: Icons.receipt_long_outlined,
      child: scanResult == null
          ? const Text('尚未执行扫描', style: TextStyle(color: AppColors.muted))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StatusLine(
                  label: '完成时间',
                  value: _formatClock(scanResult.completedAt),
                ),
                const SizedBox(height: 10),
                _StatusLine(label: '项目数量', value: '${scanResult.itemCount}'),
                const SizedBox(height: 10),
                _StatusLine(
                  label: '可清理',
                  value: _formatBytes(scanResult.totalBytes),
                ),
                const SizedBox(height: 18),
                SizedBox(
                  height: 360,
                  child: ListView.separated(
                    itemCount: scanResult.categories.length,
                    separatorBuilder: (_, __) =>
                        const Divider(color: AppColors.border),
                    itemBuilder: (context, index) {
                      final category = scanResult.categories[index];
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          category.name,
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        subtitle: Text(
                          '${category.description}\n'
                          '扫描路径 ${category.scannedPathCount} 个'
                          '${category.errors.isEmpty ? '' : ' · 错误 ${category.errors.length} 个'}',
                        ),
                        trailing: Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _formatBytes(category.totalBytes),
                              style:
                                  const TextStyle(fontWeight: FontWeight.w900),
                            ),
                            Text(
                              '${category.itemCount} 项',
                              style: const TextStyle(
                                color: AppColors.muted,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
    );
  }
}

class _ToolDialogFrame extends StatelessWidget {
  const _ToolDialogFrame({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      titlePadding: const EdgeInsets.fromLTRB(24, 22, 24, 0),
      contentPadding: const EdgeInsets.fromLTRB(24, 18, 24, 24),
      title: Row(
        children: [
          FeatureIcon(icon: icon, size: 40, iconSize: 20),
          const SizedBox(width: 12),
          Text(title),
        ],
      ),
      content: SizedBox(
        width: 720,
        child: SingleChildScrollView(child: child),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('关闭'),
        ),
      ],
    );
  }
}

class _PathInput extends StatelessWidget {
  const _PathInput({required this.controller});

  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      decoration: const InputDecoration(
        labelText: '扫描目录',
        prefixIcon: Icon(Icons.folder_outlined),
      ),
    );
  }
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 86,
          child: Text(label, style: const TextStyle(color: AppColors.muted)),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
      ],
    );
  }
}

class _DuplicateGroupList extends StatelessWidget {
  const _DuplicateGroupList({required this.groups});

  final List<DuplicateFileGroup> groups;

  @override
  Widget build(BuildContext context) {
    if (groups.isEmpty) {
      return const Text('未发现重复文件', style: TextStyle(color: AppColors.muted));
    }

    return SizedBox(
      height: 280,
      child: ListView.separated(
        itemCount: groups.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) {
          final group = groups[index];
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${group.files.length} 个文件 · 可释放 ${_formatBytes(group.wastedBytes)}',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              for (final file in group.files)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    file.path,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: AppColors.muted),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _LargeFileList extends StatelessWidget {
  const _LargeFileList({required this.files});

  final List<LargeFileEntry> files;

  @override
  Widget build(BuildContext context) {
    if (files.isEmpty) {
      return const Text('未发现超大文件', style: TextStyle(color: AppColors.muted));
    }

    return SizedBox(
      height: 280,
      child: ListView.separated(
        itemCount: files.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) {
          final file = files[index];
          return ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text(file.name, overflow: TextOverflow.ellipsis),
            subtitle: Text(file.path, overflow: TextOverflow.ellipsis),
            trailing: Text(
              _formatBytes(file.size),
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          );
        },
      ),
    );
  }
}

class _PathList extends StatelessWidget {
  const _PathList({required this.paths, required this.emptyText});

  final List<String> paths;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    if (paths.isEmpty) {
      return Text(emptyText, style: const TextStyle(color: AppColors.muted));
    }

    return SizedBox(
      height: 280,
      child: ListView.separated(
        itemCount: paths.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) => ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.folder_outlined, color: AppColors.primary),
          title: Text(paths[index], overflow: TextOverflow.ellipsis),
        ),
      ),
    );
  }
}

class _ShortcutIssueList extends StatelessWidget {
  const _ShortcutIssueList({required this.issues});

  final List<ShortcutIssue> issues;

  @override
  Widget build(BuildContext context) {
    if (issues.isEmpty) {
      return const Text('未发现无效快捷方式', style: TextStyle(color: AppColors.muted));
    }

    return SizedBox(
      height: 280,
      child: ListView.separated(
        itemCount: issues.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) {
          final issue = issues[index];
          return ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading:
                const Icon(Icons.link_off_outlined, color: AppColors.warning),
            title: Text(issue.path, overflow: TextOverflow.ellipsis),
            subtitle: Text(
              '${issue.reason} · ${issue.targetPath.isEmpty ? '无目标' : issue.targetPath}',
              overflow: TextOverflow.ellipsis,
            ),
          );
        },
      ),
    );
  }
}

class _RegistryEntryList extends StatelessWidget {
  const _RegistryEntryList({
    required this.entries,
    required this.emptyText,
    required this.onDelete,
  });

  final List<MaintenanceRegistryEntry> entries;
  final String emptyText;
  final ValueChanged<MaintenanceRegistryEntry>? onDelete;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return Text(emptyText, style: const TextStyle(color: AppColors.muted));
    }

    return SizedBox(
      height: 320,
      child: ListView.separated(
        itemCount: entries.length,
        separatorBuilder: (_, __) => const Divider(color: AppColors.border),
        itemBuilder: (context, index) {
          final entry = entries[index];
          return ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.account_tree_outlined,
                color: AppColors.primary),
            title: Text(
              entry.name,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Text(
              '${entry.detail}\n${entry.path}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            trailing: OutlinedButton(
              onPressed: onDelete == null ? null : () => onDelete!(entry),
              child: const Text('删除'),
            ),
          );
        },
      ),
    );
  }
}

class _CommandOutput extends StatelessWidget {
  const _CommandOutput({required this.output});

  final String output;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.glassStrong,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(10),
      ),
      child: SelectableText(
        output,
        style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
      ),
    );
  }
}

String _formatBytes(int bytes) {
  if (bytes < 1024) {
    return '$bytes B';
  }
  if (bytes < 1024 * 1024) {
    return '${(bytes / 1024).toStringAsFixed(1)} KB';
  }
  if (bytes < 1024 * 1024 * 1024) {
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
  return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
}

String _defaultUserScanPath() {
  final userProfile = Platform.environment['USERPROFILE'];
  if (Platform.isWindows && userProfile != null && userProfile.isNotEmpty) {
    return '$userProfile\\Downloads';
  }
  return Platform.environment['HOME'] ?? Directory.current.path;
}

List<String> _defaultShortcutRoots() {
  final userProfile = Platform.environment['USERPROFILE'] ?? '';
  final appData = Platform.environment['APPDATA'] ?? '';
  final roots = <String>[
    if (userProfile.isNotEmpty) '$userProfile\\Desktop',
    r'C:\Users\Public\Desktop',
    if (appData.isNotEmpty) '$appData\\Microsoft\\Windows\\Start Menu',
    r'C:\ProgramData\Microsoft\Windows\Start Menu',
    if (appData.isNotEmpty)
      '$appData\\Microsoft\\Internet Explorer\\Quick Launch\\User Pinned\\TaskBar',
  ];
  return roots;
}

Directory _defaultRulePackDirectory() {
  final appData = Platform.environment['APPDATA'];
  if (Platform.isWindows && appData != null && appData.isNotEmpty) {
    return Directory('$appData\\WinCleaner\\rules');
  }
  final home = Platform.environment['HOME'] ?? Directory.current.path;
  return Directory('$home/.wincleaner/rules');
}

String _formatClock(DateTime value) {
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${twoDigits(value.hour)}:${twoDigits(value.minute)}';
}

class _TrendCard extends StatelessWidget {
  const _TrendCard({required this.valuesBytes});

  final List<int> valuesBytes;

  @override
  Widget build(BuildContext context) {
    final values = valuesBytes.isEmpty ? const <int>[0] : valuesBytes;
    final maxValue =
        values.fold<int>(1, (max, value) => value > max ? value : max);
    return GlassPanel(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('最近清理趋势', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 34),
          SizedBox(
            height: 230,
            child: valuesBytes.isEmpty
                ? const Center(
                    child: Text(
                      '暂无扫描记录',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      for (var i = 0; i < values.length; i++)
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 5),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                Text(
                                  _formatBytes(values[i]),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: AppColors.muted,
                                    fontSize: 11,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Expanded(
                                  child: Align(
                                    alignment: Alignment.bottomCenter,
                                    child: FractionallySizedBox(
                                      heightFactor: (values[i] / maxValue)
                                          .clamp(.05, 1)
                                          .toDouble(),
                                      child: Container(
                                        decoration: BoxDecoration(
                                          color: i == values.length - 1
                                              ? AppColors.primaryDark
                                              : const Color(0xFFD8E4FF),
                                          borderRadius:
                                              const BorderRadius.vertical(
                                            top: Radius.circular(3),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 14),
                                Text(
                                  i == values.length - 1 ? '本次' : '第${i + 1}次',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: i == values.length - 1
                                        ? FontWeight.w800
                                        : FontWeight.w500,
                                    color: AppColors.muted,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class _ActivityCard extends StatelessWidget {
  const _ActivityCard({required this.entries});

  final List<_ActivityLogEntry> entries;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('实时活动日志', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 26),
          for (final entry in entries)
            _Activity(
              icon: entry.icon,
              color: entry.color,
              title: entry.title,
              subtitle: entry.subtitle,
            ),
        ],
      ),
    );
  }
}

class _ActivityLogEntry {
  const _ActivityLogEntry({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
}

class _Activity extends StatelessWidget {
  const _Activity({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 22),
      child: Row(
        children: [
          CircleAvatar(
            radius: 21,
            backgroundColor: color,
            child: Icon(icon, color: AppColors.primary, size: 22),
          ),
          const SizedBox(width: 18),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    color: AppColors.text,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: AppColors.muted, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
