import 'dart:io';

class AdBlockStatus {
  const AdBlockStatus({
    required this.enabled,
    required this.blockedDomains,
    required this.hostsPath,
    this.message = '',
  });

  final bool enabled;
  final int blockedDomains;
  final String hostsPath;
  final String message;
}

class AdBlockService {
  AdBlockService({
    File? hostsFile,
    Directory? backupDirectory,
    this.flushDns = true,
    Future<ProcessResult> Function(String executable, List<String> arguments)?
        processRunner,
  })  : hostsFile = hostsFile ?? File(r'C:\Windows\System32\drivers\etc\hosts'),
        backupDirectory = backupDirectory ?? _defaultBackupDirectory(),
        _processRunner = processRunner ?? Process.run;

  static const beginMarker = '# WinCleaner ad block begin';
  static const endMarker = '# WinCleaner ad block end';

  static const defaultDomains = <String>[
    'doubleclick.net',
    'ad.doubleclick.net',
    'googlesyndication.com',
    'googleadservices.com',
    'adsystem.com',
    'adnxs.com',
    'adsafeprotected.com',
    'scorecardresearch.com',
    'taboola.com',
    'outbrain.com',
    'zedo.com',
    'mathtag.com',
    'rubiconproject.com',
    'pubmatic.com',
    'criteo.com',
    'openx.net',
    'moatads.com',
    'adform.net',
    'yieldmo.com',
    'advertising.com',
    'ads.yahoo.com',
    'ads.facebook.com',
  ];

  final File hostsFile;
  final Directory backupDirectory;
  final bool flushDns;
  final Future<ProcessResult> Function(
      String executable, List<String> arguments) _processRunner;

  Future<bool> isEnabled() async {
    try {
      if (!await hostsFile.exists()) {
        return false;
      }
      final content = await hostsFile.readAsString();
      return content.contains(beginMarker) && content.contains(endMarker);
    } on UnsupportedError {
      return false;
    }
  }

  Future<AdBlockStatus> status() async {
    try {
      if (!await hostsFile.exists()) {
        return AdBlockStatus(
          enabled: false,
          blockedDomains: 0,
          hostsPath: hostsFile.path,
          message: 'hosts 文件不存在',
        );
      }

      final content = await hostsFile.readAsString();
      return AdBlockStatus(
        enabled: content.contains(beginMarker) && content.contains(endMarker),
        blockedDomains: _countManagedDomains(content),
        hostsPath: hostsFile.path,
      );
    } on UnsupportedError {
      return AdBlockStatus(
        enabled: false,
        blockedDomains: 0,
        hostsPath: hostsFile.path,
        message: '广告清理仅支持 Windows 桌面运行。',
      );
    }
  }

  Future<AdBlockStatus> enable({List<String> domains = defaultDomains}) async {
    await _ensureHostsFile();
    await _backupHostsFile();

    final existing = await hostsFile.readAsString();
    final cleaned = _removeManagedBlock(existing).trimRight();
    final normalizedDomains = _normalizeDomains(domains);
    final block = _buildManagedBlock(normalizedDomains);
    await hostsFile.writeAsString('$cleaned\n\n$block\n');
    await _flushDnsIfNeeded();

    return AdBlockStatus(
      enabled: true,
      blockedDomains: normalizedDomains.length,
      hostsPath: hostsFile.path,
      message: '已写入广告屏蔽 hosts 规则',
    );
  }

  Future<AdBlockStatus> disable() async {
    if (!await hostsFile.exists()) {
      return AdBlockStatus(
        enabled: false,
        blockedDomains: 0,
        hostsPath: hostsFile.path,
        message: 'hosts 文件不存在',
      );
    }

    await _backupHostsFile();
    final existing = await hostsFile.readAsString();
    await hostsFile
        .writeAsString('${_removeManagedBlock(existing).trimRight()}\n');
    await _flushDnsIfNeeded();

    return AdBlockStatus(
      enabled: false,
      blockedDomains: 0,
      hostsPath: hostsFile.path,
      message: '已移除 WinCleaner hosts 规则',
    );
  }

  Future<void> _ensureHostsFile() async {
    if (!await hostsFile.parent.exists()) {
      await hostsFile.parent.create(recursive: true);
    }
    if (!await hostsFile.exists()) {
      await hostsFile.writeAsString('');
    }
  }

  Future<void> _backupHostsFile() async {
    await backupDirectory.create(recursive: true);
    if (!await hostsFile.exists()) {
      return;
    }
    final stamp = DateTime.now()
        .toIso8601String()
        .replaceAll(':', '')
        .replaceAll('.', '-');
    await hostsFile.copy(
      '${backupDirectory.path}${Platform.pathSeparator}hosts-$stamp.bak',
    );
  }

  Future<void> _flushDnsIfNeeded() async {
    if (!flushDns || !Platform.isWindows) {
      return;
    }
    await _processRunner('ipconfig', ['/flushdns']);
  }

  static List<String> _normalizeDomains(List<String> domains) {
    final normalized = <String>{};
    for (final domain in domains) {
      final value = domain.trim().toLowerCase();
      if (value.isEmpty || value.startsWith('#') || value.contains(' ')) {
        continue;
      }
      normalized.add(value);
    }
    return normalized.toList()..sort();
  }

  static String _buildManagedBlock(List<String> domains) {
    final lines = [
      beginMarker,
      for (final domain in domains) '0.0.0.0 $domain',
      endMarker,
    ];
    return lines.join('\n');
  }

  static String _removeManagedBlock(String content) {
    final pattern = RegExp(
      '${RegExp.escape(beginMarker)}[\\s\\S]*?${RegExp.escape(endMarker)}\\s*',
      multiLine: true,
    );
    return content.replaceAll(pattern, '');
  }

  static int _countManagedDomains(String content) {
    final start = content.indexOf(beginMarker);
    final end = content.indexOf(endMarker);
    if (start < 0 || end <= start) {
      return 0;
    }
    return content
        .substring(start, end)
        .split(RegExp(r'\r?\n'))
        .where((line) => line.trimLeft().startsWith('0.0.0.0 '))
        .length;
  }
}

Directory _defaultBackupDirectory() {
  try {
    return Directory(
      '${Directory.systemTemp.path}${Platform.pathSeparator}WinCleaner_Hosts_Backup',
    );
  } on UnsupportedError {
    return Directory('/WinCleaner_Hosts_Backup');
  }
}
