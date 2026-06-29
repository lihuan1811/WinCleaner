import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;

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

  bool get _isWindows => _isWindowsOverride ?? (!kIsWeb && Platform.isWindows);

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
      WindowsOptimizationAction(
        id: 'enable_storage_sense',
        title: '开启存储感知',
        description: '写入 Storage Sense 策略，启用 Windows 自动清理临时文件。',
        category: '存储',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy',
              '/v',
              '01',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '启用存储感知',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy',
              '/v',
              '04',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '允许清理临时文件',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy',
              '/v',
              '01',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭存储感知',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_windows_tips',
        title: '关闭 Windows 推荐与提示',
        description: '关闭开始菜单建议、欢迎体验和系统提示，减少广告式推荐。',
        category: '隐私',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager',
              '/v',
              'SubscribedContent-338389Enabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭 Windows 使用技巧推送',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager',
              '/v',
              'SoftLandingEnabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭欢迎体验建议',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager',
              '/v',
              'SystemPaneSuggestionsEnabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭系统面板建议',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager',
              '/v',
              'SubscribedContent-338388Enabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭设置页建议内容',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager',
              '/v',
              'SubscribedContent-338389Enabled',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '恢复 Windows 使用技巧推送',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_background_apps',
        title: '限制后台应用',
        description: '写入 BackgroundAccessApplications，减少商店应用后台运行。',
        category: '性能',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications',
              '/v',
              'GlobalUserDisabled',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '禁止后台应用全局运行',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications',
              '/v',
              'GlobalUserDisabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '恢复后台应用默认策略',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_search_highlights',
        title: '关闭搜索高亮',
        description: '关闭任务栏搜索框的联网高亮和推荐内容。',
        category: '隐私',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\SearchSettings',
              '/v',
              'IsDynamicSearchBoxEnabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭搜索框动态内容',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\SearchSettings',
              '/v',
              'IsDynamicSearchBoxEnabled',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '恢复搜索框动态内容',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'optimize_visual_effects',
        title: '调整为最佳性能视觉效果',
        description: '设置 Explorer VisualFXSetting，减少动画和视觉特效。',
        category: '视觉',
        riskLabel: '中风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects',
              '/v',
              'VisualFXSetting',
              '/t',
              'REG_DWORD',
              '/d',
              '2',
              '/f',
            ],
            description: '调整视觉效果为最佳性能',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects',
              '/v',
              'VisualFXSetting',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '恢复 Windows 自动选择视觉效果',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'clear_icon_cache',
        title: '重建图标缓存',
        description: '结束并重启资源管理器，删除 IconCache.db 以修复图标异常。',
        category: '修复',
        riskLabel: '中风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'taskkill /f /im explorer.exe & del /a /q "%LOCALAPPDATA%\IconCache.db" & start explorer.exe',
            ],
            description: '重建图标缓存并重启 Explorer',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'restart_explorer',
        title: '重启资源管理器',
        description: '重新启动 explorer.exe，让部分注册表优化立即生效。',
        category: '修复',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'taskkill /f /im explorer.exe & start explorer.exe',
            ],
            description: '重启 Explorer',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'office_default_optimize',
        title: '默认优化（办公稳定）',
        description: '关闭推荐内容、后台应用、启动延迟并开启存储感知，偏保守，适合日常办公。',
        category: '基础优化',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager',
              '/v',
              'SubscribedContent-338389Enabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭 Windows 使用技巧推送',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications',
              '/v',
              'GlobalUserDisabled',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '限制后台应用',
          ),
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
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy',
              '/v',
              '01',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '开启存储感知',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager',
              '/v',
              'SubscribedContent-338389Enabled',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '恢复 Windows 使用技巧推送',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications',
              '/v',
              'GlobalUserDisabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '恢复后台应用默认策略',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'esports_deep_optimize',
        title: '深度优化（电竞提帧）',
        description: '切换高性能电源、关闭休眠、关闭录制和动画，可能影响办公体验。',
        category: '基础优化',
        riskLabel: '中风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/setactive', 'SCHEME_MIN'],
            description: '启用高性能电源计划',
          ),
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/hibernate', 'off'],
            description: '关闭休眠',
          ),
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
            description: '关闭 Game DVR',
          ),
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
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCU\Software\Microsoft\Windows\CurrentVersion\PushNotifications',
              '/v',
              'ToastEnabled',
              '/t',
              'REG_DWORD',
              '/d',
              '0',
              '/f',
            ],
            description: '关闭通知横幅',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/setactive', 'SCHEME_BALANCED'],
            description: '恢复平衡电源计划',
          ),
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/hibernate', 'on'],
            description: '重新启用休眠',
          ),
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
            description: '恢复 Game DVR',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'nvidia_performance_tuning',
        title: 'NVIDIA 一键调优',
        description: '切换高性能电源并清理 NVIDIA DXCache、GLCache 与 ComputeCache。',
        category: '显卡优化',
        riskLabel: '中风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/setactive', 'SCHEME_MIN'],
            description: '启用高性能电源计划',
          ),
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'del /f /s /q "%LOCALAPPDATA%\NVIDIA\DXCache\*" "%LOCALAPPDATA%\NVIDIA\GLCache\*" "%LOCALAPPDATA%\NVIDIA Corporation\NV_Cache\*" 2>nul',
            ],
            description: '清理 NVIDIA 着色器缓存',
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
        id: 'amd_performance_tuning',
        title: 'AMD 一键调优',
        description: '切换高性能电源并清理 AMD DXCache、DxcCache 与 GLCache。',
        category: '显卡优化',
        riskLabel: '中风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/setactive', 'SCHEME_MIN'],
            description: '启用高性能电源计划',
          ),
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'del /f /s /q "%LOCALAPPDATA%\AMD\DxCache\*" "%LOCALAPPDATA%\AMD\DxcCache\*" "%LOCALAPPDATA%\AMD\GLCache\*" 2>nul',
            ],
            description: '清理 AMD 着色器缓存',
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
        id: 'gpu_restore_defaults',
        title: '恢复显卡默认设置',
        description: '恢复平衡电源计划并保留驱动默认控制面板设置。',
        category: '显卡优化',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'powercfg',
            arguments: ['/setactive', 'SCHEME_BALANCED'],
            description: '恢复平衡电源计划',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'disable_windows_update',
        title: 'Windows 自动更新：一键禁用',
        description: '停止并禁用 wuauserv、bits、UsoSvc 服务。',
        category: '高级管控',
        riskLabel: '高风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'net stop wuauserv & net stop bits & net stop UsoSvc & sc config wuauserv start= disabled & sc config bits start= disabled & sc config UsoSvc start= disabled',
            ],
            description: '禁用 Windows 自动更新服务',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'sc config wuauserv start= demand & sc config bits start= delayed-auto & sc config UsoSvc start= demand & net start bits & net start wuauserv',
            ],
            description: '恢复 Windows 自动更新服务',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'enable_windows_update',
        title: 'Windows 自动更新：一键开启',
        description: '恢复 wuauserv、bits、UsoSvc 服务启动方式并启动更新服务。',
        category: '高级管控',
        riskLabel: '低风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'sc config wuauserv start= demand & sc config bits start= delayed-auto & sc config UsoSvc start= demand & net start bits & net start wuauserv',
            ],
            description: '开启 Windows 自动更新服务',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'defender_temp_disable',
        title: 'Windows 安全中心：临时终结防护',
        description: '使用 Set-MpPreference 临时关闭实时防护，重启或策略刷新后可能恢复。',
        category: '高级管控',
        riskLabel: '高风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'powershell',
            arguments: [
              '-NoProfile',
              '-ExecutionPolicy',
              'Bypass',
              '-Command',
              r'Set-MpPreference -DisableRealtimeMonitoring $true',
            ],
            description: '临时关闭 Defender 实时防护',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'powershell',
            arguments: [
              '-NoProfile',
              '-ExecutionPolicy',
              'Bypass',
              '-Command',
              r'Set-MpPreference -DisableRealtimeMonitoring $false',
            ],
            description: '恢复 Defender 实时防护',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'defender_policy_disable',
        title: 'Windows 安全中心：永久禁用防护',
        description: '写入 Defender 策略注册表，属于高危操作，必须手动确认。',
        category: '高级管控',
        riskLabel: '高风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKLM\SOFTWARE\Policies\Microsoft\Windows Defender',
              '/v',
              'DisableAntiSpyware',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '写入 Defender 禁用策略',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection',
              '/v',
              'DisableRealtimeMonitoring',
              '/t',
              'REG_DWORD',
              '/d',
              '1',
              '/f',
            ],
            description: '写入实时防护禁用策略',
          ),
        ],
        revertCommands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'delete',
              r'HKLM\SOFTWARE\Policies\Microsoft\Windows Defender',
              '/v',
              'DisableAntiSpyware',
              '/f',
            ],
            description: '移除 Defender 禁用策略',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'defender_restore',
        title: 'Windows 安全中心：一键恢复',
        description: '移除禁用策略并恢复实时防护。',
        category: '高级管控',
        riskLabel: '低风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'powershell',
            arguments: [
              '-NoProfile',
              '-ExecutionPolicy',
              'Bypass',
              '-Command',
              r'Set-MpPreference -DisableRealtimeMonitoring $false',
            ],
            description: '恢复实时防护',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'delete',
              r'HKLM\SOFTWARE\Policies\Microsoft\Windows Defender',
              '/v',
              'DisableAntiSpyware',
              '/f',
            ],
            description: '移除 Defender 禁用策略',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'edge_silent_install',
        title: 'Edge 工具箱：一键静默安装 Edge',
        description: '通过 winget 静默安装 Microsoft Edge。',
        category: '高级管控',
        riskLabel: '低风险',
        commands: [
          WindowsOptimizationCommand(
            executable: 'winget',
            arguments: [
              'install',
              '--id',
              'Microsoft.Edge',
              '-e',
              '--silent',
              '--accept-package-agreements',
              '--accept-source-agreements',
            ],
            description: '静默安装 Edge',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'edge_force_remove',
        title: 'Edge 工具箱：一键彻底删除 Edge',
        description: '尝试卸载 Edge Appx 包并删除常见 Edge 更新残留，属于高危操作。',
        category: '高级管控',
        riskLabel: '高风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'powershell',
            arguments: [
              '-NoProfile',
              '-ExecutionPolicy',
              'Bypass',
              '-Command',
              r'Get-AppxPackage *MicrosoftEdge* | Remove-AppxPackage',
            ],
            description: '卸载 Edge Appx 包',
          ),
          WindowsOptimizationCommand(
            executable: 'cmd',
            arguments: [
              '/c',
              r'rd /s /q "%ProgramFiles(x86)%\Microsoft\EdgeUpdate" 2>nul',
            ],
            description: '删除 EdgeUpdate 残留目录',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'repair_browser_hijack',
        title: '一键修复浏览器主页篡改',
        description: '清理 Chrome/Edge 主页策略、重置代理、刷新 DNS 并重置 Winsock。',
        category: '高级管控',
        riskLabel: '中风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'delete',
              r'HKCU\Software\Policies\Google\Chrome',
              '/f',
            ],
            description: '清理 Chrome 用户策略',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'delete',
              r'HKCU\Software\Policies\Microsoft\Edge',
              '/f',
            ],
            description: '清理 Edge 用户策略',
          ),
          WindowsOptimizationCommand(
            executable: 'netsh',
            arguments: ['winhttp', 'reset', 'proxy'],
            description: '重置 WinHTTP 代理',
          ),
          WindowsOptimizationCommand(
            executable: 'ipconfig',
            arguments: ['/flushdns'],
            description: '刷新 DNS',
          ),
          WindowsOptimizationCommand(
            executable: 'netsh',
            arguments: ['winsock', 'reset'],
            description: '重置 Winsock',
          ),
        ],
      ),
      WindowsOptimizationAction(
        id: 'repair_explorer_associations',
        title: '修复默认打开关联',
        description: '参考 c_cleaner_plus 的修复逻辑，恢复 exe、bat、cmd、com、lnk 和文件夹打开关联。',
        category: '修复',
        riskLabel: '高风险',
        requiresAdmin: true,
        commands: [
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: ['add', r'HKCR\.exe', '/ve', '/d', 'exefile', '/f'],
            description: '恢复 .exe 关联',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\.bat',
              '/ve',
              '/d',
              'batfile',
              '/f',
            ],
            description: '恢复 .bat 关联',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\.cmd',
              '/ve',
              '/d',
              'cmdfile',
              '/f',
            ],
            description: '恢复 .cmd 关联',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\.lnk',
              '/ve',
              '/d',
              'lnkfile',
              '/f',
            ],
            description: '恢复 .lnk 关联',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\exefile\shell\open\command',
              '/ve',
              '/d',
              r'"%1" %*',
              '/f',
            ],
            description: '恢复可执行文件打开命令',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\batfile\shell\open\command',
              '/ve',
              '/d',
              r'"%1" %*',
              '/f',
            ],
            description: '恢复 bat 打开命令',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\cmdfile\shell\open\command',
              '/ve',
              '/d',
              r'"%1" %*',
              '/f',
            ],
            description: '恢复 cmd 打开命令',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\lnkfile',
              '/v',
              'IsShortcut',
              '/t',
              'REG_SZ',
              '/d',
              '',
              '/f',
            ],
            description: '恢复快捷方式标记',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\Directory\shell',
              '/ve',
              '/d',
              'none',
              '/f',
            ],
            description: '恢复目录默认右键动词',
          ),
          WindowsOptimizationCommand(
            executable: 'reg',
            arguments: [
              'add',
              r'HKCR\Folder\shell\open\command',
              '/ve',
              '/d',
              r'explorer.exe "%1"',
              '/f',
            ],
            description: '恢复文件夹打开命令',
          ),
        ],
      ),
    ];
  }
}
