import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:wincleaner_desktop/services/disk_optimization_service.dart';

void main() {
  test('analyze calls Windows defrag with analysis arguments', () async {
    late String executable;
    late List<String> arguments;
    final service = DiskOptimizationService(
      isWindowsOverride: true,
      processRunner: (exe, args) async {
        executable = exe;
        arguments = args;
        return ProcessResult(1, 0, 'analysis ok', '');
      },
    );

    final result = await service.analyze('C');

    expect(executable, 'defrag');
    expect(arguments, ['C:', '/A', '/U', '/V']);
    expect(result.success, isTrue);
    expect(result.output, contains('analysis ok'));
  });

  test('optimize calls Windows defrag with media-aware optimization', () async {
    late List<String> arguments;
    final service = DiskOptimizationService(
      isWindowsOverride: true,
      processRunner: (_, args) async {
        arguments = args;
        return ProcessResult(1, 0, 'optimized', '');
      },
    );

    await service.optimize('D:');

    expect(arguments, ['D:', '/O', '/U', '/V']);
  });
}
