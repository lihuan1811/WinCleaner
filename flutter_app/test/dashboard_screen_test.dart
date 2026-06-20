import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/screens/dashboard_live_screen.dart';
import 'package:wincleaner_desktop/services/drive_status_service.dart';
import 'package:wincleaner_desktop/services/system_cleanup_scan_service.dart';
import 'package:wincleaner_desktop/theme/app_theme.dart';

class _FakeDriveStatusService extends DriveStatusService {
  _FakeDriveStatusService() : super(isWindowsOverride: true);

  @override
  Future<DriveStatus> loadDrive([String drive = 'C']) async {
    return const DriveStatus(
      drive: 'C:',
      totalBytes: 500 * 1024 * 1024 * 1024,
      freeBytes: 125 * 1024 * 1024 * 1024,
      isSupported: true,
      message: 'OK',
    );
  }
}

class _FakeCleanupScanService extends SystemCleanupScanService {
  _FakeCleanupScanService() : super(targets: const []);

  @override
  Future<CleanupScanResult> scan() async {
    return CleanupScanResult(
      startedAt: DateTime(2026, 6, 20, 10),
      completedAt: DateTime(2026, 6, 20, 10, 0, 1),
      categories: const [
        CleanupCategoryResult(
          id: 'temp',
          name: '临时文件',
          description: '系统和用户临时目录',
          itemCount: 2,
          totalBytes: 12 * 1024 * 1024,
          scannedPathCount: 1,
          errors: [],
        ),
      ],
    );
  }
}

void main() {
  testWidgets('dashboard loads real status and scan report actions', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: WinCleanerTheme.light(),
        home: DashboardLiveScreen(
          driveStatusService: _FakeDriveStatusService(),
          cleanupScanService: _FakeCleanupScanService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('375.00 GB'), findsOneWidget);
    expect(find.text('125.00 GB'), findsOneWidget);
    expect(find.text('75%'), findsOneWidget);

    await tester.tap(find.text('一键开始扫描'));
    await tester.pumpAndSettle();

    expect(find.text('发现 2 个可清理项目'), findsOneWidget);
    expect(find.text('12.0 MB'), findsAtLeastNWidgets(1));

    await tester.tap(find.text('详细报告'));
    await tester.pumpAndSettle();

    expect(find.text('扫描详细报告'), findsOneWidget);
    expect(find.text('临时文件'), findsAtLeastNWidgets(1));
  });
}
