import 'ad_block_service.dart';
import 'app_data_migration_service.dart';
import 'operation_log_service.dart';
import 'windows_optimization_service.dart';

class GlobalRestoreStep {
  const GlobalRestoreStep({
    required this.name,
    required this.success,
    required this.output,
  });

  final String name;
  final bool success;
  final String output;
}

class GlobalRestoreResult {
  const GlobalRestoreResult({required this.steps});

  final List<GlobalRestoreStep> steps;

  bool get success => steps.every((step) => step.success);

  String get output => steps
      .map((step) =>
          '${step.success ? 'OK' : 'FAIL'} ${step.name}\n${step.output}')
      .join('\n\n');
}

class GlobalRestoreService {
  GlobalRestoreService({
    AdBlockService? adBlockService,
    WindowsOptimizationService? windowsOptimizationService,
    AppDataMigrationService? appDataMigrationService,
    OperationLogService? logService,
  })  : _adBlockService = adBlockService ?? AdBlockService(),
        _windowsOptimizationService =
            windowsOptimizationService ?? WindowsOptimizationService(),
        _appDataMigrationService =
            appDataMigrationService ?? AppDataMigrationService(),
        _logService = logService ?? OperationLogService();

  final AdBlockService _adBlockService;
  final WindowsOptimizationService _windowsOptimizationService;
  final AppDataMigrationService _appDataMigrationService;
  final OperationLogService _logService;

  Future<GlobalRestoreResult> restoreAll() async {
    final steps = <GlobalRestoreStep>[];

    try {
      final status = await _adBlockService.disable();
      steps.add(
        GlobalRestoreStep(
          name: '恢复 hosts 广告屏蔽',
          success: true,
          output: status.message,
        ),
      );
    } catch (error) {
      steps.add(
        GlobalRestoreStep(
          name: '恢复 hosts 广告屏蔽',
          success: false,
          output: error.toString(),
        ),
      );
    }

    for (final action in _windowsOptimizationService.actions.where(
      (action) => action.canRevert,
    )) {
      try {
        final result = await _windowsOptimizationService.revert(action.id);
        steps.add(
          GlobalRestoreStep(
            name: '恢复 ${action.title}',
            success: result.success || result.unsupported,
            output: result.output,
          ),
        );
      } catch (error) {
        steps.add(
          GlobalRestoreStep(
            name: '恢复 ${action.title}',
            success: false,
            output: error.toString(),
          ),
        );
      }
    }

    for (final record in _appDataMigrationService.loadHistory()) {
      try {
        final result = await _appDataMigrationService.restoreMigration(record);
        steps.add(
          GlobalRestoreStep(
            name: '还原 AppData ${record.name}',
            success: result.success || result.unsupported,
            output: result.output,
          ),
        );
      } catch (error) {
        steps.add(
          GlobalRestoreStep(
            name: '还原 AppData ${record.name}',
            success: false,
            output: error.toString(),
          ),
        );
      }
    }

    final result = GlobalRestoreResult(steps: steps);
    await _logService.append(
      OperationLogEntry(
        timestamp: DateTime.now(),
        module: '全局还原',
        action: 'restoreAll',
        detail: result.output,
      ),
    );
    return result;
  }
}
