import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/system_cleanup_scan_service.dart';

void main() {
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
}
