from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from dutchmate_debug_agent.coding_context import validate_coding_context

SESSION = "20260920T120000Z-a1b2c3d4"
COMMIT = "0123456789abcdef"


def _package() -> dict[str, object]:
    return {
        "schema_version": 1,
        "objective": "Explain the boot failure",
        "session_ids": [SESSION],
        "build": {
            "commit": COMMIT,
            "build_id": "debug-1042",
            "board": "pico2",
            "configuration": "debug",
        },
        "changed_files": [{"path": "src/boot.c", "summary": "Changed initialization order"}],
        "excerpts": [
            {
                "kind": "source",
                "path": "src/boot.c",
                "commit": COMMIT,
                "start_line": 80,
                "end_line": 80,
                "language": "c",
                "text": "boot();\n",
            }
        ],
        "symbols": ["boot"],
        "constraints": ["Keep the UART API stable"],
    }


def test_valid_source_context_is_versioned_and_json_serializable() -> None:
    result = validate_coding_context(_package())

    assert result.schema_version == 1
    assert result.session_ids == (SESSION,)
    assert result.source_paths == ("src/boot.c",)
    assert result.excerpt_text_bytes == 8
    assert result.limits.excerpts == 8
    assert json.loads(json.dumps(asdict(result)))["excerpts"][0]["text"] == "boot();\n"


def test_diff_requires_matching_unified_hunk_provenance() -> None:
    package = _package()
    package["excerpts"] = [
        {
            "kind": "diff",
            "path": "src/boot.c",
            "base_commit": COMMIT,
            "head_commit": "abcdef0123456789",
            "hunks": [{"old_start": 8, "old_count": 1, "new_start": 8, "new_count": 2}],
            "text": "@@ -8 +8,2 @@\n-old\n+new\n+more\n",
        }
    ]
    result = validate_coding_context(package)
    assert result.excerpts[0].hunks[0].new_count == 2

    package["excerpts"][0]["hunks"][0]["new_count"] = 3
    with pytest.raises(ValueError, match="hunk"):
        validate_coding_context(package)


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"objective": "x" * 4097},
        {"session_ids": []},
        {"session_ids": [SESSION, SESSION]},
        {"changed_files": [{"path": "../secrets", "summary": "change"}]},
        {"changed_files": [{"path": "/tmp/code.c", "summary": "change"}]},
        {"changed_files": [{"path": "C:\\code.c", "summary": "change"}]},
        {"changed_files": [{"path": ".env", "summary": "change"}]},
        {"changed_files": [{"path": "keys/private.pem", "summary": "change"}]},
    ],
)
def test_rejects_malformed_or_unsafe_package_fields(change: dict[str, object]) -> None:
    package = _package()
    package.update(change)
    with pytest.raises(ValueError):
        validate_coding_context(package)


@pytest.mark.parametrize(
    "change",
    [
        {"path": "../src/boot.c"},
        {"path": "secrets/token.txt"},
        {"commit": ""},
        {"start_line": 0},
        {"end_line": 79},
        {"text": "binary\x00data"},
        {"text": "-----BEGIN PRIVATE KEY-----\nsecret\n"},
        {"text": "api_key = 'sk-example-secret-value'\n"},
        {"text": "a" * 16385},
        {"text": "line\n" * 201, "end_line": 280},
    ],
)
def test_rejects_untrusted_excerpt_content_and_provenance(change: dict[str, object]) -> None:
    package = _package()
    package["excerpts"][0].update(change)
    with pytest.raises(ValueError):
        validate_coding_context(package)


def test_rejects_count_limits_and_unbounded_auxiliary_text() -> None:
    package = _package()
    package["excerpts"] = package["excerpts"] * 9
    with pytest.raises(ValueError, match="excerpts"):
        validate_coding_context(package)

    package = _package()
    package["changed_files"] = package["changed_files"] * 101
    with pytest.raises(ValueError, match="changed_files"):
        validate_coding_context(package)

    package = _package()
    package["symbols"] = ["boot"] * 101
    with pytest.raises(ValueError, match="symbols"):
        validate_coding_context(package)

    package = _package()
    package["constraints"] = ["x" * 4097]
    with pytest.raises(ValueError, match="constraints"):
        validate_coding_context(package)


def test_rejects_missing_source_provenance_and_unknown_fields() -> None:
    package = _package()
    del package["excerpts"][0]["commit"]
    with pytest.raises(ValueError, match="commit"):
        validate_coding_context(package)

    package = _package()
    package["repository_path"] = "/tmp/project"
    with pytest.raises(ValueError, match="field"):
        validate_coding_context(package)


def test_rejects_excerpt_range_that_does_not_match_supplied_lines() -> None:
    package = _package()
    package["excerpts"][0]["end_line"] = 81
    with pytest.raises(ValueError, match="provenance"):
        validate_coding_context(package)


def test_rejects_diff_body_that_disagrees_with_hunk_counts() -> None:
    package = _package()
    package["excerpts"] = [
        {
            "kind": "diff",
            "path": "src/boot.c",
            "base_commit": COMMIT,
            "head_commit": "abcdef0123456789",
            "hunks": [{"old_start": 8, "old_count": 1, "new_start": 8, "new_count": 2}],
            "text": "@@ -8 +8,2 @@\n-old\n+new\n",
        }
    ]
    with pytest.raises(ValueError, match="hunk"):
        validate_coding_context(package)


def test_rejects_session_id_with_control_character() -> None:
    package = _package()
    package["session_ids"] = ["bad\nname"]
    with pytest.raises(ValueError, match="session_ids"):
        validate_coding_context(package)


def test_total_excerpt_budget_counts_utf8_bytes() -> None:
    package = _package()
    excerpt = package["excerpts"][0]
    excerpt["text"] = "é" * 8000
    package["excerpts"] = [dict(excerpt) for _ in range(5)]
    with pytest.raises(ValueError, match="total text byte"):
        validate_coding_context(package)


def test_optional_build_must_be_an_object_when_supplied() -> None:
    package = _package()
    package["build"] = None
    with pytest.raises(ValueError, match="build"):
        validate_coding_context(package)


def test_repository_relative_path_may_contain_spaces() -> None:
    package = _package()
    package["changed_files"][0]["path"] = "board revisions/boot config.c"
    result = validate_coding_context(package)
    assert result.changed_files[0].path == "board revisions/boot config.c"
