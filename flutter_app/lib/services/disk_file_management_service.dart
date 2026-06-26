import 'dart:io';

typedef DiskFileProcessRunner = Future<ProcessResult> Function(
  String executable,
  List<String> arguments,
);

enum ManagedFileType {
  all('全部'),
  video('视频'),
  image('图片'),
  installer('安装包'),
  archive('压缩包'),
  document('文档');

  const ManagedFileType(this.label);

  final String label;
}

class ManagedFileEntry {
  const ManagedFileEntry({
    required this.path,
    required this.name,
    required this.sizeBytes,
    required this.type,
  });

  final String path;
  final String name;
  final int sizeBytes;
  final ManagedFileType type;
}

class FolderUsageEntry {
  const FolderUsageEntry({required this.path, required this.sizeBytes});

  final String path;
  final int sizeBytes;
}

class FileOperationResult {
  const FileOperationResult({
    required this.affectedPaths,
    required this.errors,
    this.output = '',
    this.unsupported = false,
  });

  final List<String> affectedPaths;
  final List<String> errors;
  final String output;
  final bool unsupported;

  bool get success => !unsupported && errors.isEmpty;
}

class DiskFileManagementService {
  DiskFileManagementService({
    bool? isWindowsOverride,
    DiskFileProcessRunner? processRunner,
  })  : _isWindowsOverride = isWindowsOverride,
        _processRunner = processRunner ?? Process.run;

  final bool? _isWindowsOverride;
  final DiskFileProcessRunner _processRunner;

  bool get _isWindows => _isWindowsOverride ?? Platform.isWindows;

  Future<List<ManagedFileEntry>> listFiles(
    String rootPath, {
    ManagedFileType type = ManagedFileType.all,
    int limit = 500,
  }) async {
    final root = Directory(rootPath);
    if (!await root.exists()) {
      return const [];
    }

    final files = <ManagedFileEntry>[];
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File) {
        continue;
      }
      final detectedType = detectType(entity.path);
      if (type != ManagedFileType.all && detectedType != type) {
        continue;
      }
      try {
        final stat = await entity.stat();
        files.add(
          ManagedFileEntry(
            path: entity.path,
            name: _baseName(entity.path),
            sizeBytes: stat.size,
            type: detectedType,
          ),
        );
      } on FileSystemException {
        continue;
      }
      if (files.length >= limit) {
        break;
      }
    }
    files.sort((a, b) => b.sizeBytes.compareTo(a.sizeBytes));
    return files;
  }

  Future<List<FolderUsageEntry>> topFolders(
    String rootPath, {
    int limit = 20,
  }) async {
    final root = Directory(rootPath);
    if (!await root.exists()) {
      return const [];
    }

    final entries = <FolderUsageEntry>[];
    await for (final entity in root.list(followLinks: false)) {
      if (entity is! Directory) {
        continue;
      }
      try {
        entries.add(
          FolderUsageEntry(
            path: entity.path,
            sizeBytes: await _directorySize(entity),
          ),
        );
      } on FileSystemException {
        continue;
      }
    }
    entries.sort((a, b) => b.sizeBytes.compareTo(a.sizeBytes));
    return entries.take(limit).toList();
  }

  Future<FileOperationResult> copyFiles(
    List<String> paths,
    String targetDirectory,
  ) async {
    return _copyOrMove(paths, targetDirectory, move: false);
  }

  Future<FileOperationResult> moveFiles(
    List<String> paths,
    String targetDirectory,
  ) async {
    return _copyOrMove(paths, targetDirectory, move: true);
  }

  Future<FileOperationResult> renameFile(String path, String newName) async {
    final file = File(path);
    if (!await file.exists()) {
      return FileOperationResult(
        affectedPaths: const [],
        errors: ['文件不存在: $path'],
      );
    }
    final parent = file.parent.path;
    final renamed = '$parent${Platform.pathSeparator}$newName';
    await file.rename(renamed);
    return FileOperationResult(affectedPaths: [renamed], errors: const []);
  }

  Future<FileOperationResult> deleteFiles(List<String> paths) async {
    final affected = <String>[];
    final errors = <String>[];
    for (final path in paths) {
      try {
        final file = File(path);
        final directory = Directory(path);
        if (await file.exists()) {
          await file.delete();
          affected.add(path);
        } else if (await directory.exists()) {
          await directory.delete(recursive: true);
          affected.add(path);
        }
      } on FileSystemException catch (error) {
        errors.add('$path: ${error.message}');
      }
    }
    return FileOperationResult(affectedPaths: affected, errors: errors);
  }

  Future<FileOperationResult> shredFiles(List<String> paths) async {
    final affected = <String>[];
    final errors = <String>[];
    for (final path in paths) {
      final file = File(path);
      try {
        if (!await file.exists()) {
          continue;
        }
        final length = await file.length();
        final sink = file.openWrite(mode: FileMode.write);
        final block = List<int>.filled(8192, 0);
        var written = 0;
        while (written < length) {
          final count = (length - written).clamp(0, block.length).toInt();
          sink.add(block.take(count).toList());
          written += count;
        }
        await sink.close();
        await file.delete();
        affected.add(path);
      } on FileSystemException catch (error) {
        errors.add('$path: ${error.message}');
      }
    }
    return FileOperationResult(affectedPaths: affected, errors: errors);
  }

  Future<FileOperationResult> createShortcut(String target, String shortcut) {
    if (!_isWindows) {
      return Future.value(
        const FileOperationResult(
          affectedPaths: [],
          errors: [],
          output: '创建快捷方式仅支持 Windows。',
          unsupported: true,
        ),
      );
    }
    final script =
        r'$shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut("' +
            shortcut.replaceAll('"', r'\"') +
            r'"); $shortcut.TargetPath = "' +
            target.replaceAll('"', r'\"') +
            r'"; $shortcut.Save()';
    return _runPowerShell(script, affectedPath: shortcut);
  }

  Future<FileOperationResult> repairFolderPermission(String path) {
    if (!_isWindows) {
      return Future.value(
        const FileOperationResult(
          affectedPaths: [],
          errors: [],
          output: '文件夹权限修复仅支持 Windows。',
          unsupported: true,
        ),
      );
    }
    return _run(
        'icacls',
        [
          path,
          '/reset',
          '/T',
          '/C',
        ],
        affectedPath: path);
  }

  Future<FileOperationResult> migratePersonalFolder({
    required String folderKey,
    required String targetPath,
  }) {
    if (!_isWindows) {
      return Future.value(
        const FileOperationResult(
          affectedPaths: [],
          errors: [],
          output: '系统个人目录迁移仅支持 Windows。',
          unsupported: true,
        ),
      );
    }
    return _run(
        'reg',
        [
          'add',
          r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders',
          '/v',
          folderKey,
          '/t',
          'REG_EXPAND_SZ',
          '/d',
          targetPath,
          '/f',
        ],
        affectedPath: targetPath);
  }

  Future<FileOperationResult> migrateTemp(String targetPath) {
    if (!_isWindows) {
      return Future.value(
        const FileOperationResult(
          affectedPaths: [],
          errors: [],
          output: 'Temp 迁移仅支持 Windows。',
          unsupported: true,
        ),
      );
    }
    return _run(
        'cmd',
        [
          '/c',
          'setx TEMP "$targetPath" & setx TMP "$targetPath"',
        ],
        affectedPath: targetPath);
  }

  Future<FileOperationResult> _copyOrMove(
    List<String> paths,
    String targetDirectory, {
    required bool move,
  }) async {
    final target = Directory(targetDirectory);
    await target.create(recursive: true);
    final affected = <String>[];
    final errors = <String>[];

    for (final path in paths) {
      final file = File(path);
      try {
        if (!await file.exists()) {
          continue;
        }
        final targetPath =
            '${target.path}${Platform.pathSeparator}${_baseName(path)}';
        if (move) {
          await file.rename(targetPath);
        } else {
          await file.copy(targetPath);
        }
        affected.add(targetPath);
      } on FileSystemException catch (error) {
        errors.add('$path: ${error.message}');
      }
    }
    return FileOperationResult(affectedPaths: affected, errors: errors);
  }

  Future<FileOperationResult> _runPowerShell(
    String script, {
    required String affectedPath,
  }) {
    return _run(
        'powershell',
        [
          '-NoProfile',
          '-ExecutionPolicy',
          'Bypass',
          '-Command',
          script,
        ],
        affectedPath: affectedPath);
  }

  Future<FileOperationResult> _run(
    String executable,
    List<String> arguments, {
    required String affectedPath,
  }) async {
    final result = await _processRunner(executable, arguments);
    final output = [
      if (result.stdout.toString().trim().isNotEmpty)
        result.stdout.toString().trim(),
      if (result.stderr.toString().trim().isNotEmpty)
        result.stderr.toString().trim(),
    ].join('\n');
    return FileOperationResult(
      affectedPaths: result.exitCode == 0 ? [affectedPath] : const [],
      errors: result.exitCode == 0 ? const [] : [output],
      output: output.isEmpty ? '命令无输出' : output,
    );
  }

  static ManagedFileType detectType(String path) {
    final ext = path.split('.').last.toLowerCase();
    if (['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv'].contains(ext)) {
      return ManagedFileType.video;
    }
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic'].contains(ext)) {
      return ManagedFileType.image;
    }
    if (['exe', 'msi', 'msix', 'appx'].contains(ext)) {
      return ManagedFileType.installer;
    }
    if (['zip', 'rar', '7z', 'tar', 'gz', 'iso'].contains(ext)) {
      return ManagedFileType.archive;
    }
    if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'txt']
        .contains(ext)) {
      return ManagedFileType.document;
    }
    return ManagedFileType.all;
  }

  static Future<int> _directorySize(Directory directory) async {
    var total = 0;
    await for (final entity
        in directory.list(recursive: true, followLinks: false)) {
      if (entity is File) {
        total += await entity.length();
      }
    }
    return total;
  }

  static String _baseName(String path) {
    return path.split(RegExp(r'[\\/]')).last;
  }
}
