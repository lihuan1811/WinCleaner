import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/system_cleanup_scan_service.dart';

void main() {
  test('default targets include WindowsCleanUP-inspired cleanup categories',
      () {
    final targets = SystemCleanupScanService.defaultTargets(
      environment: const {
        'SystemRoot': r'C:\Windows',
        'USERPROFILE': r'C:\Users\Ada',
        'LOCALAPPDATA': r'C:\Users\Ada\AppData\Local',
        'APPDATA': r'C:\Users\Ada\AppData\Roaming',
        'ProgramData': r'C:\ProgramData',
        'TEMP': r'C:\Users\Ada\AppData\Local\Temp',
      },
    );
    final byId = {for (final target in targets) target.id: target};

    expect(
      byId.keys,
      containsAll([
        'chrome_cache',
        'edge_cache',
        'firefox_cache',
        'browser_cookies',
        'browser_history',
        'browser_passwords',
        'chrome_update_cache',
        'edge_update_cache',
        'memory_dumps',
        'wechat_media_cache',
        'wechat_chat_backup',
        'qq_media_cache',
        'qq_chat_cache',
        'c_drive_installers_archives',
        'invalid_shortcuts',
        'recent_files',
        'registry_invalid_uninstall_entries',
        'system_event_logs',
        'windows_update_cache',
        'thumb_cache',
        'vscode_cache',
        'cursor_cache',
        'discord_cache',
        'steam_web_cache',
        'slack_cache',
        'notion_cache',
        'obs_cache',
        'crash_dumps',
      ]),
    );
    expect(
      byId['chrome_cache']!.paths,
      contains(
          r'C:\Users\Ada\AppData\Local\Google\Chrome\User Data\Default\Cache'),
    );
    expect(byId['browser_passwords']!.canClean, isFalse);
    expect(byId['browser_passwords']!.risk, CleanupRisk.high);
    expect(byId['wechat_media_cache']!.group, '微信缓存专清');
    expect(byId['wechat_media_cache']!.recommended, isTrue);
    expect(byId['wechat_chat_backup']!.recommended, isFalse);
    expect(byId['wechat_chat_backup']!.risk, CleanupRisk.caution);
    expect(byId['qq_media_cache']!.paths,
        contains(r'C:\Users\Ada\Documents\Tencent Files'));
    expect(byId['qq_chat_cache']!.recommended, isFalse);
    expect(byId['c_drive_installers_archives']!.fileNamePatterns,
        contains('*.iso'));
    expect(byId['registry_invalid_uninstall_entries']!.canClean, isFalse);
    expect(byId['downloads']!.canClean, isFalse);
    expect(
      byId['vscode_cache']!.paths,
      contains(r'C:\Users\Ada\AppData\Roaming\Code\Cache'),
    );
    expect(
      byId['steam_web_cache']!.paths,
      contains(r'C:\Users\Ada\AppData\Local\Steam\htmlcache\Cache'),
    );
  });

  test('scans cleanup targets and totals discovered file sizes', () async {
    final tempDir = await Directory.systemTemp.createTemp('cleanup-scan-test-');
    addTearDown(() => tempDir.delete(recursive: true));

    final tempTarget = Directory('${tempDir.path}${Platform.pathSeparator}temp')
      ..createSync();
    final cacheTarget =
        Directory('${tempDir.path}${Platform.pathSeparator}cache')
          ..createSync();
    File('${tempTarget.path}${Platform.pathSeparator}one.tmp')
        .writeAsStringSync('12345');
    File('${tempTarget.path}${Platform.pathSeparator}two.tmp')
        .writeAsStringSync('1234567');
    File('${cacheTarget.path}${Platform.pathSeparator}browser.bin')
        .writeAsStringSync('123');

    final service = SystemCleanupScanService(
      targets: [
        CleanupScanTarget(
          id: 'temp',
          name: '临时文件',
          description: '系统和用户临时目录',
          paths: [tempTarget.path],
        ),
        CleanupScanTarget(
          id: 'cache',
          name: '浏览器缓存',
          description: '浏览器缓存目录',
          paths: [
            cacheTarget.path,
            '${tempDir.path}${Platform.pathSeparator}missing',
          ],
        ),
      ],
    );

    final result = await service.scan();

    expect(result.itemCount, 3);
    expect(result.totalBytes, 15);
    expect(result.categories, hasLength(2));
    expect(result.categories.first.name, '临时文件');
    expect(result.categories.first.itemCount, 2);
    expect(result.categories.first.totalBytes, 12);
    expect(result.categories.last.name, '浏览器缓存');
    expect(result.categories.last.itemCount, 1);
    expect(result.categories.last.totalBytes, 3);
  });

  test('cleans eligible cleanup targets and skips protected targets', () async {
    final tempDir =
        await Directory.systemTemp.createTemp('cleanup-clean-test-');
    addTearDown(() => tempDir.delete(recursive: true));

    final tempTarget = Directory('${tempDir.path}${Platform.pathSeparator}temp')
      ..createSync();
    final protectedTarget =
        Directory('${tempDir.path}${Platform.pathSeparator}downloads')
          ..createSync();
    final removableFile =
        File('${tempTarget.path}${Platform.pathSeparator}one.tmp')
          ..writeAsStringSync('12345');
    final protectedFile =
        File('${protectedTarget.path}${Platform.pathSeparator}keep.zip')
          ..writeAsStringSync('1234567');

    final service = SystemCleanupScanService(
      targets: [
        CleanupScanTarget(
          id: 'temp',
          name: '临时文件',
          description: '系统和用户临时目录',
          paths: [tempTarget.path],
        ),
        CleanupScanTarget(
          id: 'downloads',
          name: '下载目录',
          description: '当前用户下载目录',
          paths: [protectedTarget.path],
          canClean: false,
        ),
      ],
    );

    final result = await service.clean();

    expect(result.deletedCount, 1);
    expect(result.freedBytes, 5);
    expect(result.backedUpCount, 1);
    expect(result.backupDirectory, isNotEmpty);
    expect(result.skippedCategories, contains('下载目录'));
    expect(await removableFile.exists(), isFalse);
    expect(await protectedFile.exists(), isTrue);
  });

  test('recommended clean skips cautious targets unless explicitly included',
      () async {
    final tempDir = await Directory.systemTemp.createTemp('cleanup-risk-test-');
    addTearDown(() => tempDir.delete(recursive: true));

    final safeDir = Directory('${tempDir.path}${Platform.pathSeparator}safe')
      ..createSync();
    final riskyDir = Directory('${tempDir.path}${Platform.pathSeparator}risky')
      ..createSync();
    final backupDir =
        Directory('${tempDir.path}${Platform.pathSeparator}backup');
    final safeFile = File('${safeDir.path}${Platform.pathSeparator}safe.tmp')
      ..writeAsStringSync('safe');
    final riskyFile = File('${riskyDir.path}${Platform.pathSeparator}chat.db')
      ..writeAsStringSync('chat');

    final service = SystemCleanupScanService(
      targets: [
        CleanupScanTarget(
          id: 'safe',
          name: '安全缓存',
          description: 'safe',
          paths: [safeDir.path],
        ),
        CleanupScanTarget(
          id: 'risky',
          name: '聊天记录',
          description: 'risky',
          paths: [riskyDir.path],
          risk: CleanupRisk.caution,
          recommended: false,
        ),
      ],
    );

    final recommended = await service.clean(backupDirectory: backupDir);

    expect(recommended.deletedCount, 1);
    expect(await safeFile.exists(), isFalse);
    expect(await riskyFile.exists(), isTrue);
    expect(recommended.skippedCategories, contains('聊天记录'));

    final deep = await service.clean(
      includeRisky: true,
      backupDirectory: backupDir,
    );

    expect(deep.deletedCount, 1);
    expect(await riskyFile.exists(), isFalse);
  });
}
