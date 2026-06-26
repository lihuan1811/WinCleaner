class InstalledApp {
  const InstalledApp({
    required this.name,
    required this.publisher,
    required this.version,
    required this.sizeLabel,
    required this.installDate,
    required this.source,
    required this.uninstallCommand,
    this.installLocation = '',
    this.sizeBytes = 0,
    this.isUwp = false,
    this.registryKey = '',
    this.isSelected = false,
  });

  final String name;
  final String publisher;
  final String version;
  final String sizeLabel;
  final String installDate;
  final String source;
  final String uninstallCommand;
  final String installLocation;
  final int sizeBytes;
  final bool isUwp;
  final String registryKey;
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
      installLocation: installLocation,
      sizeBytes: sizeBytes,
      isUwp: isUwp,
      registryKey: registryKey,
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
    installLocation: r'C:\Program Files\Microsoft Visual C++',
    sizeBytes: 22 * 1024 * 1024,
  ),
  InstalledApp(
    name: 'Bulk Crap Uninstaller',
    publisher: 'BCUninstaller',
    version: '6.2',
    sizeLabel: '78 MB',
    installDate: '2026-06-01',
    source: 'BCU',
    uninstallCommand: 'BCUninstaller.exe',
    installLocation: r'C:\Program Files\BCUninstaller',
    sizeBytes: 78 * 1024 * 1024,
  ),
  InstalledApp(
    name: 'Legacy Driver Utility',
    publisher: 'Unknown Publisher',
    version: '2.1.0',
    sizeLabel: '184 MB',
    installDate: '2025-12-09',
    source: 'Registry',
    uninstallCommand: 'C:\\Program Files\\Legacy\\uninstall.exe',
    installLocation: r'C:\Program Files\Legacy',
    sizeBytes: 184 * 1024 * 1024,
  ),
];
