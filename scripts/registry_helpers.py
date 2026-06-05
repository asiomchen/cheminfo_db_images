#!/usr/bin/env python3
"""Compatibility CLI for registry and PostgreSQL metadata helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.actions.github import ghcr_tag_exists, list_ghcr_tags
from scripts.actions.versions import latest_pg_minor, version_tuple


def main() -> None:
    """Run the legacy helper command interface used by shell scripts."""
    command = sys.argv[1]
    if command == "tags":
        for tag in list_ghcr_tags(sys.argv[2]):
            print(tag)
        return
    if command == "tag-exists":
        raise SystemExit(0 if ghcr_tag_exists(sys.argv[2], sys.argv[3]) else 1)
    if command == "latest-pg-minor":
        print(latest_pg_minor(sys.argv[2]))
        return
    raise RuntimeError(f"unknown command: {command}")


if __name__ == "__main__":
    main()
