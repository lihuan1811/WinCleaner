import 'dart:io';

import '../models/installed_app.dart';

class InstalledAppsService {
  const InstalledAppsService();

  static const registryRoots = <String>[
    r'HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall',
    r'HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
    r'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall',
  ];

  Future<List<InstalledApp>> loadInstalledApps() async {
    if (!Platform.isWindows) {
      return const [];
    }

    final buffer = StringBuffer();
    for (final root in registryRoots) {
      final result = await Process.run('reg', ['query', root, '/s']);
      if (result.exitCode == 0) {
        buffer.writeln(result.stdout);
      }
    }

    final apps = parseRegistryOutput(buffer.toString());
    return apps;
  }

  static List<InstalledApp> parseRegistryOutput(String output) {
    final entries = <_RegistryEntry>[];
    _RegistryEntry? current;

    for (final rawLine in output.split(RegExp(r'\r?\n'))) {
      final line = rawLine.trimRight();
      if (line.trim().isEmpty) {
        continue;
      }

      if (line.startsWith('HKEY_') ||
          line.startsWith('HKLM\\') ||
          line.startsWith('HKCU\\')) {
        if (current != null) {
          entries.add(current);
        }
        current = _RegistryEntry(line.trim(), <String, String>{});
        continue;
      }

      if (current == null) {
        continue;
      }

      final match =
          RegExp(r'^\s{2,}([^\s]+)\s+REG_\w+\s+(.*)$').firstMatch(rawLine);
      if (match == null) {
        continue;
      }
      current.values[match.group(1)!] = match.group(2)!.trim();
    }

    if (current != null) {
      entries.add(current);
    }

    final seen = <String>{};
    final apps = <InstalledApp>[];
    for (final entry in entries) {
      final name = entry.values['DisplayName']?.trim();
      if (name == null || name.isEmpty) {
        continue;
      }

      final uninstallCommand = entry.values['UninstallString']?.trim() ?? '';
      final dedupeKey =
          '${name.toLowerCase()}|${uninstallCommand.toLowerCase()}';
      if (!seen.add(dedupeKey)) {
        continue;
      }

      apps.add(
        InstalledApp(
          name: name,
          publisher: entry.values['Publisher']?.trim().isNotEmpty == true
              ? entry.values['Publisher']!.trim()
              : '未知发布者',
          version: entry.values['DisplayVersion']?.trim().isNotEmpty == true
              ? entry.values['DisplayVersion']!.trim()
              : '-',
          sizeLabel: _formatEstimatedSize(entry.values['EstimatedSize']),
          installDate: _formatInstallDate(entry.values['InstallDate']),
          source: _sourceFor(entry.keyPath, uninstallCommand),
          uninstallCommand: uninstallCommand,
          registryKey: entry.keyPath,
        ),
      );
    }

    apps.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return apps;
  }

  static String _formatEstimatedSize(String? value) {
    if (value == null || value.trim().isEmpty) {
      return '-';
    }

    final raw = value.trim();
    final sizeKb = raw.toLowerCase().startsWith('0x')
        ? int.tryParse(raw.substring(2), radix: 16)
        : int.tryParse(raw);
    if (sizeKb == null || sizeKb <= 0) {
      return '-';
    }

    final sizeMb = sizeKb / 1024;
    if (sizeMb >= 1024) {
      return '${(sizeMb / 1024).toStringAsFixed(1)} GB';
    }
    return '${sizeMb.round()} MB';
  }

  static String _formatInstallDate(String? value) {
    if (value == null || !RegExp(r'^\d{8}$').hasMatch(value)) {
      return '-';
    }
    return '${value.substring(0, 4)}-${value.substring(4, 6)}-${value.substring(6, 8)}';
  }

  static String _sourceFor(String keyPath, String uninstallCommand) {
    if (uninstallCommand.toLowerCase().contains('msiexec')) {
      return 'MSI';
    }
    if (keyPath.contains('WOW6432Node')) {
      return 'Registry x86';
    }
    return 'Registry';
  }
}

class _RegistryEntry {
  _RegistryEntry(this.keyPath, this.values);

  final String keyPath;
  final Map<String, String> values;
}
