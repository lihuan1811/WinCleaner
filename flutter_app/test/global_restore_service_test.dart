import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/ad_block_service.dart';
import 'package:wincleaner_desktop/services/app_data_migration_service.dart';
import 'package:wincleaner_desktop/services/global_restore_service.dart';
import 'package:wincleaner_desktop/services/operation_log_service.dart';
import 'package:wincleaner_desktop/services/windows_optimization_service.dart';

void main() {
  test('operation log appends and reads newest entries first', () async {
    final tempDir = await Directory.systemTemp.createTemp('operation-log-');
    addTearDown(() => tempDir.delete(recursive: true));
    final service = OperationLogService(
      logFile: File('${tempDir.path}${Platform.pathSeparator}operation.log'),
    );

    await service.append(
      OperationLogEntry(
        timestamp: DateTime(2026, 6, 20, 10),
        module: '清理',
        action: 'scan',
        detail: 'ok',
      ),
    );
    await service.append(
      OperationLogEntry(
        timestamp: DateTime(2026, 6, 20, 11),
        module: '优化',
        action: 'restore',
        detail: 'done',
      ),
    );

    final entries = await service.read();

    expect(entries, hasLength(2));
    expect(entries.first.module, '优化');
    expect(entries.last.action, 'scan');
  });

  test('global restore disables ad block and reverts optimization actions',
      () async {
    final tempDir = await Directory.systemTemp.createTemp('global-restore-');
    addTearDown(() => tempDir.delete(recursive: true));
    final hostsFile = File('${tempDir.path}${Platform.pathSeparator}hosts')
      ..writeAsStringSync(
        '${AdBlockService.beginMarker}\n0.0.0.0 ads.test\n${AdBlockService.endMarker}\n',
      );
    final calls = <String>[];
    final restore = GlobalRestoreService(
      adBlockService: AdBlockService(
        hostsFile: hostsFile,
        backupDirectory:
            Directory('${tempDir.path}${Platform.pathSeparator}backup'),
        flushDns: false,
      ),
      windowsOptimizationService: WindowsOptimizationService(
        isWindowsOverride: true,
        actions: const [
          WindowsOptimizationAction(
            id: 'restore_me',
            title: '可还原优化',
            description: 'test',
            category: '测试',
            riskLabel: '低风险',
            commands: [],
            revertCommands: [
              WindowsOptimizationCommand(
                executable: 'reg',
                arguments: ['add', r'HKCU\Test', '/f'],
                description: 'restore',
              ),
            ],
          ),
        ],
        processRunner: (exe, args) async {
          calls.add('$exe ${args.join(' ')}');
          return ProcessResult(1, 0, 'restored', '');
        },
      ),
      appDataMigrationService: AppDataMigrationService(
        historyFile:
            File('${tempDir.path}${Platform.pathSeparator}history.json'),
        isWindowsOverride: true,
      ),
      logService: OperationLogService(
        logFile: File('${tempDir.path}${Platform.pathSeparator}operation.log'),
      ),
    );

    final result = await restore.restoreAll();

    expect(result.success, isTrue);
    expect(await hostsFile.readAsString(), isNot(contains('ads.test')));
    expect(calls.single, contains(r'HKCU\Test'));
    expect(result.output, contains('恢复 可还原优化'));
  });
}
