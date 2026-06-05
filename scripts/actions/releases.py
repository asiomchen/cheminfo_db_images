"""Release discovery helpers for RDKit and Indigo/Bingo."""

from __future__ import annotations

import re

from .github import fetch_bytes, fetch_json, github_headers
from .versions import NUMERIC_SEMVER, version_tuple


INDIGO_TAG = re.compile(r"^indigo-(\d+\.\d+\.\d+)$")
RDKIT_TAG = re.compile(r"^Release_\d{4}_\d{2}_\d+$")


def get_version_from_indigo(indigo_ref: str) -> str:
    """Read the Bingo version stored in an Indigo release branch/tag."""
    version_url = (
        f"https://raw.githubusercontent.com/epam/Indigo/{indigo_ref}/.ci/version.txt"
    )
    version_txt = fetch_bytes(version_url).decode()
    lines = [line.strip() for line in version_txt.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"Unexpected version.txt format for {indigo_ref}")
    return lines[0]


def get_numeric_indigo_releases() -> list[dict[str, str]]:
    """Return non-draft, non-prerelease Indigo releases with numeric versions."""
    releases: list[dict[str, str]] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/epam/Indigo/releases?per_page=100&page={page}"
        items = fetch_json(url, github_headers())
        if not items:
            break
        for release in items:
            if release.get("draft") or release.get("prerelease"):
                continue
            tag_name = release["tag_name"]
            match = INDIGO_TAG.fullmatch(tag_name)
            if not match:
                continue
            bingo_version = match.group(1)
            if not NUMERIC_SEMVER.fullmatch(bingo_version):
                continue
            releases.append({"indigo_ref": tag_name, "bingo_version": bingo_version})
        page += 1

    releases.sort(key=lambda item: version_tuple(item["bingo_version"]))
    deduped: list[dict[str, str]] = []
    seen_versions: set[str] = set()
    for release in releases:
        version = release["bingo_version"]
        if version in seen_versions:
            continue
        seen_versions.add(version)
        deduped.append(release)
    return deduped


def get_latest_numeric_indigo_release() -> dict[str, str]:
    """Return the latest numeric Indigo release suitable for Bingo builds."""
    releases = get_numeric_indigo_releases()
    if not releases:
        raise RuntimeError("No numeric Indigo GitHub releases found")
    return releases[-1]


def get_rdkit_releases(
    min_version: str,
    max_version: str | None = None,
) -> list[dict[str, str]]:
    """Return RDKit releases whose clean versions fall within a version range."""
    min_v = version_tuple(min_version)
    max_v = version_tuple(max_version) if max_version else None
    releases: list[dict[str, str]] = []
    for page in range(1, 5):
        url = f"https://api.github.com/repos/rdkit/rdkit/releases?per_page=100&page={page}"
        page_releases = fetch_json(url, github_headers())
        if not page_releases:
            break
        for release in page_releases:
            tag = release["tag_name"]
            if not RDKIT_TAG.fullmatch(tag):
                continue
            clean = tag.replace("Release_", "").replace("_", ".")
            clean_v = version_tuple(clean)
            if clean_v >= min_v and (max_v is None or clean_v <= max_v):
                releases.append({"ref": tag, "clean": clean})
    return sorted(releases, key=lambda item: version_tuple(item["clean"]))

