import 'dart:io';

import 'package:flutter/material.dart';

import '../services/ad_block_service.dart';
import '../services/disk_optimization_service.dart';
import '../services/drive_status_service.dart';
import '../services/duplicate_files_service.dart';
import '../services/large_files_service.dart';
import '../services/system_cleanup_scan_service.dart';
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
  });

  final AdBlockService? adBlockService;
  final DuplicateFilesService? duplicateFilesService;
  final LargeFilesService? largeFilesService;
  final DiskOptimizationService? diskOptimizationService;
  final WindowsOptimizationService? windowsOptimizationService;
  final DriveStatusService? driveStatusService;
  final SystemCleanupScanService? cleanupScanService;

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
  });

  final AdBlockService? adBlockService;
  final DiskOptimizationService? diskOptimizationService;
  final WindowsOptimizationService? windowsOptimizationService;

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

  @override
  Widget build(BuildContext context) {
    return _FeatureCenterScaffold(
      title: '系统优化中心',
      subtitle: '集中处理 hosts 广告屏蔽、Windows 设置优化和磁盘优化。',
      children: [
        _ToolCard(
          icon: Icons.tune_outlined,
          title: 'Windows 设置优化',
          subtitle: '执行 powercfg、ipconfig、netsh 和注册表优化',
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
      ],
    );
  }
}

class FileManagementScreen extends StatelessWidget {
  const FileManagementScreen({
    super.key,
    this.duplicateFilesService,
    this.largeFilesService,
  });

  final DuplicateFilesService? duplicateFilesService;
  final LargeFilesService? largeFilesService;

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
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: AppColors.warmSurface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
      ),
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
          Container(
            width: 54,
            height: 54,
            decoration: const BoxDecoration(
              color: AppColors.paleBlue,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.north_east, color: AppColors.primaryDark),
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
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(24),
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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
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
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      healthLabel,
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primaryDark,
                      ),
                    ),
                    Text(
                      lastScan,
                      style: const TextStyle(color: AppColors.muted),
                    ),
                  ],
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
            Text(label, style: const TextStyle(color: AppColors.muted)),
            const Spacer(),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
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
    return Card(
      clipBehavior: Clip.antiAlias,
      color: AppColors.surfaceTint,
      child: InkWell(
        borderRadius: BorderRadius.circular(28),
        onTap: onTap,
        child: SizedBox(
          height: 190,
          child: Stack(
            children: [
              Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 58,
                      height: 58,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Icon(icon, color: AppColors.primaryDark),
                    ),
                    const Spacer(),
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 6),
                    Text(
                      subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style:
                          const TextStyle(color: AppColors.muted, fontSize: 13),
                    ),
                  ],
                ),
              ),
              Positioned(
                right: 0,
                bottom: 0,
                child: Container(
                  width: 72,
                  height: 72,
                  decoration: const BoxDecoration(
                    color: AppColors.warmSurface,
                    borderRadius:
                        BorderRadius.only(topLeft: Radius.circular(24)),
                  ),
                  child: Center(
                    child: Container(
                      width: 46,
                      height: 46,
                      decoration: const BoxDecoration(
                        color: AppColors.primary,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.north_east,
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
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

class _AllToolsDialog extends StatelessWidget {
  const _AllToolsDialog({
    required this.onOpenAdBlock,
    required this.onOpenDuplicateFiles,
    required this.onOpenLargeFiles,
    required this.onOpenDiskOptimization,
    required this.onOpenWindowsOptimization,
  });

  final VoidCallback onOpenAdBlock;
  final VoidCallback onOpenDuplicateFiles;
  final VoidCallback onOpenLargeFiles;
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
      leading: Icon(icon, color: AppColors.primary),
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
                  leading: CircleAvatar(
                    backgroundColor: AppColors.paleBlue,
                    foregroundColor: AppColors.primaryDark,
                    child: Icon(_optimizationIcon(action.category)),
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
          Icon(icon, color: AppColors.primary),
          const SizedBox(width: 10),
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
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(28),
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
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 5),
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
                                    i == values.length - 1
                                        ? '本次'
                                        : '第${i + 1}次',
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
      ),
    );
  }
}

class _ActivityCard extends StatelessWidget {
  const _ActivityCard({required this.entries});

  final List<_ActivityLogEntry> entries;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(28),
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
