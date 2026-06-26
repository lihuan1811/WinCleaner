import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/system_repair_service.dart';

void main() {
  test('default repair actions include safe and deep repair groups', () {
    final actions = SystemRepairService.defaultActions();

    expect(actions.map((action) => action.id), contains('sfc_scan'));
    expect(actions.map((action) => action.id), contains('dism_restore_health'));
    expect(actions.where((action) => action.recommended), isNotEmpty);
    expect(actions.where((action) => action.deep), isNotEmpty);
  });

  test('recommended repair preset selects only safe repair actions', () {
    final preset = SystemRepairService.recommendedPreset();

    expect(preset.map((action) => action.id), [
      'sfc_scan',
      'chkdsk_scan',
      'flush_dns',
      'winsock_reset',
    ]);
    expect(preset.every((action) => action.risk == RepairRisk.safe), isTrue);
  });

  test('runs repair actions through cmd with the expected command line',
      () async {
    final calls = <List<String>>[];
    final service = SystemRepairService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        calls.add([exe, ...args]);
        return ProcessResult(1, 0, 'ok', '');
      },
    );

    final result = await service.runAction(
      SystemRepairService.defaultActions().firstWhere(
        (action) => action.id == 'sfc_scan',
      ),
    );

    expect(result.success, isTrue);
    expect(calls.single, ['cmd', '/C', 'sfc /scannow']);
  });

  test('reports unsupported outside Windows', () async {
    const service = SystemRepairService(isWindowsOverride: false);
    final result = await service.runAction(
      SystemRepairService.defaultActions().first,
    );

    expect(result.unsupported, isTrue);
    expect(result.output, contains('仅支持 Windows'));
  });
}
