import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/duplicate_files_service.dart';

void main() {
  test('finds duplicate files by size and content hash', () async {
    final tempDir = await Directory.systemTemp.createTemp('dupes-test-');
    addTearDown(() => tempDir.delete(recursive: true));

    final first = File('${tempDir.path}${Platform.pathSeparator}first.txt')
      ..writeAsStringSync('same-content');
    final second = File('${tempDir.path}${Platform.pathSeparator}second.txt')
      ..writeAsStringSync('same-content');
    File('${tempDir.path}${Platform.pathSeparator}unique.txt')
        .writeAsStringSync('different');

    final service = DuplicateFilesService();
    final result = await service.scanDirectory(tempDir.path, minBytes: 1);

    expect(result.groups, hasLength(1));
    expect(
        result.groups.single.files.map((file) => file.path),
        containsAll([
          first.path,
          second.path,
        ]));
    expect(result.duplicateBytes, 'same-content'.length);
  });

  test('deletes duplicate copies while keeping one file per group', () async {
    final tempDir = await Directory.systemTemp.createTemp('dupes-delete-test-');
    addTearDown(() => tempDir.delete(recursive: true));

    final keep = File('${tempDir.path}/a.txt')..writeAsStringSync('abc');
    final remove = File('${tempDir.path}/b.txt')..writeAsStringSync('abc');

    final service = DuplicateFilesService();
    final result = await service.scanDirectory(tempDir.path, minBytes: 1);
    final deletion = await service.deleteDuplicateCopies(result.groups);

    expect(keep.existsSync(), isTrue);
    expect(remove.existsSync(), isFalse);
    expect(deletion.deletedCount, 1);
    expect(deletion.freedBytes, 3);
  });
}
