"""README update helpers for supported image versions."""

from __future__ import annotations

import re
from pathlib import Path

from .github import list_ghcr_tags
from .versions import version_tuple


def get_published_versions(package_name: str, extension: str) -> list[str]:
    """Extract published extension versions from final image tags."""
    versions = set()
    pattern = re.compile(rf"^rocky9-postgres\d+\.\d+-{extension}(\d+\.\d+\.\d+)$")
    for tag in list_ghcr_tags(package_name):
        match = pattern.match(tag)
        if match:
            versions.add(match.group(1))
    return sorted(versions, key=version_tuple)


def format_versions(versions: list[str]) -> str:
    """Format versions for README tables, marking the newest as latest."""
    latest = versions[-1]
    return ", ".join(
        f"**{version} (latest)**" if version == latest else version
        for version in versions
    )


def update_docs(extension: str, package_name: str) -> bool:
    """Update README supported versions for a published extension package."""
    label = {"bingo": "Bingo", "rdkit": "RDKit"}[extension]
    versions = get_published_versions(package_name, extension)
    if not versions:
        print(f"No {label} versions found on GHCR, skipping update")
        return False

    versions_str = format_versions(versions)
    print(f"Found versions: {versions_str}")
    changed = False

    readme = Path("README.md")
    content = readme.read_text(encoding="utf-8")
    new_content = re.sub(
        rf"(\| \*\*{label}\*\* \| ).*?( \|)",
        rf"\g<1>{versions_str}\g<2>",
        content,
    )
    if new_content != content:
        readme.write_text(new_content, encoding="utf-8")
        print("Updated README.md")
        changed = True
    else:
        print("README.md unchanged")

    return changed
