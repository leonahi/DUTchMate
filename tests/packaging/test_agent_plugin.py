"""Portable coding-agent plugin packaging contracts."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins/dutchmate"
MARKETPLACE_PATH = REPOSITORY_ROOT / ".agents/plugins/marketplace.json"
SCHEMA_ROOT = Path(__file__).with_name("schemas")


def test_portable_plugin_manifest_and_stdio_mcp_registration() -> None:
    plugin = _json(PLUGIN_ROOT / "plugin.json")
    mcp = _json(PLUGIN_ROOT / "mcp.json")

    Draft202012Validator(_json(SCHEMA_ROOT / "plugin.schema.json")).validate(plugin)
    Draft202012Validator(_json(SCHEMA_ROOT / "mcp.schema.json")).validate(mcp)

    assert plugin == {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "dutchmate",
        "version": "0.1.0",
        "description": (
            "Deterministic DUT control and bounded debug evidence through DUTchMate MCP."
        ),
    }
    assert mcp == {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {
            "dutchmate": {
                "type": "stdio",
                "command": "dutchmate",
                "args": ["mcp"],
            }
        },
    }


def test_repo_marketplace_exposes_the_portable_plugin() -> None:
    marketplace = _json(MARKETPLACE_PATH)

    assert marketplace == {
        "name": "dutchmate-local",
        "interface": {"displayName": "DUTchMate Local Plugins"},
        "plugins": [
            {
                "name": "dutchmate",
                "source": {"source": "local", "path": "./plugins/dutchmate"},
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Developer Tools",
            }
        ],
    }


def test_plugin_skills_have_valid_frontmatter() -> None:
    skill_paths = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))

    assert [path.parent.name for path in skill_paths] == [
        "investigate-debug-session",
        "operate-dutchmate",
    ]
    for path in skill_paths:
        frontmatter = _frontmatter(path)
        assert frontmatter["name"] == path.parent.name
        assert frontmatter["description"].strip()


def _json(path: Path) -> dict[str, object]:
    assert path.is_file(), f"missing plugin file: {path.relative_to(REPOSITORY_ROOT)}"
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    header, separator, _ = text[4:].partition("\n---\n")
    assert separator
    fields = dict(line.split(":", maxsplit=1) for line in header.splitlines())
    return {key.strip(): value.strip() for key, value in fields.items()}
