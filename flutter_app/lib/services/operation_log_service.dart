import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;

class OperationLogEntry {
  const OperationLogEntry({
    required this.timestamp,
    required this.module,
    required this.action,
    required this.detail,
  });

  final DateTime timestamp;
  final String module;
  final String action;
  final String detail;

  String toLine() =>
      '${timestamp.toIso8601String()}\t$module\t$action\t${detail.replaceAll('\n', ' ')}';

  static OperationLogEntry? fromLine(String line) {
    final parts = line.split('\t');
    if (parts.length < 4) {
      return null;
    }
    final timestamp = DateTime.tryParse(parts[0]);
    if (timestamp == null) {
      return null;
    }
    return OperationLogEntry(
      timestamp: timestamp,
      module: parts[1],
      action: parts[2],
      detail: parts.sublist(3).join('\t'),
    );
  }
}

class OperationLogService {
  OperationLogService({File? logFile}) : _logFile = logFile;

  final File? _logFile;

  Future<void> append(OperationLogEntry entry) async {
    if (kIsWeb) {
      return;
    }
    try {
      final file = _resolvedFile();
      await file.parent.create(recursive: true);
      await file.writeAsString('${entry.toLine()}\n', mode: FileMode.append);
    } on UnsupportedError {
      return;
    }
  }

  Future<List<OperationLogEntry>> read({int limit = 100}) async {
    if (kIsWeb) {
      return const [];
    }
    try {
      final file = _resolvedFile();
      if (!await file.exists()) {
        return const [];
      }
      final lines = await file.readAsLines();
      final entries = lines
          .map(OperationLogEntry.fromLine)
          .whereType<OperationLogEntry>()
          .toList();
      return entries.reversed.take(limit).toList();
    } on UnsupportedError {
      return const [];
    }
  }

  File _resolvedFile() {
    if (kIsWeb) {
      return File('/wincleaner-operation.log');
    }
    if (_logFile != null) {
      return _logFile;
    }
    try {
      final appData = Platform.environment['APPDATA'];
      if (Platform.isWindows && appData != null && appData.isNotEmpty) {
        return File('$appData\\WinCleaner\\operation.log');
      }
      final home = Platform.environment['HOME'];
      if (home != null && home.isNotEmpty) {
        return File('$home/.wincleaner/operation.log');
      }
      return File(
          '${Directory.systemTemp.path}${Platform.pathSeparator}wincleaner-operation.log');
    } on UnsupportedError {
      return File('/wincleaner-operation.log');
    }
  }
}
