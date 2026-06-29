import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/screens/dashboard_screen.dart';
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
          group: '系统临时文件',
          risk: CleanupRisk.safe,
          recommended: true,
          canClean: true,
          itemCount: 2,
          totalBytes: 12 * 1024 * 1024,
          scannedPathCount: 1,
          errors: [],
        ),
        CleanupCategoryResult(
          id: 'edgecore_old_versions',
          name: 'EdgeCore 旧版本更新',
          description: 'Microsoft EdgeCore 旧版本目录，仅统计不直接清理',
          group: '浏览器缓存',
          risk: CleanupRisk.caution,
          recommended: false,
          canClean: false,
          itemCount: 7,
          totalBytes: 664 * 1024 * 1024,
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
    tester.view
      ..physicalSize = const Size(1500, 1000)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        theme: WinCleanerTheme.light(),
        home: DashboardScreen(
          driveStatusService: _FakeDriveStatusService(),
          cleanupScanService: _FakeCleanupScanService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('375.00 GB'), findsOneWidget);
    expect(find.text('125.00 GB'), findsOneWidget);
    expect(find.text('75%'), findsAtLeastNWidgets(1));

    await tester.tap(find.text('一键开始扫描'));
    await tester.pumpAndSettle();

    expect(find.text('发现 9 个可清理项目'), findsAtLeastNWidgets(1));
    expect(find.text('676.0 MB'), findsAtLeastNWidgets(1));
    expect(
      find.byKey(const ValueKey('scan-preview-edgecore_old_versions')),
      findsOneWidget,
    );

    await tester.tap(find.text('详细报告'));
    await tester.pumpAndSettle();

    expect(find.text('扫描详细报告'), findsOneWidget);
    expect(find.text('临时文件'), findsAtLeastNWidgets(1));
    expect(find.byKey(const ValueKey('scan-logo-edge')), findsWidgets);
    expect(find.text('仅扫描'), findsAtLeastNWidgets(1));
    expect(find.textContaining('全屏'), findsNothing);
    expect(find.byIcon(Icons.fullscreen), findsNothing);
  });
}
