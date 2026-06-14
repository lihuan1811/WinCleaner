# Flutter BCU Uninstaller Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Flutter Windows desktop shell for WinCleaner with a modern dashboard UI and an embedded software-uninstall page that can use BCUninstaller as the backend.

**Architecture:** Keep the existing Python cleaner as the current shipped implementation while adding a separate Flutter app under `flutter_app/`. The first Flutter phase owns visual structure, navigation, uninstall data models, and a BCU adapter that discovers or launches a local BCU executable; it does not perform silent batch uninstall automatically.

**Tech Stack:** Flutter/Dart desktop, `flutter_test`, Python backend kept in place, GitHub Actions for Windows packaging.

---

### Task 1: Flutter Project Skeleton

**Files:**
- Create: `flutter_app/pubspec.yaml`
- Create: `flutter_app/lib/main.dart`
- Create: `flutter_app/test/widget_test.dart`

- [ ] Generate or create a minimal Flutter desktop app.
- [ ] Run `flutter test` and make sure the initial app test passes.
- [ ] Keep this isolated from the existing Python files.

### Task 2: Dashboard UI

**Files:**
- Modify: `flutter_app/lib/main.dart`
- Create: `flutter_app/lib/theme/app_theme.dart`
- Create: `flutter_app/lib/screens/dashboard_screen.dart`
- Create: `flutter_app/lib/widgets/app_shell.dart`

- [ ] Implement the Azure Cleaner style shell: left navigation, top bar, storage card, health card, tool cards, trend card, and activity log.
- [ ] Add a widget test that verifies the sidebar has `C盘清理`, `系统优化`, `软件卸载`, and `文件管理`.
- [ ] Run `flutter test`.

### Task 3: Software Uninstall Page

**Files:**
- Create: `flutter_app/lib/screens/uninstaller_screen.dart`
- Create: `flutter_app/lib/models/installed_app.dart`
- Create: `flutter_app/test/uninstaller_screen_test.dart`

- [ ] Implement a software uninstall screen matching the dashboard visual language.
- [ ] Show sample installed app rows with name, publisher, version, size, install date, and uninstall source.
- [ ] Add search/filter UI and disabled destructive actions until a row is selected.
- [ ] Run `flutter test`.

### Task 4: BCU Backend Adapter

**Files:**
- Create: `flutter_app/lib/services/bcu_service.dart`
- Create: `flutter_app/test/bcu_service_test.dart`

- [ ] Implement path discovery for a bundled or user-provided BCU executable.
- [ ] Implement launch-only integration for BCU in phase one.
- [ ] Do not add silent uninstall execution in phase one.
- [ ] Run `flutter test`.

### Task 5: Build Workflow Preparation

**Files:**
- Modify: `.github/workflows/build-windows-exe.yml`
- Create: `flutter_app/README.md`

- [ ] Add a Flutter build job only if the local Flutter project validates.
- [ ] Keep the existing Python PyInstaller job intact.
- [ ] Document that the Flutter app is the new UI track and BCU executable is an optional backend dependency.
