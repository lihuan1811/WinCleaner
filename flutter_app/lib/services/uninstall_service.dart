import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;

import '../models/installed_app.dart';

typedef UninstallProcessRunner = Future<ProcessResult> Function(
  String executable,
  List<String> arguments,
);

class UninstallCommand {
  const UninstallCommand({required this.executable, required this.arguments});

  final String executable;
  final List<String> arguments;

  static UninstallCommand parse(String rawCommand) {
    final command = rawCommand.trim();
    if (command.isEmpty) {
      throw ArgumentError('卸载命令为空');
    }

    final parts = _splitCommandLine(command);
    if (parts.isEmpty) {
      throw ArgumentError('卸载命令无效');
    }

    final executable = parts.first;
    final arguments = parts.skip(1).toList();
    if (_isMsiExec(executable)) {
      return UninstallCommand(
          executable: executable, arguments: _normalizeMsiArguments(arguments));
    }

    return UninstallCommand(executable: executable, arguments: arguments);
  }

  static bool _isMsiExec(String executable) {
    final normalized =
        executable.replaceAll('\\', '/').split('/').last.toLowerCase();
    return normalized == 'msiexec.exe' || normalized == 'msiexec';
  }

  static List<String> _normalizeMsiArguments(List<String> arguments) {
    return [
      for (final arg in arguments)
        if (arg.toLowerCase().startsWith('/i'))
          '/X${arg.substring(2)}'
        else if (arg.toLowerCase() == '/i')
          '/X'
        else
          arg,
    ];
  }

  static List<String> _splitCommandLine(String command) {
    final parts = <String>[];
    final buffer = StringBuffer();
    var inQuotes = false;

    for (var i = 0; i < command.length; i++) {
      final char = command[i];
      if (char == '"') {
        inQuotes = !inQuotes;
        continue;
      }
      if (!inQuotes && char.trim().isEmpty) {
        if (buffer.isNotEmpty) {
          parts.add(buffer.toString());
          buffer.clear();
        }
        continue;
      }
      buffer.write(char);
    }

    if (buffer.isNotEmpty) {
      parts.add(buffer.toString());
    }

    return parts;
  }
}

class ForceUninstallResult {
  const ForceUninstallResult({
    required this.deletedPaths,
    required this.registryDeleted,
    required this.output,
    required this.unsupported,
  });

  final List<String> deletedPaths;
  final bool registryDeleted;
  final String output;
  final bool unsupported;

  bool get success => !unsupported;
}

class UninstallService {
  UninstallService({
    bool? isWindowsOverride,
    UninstallProcessRunner? processRunner,
  })  : _isWindowsOverride = isWindowsOverride,
        _processRunner = processRunner ?? Process.run;

  final bool? _isWindowsOverride;
  final UninstallProcessRunner _processRunner;

  bool get _isWindows => _isWindowsOverride ?? (!kIsWeb && Platform.isWindows);

  Future<Process> launch(String rawCommand) {
    if (!_isWindows) {
      throw UnsupportedError('卸载执行仅支持 Windows');
    }

    final command = UninstallCommand.parse(rawCommand);
    return Process.start(command.executable, command.arguments,
        mode: ProcessStartMode.detached);
  }

  Future<ForceUninstallResult> forceCleanup(InstalledApp app) async {
    if (!_isWindows) {
      return const ForceUninstallResult(
        deletedPaths: [],
        registryDeleted: false,
        output: '强力粉碎卸载仅支持 Windows。',
        unsupported: true,
      );
    }

    final deletedPaths = <String>[];
    final output = <String>[];
    var registryDeleted = false;

    if (app.isUwp && app.uninstallCommand.trim().isNotEmpty) {
      final command = UninstallCommand.parse(app.uninstallCommand);
      final result =
          await _processRunner(command.executable, command.arguments);
      output.add(_formatProcessOutput('UWP 卸载', result));
    }

    if (app.installLocation.trim().isNotEmpty) {
      final directory = Directory(app.installLocation);
      final file = File(app.installLocation);
      try {
        if (await directory.exists()) {
          await directory.delete(recursive: true);
          deletedPaths.add(directory.path);
        } else if (await file.exists()) {
          await file.delete();
          deletedPaths.add(file.path);
        }
      } on FileSystemException catch (error) {
        output.add('${app.installLocation}: ${error.message}');
      }
    }

    if (app.registryKey.trim().isNotEmpty) {
      final result = await _processRunner('reg', [
        'delete',
        app.registryKey,
        '/f',
      ]);
      registryDeleted = result.exitCode == 0;
      output.add(_formatProcessOutput('删除卸载注册表', result));
    }

    return ForceUninstallResult(
      deletedPaths: deletedPaths,
      registryDeleted: registryDeleted,
      output: output.isEmpty ? '没有发现可清理的安装目录或注册表项' : output.join('\n\n'),
      unsupported: false,
    );
  }

  static String _formatProcessOutput(String label, ProcessResult result) {
    final body = [
      if (result.stdout.toString().trim().isNotEmpty)
        result.stdout.toString().trim(),
      if (result.stderr.toString().trim().isNotEmpty)
        result.stderr.toString().trim(),
    ].join('\n');
    return '$label\n退出码 ${result.exitCode}\n${body.isEmpty ? '命令无输出' : body}';
  }
}
