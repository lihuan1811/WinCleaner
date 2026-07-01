# C++/Qt Full Migration Plan

## Scope

Port the existing Python/PyQt C drive cleaner into a new sibling C++/Qt project under `cpp_qt/` without removing or rewriting the current Python implementation.

## Required Modules

- C盘清理: disk stats, scan progress path, 推荐/专业/全选 modes, backup options, selected/all cleaning, grouped scan results.
- 系统优化: 开机加速, 运行内存, 系统优化, 隐私清理, 注册表清理, direct row actions and one-click processing.
- BX(优化): BoosterX-style 基本/最佳 modes with selectable optimization cards.
- 软件卸载: in-app uninstall registry list, run uninstall command, auto-refresh after execution.
- 文件管理: large-file scan, duplicate-file scan, delete action, fragment scan/optimization.
- 系统修复: SFC, DISM, CHKDSK, Winsock, DNS and Windows Update repair commands.
- 账号会员: local login/register/card redemption flow.
- GitHub Actions: Windows Qt build, `windeployqt`, zip artifact, release publishing.

## Verification

- Source coverage test: `tests/test_cpp_qt_migration.py`
- Existing Python regression tests should remain untouched.
- A Windows GitHub runner is expected to compile/package the Qt executable.
