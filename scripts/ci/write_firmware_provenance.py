"""Collect immutable firmware artifacts and write their provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main() -> None:
    arguments = _parser().parse_args()
    output_dir: Path = arguments.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, dict[str, object]] = {}
    for source in sorted(arguments.artifact, key=lambda path: path.name):
        if not source.is_file():
            raise SystemExit(f"firmware artifact does not exist: {source}")
        if source.name in artifacts:
            raise SystemExit(f"duplicate firmware artifact name: {source.name}")
        destination = output_dir / source.name
        shutil.copy2(source, destination)
        content = destination.read_bytes()
        artifacts[source.name] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }

    manifest = {
        "component": arguments.component,
        "product_version": arguments.product_version,
        "protocol_version": arguments.protocol_version,
        "hardware_revision": arguments.hardware_revision,
        "build_commit": arguments.build_commit,
        "target": arguments.target,
        "configuration": arguments.configuration,
        "zephyr_version": arguments.zephyr_version,
        "sdk_version": arguments.sdk_version,
        "artifacts": artifacts,
    }
    (output_dir / "provenance.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", required=True)
    parser.add_argument("--product-version", required=True)
    parser.add_argument("--protocol-version", required=True)
    parser.add_argument("--hardware-revision", required=True)
    parser.add_argument("--build-commit", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--configuration", required=True)
    parser.add_argument("--zephyr-version", required=True)
    parser.add_argument("--sdk-version", required=True)
    parser.add_argument("--artifact", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


if __name__ == "__main__":
    main()
