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
    InstallLocation    REG_SZ    C:\Program Files\Example
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
    expect(apps.single.sizeBytes, 25 * 1024 * 1024);
    expect(apps.single.installLocation, r'C:\Program Files\Example');
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

  test('parses UWP PowerShell JSON rows', () {
    const output = r'''
[
  {
    "Name": "Microsoft.WindowsCalculator",
    "Publisher": "CN=Microsoft Corporation",
    "Version": "11.2405.2.0",
    "InstallLocation": "C:\\Program Files\\WindowsApps\\Calculator",
    "PackageFullName": "Microsoft.WindowsCalculator_11.2405.2.0_x64__8wekyb3d8bbwe"
  }
]
''';

    final apps = InstalledAppsService.parseUwpJson(output);

    expect(apps, hasLength(1));
    expect(apps.single.name, 'Microsoft.WindowsCalculator');
    expect(apps.single.source, 'UWP');
    expect(apps.single.isUwp, isTrue);
    expect(apps.single.installLocation,
        r'C:\Program Files\WindowsApps\Calculator');
    expect(apps.single.uninstallCommand, contains('Remove-AppxPackage'));
    expect(apps.single.uninstallCommand,
        contains('Microsoft.WindowsCalculator_11.2405.2.0_x64__8wekyb3d8bbwe'));
  });
}
