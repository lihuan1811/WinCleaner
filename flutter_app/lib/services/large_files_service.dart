import 'dart:io';

class LargeFileEntry {
  const LargeFileEntry({
    required this.path,
    required this.name,
    required this.size,
    required this.modified,
  });

  final String path;
  final String name;
  final int size;
  final DateTime modified;
}

class LargeFileScanResult {
  const LargeFileScanResult({required this.files});

  final List<LargeFileEntry> files;

  int get totalBytes => files.fold(0, (total, file) => total + file.size);
}

class LargeFilesService {
  Future<LargeFileScanResult> scanDirectory(
    String rootPath, {
    int minBytes = 1024 * 1024 * 500,
    int limit = 100,
  }) async {
    final root = Directory(rootPath);
    if (!await root.exists()) {
      throw ArgumentError('目录不存在: $rootPath');
    }

    final files = <LargeFileEntry>[];
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File) {
        continue;
      }
      try {
        final stat = await entity.stat();
        if (stat.size < minBytes) {
          continue;
        }
        files.add(
          LargeFileEntry(
            path: entity.path,
            name: entity.uri.pathSegments.isEmpty
                ? entity.path
                : entity.uri.pathSegments.last,
            size: stat.size,
            modified: stat.modified,
          ),
        );
      } on FileSystemException {
        continue;
      }
    }

    files.sort((a, b) => b.size.compareTo(a.size));
    return LargeFileScanResult(files: files.take(limit).toList());
  }
}
