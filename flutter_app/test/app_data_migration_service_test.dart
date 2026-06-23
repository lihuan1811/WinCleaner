import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/app_data_migration_service.dart';

void main() {
  test('scans first-level folders above parent ratio sorted by size', () async {
    final tempDir = await Directory.systemTemp.createTemp('appdata-scan-');
    addTearDown(() => tempDir.delete(recursive: true));

    final root = Directory('${tempDir.path}/Local')..createSync();
    final tiny = Directory('${root.path}/Tiny')..createSync();
    final chrome = Directory('${root.path}/Chrome')..createSync();
    final cursor = Directory('${root.path}/Cursor')..createSync();

    File('${tiny.path}/small.bin').writeAsBytesSync(List.filled(5, 1));
    File('${chrome.path}/cache.bin').writeAsBytesSync(List.filled(20, 1));
    File('${cursor.path}/cache.bin').writeAsBytesSync(List.filled(35, 1));

    final service = AppDataMigrationService();
    final result = await service.scanLargeFolders([
      AppDataScanSource(
        label: 'LocalAppData',
        path: root.path,
        targetSubdir: 'Local',
      ),
    ], minParentRatio: 0.25);

    expect(result.folders.map((folder) => folder.name), ['Cursor', 'Chrome']);
    expect(result.totalBytes, 55);
    expect(result.scannedCount, 3);
  });

  test('skips protected Windows app and system folders during scan', () async {
    final tempDir = await Directory.systemTemp.createTemp('appdata-safe-scan-');
    addTearDown(() => tempDir.delete(recursive: true));

    final root = Directory('${tempDir.path}/Local')..createSync();
    for (final name in [
      'WindowsApps',
      'Packages',
      'Microsoft',
      'NVIDIA Corporation',
    ]) {
      final directory = Directory('${root.path}/$name')..createSync();
      File('${directory.path}/locked.bin').writeAsBytesSync(List.filled(40, 1));
    }
    final cursor = Directory('${root.path}/Cursor')..createSync();
    File('${cursor.path}/cache.bin').writeAsBytesSync(List.filled(20, 1));

    final service = AppDataMigrationService();
    final result = await service.scanLargeFolders([
      AppDataScanSource(
        label: 'LocalAppData',
        path: root.path,
        targetSubdir: 'Local',
      ),
    ], minParentRatio: 0.05);

    expect(result.folders.map((folder) => folder.name), ['Cursor']);
    expect(result.scannedCount, 1);
  });

  test('default scan sources stay limited to user AppData folders', () {
    final sources = AppDataMigrationService.defaultScanSources(
      environment: const {
        'LOCALAPPDATA': r'C:\Users\Ada\AppData\Local',
        'APPDATA': r'C:\Users\Ada\AppData\Roaming',
        'ProgramData': r'C:\ProgramData',
        'ProgramFiles': r'C:\Program Files',
        'ProgramFiles(x86)': r'C:\Program Files (x86)',
      },
    );

    expect(sources.map((source) => source.label), [
      'LocalAppData',
      'RoamingAppData',
    ]);
  });

  test('treats Windows program roots as protected migration paths', () {
    expect(
      AppDataMigrationService.isProtectedMigrationPath(r'C:\Program Files'),
      isTrue,
    );
    expect(
      AppDataMigrationService.isProtectedMigrationPath(r'C:\ProgramData'),
      isTrue,
    );
  });

  test('rejects protected folder migrations before moving files', () async {
    final tempDir =
        await Directory.systemTemp.createTemp('appdata-protected-move-');
    addTearDown(() => tempDir.delete(recursive: true));

    final source = Directory('${tempDir.path}/WindowsApps')..createSync();
    File('${source.path}/system.bin').writeAsBytesSync(List.filled(4, 1));
    final targetRoot = Directory('${tempDir.path}/Target')..createSync();
    final service = AppDataMigrationService(
      isWindowsOverride: true,
      processRunner: (_, __) async {
        fail('protected folders must be rejected before running mklink');
      },
    );

    final result = await service.migrateFolder(
      AppDataMigrationFolder(
        path: source.path,
        name: 'WindowsApps',
        sizeBytes: 4,
        sourceLabel: 'LocalAppData',
        targetSubdir: 'Local',
        parentTotalBytes: 4,
      ),
      targetRoot.path,
    );

    expect(result.success, isFalse);
    expect(result.output, contains('受保护目录'));
    expect(Directory(source.path).existsSync(), isTrue);
  });

  test('computes Windows-style target parent preserving source hierarchy', () {
    final parent = AppDataMigrationService.computeTargetParent(
      r'D:\Yugongyipan',
      r'C:\Users\Ada\AppData\Local\Cursor',
    );

    expect(parent, r'D:\Yugongyipan\Users\Ada\AppData\Local');
  });

  test('creates junction command after same-volume directory rename', () async {
    final tempDir = await Directory.systemTemp.createTemp('appdata-move-');
    addTearDown(() => tempDir.delete(recursive: true));

    final source = Directory('${tempDir.path}/Source')..createSync();
    File('${source.path}/cache.bin').writeAsBytesSync(List.filled(12, 1));
    final targetRoot = Directory('${tempDir.path}/Target')..createSync();
    final historyFile = File('${tempDir.path}/history.json');

    late String executable;
    late List<String> arguments;
    final service = AppDataMigrationService(
      isWindowsOverride: true,
      historyFile: historyFile,
      processRunner: (exe, args) async {
        executable = exe;
        arguments = args;
        return ProcessResult(42, 0, 'Junction created', '');
      },
    );

    final result = await service.migrateFolder(
      AppDataMigrationFolder(
        path: source.path,
        name: 'Source',
        sizeBytes: 12,
        sourceLabel: 'Test',
        targetSubdir: 'Test',
        parentTotalBytes: 12,
      ),
      targetRoot.path,
    );

    expect(result.success, isTrue);
    expect(executable, 'cmd');
    expect(arguments.take(3), ['/C', 'mklink', '/J']);
    expect(Directory(source.path).existsSync(), isFalse);
    expect(result.record?.sourcePath, source.path);
    expect(result.record?.targetPath, contains('Source'));
    expect(service.loadHistory(), hasLength(1));
  });

  test('restores migration by removing link and moving target back', () async {
    final tempDir = await Directory.systemTemp.createTemp('appdata-restore-');
    addTearDown(() => tempDir.delete(recursive: true));

    final source = Directory('${tempDir.path}/Source');
    final target = Directory('${tempDir.path}/Target/Source')
      ..createSync(recursive: true);
    File('${target.path}/cache.bin').writeAsBytesSync(List.filled(4, 1));
    final historyFile = File('${tempDir.path}/history.json');
    final record = AppDataMigrationRecord(
      id: 'r1',
      name: 'Source',
      sourcePath: source.path,
      targetPath: target.path,
      sizeBytes: 4,
      createdAtMillis: 1000,
      batchId: 'b1',
    );

    final service = AppDataMigrationService(historyFile: historyFile);
    service.saveHistory([record]);

    final result = await service.restoreMigration(record);

    expect(result.success, isTrue);
    expect(File('${source.path}/cache.bin').existsSync(), isTrue);
    expect(target.existsSync(), isFalse);
    expect(service.loadHistory(), isEmpty);
  });
}
