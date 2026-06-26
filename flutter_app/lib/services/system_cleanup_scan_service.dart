import 'dart:io';

enum CleanupRisk {
  safe('✅安全无风险', '可作为推荐项默认勾选'),
  caution('⚠️谨慎操作', '可能影响聊天记录、用户文件或系统行为'),
  high('🔴高危操作', '需要明确确认后才允许执行');

  const CleanupRisk(this.label, this.description);

  final String label;
  final String description;
}

class CleanupScanTarget {
  const CleanupScanTarget({
    required this.id,
    required this.name,
    required this.description,
    required this.paths,
    this.group = '系统清理',
    this.risk = CleanupRisk.safe,
    this.recommended = true,
    this.fileNamePatterns = const [],
    this.pathContains = const [],
    this.canClean = true,
    this.backupBeforeClean = true,
  });

  final String id;
  final String name;
  final String description;
  final List<String> paths;
  final String group;
  final CleanupRisk risk;
  final bool recommended;
  final List<String> fileNamePatterns;
  final List<String> pathContains;
  final bool canClean;
  final bool backupBeforeClean;
}

class CleanupCategoryResult {
  const CleanupCategoryResult({
    required this.id,
    required this.name,
    required this.description,
    required this.group,
    required this.risk,
    required this.recommended,
    required this.canClean,
    required this.itemCount,
    required this.totalBytes,
    required this.scannedPathCount,
    required this.errors,
  });

  final String id;
  final String name;
  final String description;
  final String group;
  final CleanupRisk risk;
  final bool recommended;
  final bool canClean;
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
    required this.backedUpCount,
    required this.backupDirectory,
    required this.skippedCategories,
    required this.errors,
    required this.completedAt,
  });

  final int deletedCount;
  final int freedBytes;
  final int backedUpCount;
  final String backupDirectory;
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

  Future<CleanupCleanResult> clean({
    bool includeRisky = false,
    Directory? backupDirectory,
  }) async {
    var deletedCount = 0;
    var freedBytes = 0;
    var backedUpCount = 0;
    final skippedCategories = <String>[];
    final errors = <String>[];
    final backupRoot = backupDirectory ?? _defaultBackupDirectory();

    for (final target in _targets ?? defaultTargets()) {
      if (!target.canClean) {
        skippedCategories.add(target.name);
        continue;
      }
      if (!includeRisky &&
          (!target.recommended || target.risk != CleanupRisk.safe)) {
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
            if (target.backupBeforeClean) {
              await _backupFile(file, backupRoot, target.id);
              backedUpCount++;
            }
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
              if (target.backupBeforeClean) {
                await _backupFile(entity, backupRoot, target.id);
                backedUpCount++;
              }
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
      backedUpCount: backedUpCount,
      backupDirectory: backupRoot.path,
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
      group: target.group,
      risk: target.risk,
      recommended: target.recommended,
      canClean: target.canClean,
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
        group: '系统临时文件',
        paths: [
          temp,
          '$systemRoot\\Temp',
        ],
      ),
      const CleanupScanTarget(
        id: 'recycle',
        name: '回收站',
        description: '系统回收站内容',
        group: '回收站',
        paths: [r'C:\$Recycle.Bin'],
      ),
      CleanupScanTarget(
        id: 'chrome_cache',
        name: 'Chrome 缓存',
        description: 'Google Chrome Cache、Code Cache 和 GPUCache',
        group: '浏览器缓存',
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
        group: '浏览器缓存',
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
        group: '浏览器缓存',
        paths: [
          '$appData\\Mozilla\\Firefox\\Profiles',
        ],
        pathContains: [r'\cache2\entries\'],
      ),
      CleanupScanTarget(
        id: 'browser_cookies',
        name: '浏览器 Cookie',
        description: 'Chrome、Edge、Firefox Cookie 数据库，默认保护不自动删除',
        group: '浏览器缓存',
        risk: CleanupRisk.caution,
        recommended: false,
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
        group: '浏览器缓存',
        risk: CleanupRisk.caution,
        recommended: false,
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
        group: '浏览器缓存',
        risk: CleanupRisk.high,
        recommended: false,
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
        group: '浏览器缓存',
        paths: [
          '$localAppData\\Google\\Update',
        ],
      ),
      CleanupScanTarget(
        id: 'edge_update_cache',
        name: 'Edge 更新缓存',
        description: 'Microsoft EdgeUpdate 下载缓存',
        group: '浏览器缓存',
        paths: [
          '$localAppData\\Microsoft\\EdgeUpdate',
        ],
      ),
      CleanupScanTarget(
        id: 'system_logs',
        name: '诊断日志',
        description: 'Windows Logs 和 System32 LogFiles',
        group: '缩略图/日志/DUMP文件',
        paths: [
          '$systemRoot\\Logs',
          '$systemRoot\\System32\\LogFiles',
        ],
      ),
      CleanupScanTarget(
        id: 'system_event_logs',
        name: '系统事件日志',
        description: 'Windows 事件日志 evtx 文件，默认保护不直接删除',
        group: '缩略图/日志/DUMP文件',
        risk: CleanupRisk.caution,
        recommended: false,
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
        group: 'Windows更新残留',
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
        group: '缩略图/日志/DUMP文件',
        paths: [
          '$localAppData\\Microsoft\\Windows\\Explorer',
        ],
        fileNamePatterns: ['thumbcache_*.db'],
      ),
      CleanupScanTarget(
        id: 'prefetch',
        name: '预读取缓存',
        description: 'Windows Prefetch 文件',
        group: '系统临时文件',
        paths: [
          '$systemRoot\\Prefetch',
        ],
      ),
      CleanupScanTarget(
        id: 'error_reports',
        name: '错误报告',
        description: 'Windows 错误报告缓存',
        group: '缩略图/日志/DUMP文件',
        paths: [
          '$programData\\Microsoft\\Windows\\WER',
          '$localAppData\\Microsoft\\Windows\\WER',
        ],
      ),
      CleanupScanTarget(
        id: 'memory_dumps',
        name: '内存转储',
        description: 'Minidump 和 MEMORY.DMP 崩溃转储文件',
        group: '缩略图/日志/DUMP文件',
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
        group: '缩略图/日志/DUMP文件',
        paths: [
          '$localAppData\\CrashDumps',
        ],
      ),
      CleanupScanTarget(
        id: 'wechat_media_cache',
        name: '微信缓存专清',
        description: '微信聊天图片、语音视频、接收文件、小程序与临时缓存',
        group: '微信缓存专清',
        paths: [
          '$userProfile\\Documents\\WeChat Files',
          '$userProfile\\Documents\\WXWork',
          '$localAppData\\Tencent\\WeChat',
          '$appData\\Tencent\\WeChat',
        ],
        pathContains: [
          r'\filestorage\cache\',
          r'\filestorage\image\',
          r'\filestorage\video\',
          r'\filestorage\file\',
          r'\filestorage\applet\',
          r'\filestorage\temp\',
          r'\cache\',
        ],
      ),
      CleanupScanTarget(
        id: 'wechat_chat_backup',
        name: '微信本地聊天记录备份',
        description: '微信 Msg、聊天数据库和本地记录缓存，删除后本地聊天记录可能丢失',
        group: '微信缓存专清',
        risk: CleanupRisk.caution,
        recommended: false,
        paths: [
          '$userProfile\\Documents\\WeChat Files',
        ],
        pathContains: [
          r'\msg\',
          r'\db\',
        ],
      ),
      CleanupScanTarget(
        id: 'qq_media_cache',
        name: 'QQ 缓存专清',
        description: 'QQ 私聊/群聊图片、短视频、接收安装包和空间小程序缓存',
        group: 'QQ 缓存专清',
        paths: [
          '$userProfile\\Documents\\Tencent Files',
          '$appData\\Tencent\\QQ',
          '$localAppData\\Tencent\\QQ',
        ],
        pathContains: [
          r'\filerecv\',
          r'\image\',
          r'\video\',
          r'\shortvideo\',
          r'\cache\',
          r'\temp\',
        ],
      ),
      CleanupScanTarget(
        id: 'qq_chat_cache',
        name: 'QQ 本地聊天记录缓存',
        description: 'QQ Msg、本地聊天数据库和会话缓存，删除后本地聊天记录可能丢失',
        group: 'QQ 缓存专清',
        risk: CleanupRisk.caution,
        recommended: false,
        paths: [
          '$userProfile\\Documents\\Tencent Files',
        ],
        pathContains: [
          r'\msg\',
          r'\msg2.0\',
        ],
      ),
      CleanupScanTarget(
        id: 'c_drive_installers_archives',
        name: 'C盘大型安装包/压缩包/镜像',
        description: '扫描 C 盘常见下载位置中的 exe、msi、zip、rar、7z、iso 等冗余文件',
        group: 'C盘大型安装包',
        risk: CleanupRisk.caution,
        recommended: false,
        paths: [
          '$userProfile\\Downloads',
          '$userProfile\\Desktop',
          '$systemDrive\\',
        ],
        fileNamePatterns: [
          '*.exe',
          '*.msi',
          '*.zip',
          '*.rar',
          '*.7z',
          '*.iso',
        ],
      ),
      CleanupScanTarget(
        id: 'vscode_cache',
        name: 'VS Code 缓存',
        description: 'c_cleaner_plus 常用规则: Cache、CachedData、GPUCache 和日志',
        group: '应用缓存',
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
        group: '应用缓存',
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
        group: '应用缓存',
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
        group: '应用缓存',
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
        group: '应用缓存',
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
        group: '应用缓存',
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
        group: '应用缓存',
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
        group: '系统临时文件',
        paths: [
          '$appData\\Microsoft\\Windows\\Recent',
        ],
        fileNamePatterns: ['*.lnk'],
      ),
      CleanupScanTarget(
        id: 'invalid_shortcuts',
        name: '快捷方式检查',
        description: '桌面、开始菜单和任务栏快捷方式，默认只扫描不删除',
        group: '系统优化检查',
        recommended: false,
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
        group: '系统优化检查',
        recommended: false,
        paths: [],
        canClean: false,
      ),
      CleanupScanTarget(
        id: 'delivery_optimization',
        name: '传递优化缓存',
        description: 'Windows Delivery Optimization 缓存',
        group: 'Windows更新残留',
        paths: [
          '$systemRoot\\ServiceProfiles\\NetworkService\\AppData\\Local\\Microsoft\\Windows\\DeliveryOptimization\\Cache',
        ],
      ),
      CleanupScanTarget(
        id: 'downloads',
        name: '下载目录',
        description: '当前用户下载目录',
        group: 'C盘大型安装包',
        risk: CleanupRisk.caution,
        recommended: false,
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

  static Directory _defaultBackupDirectory() {
    try {
      final stamp = DateTime.now()
          .toIso8601String()
          .replaceAll(':', '')
          .replaceAll('.', '-');
      return Directory(
        '${Directory.systemTemp.path}${Platform.pathSeparator}WinCleaner_File_Backup'
        '${Platform.pathSeparator}$stamp',
      );
    } on UnsupportedError {
      return Directory('/WinCleaner_File_Backup');
    }
  }

  static Future<void> _backupFile(
    File file,
    Directory backupRoot,
    String targetId,
  ) async {
    final normalized =
        file.path.replaceAll(':', '').replaceAll(RegExp(r'[\\/]'), '_');
    final targetDirectory =
        Directory('${backupRoot.path}${Platform.pathSeparator}$targetId');
    await targetDirectory.create(recursive: true);
    await file
        .copy('${targetDirectory.path}${Platform.pathSeparator}$normalized');
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
