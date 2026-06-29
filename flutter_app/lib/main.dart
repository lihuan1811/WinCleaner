import 'package:flutter/material.dart';

import 'services/installed_apps_service.dart';
import 'services/local_account_service.dart';
import 'theme/app_theme.dart';
import 'widgets/app_shell.dart';

void main() {
  runApp(const WinCleanerApp());
}

class WinCleanerApp extends StatelessWidget {
  const WinCleanerApp({
    super.key,
    this.installedAppsService = const InstalledAppsService(),
    this.accountService,
  });

  final InstalledAppsService installedAppsService;
  final LocalAccountService? accountService;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WinCleaner',
      debugShowCheckedModeBanner: false,
      theme: WinCleanerTheme.light(),
      home: AppShell(
        installedAppsService: installedAppsService,
        accountService: accountService,
      ),
    );
  }
}
