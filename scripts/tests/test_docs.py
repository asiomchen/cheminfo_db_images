"""Tests for documentation update helpers."""

from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from scripts.actions import docs


class DocsTests(unittest.TestCase):
    """Validate extraction and markdown update behavior."""

    def test_get_published_versions_filters_extension_tags(self) -> None:
        with mock.patch(
            "scripts.actions.docs.list_ghcr_tags",
            return_value=[
                "rocky9-postgres17.7-rdkit2025.09.5",
                "rocky9-postgres17.7-bingo1.43.0",
                "postgres17-rdkit2025.09.5",
                "rocky9-postgres17.7-rdkit2025.09.6",
            ],
        ):
            self.assertEqual(
                docs.get_published_versions("rdkit-postgres", "rdkit"),
                ["2025.09.5", "2025.09.6"],
            )

    def test_update_docs_rewrites_supported_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text(
                "| Component | Versions |\n"
                "| **RDKit** | old |\n"
                "| **Bingo** | old |\n",
                encoding="utf-8",
            )
            with mock.patch("scripts.actions.docs.get_published_versions") as versions:
                versions.return_value = ["2025.09.5", "2025.09.6"]
                cwd = Path.cwd()
                try:
                    os.chdir(root)
                    with redirect_stdout(StringIO()):
                        changed = docs.update_docs("rdkit", "rdkit-postgres")
                finally:
                    os.chdir(cwd)

            self.assertTrue(changed)
            self.assertIn(
                "| **RDKit** | 2025.09.5, **2025.09.6 (latest)** |",
                (root / "README.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
