# WinCleaner Flutter Desktop

This is the new UI track for WinCleaner. It keeps the existing Python cleaner intact while building a modern Flutter desktop shell.

## BCU backend

The software uninstall page is designed to launch BCUninstaller as the uninstall backend.

Place a portable BCUninstaller build at:

```text
flutter_app/tool/BCUninstaller/BCUninstaller.exe
```

Phase one only discovers and launches BCU. It does not run silent batch uninstall commands automatically.
