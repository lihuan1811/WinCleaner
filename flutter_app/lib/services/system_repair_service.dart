import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;

typedef SystemRepairProcessRunner = Future<ProcessResult> Function(
  String executable,
  List<String> arguments,
);

enum RepairRisk {
  safe('安全', '日常维护可执行'),
  caution('谨慎', '可能耗时较长或需要重启');

  const RepairRisk(this.label, this.description);

  final String label;
  final String description;
}

class SystemRepairAction {
  const SystemRepairAction({
    required this.id,
    required this.name,
    required this.description,
    required this.command,
    required this.risk,
    this.recommended = false,
    this.deep = false,
  });

  final String id;
  final String name;
  final String description;
  final String command;
  final RepairRisk risk;
  final bool recommended;
  final bool deep;
}

class SystemRepairResult {
  const SystemRepairResult({
    required this.action,
    required this.exitCode,
    required this.output,
    required this.unsupported,
  });

  final SystemRepairAction action;
  final int exitCode;
  final String output;
  final bool unsupported;

  bool get success => !unsupported && exitCode == 0;
}

class SystemRepairService {
  const SystemRepairService({
    bool? isWindowsOverride,
    SystemRepairProcessRunner? processRunner,
  })  : _isWindowsOverride = isWindowsOverride,
        _processRunner = processRunner ?? Process.run;

  final bool? _isWindowsOverride;
  final SystemRepairProcessRunner _processRunner;

  bool get _isWindows => _isWindowsOverride ?? (!kIsWeb && Platform.isWindows);

  Future<SystemRepairResult> runAction(SystemRepairAction action) async {
    if (!_isWindows) {
      return SystemRepairResult(
        action: action,
        exitCode: -1,
        output: '该修复命令仅支持 Windows。',
        unsupported: true,
      );
    }

    final result = await _processRunner('cmd', ['/C', action.command]);
    final output = [
      if (result.stdout.toString().trim().isNotEmpty)
        result.stdout.toString().trim(),
      if (result.stderr.toString().trim().isNotEmpty)
        result.stderr.toString().trim(),
    ].join('\n');
    return SystemRepairResult(
      action: action,
      exitCode: result.exitCode,
      output: output.isEmpty ? '命令无输出' : output,
      unsupported: false,
    );
  }

  static List<SystemRepairAction> recommendedPreset() {
    return defaultActions().where((action) => action.recommended).toList();
  }

  static List<SystemRepairAction> deepPreset() {
    return defaultActions()
        .where((action) => action.recommended || action.deep)
        .toList();
  }

  static List<SystemRepairAction> defaultActions() {
    return const [
      SystemRepairAction(
        id: 'sfc_scan',
        name: 'SFC 系统文件修复',
        description: '使用微软 sfc /scannow 检查并修复受保护系统文件。',
        command: 'sfc /scannow',
        risk: RepairRisk.safe,
        recommended: true,
      ),
      SystemRepairAction(
        id: 'chkdsk_scan',
        name: 'CHKDSK 磁盘安全扫描',
        description: '扫描 C 盘文件系统错误，不强制修复，不要求立即重启。',
        command: 'chkdsk C: /scan',
        risk: RepairRisk.safe,
        recommended: true,
      ),
      SystemRepairAction(
        id: 'flush_dns',
        name: 'DNS 刷新',
        description: '清空本机 DNS 解析缓存，适合网页打不开或解析异常。',
        command: 'ipconfig /flushdns',
        risk: RepairRisk.safe,
        recommended: true,
      ),
      SystemRepairAction(
        id: 'winsock_reset',
        name: 'Winsock 网络重置',
        description: '重置 Windows 网络套接字目录，通常需要重启后完全生效。',
        command: 'netsh winsock reset',
        risk: RepairRisk.safe,
        recommended: true,
      ),
      SystemRepairAction(
        id: 'dism_restore_health',
        name: 'DISM 系统镜像修复',
        description: '使用 DISM 在线修复系统组件仓库，耗时较长。',
        command: 'DISM /Online /Cleanup-Image /RestoreHealth',
        risk: RepairRisk.caution,
        deep: true,
      ),
      SystemRepairAction(
        id: 'chkdsk_deep',
        name: '磁盘错误深度修复',
        description: '安排 C 盘深度修复，可能提示下次重启执行。',
        command: 'echo Y|chkdsk C: /F /R',
        risk: RepairRisk.caution,
        deep: true,
      ),
      SystemRepairAction(
        id: 'windows_update_reset',
        name: '系统更新组件修复',
        description: '停止更新服务并重建 SoftwareDistribution 与 catroot2 缓存。',
        command:
            'net stop wuauserv & net stop bits & net stop cryptsvc & ren %systemroot%\\SoftwareDistribution SoftwareDistribution.old & ren %systemroot%\\System32\\catroot2 catroot2.old & net start cryptsvc & net start bits & net start wuauserv',
        risk: RepairRisk.caution,
        deep: true,
      ),
      SystemRepairAction(
        id: 'cache_reset',
        name: '缓存重置修复',
        description: '重置微软商店缓存，适合商店应用打开异常。',
        command: 'wsreset.exe',
        risk: RepairRisk.caution,
        deep: true,
      ),
    ];
  }
}
