class InstalledApp {
  const InstalledApp({
    required this.name,
    required this.publisher,
    required this.version,
    required this.sizeLabel,
    required this.installDate,
    required this.source,
    required this.uninstallCommand,
    this.isSelected = false,
  });

  final String name;
  final String publisher;
  final String version;
  final String sizeLabel;
  final String installDate;
  final String source;
  final String uninstallCommand;
  final bool isSelected;

  InstalledApp copyWith({bool? isSelected}) {
    return InstalledApp(
      name: name,
      publisher: publisher,
      version: version,
      sizeLabel: sizeLabel,
      installDate: installDate,
      source: source,
      uninstallCommand: uninstallCommand,
      isSelected: isSelected ?? this.isSelected,
    );
  }
}

const sampleInstalledApps = <InstalledApp>[
  InstalledApp(
    name: 'Microsoft Visual C++ Redistributable',
    publisher: 'Microsoft Corporation',
    version: '14.40.33810',
    sizeLabel: '22 MB',
    installDate: '2026-05-28',
    source: 'MSI',
    uninstallCommand: 'MsiExec.exe /X{00000000-0000-0000-0000-000000000001}',
  ),
  InstalledApp(
    name: 'Bulk Crap Uninstaller',
    publisher: 'BCUninstaller',
    version: '6.2',
    sizeLabel: '78 MB',
    installDate: '2026-06-01',
    source: 'BCU',
    uninstallCommand: 'BCUninstaller.exe',
  ),
  InstalledApp(
    name: 'Legacy Driver Utility',
    publisher: 'Unknown Publisher',
    version: '2.1.0',
    sizeLabel: '184 MB',
    installDate: '2025-12-09',
    source: 'Registry',
    uninstallCommand: 'C:\\Program Files\\Legacy\\uninstall.exe',
  ),
];
