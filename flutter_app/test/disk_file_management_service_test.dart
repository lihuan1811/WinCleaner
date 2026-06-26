import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/disk_file_management_service.dart';

void main() {
  test('detects file types and lists files by filter', () async {
    final tempDir = await Directory.systemTemp.createTemp('disk-files-');
    addTearDown(() => tempDir.delete(recursive: true));
    File('${tempDir.path}${Platform.pathSeparator}movie.mp4')
        .writeAsStringSync('video');
    File('${tempDir.path}${Platform.pathSeparator}setup.msi')
        .writeAsStringSync('installer');
    File('${tempDir.path}${Platform.pathSeparator}doc.pdf')
        .writeAsStringSync('document');

    final service = DiskFileManagementService();
    final installers = await service.listFiles(
      tempDir.path,
      type: ManagedFileType.installer,
    );

    expect(
        DiskFileManagementService.detectType('a.zip'), ManagedFileType.archive);
    expect(installers, hasLength(1));
    expect(installers.single.name, 'setup.msi');
  });

  test('reports folder usage sorted by size', () async {
    final tempDir = await Directory.systemTemp.createTemp('folder-usage-');
    addTearDown(() => tempDir.delete(recursive: true));
    final small = Directory('${tempDir.path}${Platform.pathSeparator}small')
      ..createSync();
    final large = Directory('${tempDir.path}${Platform.pathSeparator}large')
      ..createSync();
    File('${small.path}${Platform.pathSeparator}a.bin').writeAsStringSync('1');
    File('${large.path}${Platform.pathSeparator}b.bin')
        .writeAsStringSync('12345');

    final service = DiskFileManagementService();
    final folders = await service.topFolders(tempDir.path);

    expect(folders.first.path, large.path);
    expect(folders.first.sizeBytes, 5);
  });

  test('copies moves renames deletes and shreds files', () async {
    final tempDir = await Directory.systemTemp.createTemp('file-ops-');
    addTearDown(() => tempDir.delete(recursive: true));
    final source = Directory('${tempDir.path}${Platform.pathSeparator}source')
      ..createSync();
    final target = Directory('${tempDir.path}${Platform.pathSeparator}target');
    final file = File('${source.path}${Platform.pathSeparator}a.txt')
      ..writeAsStringSync('abc');

    final service = DiskFileManagementService();
    final copied = await service.copyFiles([file.path], target.path);
    final copiedPath = copied.affectedPaths.single;
    expect(await File(copiedPath).exists(), isTrue);

    final renamed = await service.renameFile(copiedPath, 'renamed.txt');
    expect(await File(renamed.affectedPaths.single).exists(), isTrue);

    final moved =
        await service.moveFiles([renamed.affectedPaths.single], source.path);
    expect(await File(moved.affectedPaths.single).exists(), isTrue);

    final shredded = await service.shredFiles([moved.affectedPaths.single]);
    expect(shredded.affectedPaths, hasLength(1));
    expect(await File(moved.affectedPaths.single).exists(), isFalse);

    final deleted = await service.deleteFiles([file.path]);
    expect(deleted.affectedPaths, contains(file.path));
    expect(await file.exists(), isFalse);
  });

  test('runs Windows permission and temp migration commands', () async {
    final calls = <String>[];
    final service = DiskFileManagementService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        calls.add('$exe ${args.join(' ')}');
        return ProcessResult(1, 0, 'ok', '');
      },
    );

    await service.repairFolderPermission(r'C:\Broken');
    await service.migrateTemp(r'D:\Temp');
    await service.migratePersonalFolder(
      folderKey: 'Desktop',
      targetPath: r'D:\Desktop',
    );

    expect(calls[0], contains('icacls C:\\Broken /reset /T /C'));
    expect(calls[1], contains('setx TEMP'));
    expect(calls[2], contains('User Shell Folders'));
    expect(calls[2], contains('Desktop'));
  });
}
