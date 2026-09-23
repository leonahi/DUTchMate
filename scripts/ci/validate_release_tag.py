"""Validate a host release tag against every synchronized distribution version."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility.
    import tomli as tomllib

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VERSION_FILES = (
    Path("pyproject.toml"),
    Path("packages/dutchmate/pyproject.toml"),
    Path("core/pyproject.toml"),
    Path("apps/cli/pyproject.toml"),
    Path("apps/service/pyproject.toml"),
    Path("apps/mcp_server/pyproject.toml"),
    Path("apps/debug_agent/pyproject.toml"),
)
TAG_PATTERN = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


def validate_release_tag(tag: str, repository_root: Path = REPOSITORY_ROOT) -> str:
    """Return the release version after validating tag shape and all authorities."""
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ValueError(f"release tag must have the exact stable form vX.Y.Z: {tag!r}")
    version = tag.removeprefix("v")

    mismatches: list[str] = []
    for relative_path in VERSION_FILES:
        path = repository_root / relative_path
        project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
        declared = project["version"]
        if declared != version:
            mismatches.append(f"{relative_path}: expected {version}, found {declared}")
    if mismatches:
        raise ValueError("release tag/version mismatch:\n" + "\n".join(mismatches))
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    arguments = parser.parse_args()
    try:
        version = validate_release_tag(arguments.tag)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(version)


if __name__ == "__main__":
    main()
