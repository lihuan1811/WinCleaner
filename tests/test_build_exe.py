import unittest
from unittest import mock
from pathlib import Path

import build_exe


class BuildExeCommandTests(unittest.TestCase):
    def test_windows_command_keeps_noconfirm_and_uses_windows_add_data_separator(self):
        with mock.patch.object(build_exe.sys, "platform", "win32"):
            command = build_exe.build_pyinstaller_command()

        self.assertIn("--noconfirm", command)
        self.assertIn("--add-data=icons;icons", command)
        self.assertNotIn("--add-data=icons:icons", command)

    def test_non_windows_command_uses_platform_add_data_separator(self):
        with mock.patch.object(build_exe.sys, "platform", "darwin"):
            command = build_exe.build_pyinstaller_command()

        self.assertIn("--noconfirm", command)
        self.assertIn("--add-data=icons:icons", command)
        self.assertNotIn("--add-data=icons;icons", command)

    def test_github_actions_forces_utf8_python_output(self):
        workflow = Path(".github/workflows/build-windows-exe.yml").read_text(encoding="utf-8")

        self.assertIn("PYTHONUTF8: \"1\"", workflow)
        self.assertIn("PYTHONIOENCODING: utf-8", workflow)


if __name__ == "__main__":
    unittest.main()
