import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;

class DriveStatus {
  const DriveStatus({
    required this.drive,
    required this.totalBytes,
    required this.freeBytes,
    required this.isSupported,
    required this.message,
  });

  final String drive;
  final int totalBytes;
  final int freeBytes;
  final bool isSupported;
  final String message;

  int get usedBytes => totalBytes - freeBytes;

  double get usagePercent {
    if (totalBytes <= 0) {
      return 0;
    }
    return (usedBytes / totalBytes) * 100;
  }

  String get healthLabel {
    if (!isSupported) {
      return '不可用';
    }
    if (usagePercent >= 90) {
      return '空间紧张';
    }
    if (usagePercent >= 80) {
      return '需要关注';
    }
    return '良好';
  }

  String get healthMessage {
    if (!isSupported) {
      return message;
    }
    if (usagePercent >= 90) {
      return '建议立即清理系统盘';
    }
    if (usagePercent >= 80) {
      return '建议扫描可清理项目';
    }
    return '系统盘空间状态正常';
  }
}

class DriveStatusService {
  DriveStatusService({
    bool? isWindowsOverride,
    Future<ProcessResult> Function(String executable, List<String> arguments)?
        processRunner,
  })  : _isWindowsOverride = isWindowsOverride,
        _processRunner = processRunner ?? Process.run;

  final bool? _isWindowsOverride;
  final Future<ProcessResult> Function(
      String executable, List<String> arguments) _processRunner;

  bool get _isWindows => _isWindowsOverride ?? (!kIsWeb && Platform.isWindows);

  Future<DriveStatus> loadDrive([String drive = 'C']) async {
    final normalizedDrive = _normalizeDrive(drive);
    if (!_isWindows) {
      return DriveStatus(
        drive: normalizedDrive,
        totalBytes: 0,
        freeBytes: 0,
        isSupported: false,
        message: '磁盘状态仅支持 Windows',
      );
    }

    final command =
        "Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='$normalizedDrive'\" "
        '| Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json -Compress';
    final result = await _processRunner('powershell', [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-Command',
      command,
    ]);

    if (result.exitCode != 0) {
      throw StateError(
        '读取磁盘状态失败: ${result.stderr.toString().trim()}',
      );
    }

    final rawOutput = result.stdout.toString().trim();
    if (rawOutput.isEmpty) {
      throw StateError('读取磁盘状态失败: 命令无输出');
    }

    final payload = jsonDecode(rawOutput);
    if (payload is! Map<String, dynamic>) {
      throw StateError('读取磁盘状态失败: 输出格式无效');
    }

    return DriveStatus(
      drive: (payload['DeviceID'] ?? normalizedDrive).toString(),
      totalBytes: _parseInt(payload['Size']),
      freeBytes: _parseInt(payload['FreeSpace']),
      isSupported: true,
      message: 'OK',
    );
  }

  static int _parseInt(Object? value) {
    if (value is int) {
      return value;
    }
    if (value is double) {
      return value.toInt();
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static String _normalizeDrive(String drive) {
    final value = drive.trim().toUpperCase().replaceAll('\\', '');
    final match = RegExp(r'^([A-Z]):?$').firstMatch(value);
    if (match == null) {
      throw ArgumentError('磁盘盘符无效: $drive');
    }
    return '${match.group(1)}:';
  }
}
