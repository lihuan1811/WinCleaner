import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/bcu_service.dart';

void main() {
  test('locate reports unavailable when no configured executable exists', () {
    final service = BcuService(
      searchPaths: const ['missing/BCUninstaller.exe'],
    );

    final status = service.locate();

    expect(status.isAvailable, isFalse);
    expect(status.executablePath, isNull);
  });

  test('locate finds configured executable path', () async {
    final tempDir = await Directory.systemTemp.createTemp('bcu_service_test_');
    addTearDown(() => tempDir.delete(recursive: true));
    final executable = File(
      '${tempDir.path}${Platform.pathSeparator}BCUninstaller.exe',
    );
    await executable.writeAsString('stub');

    final service = BcuService(searchPaths: [executable.path]);

    final status = service.locate();

    expect(status.isAvailable, isTrue);
    expect(status.executablePath, executable.path);
  });
}
