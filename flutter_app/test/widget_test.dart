import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/main.dart';
import 'package:wincleaner_desktop/models/installed_app.dart';
import 'package:wincleaner_desktop/services/installed_apps_service.dart';

class _FakeInstalledAppsService extends InstalledAppsService {
  const _FakeInstalledAppsService();

  @override
  Future<List<InstalledApp>> loadInstalledApps() async {
    return sampleInstalledApps;
  }
}

void main() {
  void useDesktopTestWindow(WidgetTester tester) {
    tester.view
      ..physicalSize = const Size(1500, 1000)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets('app shell shows primary navigation items', (tester) async {
    useDesktopTestWindow(tester);

    await tester.pumpWidget(const WinCleanerApp());
    await tester.pumpAndSettle();

    expect(find.text('C盘清理'), findsOneWidget);
    expect(find.text('系统优化'), findsOneWidget);
    expect(find.text('软件卸载'), findsOneWidget);
    expect(find.text('文件管理'), findsOneWidget);
  });

  testWidgets('software uninstall navigation opens uninstall center', (
    tester,
  ) async {
    useDesktopTestWindow(tester);

    await tester.pumpWidget(
      const WinCleanerApp(installedAppsService: _FakeInstalledAppsService()),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('软件卸载'));
    await tester.pumpAndSettle();

    expect(find.text('软件卸载中心'), findsOneWidget);
    expect(find.text('BCU 后端未配置'), findsOneWidget);
    expect(find.text('卸载选中项'), findsOneWidget);
  });
}
