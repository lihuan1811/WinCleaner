import 'dart:convert';
import 'dart:io';

typedef AppDataProcessRunner = Future<ProcessResult> Function(
  String executable,
  List<String> arguments,
);

class AppDataScanSource {
  const AppDataScanSource({
    required this.label,
    required this.path,
    required this.targetSubdir,
    this.enabled = true,
  });

  final String label;
  final String path;
  final String targetSubdir;
  final bool enabled;
}

class AppDataMigrationFolder {
  const AppDataMigrationFolder({
    required this.path,
    required this.name,
    required this.sizeBytes,
    required this.sourceLabel,
    required this.targetSubdir,
    required this.parentTotalBytes,
  });

  final String path;
  final String name;
  final int sizeBytes;
  final String sourceLabel;
  final String targetSubdir;
  final int parentTotalBytes;
}

class AppDataMigrationScanResult {
  const AppDataMigrationScanResult({
    required this.folders,
    required this.scannedCount,
    required this.errors,
  });

  final List<AppDataMigrationFolder> folders;
  final int scannedCount;
  final List<String> errors;

  int get totalBytes =>
      folders.fold(0, (total, folder) => total + folder.sizeBytes);
}

class AppDataMigrationRecord {
  const AppDataMigrationRecord({
    required this.id,
    required this.name,
    required this.sourcePath,
    required this.targetPath,
    required this.sizeBytes,
    required this.createdAtMillis,
    required this.batchId,
  });

  final String id;
  final String name;
  final String sourcePath;
  final String targetPath;
  final int sizeBytes;
  final int createdAtMillis;
  final String batchId;

  Map<String, Object?> toJson() => {
        'id': id,
        'name': name,
        'sourcePath': sourcePath,
        'targetPath': targetPath,
        'sizeBytes': sizeBytes,
        'createdAtMillis': createdAtMillis,
        'batchId': batchId,
      };

  static AppDataMigrationRecord fromJson(Map<String, Object?> json) {
    return AppDataMigrationRecord(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      sourcePath: json['sourcePath']?.toString() ?? '',
      targetPath: json['targetPath']?.toString() ?? '',
      sizeBytes: _parseInt(json['sizeBytes']),
      createdAtMillis: _parseInt(json['createdAtMillis']),
      batchId: json['batchId']?.toString() ?? '',
    );
  }
}

class AppDataMigrationOperationResult {
  const AppDataMigrationOperationResult({
    required this.success,
    required this.output,
    this.unsupported = false,
    this.record,
  });

  final bool success;
  final String output;
  final bool unsupported;
  final AppDataMigrationRecord? record;
}

class AppDataMigrationService {
  AppDataMigrationService({
    bool? isWindowsOverride,
    File? historyFile,
    AppDataProcessRunner? processRunner,
  })  : _isWindowsOverride = isWindowsOverride,
        _historyFile = historyFile,
        _processRunner = processRunner ?? Process.run;

  final bool? _isWindowsOverride;
  final File? _historyFile;
  final AppDataProcessRunner _processRunner;

  bool get _isWindows => _isWindowsOverride ?? Platform.isWindows;

  Future<AppDataMigrationScanResult> scanLargeFolders(
    List<AppDataScanSource> sources, {
    double minParentRatio = 0.10,
  }) async {
    final folders = <AppDataMigrationFolder>[];
    final errors = <String>[];
    var scannedCount = 0;

    for (final source in sources.where((source) => source.enabled)) {
      final root = Directory(source.path.trim());
      if (!await root.exists()) {
        continue;
      }

      final children = <Directory>[];
      try {
        await for (final entity in root.list(followLinks: false)) {
          if (entity is! Directory) {
            continue;
          }
          if (await FileSystemEntity.isLink(entity.path)) {
            continue;
          }
          children.add(entity);
        }
      } on FileSystemException catch (error) {
        errors.add('${root.path}: ${error.message}');
        continue;
      }

      final sizedChildren = <({Directory directory, int size})>[];
      var parentTotal = 0;
      for (final child in children) {
        scannedCount++;
        try {
          final size = await _directorySize(child);
          sizedChildren.add((directory: child, size: size));
          parentTotal += size;
        } on FileSystemException catch (error) {
          errors.add('${child.path}: ${error.message}');
        }
      }

      if (parentTotal <= 0) {
        continue;
      }

      final threshold = parentTotal * minParentRatio;
      for (final item in sizedChildren) {
        if (item.size <= threshold) {
          continue;
        }
        folders.add(
          AppDataMigrationFolder(
            path: item.directory.path,
            name: _baseName(item.directory.path),
            sizeBytes: item.size,
            sourceLabel: source.label,
            targetSubdir: source.targetSubdir,
            parentTotalBytes: parentTotal,
          ),
        );
      }
    }

    folders.sort((a, b) => b.sizeBytes.compareTo(a.sizeBytes));
    return AppDataMigrationScanResult(
      folders: folders,
      scannedCount: scannedCount,
      errors: errors,
    );
  }

  Future<AppDataMigrationOperationResult> migrateFolder(
    AppDataMigrationFolder folder,
    String targetBase, {
    String? batchId,
  }) async {
    final source = Directory(folder.path);
    if (!await source.exists()) {
      return AppDataMigrationOperationResult(
        success: false,
        output: '源目录不存在：${folder.path}',
      );
    }

    final targetParent = computeTargetParent(targetBase, folder.path);
    final targetPath = _joinPath(targetParent, [_baseName(folder.path)]);
    final target = Directory(targetPath);
    final targetParentDirectory = Directory(targetParent);
    await targetParentDirectory.create(recursive: true);

    if (await target.exists()) {
      return AppDataMigrationOperationResult(
        success: false,
        output: '目标目录已存在：$targetPath',
      );
    }

    final id = DateTime.now().microsecondsSinceEpoch.toString();
    final effectiveBatchId = batchId ?? id;
    final moved = await _moveSourceToTarget(source, target);
    if (!moved.success) {
      return moved;
    }
    final backupPath =
        moved.output.contains('.wincleaner_bak_') ? moved.output : null;

    final linked = await _createJunction(source.path, target.path);
    if (!linked.success) {
      await _tryMoveBack(target, source);
      if (backupPath != null && await source.exists()) {
        await _deleteIfExists(Directory(backupPath));
      }
      return linked;
    }
    if (backupPath != null) {
      await _deleteIfExists(Directory(backupPath));
    }

    final record = AppDataMigrationRecord(
      id: id,
      name: folder.name,
      sourcePath: source.path,
      targetPath: target.path,
      sizeBytes: await _directorySize(target),
      createdAtMillis: DateTime.now().millisecondsSinceEpoch,
      batchId: effectiveBatchId,
    );
    _addHistoryRecord(record);

    return AppDataMigrationOperationResult(
      success: true,
      output: linked.output,
      record: record,
    );
  }

  Future<AppDataMigrationOperationResult> restoreMigration(
    AppDataMigrationRecord record,
  ) async {
    final source = Directory(record.sourcePath);
    final target = Directory(record.targetPath);
    if (!await target.exists()) {
      return AppDataMigrationOperationResult(
        success: false,
        output: '目标目录不存在，无法还原：${record.targetPath}',
      );
    }

    if (await source.exists()) {
      if (await FileSystemEntity.isLink(source.path)) {
        await source.delete();
      } else {
        return AppDataMigrationOperationResult(
          success: false,
          output: '原路径存在非链接目录，为保护数据已取消：${source.path}',
        );
      }
    }

    final sourceParent = source.parent;
    if (!await sourceParent.exists()) {
      await sourceParent.create(recursive: true);
    }

    try {
      await target.rename(source.path);
    } on FileSystemException {
      final partialRestore = Directory('${source.path}.partial_restore');
      if (await partialRestore.exists()) {
        await partialRestore.delete(recursive: true);
      }
      await _copyDirectory(target, partialRestore);
      await partialRestore.rename(source.path);
      await target.delete(recursive: true);
    }

    _removeHistoryRecord(record.id);
    return const AppDataMigrationOperationResult(
      success: true,
      output: '已还原到原路径。',
    );
  }

  List<AppDataMigrationRecord> loadHistory() {
    final file = _resolvedHistoryFile();
    if (!file.existsSync()) {
      return const [];
    }

    try {
      final decoded = jsonDecode(file.readAsStringSync());
      final rows = decoded is List ? decoded : const [];
      return rows
          .whereType<Map>()
          .map((row) => AppDataMigrationRecord.fromJson(
                row.cast<String, Object?>(),
              ))
          .where((record) => record.id.isNotEmpty)
          .toList();
    } on FormatException {
      return const [];
    } on FileSystemException {
      return const [];
    }
  }

  void saveHistory(List<AppDataMigrationRecord> records) {
    final file = _resolvedHistoryFile();
    file.parent.createSync(recursive: true);
    file.writeAsStringSync(
      const JsonEncoder.withIndent('  ')
          .convert(records.map((record) => record.toJson()).toList()),
    );
  }

  void _addHistoryRecord(AppDataMigrationRecord record) {
    final records = loadHistory();
    saveHistory([...records, record]);
  }

  void _removeHistoryRecord(String id) {
    final records = loadHistory().where((record) => record.id != id).toList();
    saveHistory(records);
  }

  File _resolvedHistoryFile() {
    final injected = _historyFile;
    if (injected != null) {
      return injected;
    }

    final localAppData = Platform.environment['LOCALAPPDATA'];
    if (localAppData != null && localAppData.trim().isNotEmpty) {
      return File(_joinPath(localAppData, [
        'WinCleaner',
        'appdata_migration_history.json',
      ]));
    }

    return File(_joinPath(Directory.systemTemp.path, [
      'WinCleaner',
      'appdata_migration_history.json',
    ]));
  }

  Future<AppDataMigrationOperationResult> _moveSourceToTarget(
    Directory source,
    Directory target,
  ) async {
    try {
      await source.rename(target.path);
      return const AppDataMigrationOperationResult(
        success: true,
        output: '目录移动完成。',
      );
    } on FileSystemException {
      final partial = Directory('${target.path}.partial');
      if (await partial.exists()) {
        await partial.delete(recursive: true);
      }
      try {
        await _copyDirectory(source, partial);
        await partial.rename(target.path);
      } on FileSystemException catch (error) {
        if (await partial.exists()) {
          await partial.delete(recursive: true);
        }
        return AppDataMigrationOperationResult(
          success: false,
          output: '复制目录失败：${error.message}',
        );
      }

      final backup = Directory(
        '${source.path}.wincleaner_bak_${DateTime.now().millisecondsSinceEpoch}',
      );
      try {
        await source.rename(backup.path);
      } on FileSystemException catch (error) {
        await _deleteIfExists(target);
        return AppDataMigrationOperationResult(
          success: false,
          output: '备份源目录失败：${error.message}',
        );
      }

      return AppDataMigrationOperationResult(
        success: true,
        output: backup.path,
      );
    }
  }

  Future<AppDataMigrationOperationResult> _createJunction(
    String link,
    String target,
  ) async {
    if (!_isWindows) {
      return const AppDataMigrationOperationResult(
        success: false,
        unsupported: true,
        output: '创建 Junction 仅支持 Windows，请在 Windows 上以管理员身份运行。',
      );
    }

    final result = await _processRunner('cmd', [
      '/C',
      'mklink',
      '/J',
      link,
      target,
    ]);
    final output = [
      if (result.stdout.toString().trim().isNotEmpty)
        result.stdout.toString().trim(),
      if (result.stderr.toString().trim().isNotEmpty)
        result.stderr.toString().trim(),
    ].join('\n');

    return AppDataMigrationOperationResult(
      success: result.exitCode == 0,
      output: output.isEmpty ? 'mklink 无输出' : output,
    );
  }

  static List<AppDataScanSource> defaultScanSources({
    Map<String, String>? environment,
  }) {
    final env = environment ?? Platform.environment;
    return [
      if ((env['LOCALAPPDATA'] ?? '').trim().isNotEmpty)
        AppDataScanSource(
          label: 'LocalAppData',
          path: env['LOCALAPPDATA']!,
          targetSubdir: 'Local',
        ),
      if ((env['APPDATA'] ?? '').trim().isNotEmpty)
        AppDataScanSource(
          label: 'RoamingAppData',
          path: env['APPDATA']!,
          targetSubdir: 'Roaming',
        ),
      if ((env['ProgramFiles'] ?? '').trim().isNotEmpty)
        AppDataScanSource(
          label: 'Program Files',
          path: env['ProgramFiles']!,
          targetSubdir: 'Program Files',
        ),
      if ((env['ProgramFiles(x86)'] ?? '').trim().isNotEmpty)
        AppDataScanSource(
          label: 'Program Files (x86)',
          path: env['ProgramFiles(x86)']!,
          targetSubdir: 'Program Files (x86)',
        ),
      if ((env['ProgramData'] ?? '').trim().isNotEmpty)
        AppDataScanSource(
          label: 'ProgramData',
          path: env['ProgramData']!,
          targetSubdir: 'ProgramData',
        ),
    ];
  }

  static String defaultTargetRoot({Map<String, String>? environment}) {
    final env = environment ?? Platform.environment;
    final systemDrive = env['SystemDrive'] ?? 'C:';
    final fallbackDrive =
        systemDrive.toUpperCase().startsWith('D') ? r'E:\' : r'D:\';
    return _joinPath(fallbackDrive, ['Yugongyipan']);
  }

  static String computeTargetParent(String baseTarget, String sourceFolder) {
    final sourceParent = _parentPath(sourceFolder);
    final relativeParts = _splitPath(sourceParent).where((part) {
      if (part.isEmpty) {
        return false;
      }
      if (RegExp(r'^[A-Za-z]:$').hasMatch(part)) {
        return false;
      }
      return true;
    }).toList();
    return _joinPath(baseTarget, relativeParts);
  }

  Future<void> _copyDirectory(Directory source, Directory destination) async {
    await destination.create(recursive: true);
    await for (final entity
        in source.list(recursive: false, followLinks: false)) {
      final name = _baseName(entity.path);
      final targetPath = _joinPath(destination.path, [name]);
      if (entity is Directory) {
        await _copyDirectory(entity, Directory(targetPath));
      } else if (entity is File) {
        await File(entity.path).copy(targetPath);
      }
    }
  }

  Future<void> _tryMoveBack(Directory target, Directory source) async {
    try {
      if (await target.exists() && !await source.exists()) {
        await target.rename(source.path);
      }
    } on FileSystemException {
      // Best-effort rollback. The caller receives the original mklink failure.
    }
  }

  static Future<void> _deleteIfExists(Directory directory) async {
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  }

  static Future<int> _directorySize(Directory directory) async {
    var total = 0;
    await for (final entity
        in directory.list(recursive: true, followLinks: false)) {
      if (entity is! File) {
        continue;
      }
      try {
        final stat = await entity.stat();
        total += stat.size;
      } on FileSystemException {
        continue;
      }
    }
    return total;
  }

  static String _baseName(String path) {
    final normalized = path.replaceAll(RegExp(r'[\\/]+$'), '');
    final parts = _splitPath(normalized);
    return parts.isEmpty ? normalized : parts.last;
  }

  static String _parentPath(String path) {
    final normalized = path.replaceAll(RegExp(r'[\\/]+$'), '');
    final index = normalized.lastIndexOf(RegExp(r'[\\/]'));
    if (index <= 0) {
      return '';
    }
    return normalized.substring(0, index);
  }

  static List<String> _splitPath(String path) {
    return path
        .split(RegExp(r'[\\/]'))
        .where((part) => part.isNotEmpty)
        .toList();
  }

  static String _joinPath(String root, Iterable<String> parts) {
    final separator = _preferredSeparator(root);
    var cleanedRoot = root.trim().replaceAll(RegExp(r'[\\/]+$'), '');
    if (cleanedRoot.isEmpty) {
      cleanedRoot = separator;
    }
    final cleanedParts = parts
        .map((part) => part.trim().replaceAll(RegExp(r'^[\\/]+|[\\/]+$'), ''))
        .where((part) => part.isNotEmpty)
        .toList();
    if (cleanedParts.isEmpty) {
      return cleanedRoot;
    }
    return '$cleanedRoot$separator${cleanedParts.join(separator)}';
  }

  static String _preferredSeparator(String path) {
    if (path.contains(r'\') || RegExp(r'^[A-Za-z]:').hasMatch(path)) {
      return r'\';
    }
    return Platform.pathSeparator;
  }
}

int _parseInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}
