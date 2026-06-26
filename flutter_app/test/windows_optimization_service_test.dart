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
        'enable_storage_sense',
        'disable_windows_tips',
        'disable_background_apps',
        'disable_search_highlights',
        'optimize_visual_effects',
        'repair_explorer_associations',
        'clear_icon_cache',
        'office_default_optimize',
        'esports_deep_optimize',
        'nvidia_performance_tuning',
        'amd_performance_tuning',
        'gpu_restore_defaults',
        'disable_windows_update',
        'enable_windows_update',
        'defender_temp_disable',
        'defender_policy_disable',
        'defender_restore',
        'edge_silent_install',
        'edge_force_remove',
        'repair_browser_hijack',
      ]),
    );
    expect(actions.length, greaterThanOrEqualTo(14));
    expect(actions.firstWhere((action) => action.id == 'flush_dns').commands,
        isNotEmpty);
    expect(
      actions
          .firstWhere((action) => action.id == 'repair_explorer_associations')
          .requiresAdmin,
      isTrue,
    );
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

  test('expanded Windows settings write concrete registry values', () async {
    final calls = <String>[];
    final service = WindowsOptimizationService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        calls.add('$exe ${args.join(' ')}');
        return ProcessResult(1, 0, '', '');
      },
    );

    final result = await service.apply('disable_windows_tips');

    expect(result.success, isTrue);
    expect(calls, hasLength(greaterThanOrEqualTo(3)));
    expect(calls.join('\n'), contains('ContentDeliveryManager'));
    expect(calls.join('\n'), contains('SubscribedContent-338389Enabled'));
    expect(calls.join('\n'), contains('SystemPaneSuggestionsEnabled'));
  });

  test('shell repair action restores executable and shortcut associations',
      () async {
    final calls = <String>[];
    final service = WindowsOptimizationService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        calls.add('$exe ${args.join(' ')}');
        return ProcessResult(1, 0, '', '');
      },
    );

    final result = await service.apply('repair_explorer_associations');

    expect(result.success, isTrue);
    expect(calls.join('\n'), contains(r'HKCR\.exe'));
    expect(calls.join('\n'), contains(r'HKCR\exefile\shell\open\command'));
    expect(calls.join('\n'), contains(r'HKCR\lnkfile'));
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

  test('advanced control actions expose concrete Windows commands', () {
    final actions = WindowsOptimizationService.defaultActions();
    final byId = {for (final action in actions) action.id: action};

    expect(byId['disable_windows_update']!.commands.single.commandLine,
        contains('sc config wuauserv start= disabled'));
    expect(byId['disable_windows_update']!.requiresAdmin, isTrue);
    expect(byId['disable_windows_update']!.canRevert, isTrue);
    expect(byId['defender_temp_disable']!.commands.single.commandLine,
        contains('Set-MpPreference'));
    expect(byId['defender_policy_disable']!.commands.first.commandLine,
        contains(r'HKLM\SOFTWARE\Policies\Microsoft\Windows Defender'));
    expect(byId['edge_silent_install']!.commands.single.commandLine,
        contains('winget install --id Microsoft.Edge'));
    expect(byId['edge_force_remove']!.riskLabel, '高风险');
    expect(
        byId['repair_browser_hijack']!
            .commands
            .map((command) => command.commandLine)
            .join('\n'),
        contains('winsock reset'));
  });

  test('gpu and optimization presets contain expected command groups', () {
    final actions = WindowsOptimizationService.defaultActions();
    final byId = {for (final action in actions) action.id: action};

    expect(byId['office_default_optimize']!.category, '基础优化');
    expect(
        byId['office_default_optimize']!
            .commands
            .map((command) => command.commandLine)
            .join('\n'),
        contains('StorageSense'));
    expect(
        byId['esports_deep_optimize']!
            .commands
            .map((command) => command.commandLine)
            .join('\n'),
        contains('powercfg /setactive SCHEME_MIN'));
    expect(byId['nvidia_performance_tuning']!.commands.last.commandLine,
        contains(r'NVIDIA\DXCache'));
    expect(byId['amd_performance_tuning']!.commands.last.commandLine,
        contains(r'AMD\DxCache'));
    expect(byId['gpu_restore_defaults']!.commands.single.commandLine,
        contains('SCHEME_BALANCED'));
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
