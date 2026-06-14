import 'dart:io';

class BcuStatus {
  const BcuStatus({
    required this.isAvailable,
    this.executablePath,
    this.message = '',
  });

  final bool isAvailable;
  final String? executablePath;
  final String message;
}

class BcuService {
  BcuService({List<String>? searchPaths})
      : _searchPaths = searchPaths ?? defaultSearchPaths;

  final List<String> _searchPaths;

  static const defaultSearchPaths = <String>[
    r'tool\BCUninstaller\BCUninstaller.exe',
    r'tools\BCUninstaller\BCUninstaller.exe',
    r'C:\Program Files\BCUninstaller\BCUninstaller.exe',
    r'C:\Program Files (x86)\BCUninstaller\BCUninstaller.exe',
  ];

  BcuStatus locate() {
    for (final candidate in _searchPaths) {
      final file = File(candidate);
      if (file.existsSync()) {
        return BcuStatus(
          isAvailable: true,
          executablePath: file.path,
          message: '已找到 BCUninstaller 后端',
        );
      }
    }

    return const BcuStatus(
      isAvailable: false,
      message: '未找到 BCUninstaller，请将 portable 版本放入 tool/BCUninstaller。',
    );
  }

  Future<ProcessResult> launch({List<String> arguments = const []}) {
    final status = locate();
    if (!status.isAvailable || status.executablePath == null) {
      throw StateError(status.message);
    }

    return Process.run(status.executablePath!, arguments);
  }
}
