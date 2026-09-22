"""Firmware product-version and artifact-provenance contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROVENANCE_SCRIPT = REPOSITORY_ROOT / "scripts/ci/write_firmware_provenance.py"
FIRMWARE_VERSION = (
    REPOSITORY_ROOT / "hardware/firmware/rp2350_debug_helper/PRODUCT_VERSION"
)


def test_debug_helper_has_an_independent_semantic_version() -> None:
    assert FIRMWARE_VERSION.read_text(encoding="utf-8") == "0.1.0\n"


def test_provenance_collector_copies_and_hashes_firmware_artifacts(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()
    artifacts = {
        "zephyr.elf": b"elf",
        "zephyr.map": b"map",
        "zephyr.uf2": b"uf2",
        "size.txt": b"text data bss dec hex filename\n",
    }
    for name, content in artifacts.items():
        (build / name).write_bytes(content)
    output = tmp_path / "artifacts"

    result = subprocess.run(
        [
            sys.executable,
            str(PROVENANCE_SCRIPT),
            "--component",
            "debug-helper",
            "--product-version",
            "0.1.0",
            "--protocol-version",
            "1",
            "--hardware-revision",
            "rev-a",
            "--build-commit",
            "0123456789abcdef",
            "--target",
            "rpi_pico2/rp2350a/m33",
            "--configuration",
            "default",
            "--zephyr-version",
            "4.4.2",
            "--sdk-version",
            "1.0.1",
            "--output-dir",
            str(output),
            *[
                argument
                for name in artifacts
                for argument in ("--artifact", str(build / name))
            ],
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
    assert manifest == {
        "component": "debug-helper",
        "product_version": "0.1.0",
        "protocol_version": "1",
        "hardware_revision": "rev-a",
        "build_commit": "0123456789abcdef",
        "target": "rpi_pico2/rp2350a/m33",
        "configuration": "default",
        "zephyr_version": "4.4.2",
        "sdk_version": "1.0.1",
        "artifacts": {
            name: {
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
            }
            for name, content in sorted(artifacts.items())
        },
    }
    assert {path.name for path in output.iterdir()} == {
        *artifacts,
        "provenance.json",
    }
