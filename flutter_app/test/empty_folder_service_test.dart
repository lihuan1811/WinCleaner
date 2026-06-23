import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/empty_folder_service.dart';

void main() {
  test('finds empty directories from deepest path first', () async {
    final root = await Directory.systemTemp.createTemp('empty-folder-scan-');
    addTearDown(() => root.delete(recursive: true));

    final nested = Directory('${root.path}${Platform.pathSeparator}a'
        '${Platform.pathSeparator}b')
      ..createSync(recursive: true);
    final nonEmpty = Directory('${root.path}${Platform.pathSeparator}non-empty')
      ..createSync();
    File('${nonEmpty.path}${Platform.pathSeparator}keep.txt')
        .writeAsStringSync('keep');

    final result = await EmptyFolderService().scan(root.path);

    expect(result.folders.map((f) => f.path), contains(nested.path));
    expect(result.folders.map((f) => f.path), isNot(contains(nonEmpty.path)));
    expect(result.folders.first.path, nested.path);
  });

  test('deletes only folders that are still empty', () async {
    final root = await Directory.systemTemp.createTemp('empty-folder-delete-');
    addTearDown(() async {
      if (await root.exists()) {
        await root.delete(recursive: true);
      }
    });

    final empty = Directory('${root.path}${Platform.pathSeparator}empty')
      ..createSync();
    final nonEmpty = Directory('${root.path}${Platform.pathSeparator}non-empty')
      ..createSync();
    File('${nonEmpty.path}${Platform.pathSeparator}keep.txt')
        .writeAsStringSync('keep');

    final result = await EmptyFolderService().deleteFolders([
      EmptyFolderEntry(path: empty.path),
      EmptyFolderEntry(path: nonEmpty.path),
    ]);

    expect(result.deletedCount, 1);
    expect(await empty.exists(), isFalse);
    expect(await nonEmpty.exists(), isTrue);
    expect(result.skippedPaths, contains(nonEmpty.path));
  });
}
