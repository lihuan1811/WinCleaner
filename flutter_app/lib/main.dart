import 'package:flutter/material.dart';

import 'theme/app_theme.dart';
import 'widgets/app_shell.dart';

void main() {
  runApp(const WinCleanerApp());
}

class WinCleanerApp extends StatelessWidget {
  const WinCleanerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WinCleaner',
      debugShowCheckedModeBanner: false,
      theme: WinCleanerTheme.light(),
      home: const AppShell(),
    );
  }
}
