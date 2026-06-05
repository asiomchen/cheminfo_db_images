"""Tests for workflow matrix generation helpers."""

from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from scripts.actions import matrices


class MatrixTests(unittest.TestCase):
    """Validate representative dist and runtime matrix generation."""

    def test_prepare_rdkit_dist_skips_existing_tags(self) -> None:
        with redirect_stdout(StringIO()):
            outputs = matrices.prepare_rdkit_dist(
                image_name="rdkit-postgres-dist",
                mode="single",
                rdkit_ref="Release_2025_09_5",
                min_rdkit_version="",
                max_rdkit_version="",
                pg_majors="16 17",
                tag_exists=lambda tag: tag == "2025.09.5-postgres16",
            )
        self.assertTrue(outputs.has_builds)
        self.assertEqual(len(outputs.matrix["include"]), 2)
        self.assertEqual(outputs.merge_matrix["include"], [
            {"pg_major": "17", "rdkit_clean": "2025.09.5"},
        ])

    def test_prepare_bingo_dist_range_builds_arch_entries(self) -> None:
        with mock.patch(
            "scripts.actions.matrices.get_numeric_indigo_releases",
            return_value=[
                {"indigo_ref": "indigo-1.42.0", "bingo_version": "1.42.0"},
                {"indigo_ref": "indigo-1.43.0", "bingo_version": "1.43.0"},
            ],
        ), mock.patch(
            "scripts.actions.matrices.get_version_from_indigo",
            side_effect=lambda ref: ref.removeprefix("indigo-"),
        ):
            with redirect_stdout(StringIO()):
                outputs = matrices.prepare_bingo_dist(
                    image_name="bingo-dist",
                    mode="range",
                    bingo_version="",
                    min_bingo_version="1.43.0",
                    max_bingo_version="",
                    pg_majors="15",
                    tag_exists=lambda tag: False,
                )
        self.assertTrue(outputs.has_builds)
        self.assertEqual(len(outputs.matrix["include"]), 2)
        self.assertEqual(outputs.matrix["include"][0]["bingo_version"], "1.43.0")

    def test_prepare_rdkit_dist_range_builds_arch_entries(self) -> None:
        with mock.patch(
            "scripts.actions.matrices.get_rdkit_releases",
            return_value=[
                {"ref": "Release_2025_09_4", "clean": "2025.09.4"},
                {"ref": "Release_2025_09_5", "clean": "2025.09.5"},
            ],
        ):
            with redirect_stdout(StringIO()):
                outputs = matrices.prepare_rdkit_dist(
                    image_name="rdkit-postgres-dist",
                    mode="range",
                    rdkit_ref="",
                    min_rdkit_version="2025.09.4",
                    max_rdkit_version="2025.09.5",
                    pg_majors="17",
                    tag_exists=lambda tag: False,
                )
        self.assertTrue(outputs.has_builds)
        self.assertEqual(len(outputs.matrix["include"]), 4)
        self.assertEqual(outputs.matrix["include"][0]["rdkit_clean"], "2025.09.4")

    def test_prepare_bingo_dist_single_builds_arch_entries(self) -> None:
        with mock.patch(
            "scripts.actions.matrices.get_numeric_indigo_releases",
            return_value=[
                {"indigo_ref": "indigo-1.43.0", "bingo_version": "1.43.0"},
            ],
        ), mock.patch(
            "scripts.actions.matrices.get_version_from_indigo",
            return_value="1.43.0",
        ):
            with redirect_stdout(StringIO()):
                outputs = matrices.prepare_bingo_dist(
                    image_name="bingo-dist",
                    mode="single",
                    bingo_version="1.43.0",
                    min_bingo_version="",
                    max_bingo_version="",
                    pg_majors="15",
                    tag_exists=lambda tag: False,
                )
        self.assertTrue(outputs.has_builds)
        self.assertEqual(len(outputs.matrix["include"]), 2)
        self.assertEqual(outputs.merge_matrix["include"], [
            {"pg_major": "15", "bingo_version": "1.43.0"},
        ])

    def test_prepare_rdkit_runtime_range_uses_dist_versions_and_latest_minor(self) -> None:
        with mock.patch(
            "scripts.actions.matrices.dist_versions_by_pg_major",
            return_value={"17": ["2025.09.5", "2025.09.6"]},
        ), mock.patch(
            "scripts.actions.matrices.latest_pg_minor",
            return_value="17.10",
        ):
            with redirect_stdout(StringIO()):
                outputs = matrices.prepare_rdkit_runtime_all(
                    registry="ghcr.io",
                    image_owner="asiomchen",
                    image_name="rdkit-postgres",
                    dist_image_name="rdkit-postgres-dist",
                    rocky_version="9",
                    pg_majors="17",
                    min_rdkit_version="2025.09.6",
                    max_rdkit_version="",
                    tag_exists=lambda tag: False,
                )
        self.assertTrue(outputs.has_builds)
        self.assertEqual(len(outputs.matrix["include"]), 2)
        first = outputs.matrix["include"][0]
        self.assertEqual(first["pg_minor"], "17.10")
        self.assertEqual(first["rdkit_ref"], "Release_2025_09_6")
        self.assertEqual(
            first["rdkit_dist_image"],
            "ghcr.io/asiomchen/rdkit-postgres-dist:2025.09.6-postgres17",
        )

    def test_prepare_rdkit_runtime_single_uses_requested_dist_version(self) -> None:
        with mock.patch(
            "scripts.actions.matrices.dist_versions_by_pg_major",
            return_value={"17": ["2025.09.5", "2025.09.6"]},
        ), mock.patch(
            "scripts.actions.matrices.latest_pg_minor",
            return_value="17.10",
        ):
            with redirect_stdout(StringIO()):
                outputs = matrices.prepare_rdkit_runtime(
                    registry="ghcr.io",
                    image_owner="asiomchen",
                    image_name="rdkit-postgres",
                    dist_image_name="rdkit-postgres-dist",
                    rocky_version="9",
                    pg_majors="17",
                    mode="single",
                    rdkit_version="2025.09.5",
                    min_rdkit_version="",
                    max_rdkit_version="",
                    tag_exists=lambda tag: False,
                )
        self.assertTrue(outputs.has_builds)
        self.assertEqual(outputs.matrix["include"][0]["rdkit_clean"], "2025.09.5")

    def test_prepare_bingo_runtime_returns_empty_when_no_dist_tags(self) -> None:
        with mock.patch(
            "scripts.actions.matrices.dist_versions_by_pg_major",
            return_value={},
        ):
            with redirect_stdout(StringIO()):
                outputs = matrices.prepare_bingo_runtime(
                    registry="ghcr.io",
                    image_owner="asiomchen",
                    image_name="bingo-postgres",
                    dist_image_name="bingo-dist",
                    rocky_version="9",
                    pg_majors="15",
                    mode="range",
                    bingo_version="",
                    min_bingo_version="1.34.0",
                    max_bingo_version="",
                )
        self.assertFalse(outputs.has_builds)
        self.assertEqual(outputs.matrix, {"include": []})

    def test_prepare_bingo_runtime_range_uses_dist_versions(self) -> None:
        with mock.patch(
            "scripts.actions.matrices.dist_versions_by_pg_major",
            return_value={"15": ["1.42.0", "1.43.0"]},
        ), mock.patch(
            "scripts.actions.matrices.latest_pg_minor",
            return_value="15.14",
        ):
            with redirect_stdout(StringIO()):
                outputs = matrices.prepare_bingo_runtime(
                    registry="ghcr.io",
                    image_owner="asiomchen",
                    image_name="bingo-postgres",
                    dist_image_name="bingo-dist",
                    rocky_version="9",
                    pg_majors="15",
                    mode="range",
                    bingo_version="",
                    min_bingo_version="1.43.0",
                    max_bingo_version="",
                    tag_exists=lambda tag: False,
                )
        self.assertTrue(outputs.has_builds)
        self.assertEqual(len(outputs.matrix["include"]), 2)
        self.assertEqual(outputs.matrix["include"][0]["bingo_version"], "1.43.0")


if __name__ == "__main__":
    unittest.main()
