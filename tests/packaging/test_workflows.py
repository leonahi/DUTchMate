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


def test_release_bootstraps_publishers_sequentially_without_rebuilding() -> None:
    workflow = _workflow("release.yml")

    publication_order = (
        ("core", "dist/dutchmate_core-*"),
        ("cli", "dist/dutchmate_cli-*"),
        ("service", "dist/dutchmate_service-*"),
        ("mcp-server", "dist/dutchmate_mcp_server-*"),
        ("dutchmate", "dist/dutchmate-[0-9]*"),
    )
    job_ids = (
        "build",
        *(f"publish-testpypi-{name}" for name, _artifact in publication_order),
        "verify-testpypi",
        *(f"publish-pypi-{name}" for name, _artifact in publication_order),
        "verify-pypi",
    )
    for job in job_ids:
        assert f"  {job}:\n" in workflow
    assert 'tags: ["v*.*.*"]' in workflow
    assert "validate_release_tag.py" in workflow
    assert "uv build --all-packages --no-sources" in workflow
    assert "smoke_installed_distribution.py --dist workspace-dist" in workflow
    assert "--dist dist --public-release" in workflow
    assert "environment: testpypi" in workflow
    assert "environment: pypi" in workflow
    assert workflow.count("id-token: write") == 10
    assert "verify_index_artifacts.py" in workflow
    assert "dist/dutchmate_debug_agent-*" not in workflow
    build = _job(workflow, "build")
    assert "id-token: write" not in build

    previous_test_job = "build"
    for name, artifact in publication_order:
        job_id = f"publish-testpypi-{name}"
        job = _job(workflow, job_id)
        assert f"needs: {previous_test_job}" in job
        assert "environment: testpypi" in job
        assert "id-token: write" in job
        assert "UV_PUBLISH_URL: https://test.pypi.org/legacy/" in job
        assert "UV_PUBLISH_CHECK_URL: https://test.pypi.org/simple/" in job
        assert f"uv publish --trusted-publishing always {artifact}" in job
        assert "uv build" not in job
        for other_name, other_artifact in publication_order:
            if other_name != name:
                assert other_artifact not in job
        previous_test_job = job_id

    test_verification = _job(workflow, "verify-testpypi")
    assert f"needs: {previous_test_job}" in test_verification
    assert "--index-url https://test.pypi.org" in test_verification
    assert "uv build" not in test_verification

    previous_production_job = "verify-testpypi"
    for name, artifact in publication_order:
        job_id = f"publish-pypi-{name}"
        job = _job(workflow, job_id)
        assert f"needs: {previous_production_job}" in job
        assert "environment: pypi" in job
        assert "id-token: write" in job
        assert "UV_PUBLISH_URL: https://upload.pypi.org/legacy/" in job
        assert "UV_PUBLISH_CHECK_URL: https://pypi.org/simple/" in job
        assert f"uv publish --trusted-publishing always {artifact}" in job
        assert "uv build" not in job
        for other_name, other_artifact in publication_order:
            if other_name != name:
                assert other_artifact not in job
        previous_production_job = job_id

    production_verification = _job(workflow, "verify-pypi")
    assert f"needs: {previous_production_job}" in production_verification
    assert "--index-url https://pypi.org" in production_verification
    assert "uv build" not in production_verification
    _assert_actions_are_commit_pinned(workflow)


def _workflow(name: str) -> str:
    path = WORKFLOW_ROOT / name
    assert path.is_file(), f"missing workflow: {path.relative_to(REPOSITORY_ROOT)}"
    return path.read_text(encoding="utf-8")


def _job(workflow: str, job_id: str) -> str:
    start = workflow.index(f"  {job_id}:\n")
    match = re.search(r"^  [a-z0-9-]+:\n", workflow[start + 1 :], flags=re.MULTILINE)
    if match is None:
        return workflow[start:]
    return workflow[start : start + 1 + match.start()]


def _assert_actions_are_commit_pinned(workflow: str) -> None:
    action_lines = [line for line in workflow.splitlines() if "uses:" in line]
    assert action_lines
    assert all(PINNED_ACTION.fullmatch(line) for line in action_lines)
