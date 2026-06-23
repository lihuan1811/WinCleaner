import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/windows_optimization_service.dart';

void main() {
  test('default actions expose real Windows optimization tasks', () {
    final actions = WindowsOptimizationService.defaultActions();
    final ids = actions.map((action) => action.id);

    expect(
      ids,
      containsAll([
        'flush_dns',
        'reset_winsock',
        'high_performance_power',
        'disable_hibernation',
        'disable_game_dvr',
        'disable_startup_delay',
        'disable_transparency',
      ]),
    );
    expect(actions.firstWhere((action) => action.id == 'flush_dns').commands,
        isNotEmpty);
  });

  test('apply runs configured Windows command through runner', () async {
    late String executable;
    late List<String> arguments;
    final service = WindowsOptimizationService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        executable = exe;
        arguments = args;
        return ProcessResult(1, 0, 'dns ok', '');
      },
    );

    final result = await service.apply('flush_dns');

    expect(executable, 'ipconfig');
    expect(arguments, ['/flushdns']);
    expect(result.success, isTrue);
    expect(result.output, contains('dns ok'));
  });

  test('registry optimization runs all configured commands', () async {
    final calls = <String>[];
    final service = WindowsOptimizationService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        calls.add('$exe ${args.join(' ')}');
        return ProcessResult(1, 0, '', '');
      },
    );

    final result = await service.apply('disable_game_dvr');

    expect(result.success, isTrue);
    expect(calls, hasLength(2));
    expect(calls.first, contains(r'HKCU\System\GameConfigStore'));
    expect(calls.last,
        contains(r'HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR'));
  });

  test('revert runs restore command when available', () async {
    late List<String> arguments;
    final service = WindowsOptimizationService(
      isWindowsOverride: true,
      processRunner: (_, args) async {
        arguments = args;
        return ProcessResult(1, 0, 'hibernation restored', '');
      },
    );

    final result = await service.revert('disable_hibernation');

    expect(arguments, ['/hibernate', 'on']);
    expect(result.success, isTrue);
    expect(result.output, contains('hibernation restored'));
  });

  test('reports unsupported outside Windows without running commands',
      () async {
    var ran = false;
    final service = WindowsOptimizationService(
      isWindowsOverride: false,
      processRunner: (_, __) async {
        ran = true;
        return ProcessResult(1, 0, '', '');
      },
    );

    final result = await service.apply('flush_dns');

    expect(result.success, isFalse);
    expect(result.unsupported, isTrue);
    expect(ran, isFalse);
  });
}
