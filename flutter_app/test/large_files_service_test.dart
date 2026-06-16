import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/large_files_service.dart';

void main() {
  test('finds files above the requested size sorted by size descending',
      () async {
    final tempDir = await Directory.systemTemp.createTemp('large-files-test-');
    addTearDown(() => tempDir.delete(recursive: true));

    File('${tempDir.path}/small.bin').writeAsBytesSync(List.filled(2, 1));
    File('${tempDir.path}/large.bin').writeAsBytesSync(List.filled(12, 1));
    File('${tempDir.path}/larger.bin').writeAsBytesSync(List.filled(20, 1));

    final service = LargeFilesService();
    final result = await service.scanDirectory(tempDir.path, minBytes: 10);

    expect(result.files.map((file) => file.name), ['larger.bin', 'large.bin']);
    expect(result.totalBytes, 32);
  });
}
