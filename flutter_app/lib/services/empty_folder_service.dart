import 'dart:io';

class EmptyFolderEntry {
  const EmptyFolderEntry({required this.path});

  final String path;
}

class EmptyFolderScanResult {
  const EmptyFolderScanResult({
    required this.rootPath,
    required this.folders,
    required this.scannedCount,
    required this.errors,
  });

  final String rootPath;
  final List<EmptyFolderEntry> folders;
  final int scannedCount;
  final List<String> errors;
}

class EmptyFolderDeleteResult {
  const EmptyFolderDeleteResult({
    required this.deletedCount,
    required this.skippedPaths,
    required this.errors,
  });

  final int deletedCount;
  final List<String> skippedPaths;
  final List<String> errors;
}

class EmptyFolderService {
  Future<EmptyFolderScanResult> scan(String rootPath) async {
    final root = Directory(rootPath.trim());
    if (!await root.exists()) {
      throw FileSystemException('目录不存在', root.path);
    }

    final directories = <Directory>[];
    final errors = <String>[];
    var scannedCount = 0;

    try {
      await for (final entity
          in root.list(recursive: true, followLinks: false)) {
        if (entity is Directory) {
          directories.add(entity);
          scannedCount++;
        }
      }
    } on FileSystemException catch (error) {
      errors.add('${root.path}: ${error.message}');
    }

    directories.sort((a, b) => b.path.length.compareTo(a.path.length));

    final empty = <EmptyFolderEntry>[];
    for (final directory in directories) {
      try {
        if (await _isDirectoryEmpty(directory)) {
          empty.add(EmptyFolderEntry(path: directory.path));
        }
      } on FileSystemException catch (error) {
        errors.add('${directory.path}: ${error.message}');
      }
    }

    return EmptyFolderScanResult(
      rootPath: root.path,
      folders: empty,
      scannedCount: scannedCount,
      errors: errors,
    );
  }

  Future<EmptyFolderDeleteResult> deleteFolders(
    List<EmptyFolderEntry> folders,
  ) async {
    var deletedCount = 0;
    final skipped = <String>[];
    final errors = <String>[];

    final sorted = [...folders]
      ..sort((a, b) => b.path.length.compareTo(a.path.length));

    for (final folder in sorted) {
      final directory = Directory(folder.path);
      if (!await directory.exists()) {
        skipped.add(folder.path);
        continue;
      }

      try {
        if (!await _isDirectoryEmpty(directory)) {
          skipped.add(folder.path);
          continue;
        }
        await directory.delete();
        deletedCount++;
      } on FileSystemException catch (error) {
        errors.add('${folder.path}: ${error.message}');
      }
    }

    return EmptyFolderDeleteResult(
      deletedCount: deletedCount,
      skippedPaths: skipped,
      errors: errors,
    );
  }

  Future<bool> _isDirectoryEmpty(Directory directory) async {
    await for (final _ in directory.list(followLinks: false)) {
      return false;
    }
    return true;
  }
}
