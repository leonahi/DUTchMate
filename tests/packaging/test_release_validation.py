"""Release tag and uploaded-artifact validation contracts."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str):  # type: ignore[no-untyped-def]
    path = REPOSITORY_ROOT / "scripts/ci" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_tag_matches_every_distribution_version() -> None:
    validator = _load_script("validate_release_tag.py")

    assert validator.validate_release_tag("v0.1.0", REPOSITORY_ROOT) == "0.1.0"


@pytest.mark.parametrize("tag", ["0.1.0", "v0.1", "v0.1.0rc1", "release-v0.1.0"])
def test_release_tag_rejects_unsupported_shapes(tag: str) -> None:
    validator = _load_script("validate_release_tag.py")

    with pytest.raises(ValueError, match="vX.Y.Z"):
        validator.validate_release_tag(tag, REPOSITORY_ROOT)


def test_uploaded_release_requires_every_local_artifact_digest(tmp_path: Path) -> None:
    verifier = _load_script("verify_index_artifacts.py")
    artifact = tmp_path / "dutchmate-0.1.0.tar.gz"
    artifact.write_bytes(b"accepted artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

    verifier.verify_artifacts(
        artifacts={"dutchmate": {artifact.name: digest}},
        releases={"dutchmate": {artifact.name: digest}},
    )

    with pytest.raises(ValueError, match="digest mismatch"):
        verifier.verify_artifacts(
            artifacts={"dutchmate": {artifact.name: digest}},
            releases={"dutchmate": {artifact.name: "0" * 64}},
        )
