import 'dart:io';

class CleanupScanTarget {
  const CleanupScanTarget({
    required this.id,
    required this.name,
    required this.description,
    required this.paths,
  });

  final String id;
  final String name;
  final String description;
  final List<String> paths;
}

class CleanupCategoryResult {
  const CleanupCategoryResult({
    required this.id,
    required this.name,
    required this.description,
    required this.itemCount,
    required this.totalBytes,
    required this.scannedPathCount,
    required this.errors,
  });

  final String id;
  final String name;
  final String description;
  final int itemCount;
  final int totalBytes;
  final int scannedPathCount;
  final List<String> errors;
}

class CleanupScanResult {
  const CleanupScanResult({
    required this.startedAt,
    required this.completedAt,
    required this.categories,
  });

  final DateTime startedAt;
  final DateTime completedAt;
  final List<CleanupCategoryResult> categories;

  int get itemCount =>
      categories.fold(0, (total, category) => total + category.itemCount);

  int get totalBytes =>
      categories.fold(0, (total, category) => total + category.totalBytes);
}

class SystemCleanupScanService {
  SystemCleanupScanService({List<CleanupScanTarget>? targets})
      : _targets = targets;

  final List<CleanupScanTarget>? _targets;

  Future<CleanupScanResult> scan() async {
    final startedAt = DateTime.now();
    final categories = <CleanupCategoryResult>[];

    for (final target in _targets ?? defaultTargets()) {
      categories.add(await _scanTarget(target));
    }

    categories.sort((a, b) => b.totalBytes.compareTo(a.totalBytes));
    return CleanupScanResult(
      startedAt: startedAt,
      completedAt: DateTime.now(),
      categories: categories,
    );
  }

  Future<CleanupCategoryResult> _scanTarget(CleanupScanTarget target) async {
    var totalBytes = 0;
    var itemCount = 0;
    var scannedPathCount = 0;
    final errors = <String>[];

    for (final rawPath in target.paths) {
      final path = rawPath.trim();
      if (path.isEmpty) {
        continue;
      }

      final directory = Directory(path);
      if (!await directory.exists()) {
        continue;
      }

      scannedPathCount++;
      try {
        await for (final entity
            in directory.list(recursive: true, followLinks: false)) {
          if (entity is! File) {
            continue;
          }
          try {
            final stat = await entity.stat();
            totalBytes += stat.size;
            itemCount++;
          } on FileSystemException catch (error) {
            errors.add('${entity.path}: ${error.message}');
          }
        }
      } on FileSystemException catch (error) {
        errors.add('${directory.path}: ${error.message}');
      }
    }

    return CleanupCategoryResult(
      id: target.id,
      name: target.name,
      description: target.description,
      itemCount: itemCount,
      totalBytes: totalBytes,
      scannedPathCount: scannedPathCount,
      errors: errors,
    );
  }

  static List<CleanupScanTarget> defaultTargets({
    Map<String, String>? environment,
  }) {
    final env = environment ?? Platform.environment;
    final systemRoot = env['SystemRoot'] ?? r'C:\Windows';
    final userProfile = env['USERPROFILE'] ?? '';
    final localAppData = env['LOCALAPPDATA'] ?? '';
    final programData = env['ProgramData'] ?? r'C:\ProgramData';
    final temp = env['TEMP'] ?? env['TMP'] ?? '';

    return [
      CleanupScanTarget(
        id: 'temp',
        name: '临时文件',
        description: '系统和用户临时目录',
        paths: [
          temp,
          '$systemRoot\\Temp',
        ],
      ),
      const CleanupScanTarget(
        id: 'recycle',
        name: '回收站',
        description: '系统回收站内容',
        paths: [r'C:\$Recycle.Bin'],
      ),
      CleanupScanTarget(
        id: 'browser_cache',
        name: '浏览器缓存',
        description: 'Chrome、Edge、Firefox 缓存目录',
        paths: [
          '$localAppData\\Google\\Chrome\\User Data\\Default\\Cache',
          '$localAppData\\Microsoft\\Edge\\User Data\\Default\\Cache',
          '$localAppData\\Mozilla\\Firefox\\Profiles',
        ],
      ),
      CleanupScanTarget(
        id: 'logs',
        name: '系统日志',
        description: 'Windows 日志和诊断日志',
        paths: [
          '$systemRoot\\Logs',
          '$systemRoot\\System32\\LogFiles',
        ],
      ),
      CleanupScanTarget(
        id: 'updates',
        name: '更新缓存',
        description: 'Windows 更新下载缓存',
        paths: [
          '$systemRoot\\SoftwareDistribution\\Download',
        ],
      ),
      CleanupScanTarget(
        id: 'thumbnails',
        name: '缩略图缓存',
        description: '资源管理器缩略图数据库',
        paths: [
          '$localAppData\\Microsoft\\Windows\\Explorer',
        ],
      ),
      CleanupScanTarget(
        id: 'prefetch',
        name: '预读取缓存',
        description: 'Windows Prefetch 文件',
        paths: [
          '$systemRoot\\Prefetch',
        ],
      ),
      CleanupScanTarget(
        id: 'error_reports',
        name: '错误报告',
        description: 'Windows 错误报告缓存',
        paths: [
          '$programData\\Microsoft\\Windows\\WER',
          '$localAppData\\Microsoft\\Windows\\WER',
        ],
      ),
      CleanupScanTarget(
        id: 'delivery_optimization',
        name: '传递优化缓存',
        description: 'Windows Delivery Optimization 缓存',
        paths: [
          '$systemRoot\\ServiceProfiles\\NetworkService\\AppData\\Local\\Microsoft\\Windows\\DeliveryOptimization\\Cache',
        ],
      ),
      CleanupScanTarget(
        id: 'downloads',
        name: '下载目录',
        description: '当前用户下载目录',
        paths: [
          '$userProfile\\Downloads',
        ],
      ),
    ];
  }
}
