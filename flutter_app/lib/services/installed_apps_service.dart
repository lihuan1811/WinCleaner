import 'dart:io';
import 'dart:convert';

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

    final apps = [
      ...parseRegistryOutput(buffer.toString()),
      ...await _loadUwpApps(),
    ];
    apps.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return apps;
  }

  Future<List<InstalledApp>> _loadUwpApps() async {
    final result = await Process.run('powershell', [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-Command',
      r'Get-AppxPackage | Select-Object Name,Publisher,Version,InstallLocation,PackageFullName | ConvertTo-Json -Compress',
    ]);
    if (result.exitCode != 0) {
      return const [];
    }
    return parseUwpJson(result.stdout.toString());
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
          sizeBytes: _estimatedSizeBytes(entry.values['EstimatedSize']),
          installDate: _formatInstallDate(entry.values['InstallDate']),
          source: _sourceFor(entry.keyPath, uninstallCommand),
          uninstallCommand: uninstallCommand,
          installLocation: entry.values['InstallLocation']?.trim() ?? '',
          registryKey: entry.keyPath,
        ),
      );
    }

    apps.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return apps;
  }

  static List<InstalledApp> parseUwpJson(String output) {
    final trimmed = output.trim();
    if (trimmed.isEmpty) {
      return const [];
    }

    final decoded = jsonDecode(trimmed);
    final rows = decoded is List ? decoded : [decoded];
    return rows
        .whereType<Map>()
        .map((row) {
          final name = row['Name']?.toString().trim() ?? '';
          final packageFullName =
              row['PackageFullName']?.toString().trim() ?? '';
          final installLocation =
              row['InstallLocation']?.toString().trim() ?? '';
          return InstalledApp(
            name: name.isEmpty ? packageFullName : name,
            publisher: row['Publisher']?.toString().trim().isNotEmpty == true
                ? row['Publisher']!.toString().trim()
                : 'Microsoft Store',
            version: row['Version']?.toString().trim().isNotEmpty == true
                ? row['Version']!.toString().trim()
                : '-',
            sizeLabel: '-',
            installDate: '-',
            source: 'UWP',
            uninstallCommand:
                'powershell -NoProfile -ExecutionPolicy Bypass -Command Remove-AppxPackage -Package $packageFullName',
            installLocation: installLocation,
            isUwp: true,
          );
        })
        .where((app) => app.name.isNotEmpty)
        .toList()
      ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
  }

  static int _estimatedSizeBytes(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 0;
    }

    final raw = value.trim();
    final sizeKb = raw.toLowerCase().startsWith('0x')
        ? int.tryParse(raw.substring(2), radix: 16)
        : int.tryParse(raw);
    if (sizeKb == null || sizeKb <= 0) {
      return 0;
    }
    return sizeKb * 1024;
  }

  static String _formatEstimatedSize(String? value) {
    final bytes = _estimatedSizeBytes(value);
    if (bytes <= 0) {
      return '-';
    }

    final sizeMb = bytes / (1024 * 1024);
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
