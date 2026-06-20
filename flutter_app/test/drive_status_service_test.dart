import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/drive_status_service.dart';

void main() {
  test('loads Windows drive status from PowerShell JSON output', () async {
    final service = DriveStatusService(
      isWindowsOverride: true,
      processRunner: (executable, arguments) async {
        expect(executable, 'powershell');
        expect(arguments, contains('-Command'));
        return ProcessResult(
          1,
          0,
          '{"DeviceID":"C:","Size":512000000000,"FreeSpace":128000000000}',
          '',
        );
      },
    );

    final status = await service.loadDrive('C');

    expect(status.drive, 'C:');
    expect(status.totalBytes, 512000000000);
    expect(status.freeBytes, 128000000000);
    expect(status.usedBytes, 384000000000);
    expect(status.usagePercent, 75);
    expect(status.healthLabel, '良好');
  });

  test('reports unsupported when drive status runs outside Windows', () async {
    final service = DriveStatusService(isWindowsOverride: false);

    final status = await service.loadDrive('C');

    expect(status.isSupported, isFalse);
    expect(status.message, contains('仅支持 Windows'));
  });
}
