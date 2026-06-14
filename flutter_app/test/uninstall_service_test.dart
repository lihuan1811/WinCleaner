import 'package:flutter_test/flutter_test.dart';
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
}
