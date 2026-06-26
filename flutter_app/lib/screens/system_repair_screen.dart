import 'package:flutter/material.dart';

import '../services/system_repair_service.dart';
import '../theme/app_theme.dart';

class SystemRepairScreen extends StatefulWidget {
  const SystemRepairScreen({
    super.key,
    this.service = const SystemRepairService(),
  });

  final SystemRepairService service;

  @override
  State<SystemRepairScreen> createState() => _SystemRepairScreenState();
}

class _SystemRepairScreenState extends State<SystemRepairScreen> {
  final List<SystemRepairAction> _actions = SystemRepairService.defaultActions();
  final Set<String> _selectedIds = {};
  final List<SystemRepairResult> _results = [];
  bool _busy = false;
  String _status = '等待选择修复项目';

  void _selectPreset(List<SystemRepairAction> actions) {
    setState(() {
      _selectedIds
        ..clear()
        ..addAll(actions.map((action) => action.id));
      _status = '已选择 ${actions.length} 个修复项目';
    });
  }

  Future<void> _runSelected() async {
    final selected =
        _actions.where((action) => _selectedIds.contains(action.id)).toList();
    if (selected.isEmpty) {
      setState(() => _status = '请先勾选需要执行的修复项目');
      return;
    }

    if (selected.any((action) => action.risk == RepairRisk.caution)) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('确认执行深度修复'),
          content: const Text(
            '深度修复可能耗时较长，部分命令可能需要重启后生效。请确认已保存正在编辑的文件。',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('继续执行'),
            ),
          ],
        ),
      );
      if (confirmed != true) {
        return;
      }
    }

    setState(() {
      _busy = true;
      _results.clear();
      _status = '正在执行 ${selected.first.name}...';
    });

    for (final action in selected) {
      if (!mounted) {
        return;
      }
      setState(() => _status = '正在执行 ${action.name}...');
      final result = await widget.service.runAction(action);
      if (!mounted) {
        return;
      }
      setState(() => _results.add(result));
    }

    if (!mounted) {
      return;
    }
    setState(() {
      _busy = false;
      final successCount = _results.where((result) => result.success).length;
      _status = '执行完成 $successCount/${_results.length}';
    });
  }

  void _showCommand(SystemRepairAction action) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(action.name),
        content: SelectableText(action.command),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(32, 32, 32, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GlassPanel(
            width: double.infinity,
            padding: const EdgeInsets.all(28),
            child: Row(
              children: [
                const FeatureIcon(
                  icon: Icons.terminal_outlined,
                  size: 54,
                  iconSize: 24,
                  selected: true,
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'CMD 系统修复工具箱',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        '封装微软官方原生命令，支持推荐安全修复、深度系统修复和独立勾选执行。',
                        style: TextStyle(color: AppColors.muted, height: 1.5),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          GlassPanel(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 12,
                  runSpacing: 10,
                  children: [
                    FilledButton.icon(
                      onPressed: _busy
                          ? null
                          : () => _selectPreset(
                                SystemRepairService.recommendedPreset(),
                              ),
                      icon: const Icon(Icons.verified_outlined),
                      label: const Text('推荐安全修复'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _busy
                          ? null
                          : () => _selectPreset(
                                SystemRepairService.deepPreset(),
                              ),
                      icon: const Icon(Icons.build_circle_outlined),
                      label: const Text('深度系统修复'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _busy ? null : _runSelected,
                      icon: const Icon(Icons.play_arrow_outlined),
                      label: const Text('一键执行选中修复'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _results.isEmpty
                          ? null
                          : () => setState(() => _results.clear()),
                      icon: const Icon(Icons.history_outlined),
                      label: const Text('清空本次日志'),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                Text(_status, style: const TextStyle(color: AppColors.muted)),
                if (_busy) ...[
                  const SizedBox(height: 14),
                  const LinearProgressIndicator(minHeight: 4),
                ],
              ],
            ),
          ),
          const SizedBox(height: 24),
          GlassPanel(
            padding: const EdgeInsets.all(22),
            child: Column(
              children: [
                for (final action in _actions)
                  _RepairActionTile(
                    action: action,
                    selected: _selectedIds.contains(action.id),
                    busy: _busy,
                    onChanged: (selected) {
                      setState(() {
                        if (selected) {
                          _selectedIds.add(action.id);
                        } else {
                          _selectedIds.remove(action.id);
                        }
                      });
                    },
                    onShowCommand: () => _showCommand(action),
                    onRunSingle: _busy
                        ? null
                        : () async {
                            setState(() {
                              _busy = true;
                              _status = '正在执行 ${action.name}...';
                            });
                            final result =
                                await widget.service.runAction(action);
                            if (!mounted) {
                              return;
                            }
                            setState(() {
                              _busy = false;
                              _results.insert(0, result);
                              _status = result.success
                                  ? '${action.name} 执行完成'
                                  : '${action.name} 执行失败';
                            });
                          },
                  ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          _RepairResultPanel(results: _results),
        ],
      ),
    );
  }
}

class _RepairActionTile extends StatelessWidget {
  const _RepairActionTile({
    required this.action,
    required this.selected,
    required this.busy,
    required this.onChanged,
    required this.onShowCommand,
    required this.onRunSingle,
  });

  final SystemRepairAction action;
  final bool selected;
  final bool busy;
  final ValueChanged<bool> onChanged;
  final VoidCallback onShowCommand;
  final VoidCallback? onRunSingle;

  @override
  Widget build(BuildContext context) {
    final color = action.risk == RepairRisk.safe
        ? const Color(0xFF0F8A4B)
        : const Color(0xFFB7791F);
    return Tooltip(
      message:
          '${action.description}\n适用场景：${action.risk.description}\n风险等级：${action.risk.label}',
      waitDuration: const Duration(milliseconds: 350),
      child: ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Checkbox(
          value: selected,
          onChanged: busy ? null : (value) => onChanged(value ?? false),
        ),
        title: Text(
          action.name,
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        subtitle: Text(action.description, overflow: TextOverflow.ellipsis),
        trailing: Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Chip(
              visualDensity: VisualDensity.compact,
              avatar: Icon(
                action.risk == RepairRisk.safe
                    ? Icons.check_circle_outline
                    : Icons.warning_amber_outlined,
                color: color,
                size: 18,
              ),
              label: Text(action.risk.label),
              side: BorderSide(color: color.withValues(alpha: 0.35)),
            ),
            PopupMenuButton<String>(
              tooltip: '更多操作',
              onSelected: (value) {
                if (value == 'command') {
                  onShowCommand();
                }
                if (value == 'run') {
                  onRunSingle?.call();
                }
              },
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'command',
                  child: Text('查看底层命令'),
                ),
                PopupMenuItem(
                  value: 'run',
                  enabled: onRunSingle != null,
                  child: const Text('单独执行'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RepairResultPanel extends StatelessWidget {
  const _RepairResultPanel({required this.results});

  final List<SystemRepairResult> results;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('历史修复日志', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          if (results.isEmpty)
            const Text('暂无本次执行日志', style: TextStyle(color: AppColors.muted))
          else
            SizedBox(
              height: 240,
              child: ListView.separated(
                itemCount: results.length,
                separatorBuilder: (_, __) =>
                    const Divider(color: AppColors.border),
                itemBuilder: (context, index) {
                  final result = results[index];
                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      result.success
                          ? Icons.check_circle_outline
                          : Icons.error_outline,
                      color: result.success
                          ? const Color(0xFF0F8A4B)
                          : AppColors.warning,
                    ),
                    title: Text(result.action.name),
                    subtitle: SelectableText(
                      result.output,
                      maxLines: 3,
                    ),
                    trailing: Text('退出码 ${result.exitCode}'),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}
