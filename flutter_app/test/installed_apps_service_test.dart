import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/installed_apps_service.dart';

void main() {
  test('parses Windows uninstall registry query output', () {
    const output = r'''
HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Uninstall\Example
    DisplayName    REG_SZ    Example App
    DisplayVersion    REG_SZ    1.2.3
    Publisher    REG_SZ    Example Inc.
    InstallDate    REG_SZ    20240601
    EstimatedSize    REG_DWORD    0x6400
    UninstallString    REG_SZ    "C:\Program Files\Example\uninstall.exe" /remove

HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Uninstall\Hidden
    DisplayVersion    REG_SZ    9.9.9
''';

    final apps = InstalledAppsService.parseRegistryOutput(output);

    expect(apps, hasLength(1));
    expect(apps.single.name, 'Example App');
    expect(apps.single.publisher, 'Example Inc.');
    expect(apps.single.version, '1.2.3');
    expect(apps.single.installDate, '2024-06-01');
    expect(apps.single.sizeLabel, '25 MB');
    expect(apps.single.uninstallCommand,
        r'"C:\Program Files\Example\uninstall.exe" /remove');
  });

  test('deduplicates apps by name and uninstall command', () {
    const output = r'''
HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Uninstall\Example
    DisplayName    REG_SZ    Example App
    UninstallString    REG_SZ    MsiExec.exe /I{ABC}

HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Uninstall\Example
    DisplayName    REG_SZ    Example App
    UninstallString    REG_SZ    MsiExec.exe /I{ABC}
''';

    final apps = InstalledAppsService.parseRegistryOutput(output);

    expect(apps, hasLength(1));
  });
}
