import tempfile
import unittest
from pathlib import Path

from cleaner_logic import CleanerLogic


class CleanerAdditionalScanTargetsTests(unittest.TestCase):
    def test_additional_scan_targets_include_observed_remote_paths(self):
        targets = CleanerLogic.additional_scan_targets()
        by_category = {target["category"]: target for target in targets}

        self.assertIn("edgecore_old_versions", by_category)
        self.assertIn(
            r"C:\Program Files (x86)\Microsoft\EdgeCore",
            by_category["edgecore_old_versions"]["paths"],
        )
        self.assertIn("drvpath_driver_packages", by_category)
        self.assertIn(r"C:\DrvPath", by_category["drvpath_driver_packages"]["paths"])
        self.assertIn("windows_update_lcu_backup", by_category)
        self.assertIn(
            r"C:\Windows\servicing\LCU",
            by_category["windows_update_lcu_backup"]["paths"],
        )
        self.assertIn("winsxs_component_store", by_category)
        self.assertIn(
            r"C:\Windows\WinSxS",
            by_category["winsxs_component_store"]["paths"],
        )
        self.assertTrue(by_category["winsxs_component_store"]["scan_only"])

    def test_clean_selected_skips_scan_only_items(self):
        cleaner = CleanerLogic()
        cleaner.set_options({"simulate": False, "backup": False})

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "keep.log"
            file_path.write_text("keep", encoding="utf-8")

            result = cleaner.clean_selected(
                [
                    {
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "type": "winsxs_component_store",
                        "scan_only": True,
                    }
                ]
            )

            self.assertTrue(file_path.exists())
            self.assertEqual(result["cleaned_items"], [])
            self.assertEqual(result["freed_space"], 0)
            self.assertEqual(result["errors"][0]["error"], "仅扫描项，未清理")


if __name__ == "__main__":
    unittest.main()
