"""Version parsing and PostgreSQL package metadata helpers."""

from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET

from .github import fetch_bytes


NUMERIC_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def version_tuple(value: str) -> tuple[int, ...]:
    """Convert a dot-separated numeric version into a sortable tuple."""
    return tuple(int(part) for part in value.split("."))


def parse_numeric_semver(value: str, field_name: str) -> str:
    """Validate and return a numeric X.Y.Z version string."""
    if not value:
        raise RuntimeError(f"Missing required value: {field_name}")
    if not NUMERIC_SEMVER.fullmatch(value):
        raise RuntimeError(
            f"Unexpected {field_name}: {value}. Expected numeric semver X.Y.Z"
        )
    return value


def parse_pg_majors(raw_value: str) -> list[str]:
    """Parse PostgreSQL major versions from a space- or comma-separated string."""
    values = [value for value in re.split(r"[\s,]+", raw_value.strip()) if value]
    if not values:
        raise RuntimeError("No PostgreSQL majors provided")

    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not re.fullmatch(r"\d+", value):
            raise RuntimeError(f"Unexpected PostgreSQL major value: {value}")
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def parse_rdkit_ref(rdkit_ref: str) -> str:
    """Convert an RDKit release tag into a clean dotted version."""
    match = re.fullmatch(r"Release_(\d{4})_(\d{2})_(\d+)", rdkit_ref)
    if not match:
        raise RuntimeError(
            "Unexpected RDKit tag format: "
            f"{rdkit_ref}. Expected Release_YYYY_MM_PATCH"
        )
    return ".".join(match.groups())


def rdkit_ref_from_clean(clean_version: str) -> str:
    """Convert a clean RDKit version into the upstream release tag format."""
    return f"Release_{clean_version.replace('.', '_')}"


def latest_pg_minor(major: str, arch: str = "x86_64") -> str:
    """Return the latest PGDG minor version for a PostgreSQL major version."""
    repo_base = (
        "https://download.postgresql.org/pub/repos/yum/reporpms/"
        f"EL-9-{arch}"
    )
    repomd_url = (
        f"https://download.postgresql.org/pub/repos/yum/{major}/redhat/"
        f"rhel-9-{arch}/repodata/repomd.xml"
    )
    repomd = ET.fromstring(fetch_bytes(repomd_url))
    ns = {"repo": "http://linux.duke.edu/metadata/repo"}
    primary_href = None
    for data in repomd.findall("repo:data", ns):
        if data.attrib.get("type") != "primary":
            continue
        location = data.find("repo:location", ns)
        if location is not None:
            primary_href = location.attrib["href"]
            break
    if not primary_href:
        raise RuntimeError(f"No primary metadata found for PostgreSQL {major}")

    primary_url = repomd_url.rsplit("/", 1)[0] + "/" + primary_href.split("/")[-1]
    primary_xml = gzip.decompress(fetch_bytes(primary_url))
    root = ET.fromstring(primary_xml)
    common = {"rpm": "http://linux.duke.edu/metadata/common"}
    package_name = f"postgresql{major}-server"
    versions = []
    for package in root.findall("rpm:package", common):
        name = package.findtext("rpm:name", namespaces=common)
        if name != package_name:
            continue
        version_node = package.find("rpm:version", common)
        if version_node is None:
            continue
        version = version_node.attrib.get("ver", "")
        if re.fullmatch(rf"{re.escape(str(major))}\.\d+", version):
            versions.append(version)

    if not versions:
        raise RuntimeError(f"No {package_name} versions found in {repo_base}")
    return sorted(versions, key=version_tuple)[-1]

