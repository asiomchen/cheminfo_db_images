#!/usr/bin/env python3
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET


GITHUB_API = "https://api.github.com"
GHCR_OWNER = os.environ.get("GHCR_OWNER", "asiomchen")


def fetch_bytes(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def fetch_json(url, headers=None):
    return json.loads(fetch_bytes(url, headers).decode())


def github_headers():
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def version_tuple(value):
    return tuple(int(part) for part in value.split("."))


def list_ghcr_tags(package_name):
    tags = set()
    page = 1
    while True:
        url = (
            f"{GITHUB_API}/users/{GHCR_OWNER}/packages/container/"
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


def ghcr_tag_exists(package_name, tag):
    return tag in set(list_ghcr_tags(package_name))


def latest_pg_minor(major, arch="x86_64"):
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
        if data.attrib.get("type") == "primary":
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


def main():
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
