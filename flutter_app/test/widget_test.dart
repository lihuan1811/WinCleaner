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

  testWidgets('primary navigation opens distinct feature centers', (
    tester,
  ) async {
    useDesktopTestWindow(tester);

    await tester.pumpWidget(
      const WinCleanerApp(installedAppsService: _FakeInstalledAppsService()),
    );
    await tester.pumpAndSettle();

    expect(find.text('C盘清理工作台'), findsOneWidget);

    await tester.tap(find.text('系统优化'));
    await tester.pumpAndSettle();
    expect(find.text('系统优化中心'), findsOneWidget);
    expect(find.text('广告清理'), findsWidgets);
    expect(find.text('碎片整理'), findsWidgets);
    expect(find.text('Windows 设置优化'), findsWidgets);
    expect(find.text('无效快捷方式'), findsWidgets);
    expect(find.text('右键菜单清理'), findsWidgets);
    expect(find.text('卸载残留注册表'), findsWidgets);
    expect(find.text('定时任务'), findsWidgets);
    expect(find.text('规则商店'), findsWidgets);

    await tester.tap(find.text('Windows 设置优化').first);
    await tester.pumpAndSettle();
    expect(find.text('刷新 DNS 缓存'), findsOneWidget);

    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('文件管理'));
    await tester.pumpAndSettle();
    expect(find.text('文件管理中心'), findsOneWidget);
    expect(find.text('重复文件'), findsWidgets);
    expect(find.text('超大文件'), findsWidgets);
    expect(find.text('空文件夹'), findsWidgets);
    expect(find.text('C盘瘦身'), findsWidgets);
  });

  testWidgets('dashboard tool cards open their feature dialogs', (
    tester,
  ) async {
    useDesktopTestWindow(tester);

    await tester.pumpWidget(
      const WinCleanerApp(installedAppsService: _FakeInstalledAppsService()),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('广告清理').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('广告清理').first);
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('启用屏蔽'), findsOneWidget);

    await tester.tap(find.text('关闭'));
    await tester.pump(const Duration(milliseconds: 300));

    await tester.ensureVisible(find.text('重复文件').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('重复文件').first);
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('扫描重复文件'), findsOneWidget);
  });

  testWidgets('new maintenance tool cards open action dialogs', (tester) async {
    useDesktopTestWindow(tester);

    await tester.pumpWidget(
      const WinCleanerApp(installedAppsService: _FakeInstalledAppsService()),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('系统优化'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('无效快捷方式').first);
    await tester.pumpAndSettle();
    expect(find.text('扫描快捷方式'), findsOneWidget);

    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('定时任务').first);
    await tester.pumpAndSettle();
    expect(find.text('创建每日任务'), findsOneWidget);

    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('规则商店').first);
    await tester.pumpAndSettle();
    expect(find.text('通用应用缓存'), findsOneWidget);

    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('文件管理'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('空文件夹').first);
    await tester.pumpAndSettle();
    expect(find.text('扫描空文件夹'), findsOneWidget);

    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('C盘瘦身').first);
    await tester.pumpAndSettle();
    expect(find.text('AppData 迁移瘦身'), findsOneWidget);
    expect(find.text('扫描大目录'), findsOneWidget);
    expect(find.text('执行迁移'), findsOneWidget);
  });

  testWidgets('about and settings actions are clickable', (tester) async {
    useDesktopTestWindow(tester);

    await tester.pumpWidget(
      const WinCleanerApp(installedAppsService: _FakeInstalledAppsService()),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('设置'));
    await tester.pumpAndSettle();
    expect(find.text('设置'), findsWidgets);

    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('关于我们'));
    await tester.pumpAndSettle();
    expect(find.text('关于 WinCleaner'), findsOneWidget);
  });

  testWidgets('search and account actions provide feedback', (tester) async {
    useDesktopTestWindow(tester);

    await tester.pumpWidget(
      const WinCleanerApp(installedAppsService: _FakeInstalledAppsService()),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('搜索'));
    await tester.pumpAndSettle();
    expect(find.text('搜索工具'), findsOneWidget);

    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Administrator'));
    await tester.pumpAndSettle();
    expect(find.text('账户'), findsOneWidget);
  });
}
