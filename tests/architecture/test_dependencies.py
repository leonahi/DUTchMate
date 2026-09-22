"""Executable dependency constraints for the DUTchMate modular monolith."""

from __future__ import annotations

import ast
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ROOTS = {
    "dutchmate": REPOSITORY_ROOT / "packages/dutchmate/src/dutchmate",
    "dutchmate_core": REPOSITORY_ROOT / "core/src/dutchmate_core",
    "dutchmate_cli": REPOSITORY_ROOT / "apps/cli/src/dutchmate_cli",
    "dutchmate_service": REPOSITORY_ROOT / "apps/service/src/dutchmate_service",
    "dutchmate_mcp_server": REPOSITORY_ROOT / "apps/mcp_server/src/dutchmate_mcp_server",
    "dutchmate_debug_agent": REPOSITORY_ROOT / "apps/debug_agent/src/dutchmate_debug_agent",
}

DELIVERY_FRAMEWORKS = frozenset(
    {
        "fastapi",
        "httpx",
        "mcp",
        "pydantic",
        "typer",
        "uvicorn",
    }
)
APPLICATION_MODULES = frozenset(
    {
        "dutchmate_core.gpio_config.configurator",
        "dutchmate_core.runtime",
        "dutchmate_core.workflows.capture",
        "dutchmate_core.workflows.device_actions",
    }
)
ADAPTER_DEPENDENCY_PREFIXES = (
    "dutchmate_core.backends.basic",
    "dutchmate_core.backends.enhanced",
    "dutchmate_core.device_connection",
    "dutchmate_core.session_store.store",
    "pathlib",
)

# These are the concrete boundary leaks recorded by the 2026-08-17 audit. The
# test intentionally requires an exact match: new exceptions fail immediately,
# and removing an exception requires deleting its stale entry here.
KNOWN_APPLICATION_ADAPTER_EXCEPTIONS: frozenset[tuple[str, str]] = frozenset()


def test_core_never_depends_on_delivery_packages_or_frameworks() -> None:
    modules = _production_modules()
    violations: set[tuple[str, str]] = set()
    forbidden_prefixes = (
        "dutchmate",
        "dutchmate_cli",
        "dutchmate_debug_agent",
        "dutchmate_mcp_server",
        "dutchmate_service",
    )

    for module, path in modules.items():
        if not _matches_prefix(module, "dutchmate_core"):
            continue
        for imported in _module_imports(path):
            if imported.split(".", maxsplit=1)[0] in DELIVERY_FRAMEWORKS or any(
                _matches_prefix(imported, prefix) for prefix in forbidden_prefixes
            ):
                violations.add((module, imported))

    assert violations == set()


def test_delivery_packages_do_not_import_each_other() -> None:
    modules = _production_modules()
    forbidden_by_package = {
        "dutchmate_cli": (
            "dutchmate",
            "dutchmate_debug_agent",
            "dutchmate_mcp_server",
            "dutchmate_service",
        ),
        "dutchmate_debug_agent": (
            "dutchmate",
            "dutchmate_cli",
            "dutchmate_mcp_server",
            "dutchmate_service",
        ),
        "dutchmate_mcp_server": (
            "dutchmate",
            "dutchmate_cli",
            "dutchmate_debug_agent",
            "dutchmate_service",
        ),
        "dutchmate_service": (
            "dutchmate",
            "dutchmate_cli",
            "dutchmate_debug_agent",
            "dutchmate_mcp_server",
        ),
    }
    violations: set[tuple[str, str]] = set()

    for module, path in modules.items():
        package = module.split(".", maxsplit=1)[0]
        forbidden = forbidden_by_package.get(package)
        if forbidden is None:
            continue
        for imported in _module_imports(path):
            if any(_matches_prefix(imported, prefix) for prefix in forbidden):
                violations.add((module, imported))

    assert violations == set()


def test_production_import_graph_is_acyclic() -> None:
    modules = _production_modules()
    graph = {
        module: {
            imported
            for imported in _module_imports(path)
            if imported in modules
        }
        for module, path in modules.items()
    }

    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:  # pragma: no cover - exercised only by a regression.
        raise AssertionError(f"production import cycle detected: {exc.args[1]}") from exc


def test_known_application_adapter_exceptions_do_not_expand_or_go_stale() -> None:
    modules = _production_modules()
    actual = {
        (module, imported)
        for module in APPLICATION_MODULES
        for imported in _module_imports(modules[module])
        if any(
            _matches_prefix(imported, prefix)
            for prefix in ADAPTER_DEPENDENCY_PREFIXES
        )
    }

    assert actual == KNOWN_APPLICATION_ADAPTER_EXCEPTIONS


def _production_modules() -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for package, root in PRODUCTION_ROOTS.items():
        for path in root.rglob("*.py"):
            relative = path.relative_to(root).with_suffix("")
            parts = relative.parts
            if parts == ("__init__",):
                module = package
            elif parts[-1] == "__init__":
                module = f"{package}.{'.'.join(parts[:-1])}"
            else:
                module = f"{package}.{'.'.join(parts)}"
            modules[module] = path
    return modules


def _module_imports(path: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    return imports


def _matches_prefix(value: str, prefix: str) -> bool:
    return value == prefix or value.startswith(f"{prefix}.")
