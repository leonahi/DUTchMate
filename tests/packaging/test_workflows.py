"""Delivery workflow configuration contracts."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github/workflows"
PINNED_ACTION = re.compile(r"\s*- uses: [^@\s]+@[0-9a-f]{40}(?:\s+#.*)?$")


def test_python_ci_has_the_required_jobs_and_pinned_actions() -> None:
    workflow = _workflow("ci.yml")

    for job in ("quality", "python-tests", "contracts", "package-build"):
        assert f"  {job}:\n" in workflow
    for version in ("3.10", "3.11", "3.12", "3.13", "3.14"):
        assert f'"{version}"' in workflow
    assert "uv sync --locked --all-packages --dev" in workflow
    assert "uv build --all-packages --no-sources" in workflow
    assert not (WORKFLOW_ROOT / "package.yml").exists()
    _assert_actions_are_commit_pinned(workflow)


def test_firmware_ci_has_three_builds_and_pinned_inputs() -> None:
    workflow = _workflow("firmware.yml")

    assert "--mr v4.4.2" in workflow
    assert "--mr v4.4.0" in workflow
    assert "configuration: default-115200" in workflow
    assert "configuration: enhanced-460800" in workflow
    assert re.search(
        r"image: ghcr\.io/zephyrproject-rtos/ci:v0\.29\.4@sha256:[0-9a-f]{64}$",
        workflow,
        flags=re.MULTILINE,
    )
    assert "defaults:\n  run:\n    shell: bash" in workflow
    assert "write_firmware_provenance.py" in workflow
    assert not (WORKFLOW_ROOT / "hil.yml").exists()
    _assert_actions_are_commit_pinned(workflow)


def _workflow(name: str) -> str:
    path = WORKFLOW_ROOT / name
    assert path.is_file(), f"missing workflow: {path.relative_to(REPOSITORY_ROOT)}"
    return path.read_text(encoding="utf-8")


def _assert_actions_are_commit_pinned(workflow: str) -> None:
    action_lines = [line for line in workflow.splitlines() if "uses:" in line]
    assert action_lines
    assert all(PINNED_ACTION.fullmatch(line) for line in action_lines)
