import unittest
from unittest import mock
from pathlib import Path

import build_exe


class BuildExeCommandTests(unittest.TestCase):
    def test_windows_command_keeps_noconfirm_and_uses_windows_add_data_separator(self):
        with mock.patch.object(build_exe.sys, "platform", "win32"):
            command = build_exe.build_pyinstaller_command()

        self.assertIn("--name=C盘清理精灵", command)
        self.assertIn("--noconfirm", command)
        self.assertIn("--add-data=icons;icons", command)
        self.assertIn("--add-data=rules;rules", command)
        self.assertNotIn("--add-data=icons:icons", command)
        self.assertEqual(command[-1], "cleaner_ui.py")

    def test_non_windows_command_uses_platform_add_data_separator(self):
        with mock.patch.object(build_exe.sys, "platform", "darwin"):
            command = build_exe.build_pyinstaller_command()

        self.assertIn("--name=C盘清理精灵", command)
        self.assertIn("--noconfirm", command)
        self.assertIn("--add-data=icons:icons", command)
        self.assertIn("--add-data=rules:rules", command)
        self.assertNotIn("--add-data=icons;icons", command)
        self.assertEqual(command[-1], "cleaner_ui.py")

    def test_github_actions_forces_utf8_python_output(self):
        workflow = Path(".github/workflows/build-windows-exe.yml").read_text(encoding="utf-8")

        self.assertIn("PYTHONUTF8: \"1\"", workflow)
        self.assertIn("PYTHONIOENCODING: utf-8", workflow)
        self.assertIn("C盘清理精灵.exe", workflow)
        self.assertNotIn("Build Flutter Windows UI", workflow)

    def test_local_launcher_uses_qt_entrypoint(self):
        launcher = Path("启动C盘清理工具.bat").read_text(encoding="utf-8")

        self.assertIn("C盘清理精灵", launcher)
        self.assertIn("python cleaner_ui.py", launcher)
        self.assertNotIn("python main.py", launcher)

    def test_qt_entrypoint_can_launch_main_window(self):
        qt_source = Path("cleaner_ui.py").read_text(encoding="utf-8")

        self.assertIn("QApplication", qt_source)
        self.assertIn("CleanerMainWindow", qt_source)
        self.assertIn("if __name__ == '__main__':", qt_source)

    def test_flutter_windows_runner_disables_maximize_button(self):
        runner = Path("flutter_app/windows/runner/win32_window.cpp").read_text(
            encoding="utf-8"
        )

        self.assertIn("kWindowStyle", runner)
        self.assertIn("~WS_MAXIMIZEBOX", runner)


if __name__ == "__main__":
    unittest.main()
