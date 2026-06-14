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

GitHub Actions builds both artifacts on Windows:

- `WinCleaner-exe`: the original Python cleaner executable.
- `WinCleaner-Flutter-Windows`: the new Flutter desktop UI release folder.
