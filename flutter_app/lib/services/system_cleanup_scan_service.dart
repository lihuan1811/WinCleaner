import 'dart:io';

class CleanupScanTarget {
  const CleanupScanTarget({
    required this.id,
    required this.name,
    required this.description,
    required this.paths,
    this.fileNamePatterns = const [],
    this.pathContains = const [],
    this.canClean = true,
  });

  final String id;
  final String name;
  final String description;
  final List<String> paths;
  final List<String> fileNamePatterns;
  final List<String> pathContains;
  final bool canClean;
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

class CleanupCleanResult {
  const CleanupCleanResult({
    required this.deletedCount,
    required this.freedBytes,
    required this.skippedCategories,
    required this.errors,
    required this.completedAt,
  });

  final int deletedCount;
  final int freedBytes;
  final List<String> skippedCategories;
  final List<String> errors;
  final DateTime completedAt;
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

  Future<CleanupCleanResult> clean() async {
    var deletedCount = 0;
    var freedBytes = 0;
    final skippedCategories = <String>[];
    final errors = <String>[];

    for (final target in _targets ?? defaultTargets()) {
      if (!target.canClean) {
        skippedCategories.add(target.name);
        continue;
      }

      for (final rawPath in target.paths) {
        final path = rawPath.trim();
        if (path.isEmpty) {
          continue;
        }

        final file = File(path);
        if (await file.exists()) {
          if (!target.matches(file.path)) {
            continue;
          }

          try {
            final stat = await file.stat();
            await file.delete();
            deletedCount++;
            freedBytes += stat.size;
          } on FileSystemException catch (error) {
            errors.add('${file.path}: ${error.message}');
          }
          continue;
        }

        final directory = Directory(path);
        if (!await directory.exists()) {
          continue;
        }

        try {
          await for (final entity
              in directory.list(recursive: true, followLinks: false)) {
            if (entity is! File || !target.matches(entity.path)) {
              continue;
            }

            try {
              final stat = await entity.stat();
              await entity.delete();
              deletedCount++;
              freedBytes += stat.size;
            } on FileSystemException catch (error) {
              errors.add('${entity.path}: ${error.message}');
            }
          }
        } on FileSystemException catch (error) {
          errors.add('${directory.path}: ${error.message}');
        }
      }
    }

    return CleanupCleanResult(
      deletedCount: deletedCount,
      freedBytes: freedBytes,
      skippedCategories: skippedCategories,
      errors: errors,
      completedAt: DateTime.now(),
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

      final file = File(path);
      if (await file.exists()) {
        if (!target.matches(file.path)) {
          continue;
        }

        scannedPathCount++;
        try {
          final stat = await file.stat();
          totalBytes += stat.size;
          itemCount++;
        } on FileSystemException catch (error) {
          errors.add('${file.path}: ${error.message}');
        }
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
          if (entity is! File || !target.matches(entity.path)) {
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
    final appData = env['APPDATA'] ?? '';
    final programData = env['ProgramData'] ?? r'C:\ProgramData';
    final temp = env['TEMP'] ?? env['TMP'] ?? '';
    final systemDrive = env['SystemDrive'] ?? _driveFromSystemRoot(systemRoot);

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
        id: 'chrome_cache',
        name: 'Chrome 缓存',
        description: 'Google Chrome Cache、Code Cache 和 GPUCache',
        paths: [
          '$localAppData\\Google\\Chrome\\User Data\\Default\\Cache',
          '$localAppData\\Google\\Chrome\\User Data\\Default\\Code Cache',
          '$localAppData\\Google\\Chrome\\User Data\\Default\\GPUCache',
        ],
      ),
      CleanupScanTarget(
        id: 'edge_cache',
        name: 'Edge 缓存',
        description: 'Microsoft Edge Cache、Code Cache 和 GPUCache',
        paths: [
          '$localAppData\\Microsoft\\Edge\\User Data\\Default\\Cache',
          '$localAppData\\Microsoft\\Edge\\User Data\\Default\\Code Cache',
          '$localAppData\\Microsoft\\Edge\\User Data\\Default\\GPUCache',
        ],
      ),
      CleanupScanTarget(
        id: 'firefox_cache',
        name: 'Firefox 缓存',
        description: 'Mozilla Firefox profile cache2 entries',
        paths: [
          '$appData\\Mozilla\\Firefox\\Profiles',
        ],
        pathContains: [r'\cache2\entries\'],
      ),
      CleanupScanTarget(
        id: 'browser_cookies',
        name: '浏览器 Cookie',
        description: 'Chrome、Edge、Firefox Cookie 数据库，默认保护不自动删除',
        paths: [
          '$localAppData\\Google\\Chrome\\User Data\\Default\\Network\\Cookies',
          '$localAppData\\Microsoft\\Edge\\User Data\\Default\\Network\\Cookies',
          '$appData\\Mozilla\\Firefox\\Profiles',
        ],
        fileNamePatterns: ['Cookies', 'cookies.sqlite'],
        canClean: false,
      ),
      CleanupScanTarget(
        id: 'browser_history',
        name: '浏览器历史记录',
        description: 'Chrome、Edge、Firefox 历史数据库，默认保护不自动删除',
        paths: [
          '$localAppData\\Google\\Chrome\\User Data\\Default\\History',
          '$localAppData\\Microsoft\\Edge\\User Data\\Default\\History',
          '$appData\\Mozilla\\Firefox\\Profiles',
        ],
        fileNamePatterns: ['History', 'places.sqlite'],
        canClean: false,
      ),
      CleanupScanTarget(
        id: 'browser_passwords',
        name: '浏览器保存密码',
        description: 'Chrome、Edge、Firefox 登录数据，只统计不自动清理',
        paths: [
          '$localAppData\\Google\\Chrome\\User Data\\Default\\Login Data',
          '$localAppData\\Microsoft\\Edge\\User Data\\Default\\Login Data',
          '$appData\\Mozilla\\Firefox\\Profiles',
        ],
        fileNamePatterns: ['Login Data', 'logins.json', 'key4.db'],
        canClean: false,
      ),
      CleanupScanTarget(
        id: 'chrome_update_cache',
        name: 'Chrome 更新缓存',
        description: 'Google Update 下载缓存',
        paths: [
          '$localAppData\\Google\\Update',
        ],
      ),
      CleanupScanTarget(
        id: 'edge_update_cache',
        name: 'Edge 更新缓存',
        description: 'Microsoft EdgeUpdate 下载缓存',
        paths: [
          '$localAppData\\Microsoft\\EdgeUpdate',
        ],
      ),
      CleanupScanTarget(
        id: 'system_logs',
        name: '诊断日志',
        description: 'Windows Logs 和 System32 LogFiles',
        paths: [
          '$systemRoot\\Logs',
          '$systemRoot\\System32\\LogFiles',
        ],
      ),
      CleanupScanTarget(
        id: 'system_event_logs',
        name: '系统事件日志',
        description: 'Windows 事件日志 evtx 文件，默认保护不直接删除',
        paths: [
          '$systemRoot\\System32\\winevt\\Logs',
        ],
        fileNamePatterns: ['*.evtx'],
        canClean: false,
      ),
      CleanupScanTarget(
        id: 'windows_update_cache',
        name: 'Windows 更新缓存',
        description: 'SoftwareDistribution、DeliveryOptimization 和 Windows.old',
        paths: [
          '$systemRoot\\SoftwareDistribution\\Download',
          '$systemRoot\\SoftwareDistribution\\DeliveryOptimization',
          '$systemDrive\\Windows.old',
        ],
      ),
      CleanupScanTarget(
        id: 'thumb_cache',
        name: '缩略图缓存',
        description: '资源管理器 thumbcache_*.db 数据库',
        paths: [
          '$localAppData\\Microsoft\\Windows\\Explorer',
        ],
        fileNamePatterns: ['thumbcache_*.db'],
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
        id: 'memory_dumps',
        name: '内存转储',
        description: 'Minidump 和 MEMORY.DMP 崩溃转储文件',
        paths: [
          '$systemRoot\\Minidump',
          '$systemRoot\\MEMORY.DMP',
        ],
        fileNamePatterns: ['*.dmp', 'MEMORY.DMP'],
      ),
      CleanupScanTarget(
        id: 'crash_dumps',
        name: '应用崩溃转储',
        description: 'c_cleaner_plus 常用规则: 用户态 CrashDumps',
        paths: [
          '$localAppData\\CrashDumps',
        ],
      ),
      CleanupScanTarget(
        id: 'vscode_cache',
        name: 'VS Code 缓存',
        description: 'c_cleaner_plus 常用规则: Cache、CachedData、GPUCache 和日志',
        paths: [
          '$appData\\Code\\Cache',
          '$appData\\Code\\CachedData',
          '$appData\\Code\\GPUCache',
          '$appData\\Code\\Service Worker\\CacheStorage',
          '$appData\\Code\\logs',
        ],
      ),
      CleanupScanTarget(
        id: 'cursor_cache',
        name: 'Cursor 缓存',
        description: 'c_cleaner_plus 常用规则: Cache、CachedData、GPUCache 和日志',
        paths: [
          '$appData\\Cursor\\Cache',
          '$appData\\Cursor\\CachedData',
          '$appData\\Cursor\\GPUCache',
          '$appData\\Cursor\\Service Worker\\CacheStorage',
          '$appData\\Cursor\\logs',
        ],
      ),
      CleanupScanTarget(
        id: 'discord_cache',
        name: 'Discord 缓存',
        description: 'c_cleaner_plus 常用规则: Cache、Code Cache、GPUCache',
        paths: [
          '$appData\\discord\\Cache',
          '$appData\\discord\\Code Cache',
          '$appData\\discord\\GPUCache',
          '$appData\\discord\\Service Worker\\CacheStorage',
        ],
      ),
      CleanupScanTarget(
        id: 'steam_web_cache',
        name: 'Steam 网页缓存',
        description: 'c_cleaner_plus 常用规则: Steam htmlcache',
        paths: [
          '$localAppData\\Steam\\htmlcache\\Cache',
          '$localAppData\\Steam\\htmlcache\\Code Cache',
          '$localAppData\\Steam\\htmlcache\\GPUCache',
        ],
      ),
      CleanupScanTarget(
        id: 'slack_cache',
        name: 'Slack 缓存',
        description: 'c_cleaner_plus 常用规则: Cache、Code Cache、GPUCache 和日志',
        paths: [
          '$appData\\Slack\\Cache',
          '$appData\\Slack\\Code Cache',
          '$appData\\Slack\\GPUCache',
          '$appData\\Slack\\Service Worker\\CacheStorage',
          '$appData\\Slack\\logs',
        ],
      ),
      CleanupScanTarget(
        id: 'notion_cache',
        name: 'Notion 缓存',
        description: 'c_cleaner_plus 常用规则: Cache、Code Cache、GPUCache',
        paths: [
          '$appData\\Notion\\Cache',
          '$appData\\Notion\\Code Cache',
          '$appData\\Notion\\GPUCache',
          '$appData\\Notion\\Service Worker\\CacheStorage',
        ],
      ),
      CleanupScanTarget(
        id: 'obs_cache',
        name: 'OBS Studio 缓存',
        description: 'c_cleaner_plus 常用规则: 日志、崩溃记录和浏览器源缓存',
        paths: [
          '$appData\\obs-studio\\logs',
          '$appData\\obs-studio\\crashes',
          '$appData\\obs-studio\\plugin_config\\obs-browser\\Cache',
        ],
      ),
      CleanupScanTarget(
        id: 'recent_files',
        name: '最近文件记录',
        description: 'Windows 最近使用项目快捷方式',
        paths: [
          '$appData\\Microsoft\\Windows\\Recent',
        ],
        fileNamePatterns: ['*.lnk'],
      ),
      CleanupScanTarget(
        id: 'invalid_shortcuts',
        name: '快捷方式检查',
        description: '桌面、开始菜单和任务栏快捷方式，默认只扫描不删除',
        paths: [
          '$userProfile\\Desktop',
          r'C:\Users\Public\Desktop',
          '$appData\\Microsoft\\Windows\\Start Menu',
          r'C:\ProgramData\Microsoft\Windows\Start Menu',
          '$appData\\Microsoft\\Internet Explorer\\Quick Launch\\User Pinned\\TaskBar',
        ],
        fileNamePatterns: ['*.lnk'],
        canClean: false,
      ),
      const CleanupScanTarget(
        id: 'registry_invalid_uninstall_entries',
        name: '卸载注册表残留',
        description: 'WindowsCleanUP 提到的无效卸载注册表项，默认保护不删除',
        paths: [],
        canClean: false,
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
        canClean: false,
      ),
    ];
  }

  static String _driveFromSystemRoot(String systemRoot) {
    final match = RegExp(r'^[A-Za-z]:').firstMatch(systemRoot);
    return match?.group(0) ?? r'C:';
  }
}

extension on CleanupScanTarget {
  bool matches(String path) {
    final normalizedPath = path.replaceAll('/', r'\').toLowerCase();
    if (pathContains.isNotEmpty &&
        !pathContains.any((fragment) => normalizedPath
            .contains(fragment.replaceAll('/', r'\').toLowerCase()))) {
      return false;
    }

    if (fileNamePatterns.isEmpty) {
      return true;
    }

    final fileName = path.split(RegExp(r'[\\/]')).last;
    return fileNamePatterns
        .any((pattern) => _matchesWildcard(fileName, pattern));
  }

  bool _matchesWildcard(String value, String pattern) {
    if (!pattern.contains('*')) {
      return value.toLowerCase() == pattern.toLowerCase();
    }

    final escaped = RegExp.escape(pattern).replaceAll(r'\*', '.*');
    return RegExp('^$escaped\$', caseSensitive: false).hasMatch(value);
  }
}
