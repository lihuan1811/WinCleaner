import unittest

from category_display import (
    category_key_from_tree_tags,
    category_tree_label,
    strip_category_badge,
)


class CategoryDisplayTests(unittest.TestCase):
    def test_edgecore_category_uses_edge_badge(self):
        self.assertEqual(
            category_tree_label("edgecore_old_versions"),
            "[Edge] EdgeCore旧版本更新",
        )

    def test_defender_category_uses_defender_badge(self):
        self.assertEqual(
            category_tree_label("defender_quarantine"),
            "[Def] Defender隔离区",
        )

    def test_category_key_is_kept_in_tree_tags(self):
        self.assertEqual(
            category_key_from_tree_tags(("item", "category:edgecore_old_versions")),
            "edgecore_old_versions",
        )

    def test_category_badge_can_be_stripped_for_legacy_lookup(self):
        self.assertEqual(
            strip_category_badge("[Edge] EdgeCore旧版本更新"),
            "EdgeCore旧版本更新",
        )


if __name__ == "__main__":
    unittest.main()
