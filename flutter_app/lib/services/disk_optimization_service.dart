import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;

class DiskOptimizationResult {
  const DiskOptimizationResult({
    required this.success,
    required this.exitCode,
    required this.output,
  });

  final bool success;
  final int exitCode;
  final String output;
}

class DiskOptimizationService {
  DiskOptimizationService({
    bool? isWindowsOverride,
    Future<ProcessResult> Function(String executable, List<String> arguments)?
        processRunner,
  })  : _isWindowsOverride = isWindowsOverride,
        _processRunner = processRunner ?? Process.run;

  final bool? _isWindowsOverride;
  final Future<ProcessResult> Function(
      String executable, List<String> arguments) _processRunner;

  bool get _isWindows => _isWindowsOverride ?? (!kIsWeb && Platform.isWindows);

  Future<DiskOptimizationResult> analyze(String drive) {
    return _runDefrag(_normalizeDrive(drive), const ['/A', '/U', '/V']);
  }

  Future<DiskOptimizationResult> optimize(String drive) {
    return _runDefrag(_normalizeDrive(drive), const ['/O', '/U', '/V']);
  }

  Future<DiskOptimizationResult> _runDefrag(
    String drive,
    List<String> arguments,
  ) async {
    if (!_isWindows) {
      throw UnsupportedError('磁盘优化仅支持 Windows');
    }

    final result = await _processRunner('defrag', [drive, ...arguments]);
    final output = [
      if (result.stdout.toString().trim().isNotEmpty)
        result.stdout.toString().trim(),
      if (result.stderr.toString().trim().isNotEmpty)
        result.stderr.toString().trim(),
    ].join('\n');

    return DiskOptimizationResult(
      success: result.exitCode == 0,
      exitCode: result.exitCode,
      output: output,
    );
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
