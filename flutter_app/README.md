# WinCleaner Flutter Desktop

This is the new UI track for WinCleaner. It keeps the existing Python cleaner intact while building a modern Flutter desktop shell.

## BCU backend

The software uninstall page can launch BCUninstaller as an external backend.

Place a portable BCUninstaller build at:

```text
flutter_app/tool/BCUninstaller/BCUninstaller.exe
```

The app also reads the Windows uninstall registry directly and can start each
program's official uninstall command after confirmation. It does not run silent
batch uninstall commands automatically, and it does not remove leftovers after
the vendor uninstaller finishes.

## Toolbox features

The advanced toolbox entries are functional:

- Ad cleanup writes and restores a WinCleaner-managed block in the Windows
  `hosts` file, with a backup before every change.
- Duplicate files scans a selected directory, groups files by size, verifies
  duplicates with SHA-256, and can delete duplicate copies while keeping one
  file from each group.
- Large files scans a selected directory and lists the largest files above the
  configured threshold.
- Disk defragment/optimization calls Windows `defrag.exe`; analysis uses
  `/A /U /V`, and optimization uses `/O /U /V` so Windows chooses the correct
  optimization for HDD or SSD.

Hosts editing and disk optimization require Windows permissions appropriate for
the operation. On non-Windows systems those operations report unsupported
instead of pretending to succeed.

GitHub Actions builds both artifacts on Windows:

- `WinCleaner-exe`: the original Python cleaner executable.
- `WinCleaner-Flutter-Windows`: the new Flutter desktop UI release folder.
