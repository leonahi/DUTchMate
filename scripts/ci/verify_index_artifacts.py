"""Verify that a package index exposes the exact locally accepted artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from email.parser import Parser
from pathlib import Path


def verify_artifacts(
    *,
    artifacts: dict[str, dict[str, str]],
    releases: dict[str, dict[str, str]],
) -> None:
    """Require each local filename and SHA-256 digest on the remote index."""
    for project, files in artifacts.items():
        remote_files = releases.get(project, {})
        for filename, digest in files.items():
            remote_digest = remote_files.get(filename)
            if remote_digest is None:
                raise ValueError(f"missing uploaded artifact: {project}/{filename}")
            if remote_digest != digest:
                raise ValueError(
                    f"digest mismatch for {project}/{filename}: "
                    f"local {digest}, remote {remote_digest}"
                )


def collect_artifacts(dist: Path) -> tuple[str, dict[str, dict[str, str]]]:
    """Read project identities from wheel/sdist metadata and hash each artifact."""
    version: str | None = None
    artifacts: dict[str, dict[str, str]] = {}
    paths = sorted((*dist.glob("*.whl"), *dist.glob("*.tar.gz")))
    if not paths:
        raise ValueError(f"no distributions found in {dist}")
    for path in paths:
        name, artifact_version = _artifact_identity(path)
        if version is None:
            version = artifact_version
        elif artifact_version != version:
            raise ValueError(
                f"mixed artifact versions: expected {version}, "
                f"found {artifact_version} in {path.name}"
            )
        canonical_name = re.sub(r"[-_.]+", "-", name).lower()
        artifacts.setdefault(canonical_name, {})[path.name] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    assert version is not None
    return version, artifacts


def fetch_releases(
    *, index_url: str, version: str, projects: set[str]
) -> dict[str, dict[str, str]]:
    releases: dict[str, dict[str, str]] = {}
    for project in sorted(projects):
        url = f"{index_url.rstrip('/')}/pypi/{project}/{version}/json"
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
            payload = json.load(response)
        releases[project] = {
            item["filename"]: item["digests"]["sha256"] for item in payload["urls"]
        }
    return releases


def _artifact_identity(path: Path) -> tuple[str, str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            metadata_path = next(
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            )
            metadata = Parser().parsestr(archive.read(metadata_path).decode("utf-8"))
    else:
        with tarfile.open(path, mode="r:gz") as archive:
            member = next(
                item
                for item in archive.getmembers()
                if item.name.count("/") == 1 and item.name.endswith("/PKG-INFO")
            )
            extracted = archive.extractfile(member)
            assert extracted is not None
            metadata = Parser().parsestr(extracted.read().decode("utf-8"))
    return metadata["Name"], metadata["Version"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--index-url", required=True)
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay-seconds", type=float, default=10)
    arguments = parser.parse_args()
    version, artifacts = collect_artifacts(arguments.dist.resolve())

    error: Exception | None = None
    for attempt in range(1, arguments.attempts + 1):
        try:
            releases = fetch_releases(
                index_url=arguments.index_url,
                version=version,
                projects=set(artifacts),
            )
            verify_artifacts(artifacts=artifacts, releases=releases)
            print(f"verified {sum(map(len, artifacts.values()))} artifacts for {version}")
            return
        except (ValueError, urllib.error.URLError) as caught:
            error = caught
            if attempt < arguments.attempts:
                time.sleep(arguments.delay_seconds)
    raise SystemExit(f"index artifact verification failed: {error}")


if __name__ == "__main__":
    main()
