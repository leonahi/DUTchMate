"""Distribution metadata contracts for one synchronized DUTchMate release."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility.
    import tomli as tomllib

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HOST_VERSION_AUTHORITY = REPOSITORY_ROOT / "pyproject.toml"
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
    assert aggregator["optional-dependencies"] == {
        "debug-agent": [f"dutchmate-debug-agent=={host_version}"]
    }


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


def _project(path: Path) -> dict[str, object]:
    assert path.is_file(), f"missing distribution metadata: {path.relative_to(REPOSITORY_ROOT)}"
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    project = parsed["project"]
    assert isinstance(project, dict)
    return project
