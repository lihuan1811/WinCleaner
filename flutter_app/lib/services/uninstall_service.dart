import 'dart:io';

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

class UninstallService {
  Future<Process> launch(String rawCommand) {
    if (!Platform.isWindows) {
      throw UnsupportedError('卸载执行仅支持 Windows');
    }

    final command = UninstallCommand.parse(rawCommand);
    return Process.start(command.executable, command.arguments,
        mode: ProcessStartMode.detached);
  }
}
