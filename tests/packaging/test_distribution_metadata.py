"""Distribution metadata contracts for one synchronized DUTchMate release."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility.
    import tomli as tomllib

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HOST_VERSION_AUTHORITY = REPOSITORY_ROOT / "pyproject.toml"
APACHE_LICENSE = REPOSITORY_ROOT / "LICENSES/Apache-2.0.txt"
EXPECTED_AUTHOR = [{"name": "Nahit Pawar"}]
EXPECTED_URLS = {
    "Homepage": "https://github.com/leonahi/DUTchMate",
    "Repository": "https://github.com/leonahi/DUTchMate",
    "Issues": "https://github.com/leonahi/DUTchMate/issues",
}
DISTRIBUTIONS = {
    "dutchmate": REPOSITORY_ROOT / "packages/dutchmate/pyproject.toml",
    "dutchmate-core": REPOSITORY_ROOT / "core/pyproject.toml",
    "dutchmate-cli": REPOSITORY_ROOT / "apps/cli/pyproject.toml",
    "dutchmate-service": REPOSITORY_ROOT / "apps/service/pyproject.toml",
    "dutchmate-mcp-server": REPOSITORY_ROOT / "apps/mcp_server/pyproject.toml",
    "dutchmate-debug-agent": REPOSITORY_ROOT / "apps/debug_agent/pyproject.toml",
}
EXPECTED_SCRIPTS = {
    "dutchmate": {
        "dutchmate": "dutchmate.entrypoints:app",
        "dm": "dutchmate.entrypoints:app",
        "dutchmate-service": "dutchmate_service.main:main",
        "dutchmate-mcp": "dutchmate_mcp_server.main:main",
    },
    "dutchmate-core": {},
    "dutchmate-cli": {},
    "dutchmate-service": {},
    "dutchmate-mcp-server": {},
    "dutchmate-debug-agent": {
        "dutchmate-debug": "dutchmate_debug_agent.cli:main",
    },
}
EXPECTED_FIRST_PARTY_DEPENDENCIES = {
    "dutchmate": {
        "dutchmate-cli",
        "dutchmate-service",
        "dutchmate-mcp-server",
    },
    "dutchmate-core": set(),
    "dutchmate-cli": {"dutchmate-core"},
    "dutchmate-service": {"dutchmate-core"},
    "dutchmate-mcp-server": {"dutchmate-core"},
    "dutchmate-debug-agent": {"dutchmate-core"},
}


def test_all_host_distributions_use_the_workspace_version() -> None:
    host_version = _project(HOST_VERSION_AUTHORITY)["version"]

    versions = {name: _project(path)["version"] for name, path in DISTRIBUTIONS.items()}

    assert versions == dict.fromkeys(DISTRIBUTIONS, host_version)


def test_first_party_dependencies_use_exact_host_version_constraints() -> None:
    host_version = _project(HOST_VERSION_AUTHORITY)["version"]

    for distribution, expected_names in EXPECTED_FIRST_PARTY_DEPENDENCIES.items():
        project = _project(DISTRIBUTIONS[distribution])
        dependencies = {
            dependency.split("==", maxsplit=1)[0]: dependency
            for dependency in project.get("dependencies", [])
            if dependency.startswith("dutchmate-")
        }
        assert dependencies == {
            name: f"{name}=={host_version}" for name in expected_names
        }

    aggregator = _project(DISTRIBUTIONS["dutchmate"])
    assert "optional-dependencies" not in aggregator


def test_console_scripts_have_one_authoritative_owner() -> None:
    owners: dict[str, str] = {}

    for distribution, path in DISTRIBUTIONS.items():
        scripts = _project(path).get("scripts", {})
        assert scripts == EXPECTED_SCRIPTS[distribution]
        for executable in scripts:
            assert executable not in owners, (
                f"{executable!r} is owned by both {owners[executable]!r} "
                f"and {distribution!r}"
            )
            owners[executable] = distribution


def test_all_host_distributions_publish_apache_license_and_owner_metadata() -> None:
    canonical_license = APACHE_LICENSE.read_text(encoding="utf-8")

    for path in DISTRIBUTIONS.values():
        project = _project(path)
        assert project["license"] == "Apache-2.0"
        assert project["license-files"] == ["LICENSE"]
        assert project["authors"] == EXPECTED_AUTHOR
        assert project["urls"] == EXPECTED_URLS
        assert (path.parent / "LICENSE").read_text(encoding="utf-8") == canonical_license


def test_workspace_root_remains_unlicensed_as_one_distribution() -> None:
    project = _project(HOST_VERSION_AUTHORITY)

    assert "license" not in project
    assert "license-files" not in project


def test_repository_license_policy_preserves_hardware_design_gate() -> None:
    policy = (REPOSITORY_ROOT / "LICENSE.md").read_text(encoding="utf-8")

    assert "Apache-2.0" in policy
    assert "CC-BY-4.0" in policy
    assert "hardware/pcb/debug-helper/legacy-eagle/" in policy
    assert "hardware/pcb/debug-helper/rev-a/" in policy
    assert "not covered" in policy.lower()
    assert "KiCad" in policy


def test_repository_requires_future_dco_sign_off() -> None:
    dco = (REPOSITORY_ROOT / "DCO").read_text(encoding="utf-8")
    contributing = (REPOSITORY_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    pull_request_template = (
        REPOSITORY_ROOT / ".github/pull_request_template.md"
    ).read_text(encoding="utf-8")

    assert "Developer's Certificate of Origin 1.1" in dco
    assert "git commit -s" in contributing
    assert "Signed-off-by:" in contributing
    assert "DCO" in pull_request_template


def _project(path: Path) -> dict[str, object]:
    assert path.is_file(), f"missing distribution metadata: {path.relative_to(REPOSITORY_ROOT)}"
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    project = parsed["project"]
    assert isinstance(project, dict)
    return project
