import 'dart:io';

typedef ProcessRunner = Future<ProcessResult> Function(
  String executable,
  List<String> arguments,
);

class WindowsOptimizationCommand {
  const WindowsOptimizationCommand({
    required this.executable,
    required this.arguments,
    required this.description,
  });

  final String executable;
  final List<String> arguments;
  final String description;

  String get commandLine => '$executable ${arguments.join(' ')}';
}

class WindowsOptimizationAction {
  const WindowsOptimizationAction({
    required this.id,
    required this.title,
    required this.description,
    required this.category,
    required this.riskLabel,
    required this.commands,
    this.revertCommands = const [],
    this.requiresAdmin = false,
  });

  final String id;
  final String title;
  final String description;
  final String category;
  final String riskLabel;
  final List<WindowsOptimizationCommand> commands;
  final List<WindowsOptimizationCommand> revertCommands;
  final bool requiresAdmin;

  bool get canRevert => revertCommands.isNotEmpty;
}

class WindowsOptimizationCommandResult {
  const WindowsOptimizationCommandResult({
    required this.command,
    required this.exitCode,
    required this.output,
  });

  final WindowsOptimizationCommand command;
  final int exitCode;
  final String output;

  bool get success => exitCode == 0;
}

class WindowsOptimizationResult {
  const WindowsOptimizationResult({
    required this.actionId,
    required this.title,
    required this.commandResults,
    required this.unsupported,
  });

  final String actionId;
  final String title;
  final List<WindowsOptimizationCommandResult> commandResults;
  final bool unsupported;

  bool get success =>
      !unsupported &&
      commandResults.isNotEmpty &&
      commandResults.every((r) => r.success);

  String get output {
    if (unsupported) {
      return '该优化仅支持在 Windows 上执行。';
    }
    return commandResults.map((result) {
      final body =
          result.output.trim().isEmpty ? '命令无输出' : result.output.trim();
      return '${result.command.commandLine}\n退出码 ${result.exitCode}\n$body';
    }).join('\n\n');
  }
}

class WindowsOptimizationService {
  WindowsOptimizationService({
    bool? isWindowsOverride,
    ProcessRunner? processRunner,
    List<WindowsOptimizationAction>? actions,
  })  : _isWindowsOverride = isWindowsOverride,
        _processRunner = processRunner ?? Process.run,
        _actions = actions ?? defaultActions();

  final bool? _isWindowsOverride;
  final ProcessRunner _processRunner;
  final List<WindowsOptimizationAction> _actions;

  bool get _isWindows => _isWindowsOverride ?? Platform.isWindows;

  List<WindowsOptimizationAction> get actions => List.unmodifiable(_actions);

  Future<WindowsOptimizationResult> apply(String actionId) {
    final action = _findAction(actionId);
    return _run(action, action.commands);
  }

  Future<WindowsOptimizationResult> revert(String actionId) async {
    final action = _findAction(actionId);
    if (action.revertCommands.isEmpty) {
      return WindowsOptimizationResult(
        actionId: action.id,
        title: action.title,
        commandResults: const [],
        unsupported: false,
      );
    }
    return _run(action, action.revertCommands);
  }

  Future<WindowsOptimizationResult> _run(
    WindowsOptimizationAction action,
    List<WindowsOptimizationCommand> commands,
  ) async {
    if (!_isWindows) {
      return WindowsOptimizationResult(
        actionId: action.id,
        title: action.title,
        commandResults: const [],
        unsupported: true,
      );
    }

    final results = <WindowsOptimizationCommandResult>[];
    for (final command in commands) {
      try {
        final result =
            await _processRunner(command.executable, command.arguments);
        final output = [
          if (result.stdout.toString().trim().isNotEmpty)
            result.stdout.toString().trim(),
          if (result.stderr.toString().trim().isNotEmpty)
            result.stderr.toString().trim(),
        ].join('\n');
        results.add(
          WindowsOptimizationCommandResult(
            command: command,
            exitCode: result.exitCode,
            output: output,
          ),
        );
      } on ProcessException catch (error) {
        results.add(
          WindowsOptimizationCommandResult(
            command: command,
            exitCode: error.errorCode,
            output: error.message,
          ),
        );
      }

      if (!results.last.success) {
        break;
      }
    }

    return WindowsOptimizationResult(
      actionId: action.id,
      title: action.title,
      commandResults: results,
      unsupported: false,
    );
  }

  WindowsOptimizationAction _findAction(String id) {
    return _actions.firstWhere(
      (action) => action.id == id,
      orElse: () => throw ArgumentError('未知系统优化项: $id'),
    );
  }

  static List<WindowsOptimizationAction> defaultActions() {
    return const [
      WindowsOptimizationAction(
        id: 'flush_dns',
        title: '刷新 DNS 缓存',
        description: '执行 ipconfig /flushdns，清除本机 DNS 解析缓存。',
        category: '网络',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'ipconfig',
            arguments: ['/flushdns'],
            description: '刷新 DNS 缓存',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'reset_winsock',
        title: '重置 Winsock',
        description: '执行 netsh winsock reset，修复网络协议栈异常，通常需要重启。',
        category: '网络',
        riskLabel: '中风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'netsh',
            arguments: ['winsock', 'reset'],
            description: '重置 Winsock 目录',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'reset_tcp_ip',
        title: '重置 TCP/IP',
        description: '执行 netsh int ip reset，重置 TCP/IP 配置，通常需要重启。',
        category: '网络',
        riskLabel: '中风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'netsh',
            arguments: ['int', 'ip', 'reset'],
            description: '重置 TCP/IP 配置',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'high_performance_power',
        title: '切换高性能电源计划',
        description: '执行 powercfg /setactive SCHEME_MIN，提高性能优先级。',
        category: '性能',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/setactive', 'SCHEME_MIN'],
            description: '启用高性能电源计划',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/setactive', 'SCHEME_BALANCED'],
            description: '恢复平衡电源计划',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_hibernation',
        title: '关闭休眠释放 hiberfil.sys',
        description: '执行 powercfg /hibernate off，释放休眠文件占用的系统盘空间。',
        category: '存储',
        riskLabel: '中风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/hibernate', 'off'],
            description: '关闭 Windows 休眠',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/hibernate', 'on'],
            description: '重新启用 Windows 休眠',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_game_dvr',
        title: '关闭 Game DVR 录制',
        description: '写入 HKCU GameDVR 注册表项，减少后台录制占用。',
        category: '性能',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\System\GameConfigStore',
              '/v',
              'GameDVR_Enabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭 GameConfigStore GameDVR',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR',
              '/v',
              'AppCaptureEnabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭 AppCapture',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\System\GameConfigStore',
              '/v',
              'GameDVR_Enabled',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '恢复 GameConfigStore GameDVR',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR',
              '/v',
              'AppCaptureEnabled',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '恢复 AppCapture',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_startup_delay',
        title: '关闭启动应用延迟',
        description: '写入 Explorer Serialize 注册表项，减少登录后启动项延迟。',
        category: '启动',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize',
              '/v',
              'StartupDelayInMSec',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭启动应用延迟',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'delete',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize',
              '/v',
              'StartupDelayInMSec',
              '/f',
            ],
            description: '恢复启动应用默认延迟',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_transparency',
        title: '关闭透明效果',
        description: '写入 Personalize 注册表项，降低桌面合成负担。',
        category: '视觉',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
              '/v',
              'EnableTransparency',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭透明效果',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
              '/v',
              'EnableTransparency',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '恢复透明效果',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_minimize_animation',
        title: '关闭窗口动画',
        description: '写入 WindowMetrics MinAnimate，减少窗口最小化动画。',
        category: '视觉',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Control Panel\Desktop\WindowMetrics',
              '/v',
              'MinAnimate',
              '/t',
              'REG_SZ',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭窗口动画',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Control Panel\Desktop\WindowMetrics',
              '/v',
              'MinAnimate',
              '/t',
              'REG_SZ',
              '/d',
              '1',
              '/f',
            ],
            description: '恢复窗口动画',
          ),
        ],
      ),
    ];
  }
}
