import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/windows_maintenance_service.dart';

void main() {
  test('parses invalid shortcut PowerShell JSON rows', () {
    const output = '''
[
  {"Path":"C:\\\\Users\\\\Ada\\\\Desktop\\\\Old.lnk","TargetPath":"Z:\\\\missing.exe","Reason":"目标不存在"},
  {"Path":"C:\\\\Users\\\\Ada\\\\Desktop\\\\Blank.lnk","TargetPath":"","Reason":"没有目标"}
]
''';

    final entries = WindowsMaintenanceService.parseInvalidShortcutRows(output);

    expect(entries, hasLength(2));
    expect(entries.first.path, r'C:\Users\Ada\Desktop\Old.lnk');
    expect(entries.first.targetPath, r'Z:\missing.exe');
    expect(entries.last.reason, '没有目标');
  });

  test('parses registry paths from reg query output', () {
    const output = r'''
HKEY_CLASSES_ROOT\Directory\shell\GitExt
    (Default)    REG_SZ    Git GUI Here

HKEY_CLASSES_ROOT\Directory\shell\SafeOpen
    (Default)    REG_SZ    open
''';

    final entries = WindowsMaintenanceService.parseContextMenuRegistry(output);

    expect(entries, hasLength(2));
    expect(entries.first.path, r'HKEY_CLASSES_ROOT\Directory\shell\GitExt');
    expect(entries.first.name, 'GitExt');
    expect(entries.first.detail, contains('Git GUI Here'));
  });

  test('delete registry entry runs reg delete with force', () async {
    late String executable;
    late List<String> arguments;
    final service = WindowsMaintenanceService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        executable = exe;
        arguments = args;
        return ProcessResult(1, 0, 'deleted', '');
      },
    );

    final result = await service.deleteRegistryEntry(
      r'HKCU\Software\Classes\Example',
    );

    expect(result.success, isTrue);
    expect(executable, 'reg');
    expect(arguments, [
      'delete',
      r'HKCU\Software\Classes\Example',
      '/f',
    ]);
  });

  test('builds scheduled cleanup task command', () async {
    late List<String> arguments;
    final service = WindowsMaintenanceService(
      isWindowsOverride: true,
      processRunner: (_, args) async {
        arguments = args;
        return ProcessResult(1, 0, 'created', '');
      },
    );

    final result = await service.createScheduledCleanupTask(
      taskName: 'DailyClean',
      executablePath: r'C:\Tools\WinCleaner.exe',
      schedule: MaintenanceSchedule.daily,
      time: '09:30',
    );

    expect(result.success, isTrue);
    expect(arguments, containsAll(['/Create', '/SC', 'DAILY', '/ST', '09:30']));
    expect(arguments, contains('/RL'));
    expect(arguments.join(' '), contains(r'C:\Tools\WinCleaner.exe'));
  });
}
