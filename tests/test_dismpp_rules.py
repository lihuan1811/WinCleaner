import os
import tempfile
import unittest
from pathlib import Path

from dismpp_rules import DismRuleScanner, get_default_rules_path


class DismRuleScannerTests(unittest.TestCase):
    def test_scans_general_query_rules_with_expanded_environment_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache_dir = root / "Users" / "alice" / "AppData" / "Local" / "Temp"
            cache_dir.mkdir(parents=True)
            keep_file = cache_dir / "keep.txt"
            old_file = cache_dir / "old.tmp"
            keep_file.write_text("keep", encoding="utf-8")
            old_file.write_text("old", encoding="utf-8")

            rules_path = root / "Data.xml"
            rules_path.write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<Data>
  <CleanCollection4>
    <Item Name="#临时缓存">
      <Group>#缓存文件</Group>
      <Scan>
        <Activate>
          <General RootPath="%LOCALAPPDATA%\\Temp">
            <Query>*.tmp</Query>
          </General>
        </Activate>
      </Scan>
    </Item>
  </CleanCollection4>
</Data>
""",
                encoding="utf-8",
            )

            scanner = DismRuleScanner(
                rules_path,
                env={"LOCALAPPDATA": str(root / "Users" / "alice" / "AppData" / "Local")},
            )

            results = scanner.scan()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["path"], str(old_file))
        self.assertEqual(results[0]["type"], "dismpp_rules")
        self.assertEqual(results[0]["rule_name"], "临时缓存")
        self.assertEqual(results[0]["group"], "缓存文件")

    def test_skips_dynamic_dism_function_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules_path = Path(tmp) / "Data.xml"
            rules_path.write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<Data>
  <CleanCollection4>
    <Item Name="#动态规则">
      <Scan>
        <Activate>
          <General RootPath="?GetRegSz(HKEY_LOCAL_MACHINE\\Software\\Example,Path)" Flags="Directory">
            <Query>*</Query>
          </General>
        </Activate>
      </Scan>
    </Item>
  </CleanCollection4>
</Data>
""",
                encoding="utf-8",
            )

            scanner = DismRuleScanner(rules_path, env=os.environ)

            self.assertEqual(scanner.scan(), [])

    def test_default_rules_path_points_to_bundled_data_xml(self):
        self.assertTrue(str(get_default_rules_path()).endswith(os.path.join("rules", "dismpp", "Data.xml")))


if __name__ == "__main__":
    unittest.main()
