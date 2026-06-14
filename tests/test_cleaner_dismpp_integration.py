import unittest
from unittest import mock

import cleaner_logic
from cleaner_logic import CleanerLogic


class _FakeDismScanner:
    def scan(self):
        return [
            {"path": "/tmp/safe-cache.tmp", "size": 12, "type": "dismpp_rules"},
            {"path": "C:\\Windows\\System32\\unsafe.tmp", "size": 34, "type": "dismpp_rules"},
        ]


class CleanerDismIntegrationTests(unittest.TestCase):
    def test_dismpp_scan_adds_supported_items_and_filters_unsafe_paths(self):
        cleaner = CleanerLogic()
        results = {"dismpp_rules": []}

        with mock.patch.object(cleaner_logic, "DismRuleScanner", return_value=_FakeDismScanner()):
            cleaner._scan_dismpp_rules(results)

        self.assertEqual(results["dismpp_rules"], [{"path": "/tmp/safe-cache.tmp", "size": 12, "type": "dismpp_rules"}])


if __name__ == "__main__":
    unittest.main()
