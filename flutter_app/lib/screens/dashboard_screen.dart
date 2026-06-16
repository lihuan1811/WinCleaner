import 'package:flutter/material.dart';
import 'dart:io';

import '../services/ad_block_service.dart';
import '../services/disk_optimization_service.dart';
import '../services/duplicate_files_service.dart';
import '../services/large_files_service.dart';
import '../theme/app_theme.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    this.adBlockService,
    this.duplicateFilesService,
    this.largeFilesService,
    this.diskOptimizationService,
  });

  final AdBlockService? adBlockService;
  final DuplicateFilesService? duplicateFilesService;
  final LargeFilesService? largeFilesService;
  final DiskOptimizationService? diskOptimizationService;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late final AdBlockService _adBlockService;
  late final DuplicateFilesService _duplicateFilesService;
  late final LargeFilesService _largeFilesService;
  late final DiskOptimizationService _diskOptimizationService;

  @override
  void initState() {
    super.initState();
    _adBlockService = widget.adBlockService ?? AdBlockService();
    _duplicateFilesService =
        widget.duplicateFilesService ?? DuplicateFilesService();
    _largeFilesService = widget.largeFilesService ?? LargeFilesService();
    _diskOptimizationService =
        widget.diskOptimizationService ?? DiskOptimizationService();
  }

  String get _defaultScanPath {
    final userProfile = Platform.environment['USERPROFILE'];
    if (Platform.isWindows && userProfile != null && userProfile.isNotEmpty) {
      return '$userProfile\\Downloads';
    }
    return Platform.environment['HOME'] ?? Directory.current.path;
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

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Expanded(flex: 2, child: _StorageCard()),
              const SizedBox(width: 32),
              Expanded(child: _HealthCard()),
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
                onPressed: () {},
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
              const Expanded(flex: 2, child: _TrendCard()),
              const SizedBox(width: 32),
              Expanded(child: _ActivityCard()),
            ],
          ),
        ],
      ),
    );
  }
}

class _StorageCard extends StatelessWidget {
  const _StorageCard();

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
                  Text(
                    '系统存储监控',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    '正在实时分析驱动器 C: 的健康状况',
                    style: TextStyle(color: AppColors.muted),
                  ),
                  const SizedBox(height: 34),
                  const Wrap(
                    spacing: 30,
                    runSpacing: 16,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      _Metric(label: '已用空间', value: '384.2 GB'),
                      SizedBox(
                        height: 52,
                        child: VerticalDivider(color: AppColors.border),
                      ),
                      _Metric(label: '剩余空间', value: '127.8 GB', dark: true),
                    ],
                  ),
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
                        onPressed: () {},
                        icon: const Icon(Icons.search),
                        label: const Text(
                          '一键开始扫描',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                      const SizedBox(width: 18),
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          fixedSize: const Size(150, 62),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        onPressed: () {},
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
            const SizedBox(
              width: 230,
              height: 230,
              child: _PercentRing(percent: .75),
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
    return Stack(
      alignment: Alignment.center,
      children: [
        SizedBox(
          width: 210,
          height: 210,
          child: CircularProgressIndicator(
            value: percent,
            strokeWidth: 22,
            backgroundColor: const Color(0xFFE5EBF4),
            color: AppColors.primary,
            strokeCap: StrokeCap.butt,
          ),
        ),
        const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '75%',
              style: TextStyle(
                fontSize: 52,
                fontWeight: FontWeight.w900,
                color: AppColors.primaryDark,
              ),
            ),
            Text(
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
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('系统健康状态', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 28),
            const Row(
              children: [
                CircleAvatar(
                  radius: 42,
                  backgroundColor: Color(0xFFE6ECF5),
                  child: Icon(
                    Icons.shield_outlined,
                    color: AppColors.primary,
                    size: 40,
                  ),
                ),
                SizedBox(width: 22),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '良好',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primaryDark,
                      ),
                    ),
                    Text(
                      '上次检查: 2小时前',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 36),
            const _HealthLine(label: '启动项', value: '12 个高能耗', percent: .45),
            const SizedBox(height: 26),
            const _HealthLine(
              label: '内存占用',
              value: '3.2 GB / 16 GB',
              percent: .2,
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
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: SizedBox(
          height: 170,
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: AppColors.paleBlue,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: AppColors.text),
                ),
                const Spacer(),
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  style: const TextStyle(color: AppColors.muted, fontSize: 13),
                ),
              ],
            ),
          ),
        ),
      ),
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

class _TrendCard extends StatelessWidget {
  const _TrendCard();

  @override
  Widget build(BuildContext context) {
    final values = [12, 20, 11, 28, 17, 23, 32];
    final labels = ['周一', '周二', '周三', '周四', '周五', '周六', '今天'];
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
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  for (var i = 0; i < values.length; i++)
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 5),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            Expanded(
                              child: Align(
                                alignment: Alignment.bottomCenter,
                                child: FractionallySizedBox(
                                  heightFactor: values[i] / 36,
                                  child: Container(
                                    decoration: BoxDecoration(
                                      color: i == values.length - 1
                                          ? AppColors.primaryDark
                                          : const Color(0xFFD8E4FF),
                                      borderRadius: const BorderRadius.vertical(
                                        top: Radius.circular(3),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(height: 14),
                            Text(
                              labels[i],
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
            const _Activity(
              icon: Icons.done_all,
              color: Color(0xFFD8FBE4),
              title: '成功清理 12.4 GB',
              subtitle: '35 分钟前 · 临时文件',
            ),
            const _Activity(
              icon: Icons.sync,
              color: Color(0xFFDDEBFF),
              title: '数据库更新完成',
              subtitle: '2 小时前 · 版本 v4.5.2',
            ),
            const _Activity(
              icon: Icons.warning_amber,
              color: Color(0xFFFFF1C7),
              title: '发现 5 个安全威胁',
              subtitle: '昨天 18:42 · 深度扫描',
            ),
          ],
        ),
      ),
    );
  }
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
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  color: AppColors.text,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: const TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
