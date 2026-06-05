"""Workflow matrix builders for RDKit and Bingo image jobs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .github import ghcr_tag_exists, list_ghcr_tags
from .releases import (
    get_latest_numeric_indigo_release,
    get_numeric_indigo_releases,
    get_rdkit_releases,
    get_version_from_indigo,
)
from .versions import (
    parse_numeric_semver,
    parse_pg_majors,
    parse_rdkit_ref,
    rdkit_ref_from_clean,
    version_tuple,
    latest_pg_minor,
)


ARCHES = (
    ("amd64", "ubuntu-24.04", "linux/amd64"),
    ("arm64", "ubuntu-24.04-arm", "linux/arm64"),
)


@dataclass(frozen=True)
class ActionOutputs:
    """GitHub Actions output values produced by matrix preparation commands."""

    matrix: dict[str, list[dict[str, str]]]
    merge_matrix: dict[str, list[dict[str, str]]]
    has_builds: bool

    def write(self, output_path: str | None) -> None:
        """Write outputs to a GitHub Actions output file when available."""
        if not output_path:
            return
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write(f"matrix={json.dumps(self.matrix)}\n")
            handle.write(f"merge_matrix={json.dumps(self.merge_matrix)}\n")
            handle.write(f"has_builds={'true' if self.has_builds else 'false'}\n")


def _outputs(
    matrix_entries: list[dict[str, str]],
    merge_entries: list[dict[str, str]],
) -> ActionOutputs:
    return ActionOutputs(
        matrix={"include": matrix_entries},
        merge_matrix={"include": merge_entries},
        has_builds=bool(matrix_entries),
    )


def _append_arch_entries(
    matrix_entries: list[dict[str, str]],
    base: dict[str, str],
) -> None:
    for arch, runner, platform in ARCHES:
        matrix_entries.append({
            **base,
            "arch": arch,
            "runner": runner,
            "platform": platform,
        })


def prepare_bingo_dist(
    image_name: str,
    mode: str,
    bingo_version: str,
    min_bingo_version: str,
    max_bingo_version: str,
    pg_majors: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for manual Bingo dist image builds."""
    tag_exists = tag_exists or (lambda tag: ghcr_tag_exists(image_name, tag))
    releases = get_numeric_indigo_releases()
    release_map = {item["bingo_version"]: item for item in releases}

    if mode == "single":
        version = parse_numeric_semver(bingo_version, "bingo_version")
        if version not in release_map:
            raise RuntimeError(f"No GitHub release found for Bingo version {version}")
        targets = [release_map[version]]
    elif mode == "range":
        min_version = parse_numeric_semver(min_bingo_version, "min_bingo_version")
        max_version = (
            parse_numeric_semver(max_bingo_version, "max_bingo_version")
            if max_bingo_version
            else None
        )
        if max_version and version_tuple(max_version) < version_tuple(min_version):
            raise RuntimeError(
                "max_bingo_version must be greater than or equal to min_bingo_version"
            )
        targets = [
            item for item in releases
            if version_tuple(item["bingo_version"]) >= version_tuple(min_version)
            and (
                max_version is None
                or version_tuple(item["bingo_version"]) <= version_tuple(max_version)
            )
        ]
        if not targets:
            bound = f"{min_version}..{max_version}" if max_version else f">={min_version}"
            raise RuntimeError(f"No numeric Bingo releases found for range {bound}")
    else:
        raise RuntimeError(f"Unsupported mode: {mode}")

    print(f"Mode: {mode}", flush=True)
    print(
        "Selected Bingo versions: "
        + ", ".join(target["bingo_version"] for target in targets),
        flush=True,
    )
    return _prepare_bingo_dist_targets(targets, pg_majors, tag_exists)


def prepare_bingo_dist_latest(
    image_name: str,
    pg_majors: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for the latest Bingo dist image build."""
    tag_exists = tag_exists or (lambda tag: ghcr_tag_exists(image_name, tag))
    target = get_latest_numeric_indigo_release()
    bingo_version = target["bingo_version"]
    indigo_ref = target["indigo_ref"]
    version_from_repo = get_version_from_indigo(indigo_ref)
    if version_from_repo != bingo_version:
        raise RuntimeError(
            f"Version mismatch for {indigo_ref}: "
            f"derived {bingo_version}, version.txt has {version_from_repo}"
        )
    print(f"Latest numeric release: {indigo_ref} -> {bingo_version}", flush=True)
    return _prepare_bingo_dist_targets([target], pg_majors, tag_exists, verify=False)


def _prepare_bingo_dist_targets(
    targets: list[dict[str, str]],
    pg_majors: str,
    tag_exists: Callable[[str], bool],
    verify: bool = True,
) -> ActionOutputs:
    pg_major_values = parse_pg_majors(pg_majors)
    print(f"Requested PostgreSQL majors: {' '.join(pg_major_values)}", flush=True)
    matrix_entries: list[dict[str, str]] = []
    merge_entries: list[dict[str, str]] = []

    for target in targets:
        bingo_version = target["bingo_version"]
        indigo_ref = target["indigo_ref"]
        if verify:
            version_from_repo = get_version_from_indigo(indigo_ref)
            if version_from_repo != bingo_version:
                raise RuntimeError(
                    f"Version mismatch for {indigo_ref}: "
                    f"derived {bingo_version}, version.txt has {version_from_repo}"
                )
        for pg_major in pg_major_values:
            tag = f"{bingo_version}-postgres{pg_major}"
            print(f"Checking: {tag}", flush=True)
            if tag_exists(tag):
                print("  -> exists, skipping", flush=True)
                continue
            print("  -> missing, will build", flush=True)
            _append_arch_entries(
                matrix_entries,
                {
                    "pg_major": pg_major,
                    "indigo_ref": indigo_ref,
                    "bingo_version": bingo_version,
                },
            )
            merge_entries.append({"pg_major": pg_major, "bingo_version": bingo_version})
    return _outputs(matrix_entries, merge_entries)


def prepare_rdkit_dist(
    image_name: str,
    mode: str,
    rdkit_ref: str,
    min_rdkit_version: str,
    max_rdkit_version: str,
    pg_majors: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for RDKit dist image builds."""
    tag_exists = tag_exists or (lambda tag: ghcr_tag_exists(image_name, tag))
    if mode == "single":
        rdkit_clean = parse_rdkit_ref(rdkit_ref)
        rdkit_releases = [{"ref": rdkit_ref, "clean": rdkit_clean}]
        print(f"Single RDKit dist build: {rdkit_ref} -> {rdkit_clean}", flush=True)
    elif mode == "range":
        rdkit_releases = _rdkit_releases_in_range(min_rdkit_version, max_rdkit_version)
    else:
        raise RuntimeError(f"Unsupported mode: {mode}")
    print(f"Mode: {mode}", flush=True)
    return _prepare_rdkit_dist_targets(rdkit_releases, pg_majors, tag_exists)


def prepare_rdkit_dist_all(
    image_name: str,
    min_rdkit_version: str,
    max_rdkit_version: str,
    pg_majors: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for all RDKit dist versions in a range."""
    tag_exists = tag_exists or (lambda tag: ghcr_tag_exists(image_name, tag))
    rdkit_releases = _rdkit_releases_in_range(min_rdkit_version, max_rdkit_version)
    return _prepare_rdkit_dist_targets(rdkit_releases, pg_majors, tag_exists)


def _rdkit_releases_in_range(
    min_rdkit_version: str,
    max_rdkit_version: str,
) -> list[dict[str, str]]:
    max_version = max_rdkit_version or None
    rdkit_releases = get_rdkit_releases(min_rdkit_version, max_version)
    if max_version:
        print(
            f"RDKit releases from {min_rdkit_version} to {max_version}: "
            f"{[item['clean'] for item in rdkit_releases]}",
            flush=True,
        )
    else:
        print(
            f"RDKit releases >= {min_rdkit_version}: "
            f"{[item['clean'] for item in rdkit_releases]}",
            flush=True,
        )
    return rdkit_releases


def _prepare_rdkit_dist_targets(
    rdkit_releases: list[dict[str, str]],
    pg_majors: str,
    tag_exists: Callable[[str], bool],
) -> ActionOutputs:
    matrix_entries: list[dict[str, str]] = []
    merge_entries: list[dict[str, str]] = []
    for pg_major in parse_pg_majors(pg_majors):
        for rdkit in rdkit_releases:
            tag = f"{rdkit['clean']}-postgres{pg_major}"
            print(f"Checking: {tag}", flush=True)
            if tag_exists(tag):
                print("  -> exists, skipping", flush=True)
                continue
            print("  -> missing, will build", flush=True)
            _append_arch_entries(
                matrix_entries,
                {
                    "pg_major": pg_major,
                    "rdkit_ref": rdkit["ref"],
                    "rdkit_clean": rdkit["clean"],
                },
            )
            merge_entries.append({"pg_major": pg_major, "rdkit_clean": rdkit["clean"]})
    return _outputs(matrix_entries, merge_entries)


def dist_versions_by_pg_major(dist_image_name: str) -> dict[str, list[str]]:
    """Group dist image clean versions by PostgreSQL major from GHCR tags."""
    versions: dict[str, set[str]] = {}
    pattern = re.compile(r"^(\d+\.\d+\.\d+)-postgres(\d+)$")
    for tag in list_ghcr_tags(dist_image_name):
        match = pattern.match(tag)
        if not match:
            continue
        version, pg_major = match.groups()
        versions.setdefault(pg_major, set()).add(version)
    return {
        pg_major: sorted(pg_versions, key=version_tuple)
        for pg_major, pg_versions in versions.items()
    }


def prepare_bingo_runtime(
    registry: str,
    image_owner: str,
    image_name: str,
    dist_image_name: str,
    rocky_version: str,
    pg_majors: str,
    mode: str,
    bingo_version: str,
    min_bingo_version: str,
    max_bingo_version: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for Bingo final images."""
    tag_exists = tag_exists or (lambda tag: tag in set(list_ghcr_tags(image_name)))
    dist_versions = dist_versions_by_pg_major(dist_image_name)
    versions_by_major = _runtime_versions_by_mode(
        "Bingo",
        mode,
        bingo_version,
        min_bingo_version,
        max_bingo_version,
        dist_versions,
        pg_majors,
    )
    return _prepare_bingo_runtime_versions(
        registry,
        image_owner,
        dist_image_name,
        rocky_version,
        pg_majors,
        versions_by_major,
        dist_versions,
        tag_exists,
    )


def prepare_bingo_runtime_all(
    registry: str,
    image_owner: str,
    image_name: str,
    dist_image_name: str,
    rocky_version: str,
    pg_majors: str,
    min_bingo_version: str,
    max_bingo_version: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for all Bingo final image versions in a range."""
    return prepare_bingo_runtime(
        registry,
        image_owner,
        image_name,
        dist_image_name,
        rocky_version,
        pg_majors,
        "range",
        "",
        min_bingo_version,
        max_bingo_version,
        tag_exists,
    )


def prepare_rdkit_runtime(
    registry: str,
    image_owner: str,
    image_name: str,
    dist_image_name: str,
    rocky_version: str,
    pg_majors: str,
    mode: str,
    rdkit_version: str,
    min_rdkit_version: str,
    max_rdkit_version: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for RDKit final images."""
    tag_exists = tag_exists or (lambda tag: tag in set(list_ghcr_tags(image_name)))
    dist_versions = dist_versions_by_pg_major(dist_image_name)
    versions_by_major = _runtime_versions_by_mode(
        "RDKit",
        mode,
        rdkit_version,
        min_rdkit_version,
        max_rdkit_version,
        dist_versions,
        pg_majors,
    )
    return _prepare_rdkit_runtime_versions(
        registry,
        image_owner,
        dist_image_name,
        rocky_version,
        pg_majors,
        versions_by_major,
        dist_versions,
        tag_exists,
    )


def prepare_rdkit_runtime_all(
    registry: str,
    image_owner: str,
    image_name: str,
    dist_image_name: str,
    rocky_version: str,
    pg_majors: str,
    min_rdkit_version: str,
    max_rdkit_version: str,
    tag_exists: Callable[[str], bool] | None = None,
) -> ActionOutputs:
    """Prepare the matrix for all RDKit final image versions in a range."""
    return prepare_rdkit_runtime(
        registry,
        image_owner,
        image_name,
        dist_image_name,
        rocky_version,
        pg_majors,
        "range",
        "",
        min_rdkit_version,
        max_rdkit_version,
        tag_exists,
    )


def _runtime_versions_by_mode(
    name: str,
    mode: str,
    version: str,
    min_version: str,
    max_version: str,
    dist_versions: dict[str, list[str]],
    pg_majors: str,
) -> dict[str, list[str]]:
    pg_major_values = parse_pg_majors(pg_majors)
    if mode == "single":
        clean_version = parse_numeric_semver(version, f"{name.lower()}_version")
        print(f"Using {name} dist tag version {clean_version}", flush=True)
        return {major: [clean_version] for major in pg_major_values}
    if mode != "range":
        raise RuntimeError(f"Unsupported mode: {mode}")

    min_v = version_tuple(min_version)
    max_v = version_tuple(max_version) if max_version else None
    if max_version:
        print(
            f"Using dist tags for {name} versions from {min_version} to {max_version}",
            flush=True,
        )
    else:
        print(f"Using dist tags for {name} versions >= {min_version}", flush=True)
    versions_by_major = {
        major: [
            candidate for candidate in dist_versions.get(major, [])
            if version_tuple(candidate) >= min_v
            and (max_v is None or version_tuple(candidate) <= max_v)
        ]
        for major in pg_major_values
    }
    for major, versions in versions_by_major.items():
        print(f"PG{major} {name} dist versions in range: {versions}", flush=True)
    return versions_by_major


def _prepare_bingo_runtime_versions(
    registry: str,
    image_owner: str,
    dist_image_name: str,
    rocky_version: str,
    pg_majors: str,
    versions_by_major: dict[str, list[str]],
    dist_versions: dict[str, list[str]],
    tag_exists: Callable[[str], bool],
) -> ActionOutputs:
    matrix_entries: list[dict[str, str]] = []
    merge_entries: list[dict[str, str]] = []
    for major in parse_pg_majors(pg_majors):
        versions = versions_by_major.get(major, [])
        if not versions:
            print(f"PG{major} Bingo versions to build: []", flush=True)
            continue
        minor = latest_pg_minor(major)
        print(f"PG{major} latest minor: {minor}", flush=True)
        for bingo_version in versions:
            if bingo_version not in dist_versions.get(major, []):
                print(
                    f"  -> No bingo-dist tag for Bingo {bingo_version} + PG{major}, skipping",
                    flush=True,
                )
                continue
            tag = f"rocky{rocky_version}-postgres{minor}-bingo{bingo_version}"
            print(f"Checking: {tag}", flush=True)
            if tag_exists(tag):
                print("  -> exists, skipping", flush=True)
                continue
            print("  -> missing, will build", flush=True)
            _append_arch_entries(
                matrix_entries,
                {
                    "pg_minor": minor,
                    "pg_major": major,
                    "bingo_version": bingo_version,
                    "bingo_dist_image": (
                        f"{registry}/{image_owner}/{dist_image_name}:"
                        f"{bingo_version}-postgres{major}"
                    ),
                },
            )
            merge_entries.append({
                "pg_minor": minor,
                "pg_major": major,
                "bingo_version": bingo_version,
            })
    print(f"has_builds={bool(matrix_entries)}, {len(merge_entries)} combos to build", flush=True)
    return _outputs(matrix_entries, merge_entries)


def _prepare_rdkit_runtime_versions(
    registry: str,
    image_owner: str,
    dist_image_name: str,
    rocky_version: str,
    pg_majors: str,
    versions_by_major: dict[str, list[str]],
    dist_versions: dict[str, list[str]],
    tag_exists: Callable[[str], bool],
) -> ActionOutputs:
    matrix_entries: list[dict[str, str]] = []
    merge_entries: list[dict[str, str]] = []
    for major in parse_pg_majors(pg_majors):
        versions = versions_by_major.get(major, [])
        if not versions:
            print(f"PG{major} RDKit versions to build: []", flush=True)
            continue
        minor = latest_pg_minor(major)
        print(f"PG{major} latest minor: {minor}", flush=True)
        for rdkit_clean in versions:
            if rdkit_clean not in dist_versions.get(major, []):
                print(
                    f"  -> No rdkit-postgres-dist tag for RDKit {rdkit_clean} + PG{major}, skipping",
                    flush=True,
                )
                continue
            tag = f"rocky{rocky_version}-postgres{minor}-rdkit{rdkit_clean}"
            print(f"Checking: {tag}", flush=True)
            if tag_exists(tag):
                print("  -> exists, skipping", flush=True)
                continue
            print("  -> missing, will build", flush=True)
            _append_arch_entries(
                matrix_entries,
                {
                    "pg_minor": minor,
                    "pg_major": major,
                    "rdkit_ref": rdkit_ref_from_clean(rdkit_clean),
                    "rdkit_clean": rdkit_clean,
                    "rdkit_dist_image": (
                        f"{registry}/{image_owner}/{dist_image_name}:"
                        f"{rdkit_clean}-postgres{major}"
                    ),
                },
            )
            merge_entries.append({
                "pg_minor": minor,
                "pg_major": major,
                "rdkit_ref": rdkit_ref_from_clean(rdkit_clean),
                "rdkit_clean": rdkit_clean,
            })
    print(f"has_builds={bool(matrix_entries)}, {len(merge_entries)} combos to build", flush=True)
    return _outputs(matrix_entries, merge_entries)
