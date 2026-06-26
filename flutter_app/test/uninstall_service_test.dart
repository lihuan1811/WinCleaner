import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/models/installed_app.dart';
import 'package:wincleaner_desktop/services/uninstall_service.dart';

void main() {
  test('parses quoted uninstall command with arguments', () {
    final command = UninstallCommand.parse(
        r'"C:\Program Files\App\uninstall.exe" /remove /norestart');

    expect(command.executable, r'C:\Program Files\App\uninstall.exe');
    expect(command.arguments, ['/remove', '/norestart']);
  });

  test('converts msi install command to uninstall command', () {
    final command = UninstallCommand.parse(
        r'MsiExec.exe /I{00000000-0000-0000-0000-000000000001}');

    expect(command.executable.toLowerCase(), 'msiexec.exe');
    expect(command.arguments, ['/X{00000000-0000-0000-0000-000000000001}']);
  });

  test('rejects empty uninstall commands', () {
    expect(() => UninstallCommand.parse(''), throwsArgumentError);
  });

  test('force cleanup removes install directory and registry key', () async {
    final tempDir = await Directory.systemTemp.createTemp('force-uninstall-');
    addTearDown(() => tempDir.delete(recursive: true));
    final installDir = Directory('${tempDir.path}${Platform.pathSeparator}App')
      ..createSync();
    File('${installDir.path}${Platform.pathSeparator}app.exe')
        .writeAsStringSync('bin');
    final calls = <String>[];
    final service = UninstallService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        calls.add('$exe ${args.join(' ')}');
        return ProcessResult(1, 0, 'deleted', '');
      },
    );

    final result = await service.forceCleanup(
      InstalledApp(
        name: 'Example',
        publisher: 'Example',
        version: '1',
        sizeLabel: '1 MB',
        installDate: '-',
        source: 'Registry',
        uninstallCommand: '',
        installLocation: installDir.path,
        registryKey: r'HKCU\Software\Example',
      ),
    );

    expect(result.success, isTrue);
    expect(result.deletedPaths, contains(installDir.path));
    expect(result.registryDeleted, isTrue);
    expect(await installDir.exists(), isFalse);
    expect(calls.single, r'reg delete HKCU\Software\Example /f');
  });

  test('force cleanup runs UWP removal command when app is UWP', () async {
    final calls = <String>[];
    final service = UninstallService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        calls.add('$exe ${args.join(' ')}');
        return ProcessResult(1, 0, 'removed', '');
      },
    );

    final result = await service.forceCleanup(
      const InstalledApp(
        name: 'Calculator',
        publisher: 'Microsoft',
        version: '1',
        sizeLabel: '-',
        installDate: '-',
        source: 'UWP',
        uninstallCommand:
            'powershell -NoProfile -ExecutionPolicy Bypass -Command Remove-AppxPackage -Package Microsoft.WindowsCalculator_1',
        isUwp: true,
      ),
    );

    expect(result.success, isTrue);
    expect(calls.single, contains('Remove-AppxPackage'));
    expect(result.output, contains('removed'));
  });
}
