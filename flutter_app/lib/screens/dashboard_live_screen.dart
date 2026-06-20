import 'package:flutter/material.dart';

import '../services/drive_status_service.dart';
import '../services/system_cleanup_scan_service.dart';
import '../theme/app_theme.dart';

class DashboardLiveScreen extends StatefulWidget {
  const DashboardLiveScreen({
    super.key,
    this.driveStatusService,
    this.cleanupScanService,
  });

  final DriveStatusService? driveStatusService;
  final SystemCleanupScanService? cleanupScanService;

  @override
  State<DashboardLiveScreen> createState() => _DashboardLiveScreenState();
}

class _DashboardLiveScreenState extends State<DashboardLiveScreen> {
  late final DriveStatusService _driveStatusService;
  late final SystemCleanupScanService _cleanupScanService;
  DriveStatus? _driveStatus;
  CleanupScanResult? _scanResult;
  bool _loading = true;
  bool _scanning = false;
  String? _message;
  final List<int> _trend = [];

  @override
  void initState() {
    super.initState();
    _driveStatusService = widget.driveStatusService ?? DriveStatusService();
    _cleanupScanService =
        widget.cleanupScanService ?? SystemCleanupScanService();
    _loadDriveStatus();
  }

  Future<void> _loadDriveStatus() async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      final status = await _driveStatusService.loadDrive('C');
      if (!mounted) {
        return;
      }
      setState(() {
        _driveStatus = status;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _message = '读取磁盘状态失败：$error';
      });
    }
  }

  Future<void> _scanSystem() async {
    setState(() {
      _scanning = true;
      _message = '正在扫描系统可清理项目...';
    });
    try {
      final result = await _cleanupScanService.scan();
      if (!mounted) {
        return;
      }
      setState(() {
        _scanResult = result;
        _scanning = false;
        _message = '发现 ${result.itemCount} 个可清理项目';
        _trend
          ..add(result.totalBytes)
          ..removeRange(0, _trend.length > 7 ? _trend.length - 7 : 0);
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _scanning = false;
        _message = '扫描失败：$error';
      });
    }
  }

  void _openReport() {
    showDialog<void>(
      context: context,
      builder: (context) => _ReportDialog(result: _scanResult),
    );
  }

  @override
  Widget build(BuildContext context) {
    final status = _driveStatus;
    final used =
        status?.isSupported == true ? _formatBytes(status!.usedBytes) : '--';
    final free =
        status?.isSupported == true ? _formatBytes(status!.freeBytes) : '--';
    final percent = status == null ? 0.0 : status.usagePercent;
    final scanBytes = _scanResult == null
        ? '尚未扫描'
        : '本次可清理 ${_formatBytes(_scanResult!.totalBytes)}';

    return LayoutBuilder(
      builder: (context, constraints) {
        final isNarrow = constraints.maxWidth < 1100;
        final storageCard = _StorageCard(
          used: used,
          free: free,
          percent: percent,
          scanBytes: scanBytes,
          message: _loading
              ? '正在读取驱动器 C: 的实时状态'
              : _message ?? status?.healthMessage ?? '等待读取驱动器 C:',
          scanning: _scanning,
          onScan: _scanSystem,
          onReport: _openReport,
        );
        final healthCard = _HealthCard(
          health: status?.healthLabel ?? '读取中',
          lastScan: _scanResult == null
              ? '上次检查: 尚未扫描'
              : '上次检查: ${_formatClock(_scanResult!.completedAt)}',
          diskPercent: percent,
          cleanableBytes: _scanResult?.totalBytes ?? 0,
        );

        return SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (isNarrow)
                Column(
                  children: [
                    storageCard,
                    const SizedBox(height: 24),
                    healthCard,
                  ],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 2, child: storageCard),
                    const SizedBox(width: 32),
                    Expanded(child: healthCard),
                  ],
                ),
              const SizedBox(height: 34),
              Text('高级工具箱', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 4),
              const Text('深层优化您的电脑性能',
                  style: TextStyle(color: AppColors.muted)),
              const SizedBox(height: 24),
              const _ToolSummaryGrid(),
              const SizedBox(height: 32),
              if (isNarrow)
                Column(
                  children: [
                    _TrendCard(values: _trend),
                    const SizedBox(height: 24),
                    _ActivityCard(
                      message: _message ?? '等待首次扫描',
                      result: _scanResult,
                    ),
                  ],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 2, child: _TrendCard(values: _trend)),
                    const SizedBox(width: 32),
                    Expanded(
                      child: _ActivityCard(
                        message: _message ?? '等待首次扫描',
                        result: _scanResult,
                      ),
                    ),
                  ],
                ),
            ],
          ),
        );
      },
    );
  }
}

class _StorageCard extends StatelessWidget {
  const _StorageCard({
    required this.used,
    required this.free,
    required this.percent,
    required this.scanBytes,
    required this.message,
    required this.scanning,
    required this.onScan,
    required this.onReport,
  });

  final String used;
  final String free;
  final double percent;
  final String scanBytes;
  final String message;
  final bool scanning;
  final VoidCallback onScan;
  final VoidCallback onReport;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('系统存储监控',
                      style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: 10),
                  Text(message, style: const TextStyle(color: AppColors.muted)),
                  const SizedBox(height: 34),
                  Wrap(
                    spacing: 30,
                    runSpacing: 16,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      _Metric(label: '已用空间', value: used),
                      const SizedBox(
                          height: 52,
                          child: VerticalDivider(color: AppColors.border)),
                      _Metric(label: '剩余空间', value: free, dark: true),
                      const SizedBox(
                          height: 52,
                          child: VerticalDivider(color: AppColors.border)),
                      _Metric(label: '扫描结果', value: scanBytes, dark: true),
                    ],
                  ),
                  if (scanning) ...[
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
                              borderRadius: BorderRadius.circular(10)),
                        ),
                        onPressed: scanning ? null : onScan,
                        icon: const Icon(Icons.search),
                        label: const Text('一键开始扫描',
                            style: TextStyle(fontWeight: FontWeight.w800)),
                      ),
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          fixedSize: const Size(150, 62),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                        onPressed: onReport,
                        child: const Text('详细报告',
                            style: TextStyle(fontWeight: FontWeight.w800)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 30),
            SizedBox(
                width: 230, height: 230, child: _PercentRing(percent: percent)),
          ],
        ),
      ),
    );
  }
}

class _HealthCard extends StatelessWidget {
  const _HealthCard({
    required this.health,
    required this.lastScan,
    required this.diskPercent,
    required this.cleanableBytes,
  });

  final String health;
  final String lastScan;
  final double diskPercent;
  final int cleanableBytes;

  @override
  Widget build(BuildContext context) {
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
                  child: Icon(Icons.shield_outlined,
                      color: AppColors.primary, size: 40),
                ),
                const SizedBox(width: 22),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(health,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.w900,
                              color: AppColors.primaryDark)),
                      Text(lastScan,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: AppColors.muted)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 36),
            _HealthLine(
                label: '系统盘占用',
                value: '${diskPercent.round()}%',
                percent: (diskPercent / 100).clamp(0.0, 1.0).toDouble()),
            const SizedBox(height: 26),
            _HealthLine(
                label: '可清理空间',
                value:
                    cleanableBytes == 0 ? '待扫描' : _formatBytes(cleanableBytes),
                percent: cleanablePercent),
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
              color: dark ? AppColors.text : AppColors.primaryDark),
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
          ),
        ),
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('${percent.round()}%',
                style: const TextStyle(
                    fontSize: 52,
                    fontWeight: FontWeight.w900,
                    color: AppColors.primaryDark)),
            const Text('占用率',
                style: TextStyle(
                    color: AppColors.muted, fontWeight: FontWeight.w700)),
          ],
        ),
      ],
    );
  }
}

class _HealthLine extends StatelessWidget {
  const _HealthLine(
      {required this.label, required this.value, required this.percent});

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
            borderRadius: BorderRadius.circular(4)),
      ],
    );
  }
}

class _ToolSummary extends StatelessWidget {
  const _ToolSummary(
      {required this.icon, required this.title, required this.subtitle});

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        height: 182,
        child: Padding(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                    color: AppColors.paleBlue,
                    borderRadius: BorderRadius.circular(10)),
                child: Icon(icon, color: AppColors.text),
              ),
              const Spacer(),
              Text(title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 6),
              Text(subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: AppColors.muted, fontSize: 13)),
            ],
          ),
        ),
      ),
    );
  }
}

class _ToolSummaryGrid extends StatelessWidget {
  const _ToolSummaryGrid();

  static const _tools = [
    _ToolSummary(
        icon: Icons.block_outlined,
        title: '广告清理',
        subtitle: 'hosts 广告屏蔽已集成'),
    _ToolSummary(
        icon: Icons.copy_outlined,
        title: '重复文件',
        subtitle: 'SHA-256 重复识别已集成'),
    _ToolSummary(
        icon: Icons.sd_storage_outlined,
        title: '超大文件',
        subtitle: '目录大文件扫描已集成'),
    _ToolSummary(
        icon: Icons.grid_view_outlined,
        title: '碎片整理',
        subtitle: 'Windows defrag 已集成'),
  ];

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const gap = 24.0;
        final columns = constraints.maxWidth < 720
            ? 1
            : constraints.maxWidth < 1050
                ? 2
                : 4;
        final tileWidth =
            (constraints.maxWidth - gap * (columns - 1)) / columns;

        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: [
            for (final tool in _tools) SizedBox(width: tileWidth, child: tool),
          ],
        );
      },
    );
  }
}

class _TrendCard extends StatelessWidget {
  const _TrendCard({required this.values});

  final List<int> values;

  @override
  Widget build(BuildContext context) {
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
              child: values.isEmpty
                  ? const Center(
                      child: Text('暂无扫描记录',
                          style: TextStyle(color: AppColors.muted)))
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
                                  Text(_formatBytes(values[i]),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                          color: AppColors.muted,
                                          fontSize: 11)),
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
                                                    top: Radius.circular(3)),
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
                                          color: AppColors.muted)),
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
  const _ActivityCard({required this.message, required this.result});

  final String message;
  final CleanupScanResult? result;

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
            _Activity(
              icon: result == null ? Icons.info_outline : Icons.done_all,
              color: result == null
                  ? const Color(0xFFDDEBFF)
                  : const Color(0xFFD8FBE4),
              title: message,
              subtitle: result == null
                  ? '点击一键开始扫描'
                  : '${result!.itemCount} 个项目 · ${_formatClock(result!.completedAt)}',
            ),
          ],
        ),
      ),
    );
  }
}

class _Activity extends StatelessWidget {
  const _Activity(
      {required this.icon,
      required this.color,
      required this.title,
      required this.subtitle});

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        CircleAvatar(
            radius: 21,
            backgroundColor: color,
            child: Icon(icon, color: AppColors.primary, size: 22)),
        const SizedBox(width: 18),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, color: AppColors.text)),
              const SizedBox(height: 3),
              Text(subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: AppColors.muted, fontSize: 12)),
            ],
          ),
        ),
      ],
    );
  }
}

class _ReportDialog extends StatelessWidget {
  const _ReportDialog({required this.result});

  final CleanupScanResult? result;

  @override
  Widget build(BuildContext context) {
    final scanResult = result;
    return AlertDialog(
      title: const Text('扫描详细报告'),
      content: SizedBox(
        width: 720,
        child: scanResult == null
            ? const Text('尚未执行扫描', style: TextStyle(color: AppColors.muted))
            : Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('完成时间: ${_formatClock(scanResult.completedAt)}'),
                  const SizedBox(height: 8),
                  Text('项目数量: ${scanResult.itemCount}'),
                  const SizedBox(height: 8),
                  Text('可清理: ${_formatBytes(scanResult.totalBytes)}'),
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
                          title: Text(category.name,
                              style:
                                  const TextStyle(fontWeight: FontWeight.w800)),
                          subtitle: Text(
                              '${category.description}\n扫描路径 ${category.scannedPathCount} 个${category.errors.isEmpty ? '' : ' · 错误 ${category.errors.length} 个'}'),
                          trailing: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(_formatBytes(category.totalBytes),
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w900)),
                              Text('${category.itemCount} 项',
                                  style: const TextStyle(
                                      color: AppColors.muted, fontSize: 12)),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭')),
      ],
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

String _formatClock(DateTime value) {
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${twoDigits(value.hour)}:${twoDigits(value.minute)}';
}
