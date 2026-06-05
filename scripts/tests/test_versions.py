"""Tests for version parsing helpers."""

from __future__ import annotations

import unittest

from scripts.actions import versions


class VersionParsingTests(unittest.TestCase):
    """Validate reusable parsing helpers used by workflow commands."""

    def test_parse_pg_majors_deduplicates_and_preserves_order(self) -> None:
        self.assertEqual(
            versions.parse_pg_majors("15, 16 15\n17"),
            ["15", "16", "17"],
        )

    def test_parse_pg_majors_rejects_non_numeric_values(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unexpected PostgreSQL major"):
            versions.parse_pg_majors("15 pg16")

    def test_parse_rdkit_ref_returns_clean_version(self) -> None:
        self.assertEqual(
            versions.parse_rdkit_ref("Release_2025_09_5"),
            "2025.09.5",
        )

    def test_parse_numeric_semver_rejects_partial_versions(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Expected numeric semver"):
            versions.parse_numeric_semver("2025.09", "rdkit")

    def test_version_tuple_sorts_numeric_components(self) -> None:
        self.assertGreater(
            versions.version_tuple("2025.09.10"),
            versions.version_tuple("2025.09.5"),
        )


if __name__ == "__main__":
    unittest.main()

