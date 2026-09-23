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
        r"ZEPHYR_CI_IMAGE: ghcr\.io/zephyrproject-rtos/ci:v0\.29\.4@sha256:[0-9a-f]{64}$",
        workflow,
        flags=re.MULTILINE,
    )
    assert "\n    container:" not in workflow
    assert "defaults:\n  run:\n    shell: bash" in workflow
    assert "write_firmware_provenance.py" in workflow
    assert not (WORKFLOW_ROOT / "hil.yml").exists()
    debug_job = workflow[
        workflow.index("  debug-helper:\n") : workflow.index("  pico-fixture:\n")
    ]
    fixture_job = workflow[workflow.index("  pico-fixture:\n") :]
    for job in (debug_job, fixture_job):
        cleanup = job.index("- name: Free disk space before pulling Zephyr")
        pull = job.index('docker pull "$ZEPHYR_CI_IMAGE"')
        run = job.index("docker run --rm")
        assert cleanup < pull < run
        assert '--volume "$GITHUB_WORKSPACE:$GITHUB_WORKSPACE"' in job
        assert '--volume "$RUNNER_TEMP:$RUNNER_TEMP"' in job
    _assert_actions_are_commit_pinned(workflow)


def test_firmware_ci_uses_the_pinned_sdk_size_tool_without_path_lookup() -> None:
    workflow = _workflow("firmware.yml")
    sdk_size_tool = (
        '"/opt/toolchains/zephyr-sdk-${ZSDK_VERSION}/gnu/arm-zephyr-eabi/bin/'
        'arm-zephyr-eabi-size"'
    )

    assert workflow.count(sdk_size_tool) == 2
    assert not re.search(r"^\s+arm-zephyr-eabi-size \\$", workflow, flags=re.MULTILINE)


def test_release_build_and_publish_authority_are_separated() -> None:
    workflow = _workflow("release.yml")

    for job in ("build", "publish-testpypi", "verify-testpypi", "publish-pypi"):
        assert f"  {job}:\n" in workflow
    assert 'tags: ["v*.*.*"]' in workflow
    assert "validate_release_tag.py" in workflow
    assert "uv build --all-packages --no-sources" in workflow
    assert "smoke_installed_distribution.py --dist workspace-dist" in workflow
    assert "--dist dist --public-release" in workflow
    assert "environment: testpypi" in workflow
    assert "environment: pypi" in workflow
    assert workflow.count("id-token: write") == 2
    assert "verify_index_artifacts.py" in workflow
    assert "dist/dutchmate_debug_agent-*" not in workflow
    for artifact in (
        "dist/dutchmate_core-*",
        "dist/dutchmate_cli-*",
        "dist/dutchmate_service-*",
        "dist/dutchmate_mcp_server-*",
        "dist/dutchmate-[0-9]*",
    ):
        assert artifact in workflow

    build = workflow[workflow.index("  build:\n") : workflow.index("  publish-testpypi:\n")]
    test_publish = workflow[
        workflow.index("  publish-testpypi:\n") : workflow.index("  verify-testpypi:\n")
    ]
    verification = workflow[
        workflow.index("  verify-testpypi:\n") : workflow.index("  publish-pypi:\n")
    ]
    production_publish = workflow[workflow.index("  publish-pypi:\n") :]

    assert "id-token: write" not in build
    assert "uv build" not in test_publish
    assert "uv build" not in verification
    assert "uv build" not in production_publish
    assert "needs: verify-testpypi" in production_publish
    _assert_actions_are_commit_pinned(workflow)


def _workflow(name: str) -> str:
    path = WORKFLOW_ROOT / name
    assert path.is_file(), f"missing workflow: {path.relative_to(REPOSITORY_ROOT)}"
    return path.read_text(encoding="utf-8")


def _assert_actions_are_commit_pinned(workflow: str) -> None:
    action_lines = [line for line in workflow.splitlines() if "uses:" in line]
    assert action_lines
    assert all(PINNED_ACTION.fullmatch(line) for line in action_lines)
