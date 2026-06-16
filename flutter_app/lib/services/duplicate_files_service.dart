import 'dart:io';

import 'package:crypto/crypto.dart';

class DuplicateFile {
  const DuplicateFile({
    required this.path,
    required this.name,
    required this.size,
  });

  final String path;
  final String name;
  final int size;
}

class DuplicateFileGroup {
  const DuplicateFileGroup({
    required this.hash,
    required this.size,
    required this.files,
  });

  final String hash;
  final int size;
  final List<DuplicateFile> files;

  int get wastedBytes => size * (files.length - 1);
}

class DuplicateScanResult {
  const DuplicateScanResult({required this.groups});

  final List<DuplicateFileGroup> groups;

  int get duplicateBytes =>
      groups.fold(0, (total, group) => total + group.wastedBytes);
}

class DuplicateDeleteResult {
  const DuplicateDeleteResult({
    required this.deletedCount,
    required this.freedBytes,
    required this.errors,
  });

  final int deletedCount;
  final int freedBytes;
  final List<String> errors;
}

class DuplicateFilesService {
  Future<DuplicateScanResult> scanDirectory(
    String rootPath, {
    int minBytes = 1024 * 1024,
  }) async {
    final root = Directory(rootPath);
    if (!await root.exists()) {
      throw ArgumentError('目录不存在: $rootPath');
    }

    final bySize = <int, List<File>>{};
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File) {
        continue;
      }
      try {
        final stat = await entity.stat();
        if (stat.size < minBytes) {
          continue;
        }
        bySize.putIfAbsent(stat.size, () => <File>[]).add(entity);
      } on FileSystemException {
        continue;
      }
    }

    final groups = <DuplicateFileGroup>[];
    for (final entry
        in bySize.entries.where((entry) => entry.value.length > 1)) {
      final byHash = <String, List<File>>{};
      for (final file in entry.value) {
        try {
          final digest = await sha256.bind(file.openRead()).first;
          byHash.putIfAbsent(digest.toString(), () => <File>[]).add(file);
        } on FileSystemException {
          continue;
        }
      }

      for (final hashEntry
          in byHash.entries.where((entry) => entry.value.length > 1)) {
        final files = [
          for (final file in hashEntry.value)
            DuplicateFile(
              path: file.path,
              name: file.uri.pathSegments.isEmpty
                  ? file.path
                  : file.uri.pathSegments.last,
              size: entry.key,
            ),
        ]..sort((a, b) => a.path.compareTo(b.path));

        groups.add(
          DuplicateFileGroup(
              hash: hashEntry.key, size: entry.key, files: files),
        );
      }
    }

    groups.sort((a, b) => b.wastedBytes.compareTo(a.wastedBytes));
    return DuplicateScanResult(groups: groups);
  }

  Future<DuplicateDeleteResult> deleteDuplicateCopies(
    List<DuplicateFileGroup> groups,
  ) async {
    var deletedCount = 0;
    var freedBytes = 0;
    final errors = <String>[];

    for (final group in groups) {
      for (final duplicate in group.files.skip(1)) {
        try {
          final file = File(duplicate.path);
          if (await file.exists()) {
            await file.delete();
            deletedCount++;
            freedBytes += duplicate.size;
          }
        } on FileSystemException catch (error) {
          errors.add('${duplicate.path}: ${error.message}');
        }
      }
    }

    return DuplicateDeleteResult(
      deletedCount: deletedCount,
      freedBytes: freedBytes,
      errors: errors,
    );
  }
}
