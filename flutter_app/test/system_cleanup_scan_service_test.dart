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
    expect(result.skippedCategories, contains('下载目录'));
    expect(await removableFile.exists(), isFalse);
    expect(await protectedFile.exists(), isTrue);
  });
}
