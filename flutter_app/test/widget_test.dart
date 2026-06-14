import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/main.dart';

void main() {
  testWidgets('app shell shows primary navigation items', (tester) async {
    await tester.pumpWidget(const WinCleanerApp());

    expect(find.text('C盘清理'), findsOneWidget);
    expect(find.text('系统优化'), findsOneWidget);
    expect(find.text('软件卸载'), findsOneWidget);
    expect(find.text('文件管理'), findsOneWidget);
  });

  testWidgets('software uninstall navigation opens uninstall center', (
    tester,
  ) async {
    await tester.pumpWidget(const WinCleanerApp());

    await tester.tap(find.text('软件卸载'));
    await tester.pumpAndSettle();

    expect(find.text('软件卸载中心'), findsOneWidget);
    expect(find.text('BCU 后端未配置'), findsOneWidget);
    expect(find.text('卸载选中项'), findsOneWidget);
  });
}
