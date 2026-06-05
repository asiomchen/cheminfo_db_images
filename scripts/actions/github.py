"""GitHub and GHCR API helpers used by workflow matrix generation."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


GITHUB_API = "https://api.github.com"
DEFAULT_GHCR_OWNER = "asiomchen"


def fetch_bytes(url: str, headers: dict[str, str] | None = None) -> bytes:
    """Fetch raw bytes from a URL using optional HTTP headers."""
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request) as response:
        return response.read()


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    """Fetch and decode JSON from a URL using optional HTTP headers."""
    return json.loads(fetch_bytes(url, headers).decode())


def github_headers(token: str | None = None) -> dict[str, str]:
    """Return GitHub API headers, including authorization when a token exists."""
    token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def list_ghcr_tags(package_name: str, owner: str | None = None) -> list[str]:
    """List all tags published for a GHCR container package."""
    owner = owner or os.environ.get("GHCR_OWNER", DEFAULT_GHCR_OWNER)
    tags: set[str] = set()
    page = 1
    while True:
        url = (
            f"{GITHUB_API}/users/{owner}/packages/container/"
            f"{package_name}/versions?per_page=100&page={page}"
        )
        try:
            versions = fetch_json(url, github_headers())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return sorted(tags)
            raise
        if not versions:
            return sorted(tags)
        for version in versions:
            container = version.get("metadata", {}).get("container", {})
            tags.update(container.get("tags", []))
        page += 1


def ghcr_tag_exists(package_name: str, tag: str, owner: str | None = None) -> bool:
    """Return whether a GHCR container package has a specific tag."""
    return tag in set(list_ghcr_tags(package_name, owner=owner))

