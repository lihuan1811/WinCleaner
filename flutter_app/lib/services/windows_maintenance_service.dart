import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;

typedef MaintenanceProcessRunner = Future<ProcessResult> Function(
  String executable,
  List<String> arguments,
);

enum MaintenanceSchedule {
  daily('DAILY'),
  weekly('WEEKLY'),
  hourly('HOURLY'),
  minute('MINUTE'),
  logon('ONLOGON');

  const MaintenanceSchedule(this.schTasksValue);

  final String schTasksValue;
}

class MaintenanceResult {
  const MaintenanceResult({
    required this.exitCode,
    required this.output,
    required this.unsupported,
  });

  final int exitCode;
  final String output;
  final bool unsupported;

  bool get success => !unsupported && exitCode == 0;
}

class ShortcutIssue {
  const ShortcutIssue({
    required this.path,
    required this.targetPath,
    required this.reason,
  });

  final String path;
  final String targetPath;
  final String reason;
}

class MaintenanceRegistryEntry {
  const MaintenanceRegistryEntry({
    required this.path,
    required this.name,
    required this.kind,
    required this.detail,
  });

  final String path;
  final String name;
  final String kind;
  final String detail;
}

class WindowsMaintenanceService {
  WindowsMaintenanceService({
    bool? isWindowsOverride,
    MaintenanceProcessRunner? processRunner,
  })  : _isWindowsOverride = isWindowsOverride,
        _processRunner = processRunner ?? Process.run;

  final bool? _isWindowsOverride;
  final MaintenanceProcessRunner _processRunner;

  bool get _isWindows => _isWindowsOverride ?? (!kIsWeb && Platform.isWindows);

  Future<List<ShortcutIssue>> scanInvalidShortcuts(List<String> roots) async {
    if (!_isWindows) {
      return const [];
    }

    final escapedRoots = roots
        .where((root) => root.trim().isNotEmpty)
        .map((root) => "'${root.replaceAll("'", "''")}'")
        .join(',');
    if (escapedRoots.isEmpty) {
      return const [];
    }

    final script = '''
\$roots = @($escapedRoots)
\$shell = New-Object -ComObject WScript.Shell
\$rows = foreach (\$root in \$roots) {
  if (Test-Path -LiteralPath \$root) {
    Get-ChildItem -LiteralPath \$root -Filter *.lnk -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
      try {
        \$shortcut = \$shell.CreateShortcut(\$_.FullName)
        \$target = [string]\$shortcut.TargetPath
        if ([string]::IsNullOrWhiteSpace(\$target)) {
          [pscustomobject]@{ Path = \$_.FullName; TargetPath = ""; Reason = "没有目标" }
        } elseif (-not (Test-Path -LiteralPath \$target)) {
          [pscustomobject]@{ Path = \$_.FullName; TargetPath = \$target; Reason = "目标不存在" }
        }
      } catch {
        [pscustomobject]@{ Path = \$_.FullName; TargetPath = ""; Reason = \$_.Exception.Message }
      }
    }
  }
}
\$rows | ConvertTo-Json -Compress
''';

    final result = await _processRunner('powershell', [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-Command',
      script,
    ]);

    if (result.exitCode != 0) {
      throw ProcessException(
        'powershell',
        const [],
        result.stderr.toString(),
        result.exitCode,
      );
    }
    return parseInvalidShortcutRows(result.stdout.toString());
  }

  Future<List<MaintenanceRegistryEntry>> scanContextMenuEntries() async {
    if (!_isWindows) {
      return const [];
    }

    const roots = [
      r'HKCR\Directory\shell',
      r'HKCR\Directory\shellex\ContextMenuHandlers',
      r'HKCR\Folder\shell',
      r'HKCR\Folder\shellex\ContextMenuHandlers',
      r'HKCR\Drive\shell',
      r'HKCR\Drive\shellex\ContextMenuHandlers',
      r'HKCR\*\shell',
      r'HKCR\*\shellex\ContextMenuHandlers',
    ];

    final entries = <MaintenanceRegistryEntry>[];
    for (final root in roots) {
      final result = await _processRunner('reg', ['query', root]);
      if (result.exitCode == 0) {
        entries.addAll(parseContextMenuRegistry(result.stdout.toString()));
      }
    }
    return entries;
  }

  Future<List<MaintenanceRegistryEntry>> scanInvalidUninstallEntries() async {
    if (!_isWindows) {
      return const [];
    }

    const roots = [
      r'HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall',
      r'HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
      r'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall',
    ];

    final entries = <MaintenanceRegistryEntry>[];
    for (final root in roots) {
      final result = await _processRunner('reg', ['query', root, '/s']);
      if (result.exitCode == 0) {
        entries.addAll(parseUninstallRegistry(result.stdout.toString()));
      }
    }
    return entries;
  }

  Future<MaintenanceResult> deleteRegistryEntry(String registryPath) {
    return _run('reg', ['delete', registryPath, '/f']);
  }

  Future<MaintenanceResult> createScheduledCleanupTask({
    required String taskName,
    required String executablePath,
    required MaintenanceSchedule schedule,
    String time = '09:00',
    int interval = 1,
  }) {
    final normalizedName = _normalizeTaskName(taskName);
    final trigger = <String>[
      '/SC',
      schedule.schTasksValue,
      if (schedule != MaintenanceSchedule.logon) ...[
        '/MO',
        interval.clamp(1, 999).toString(),
        '/ST',
        _normalizeTime(time),
      ],
    ];

    return _run('schtasks', [
      '/Create',
      '/TN',
      normalizedName,
      '/TR',
      '"$executablePath"',
      ...trigger,
      '/RL',
      'HIGHEST',
      '/F',
    ]);
  }

  Future<MaintenanceResult> deleteScheduledTask(String taskName) {
    return _run(
        'schtasks', ['/Delete', '/TN', _normalizeTaskName(taskName), '/F']);
  }

  Future<MaintenanceResult> runScheduledTask(String taskName) {
    return _run('schtasks', ['/Run', '/TN', _normalizeTaskName(taskName)]);
  }

  Future<MaintenanceResult> _run(
      String executable, List<String> arguments) async {
    if (!_isWindows) {
      return const MaintenanceResult(
        exitCode: -1,
        output: '该功能仅支持 Windows。',
        unsupported: true,
      );
    }

    final result = await _processRunner(executable, arguments);
    final output = [
      if (result.stdout.toString().trim().isNotEmpty)
        result.stdout.toString().trim(),
      if (result.stderr.toString().trim().isNotEmpty)
        result.stderr.toString().trim(),
    ].join('\n');
    return MaintenanceResult(
      exitCode: result.exitCode,
      output: output.isEmpty ? '命令无输出' : output,
      unsupported: false,
    );
  }

  static List<ShortcutIssue> parseInvalidShortcutRows(String output) {
    final trimmed = output.trim();
    if (trimmed.isEmpty) {
      return const [];
    }

    final decoded = jsonDecode(trimmed);
    final rows = decoded is List ? decoded : [decoded];
    return rows
        .whereType<Map>()
        .map((row) {
          return ShortcutIssue(
            path: row['Path']?.toString() ?? '',
            targetPath: row['TargetPath']?.toString() ?? '',
            reason: row['Reason']?.toString() ?? '目标无效',
          );
        })
        .where((entry) => entry.path.isNotEmpty)
        .toList();
  }

  static List<MaintenanceRegistryEntry> parseContextMenuRegistry(
      String output) {
    final entries = <MaintenanceRegistryEntry>[];
    String? currentPath;
    var detail = '';

    void flush() {
      final path = currentPath;
      if (path == null || path.isEmpty) {
        return;
      }
      entries.add(
        MaintenanceRegistryEntry(
          path: path,
          name: path.split(r'\').last,
          kind: '右键菜单',
          detail: detail.trim().isEmpty ? '未读取到默认值' : detail.trim(),
        ),
      );
    }

    for (final rawLine in output.split(RegExp(r'\r?\n'))) {
      final line = rawLine.trimRight();
      if (line.startsWith('HKEY_')) {
        flush();
        currentPath = line.trim();
        detail = '';
        continue;
      }
      final trimmed = line.trim();
      if (trimmed.startsWith('(Default)') || trimmed.startsWith('@')) {
        detail = trimmed.replaceAll(RegExp(r'\s+'), ' ');
      }
    }
    flush();
    return entries;
  }

  static List<MaintenanceRegistryEntry> parseUninstallRegistry(String output) {
    final entries = <MaintenanceRegistryEntry>[];
    String? currentPath;
    var displayName = '';
    var installLocation = '';

    void flush() {
      final path = currentPath;
      if (path == null || displayName.trim().isEmpty) {
        return;
      }
      final location = installLocation.trim();
      if (location.isEmpty) {
        return;
      }
      if (!Directory(location).existsSync() && !File(location).existsSync()) {
        entries.add(
          MaintenanceRegistryEntry(
            path: path,
            name: displayName.trim(),
            kind: '卸载残留',
            detail: '原安装目录不存在: $location',
          ),
        );
      }
    }

    for (final rawLine in output.split(RegExp(r'\r?\n'))) {
      final line = rawLine.trimRight();
      if (line.startsWith('HKEY_')) {
        flush();
        currentPath = line.trim();
        displayName = '';
        installLocation = '';
        continue;
      }
      final trimmed = line.trim();
      if (trimmed.startsWith('DisplayName')) {
        displayName = _regValue(trimmed);
      } else if (trimmed.startsWith('InstallLocation')) {
        installLocation = _regValue(trimmed);
      }
    }
    flush();
    return entries;
  }

  static String _regValue(String line) {
    final parts = line.split(RegExp(r'\s{2,}'));
    return parts.length >= 3 ? parts.sublist(2).join(' ').trim() : '';
  }

  static String _normalizeTaskName(String taskName) {
    final clean = taskName.trim().replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
    return clean.startsWith(r'\WinCleaner_') ? clean : r'\WinCleaner_$clean';
  }

  static String _normalizeTime(String time) {
    final match = RegExp(r'^(\d{1,2}):(\d{1,2})$').firstMatch(time.trim());
    if (match == null) {
      return '09:00';
    }
    final hour = int.parse(match.group(1)!).clamp(0, 23);
    final minute = int.parse(match.group(2)!).clamp(0, 59);
    return '${hour.toString().padLeft(2, '0')}:'
        '${minute.toString().padLeft(2, '0')}';
  }
}
