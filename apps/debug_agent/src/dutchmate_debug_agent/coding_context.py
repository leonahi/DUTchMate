"""Pure validation of caller-selected source context; no repository access."""

from __future__ import annotations

import re
from dataclasses import dataclass

_COMMIT = re.compile(r"[0-9a-fA-F]{7,64}\Z")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*$")
_SECRET = re.compile(
    r"-----BEGIN (?:[A-Z ]* )?PRIVATE KEY-----"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    r"|\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"
    r"|\bsk-[A-Za-z0-9_-]{16,}\b"
    r"|\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|password|client[_-]?secret)"
    r"\s*[=:]\s*['\"]?[^\s'\"]{8,}",
    re.IGNORECASE,
)
_SENSITIVE_NAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "kubeconfig",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "service-account.json",
}
_SENSITIVE_DIRS = {".git", ".ssh", ".aws", "secrets", "credentials", "private_keys"}
_SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}


@dataclass(frozen=True, slots=True)
class CodingContextLimits:
    objective_bytes: int = 4096
    changed_files: int = 100
    symbols: int = 100
    excerpts: int = 8
    excerpt_lines: int = 200
    excerpt_bytes: int = 16384
    total_excerpt_bytes: int = 65536
    session_ids: int = 8
    constraints: int = 100
    auxiliary_text_bytes: int = 4096
    identifier_bytes: int = 256
    path_bytes: int = 1024


@dataclass(frozen=True, slots=True)
class BuildContext:
    commit: str
    build_id: str
    board: str
    configuration: str


@dataclass(frozen=True, slots=True)
class ChangedFile:
    path: str
    summary: str


@dataclass(frozen=True, slots=True)
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int


@dataclass(frozen=True, slots=True)
class ContextExcerpt:
    kind: str
    path: str
    text: str
    commit: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    language: str | None = None
    base_commit: str | None = None
    head_commit: str | None = None
    hunks: tuple[DiffHunk, ...] = ()


@dataclass(frozen=True, slots=True)
class CodingContext:
    schema_version: int
    objective: str
    session_ids: tuple[str, ...]
    build: BuildContext | None
    changed_files: tuple[ChangedFile, ...]
    excerpts: tuple[ContextExcerpt, ...]
    symbols: tuple[str, ...]
    constraints: tuple[str, ...]
    source_paths: tuple[str, ...]
    excerpt_text_bytes: int
    limits: CodingContextLimits


def _mapping(
    value: object,
    *,
    field: str,
    required: set[str],
    optional: set[str] | frozenset[str] = frozenset(),
) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise ValueError(f"{field} has missing or unknown field(s): {sorted(missing | unknown)}")
    return value


def _sequence(value: object, *, field: str, maximum: int, nonempty: bool = False) -> list[object]:
    if not isinstance(value, list) or len(value) > maximum or (nonempty and not value):
        raise ValueError(f"{field} must be a list with {int(nonempty)}..{maximum} entries")
    return value


def _text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or value.strip() == "":
        raise ValueError(f"{field} must be nonempty text")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError(f"{field} is not UTF-8 text") from exc
    if size > maximum or any(
        (ord(char) < 32 and char not in "\n\t") or 127 <= ord(char) <= 159 for char in value
    ):
        raise ValueError(f"{field} exceeds its text limit or contains binary/control data")
    if _SECRET.search(value):
        raise ValueError(f"{field} contains known secret material")
    return value


def _path(value: object, *, field: str, limits: CodingContextLimits) -> str:
    path = _text(value, field=field, maximum=limits.path_bytes)
    parts = path.split("/")
    lowered = [part.lower() for part in parts]
    if (
        path.startswith("/")
        or "\\" in path
        or ":" in path
        or any(part in {"", ".", ".."} for part in parts)
        or any(char in "\n\t" for char in path)
        or any(part in _SENSITIVE_DIRS for part in lowered[:-1])
        or lowered[-1] in _SENSITIVE_NAMES
        or lowered[-1].startswith((".env.", "credentials.", "secret.", "secrets."))
        or any(lowered[-1].endswith(suffix) for suffix in _SENSITIVE_SUFFIXES)
    ):
        raise ValueError(f"{field} must be a safe repository-relative path")
    return path


def _commit(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _COMMIT.fullmatch(value):
        raise ValueError(f"{field} must be a Git commit identifier")
    return value


def _positive(value: object, *, field: str, allow_zero: bool = False) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < int(not allow_zero):
        raise ValueError(
            f"{field} must be a nonnegative integer"
            if allow_zero
            else f"{field} must be a positive integer"
        )
    return value


def _diff_hunks(text: str, raw: object, limits: CodingContextLimits) -> tuple[DiffHunk, ...]:
    entries = _sequence(raw, field="excerpts.hunks", maximum=limits.excerpt_lines, nonempty=True)
    hunks: list[DiffHunk] = []
    for entry in entries:
        item = _mapping(
            entry,
            field="excerpts.hunks",
            required={"old_start", "old_count", "new_start", "new_count"},
        )
        hunks.append(
            DiffHunk(
                old_start=_positive(item["old_start"], field="old_start", allow_zero=True),
                old_count=_positive(item["old_count"], field="old_count", allow_zero=True),
                new_start=_positive(item["new_start"], field="new_start", allow_zero=True),
                new_count=_positive(item["new_count"], field="new_count", allow_zero=True),
            )
        )
    parsed: list[DiffHunk] = []
    old_lines = new_lines = 0
    active: DiffHunk | None = None
    for line in text.splitlines():
        if line.startswith("@@"):
            if active is not None and (old_lines, new_lines) != (
                active.old_count,
                active.new_count,
            ):
                raise ValueError("diff hunk body disagrees with ranges")
            match = _HUNK.fullmatch(line)
            if match is None:
                raise ValueError("diff hunk header is malformed")
            active = DiffHunk(
                old_start=int(match[1]),
                old_count=int(match[2] or 1),
                new_start=int(match[3]),
                new_count=int(match[4] or 1),
            )
            parsed.append(active)
            old_lines = new_lines = 0
            continue
        if active is None or line.startswith("\\"):
            continue
        if line.startswith(" "):
            old_lines += 1
            new_lines += 1
        elif line.startswith("-"):
            old_lines += 1
        elif line.startswith("+"):
            new_lines += 1
        else:
            raise ValueError("diff hunk body contains an invalid line")
    if active is not None and (old_lines, new_lines) != (active.old_count, active.new_count):
        raise ValueError("diff hunk body disagrees with ranges")
    if tuple(parsed) != tuple(hunks):
        raise ValueError("diff hunk ranges disagree with text")
    return tuple(hunks)


def _excerpt(value: object, limits: CodingContextLimits) -> ContextExcerpt:
    item = _mapping(
        value,
        field="excerpts",
        required={"kind", "path", "text"},
        optional={
            "commit",
            "start_line",
            "end_line",
            "language",
            "base_commit",
            "head_commit",
            "hunks",
        },
    )
    kind = item["kind"]
    if not isinstance(kind, str) or kind not in {"source", "configuration", "diff"}:
        raise ValueError("excerpts.kind is unsupported")
    path = _path(item["path"], field="excerpts.path", limits=limits)
    text = _text(item["text"], field="excerpts.text", maximum=limits.excerpt_bytes)
    lines = len(text.splitlines())
    if lines > limits.excerpt_lines:
        raise ValueError("excerpts.text exceeds line limit")
    if kind == "diff":
        if set(item) != {"kind", "path", "text", "base_commit", "head_commit", "hunks"}:
            raise ValueError("diff excerpt requires base/head commit and hunk provenance")
        return ContextExcerpt(
            kind=kind,
            path=path,
            text=text,
            base_commit=_commit(item["base_commit"], field="base_commit"),
            head_commit=_commit(item["head_commit"], field="head_commit"),
            hunks=_diff_hunks(text, item["hunks"], limits),
        )
    if set(item) not in (
        {"kind", "path", "text", "commit", "start_line", "end_line"},
        {"kind", "path", "text", "commit", "start_line", "end_line", "language"},
    ):
        raise ValueError("source/configuration excerpt requires commit and line provenance")
    start = _positive(item["start_line"], field="start_line")
    end = _positive(item["end_line"], field="end_line")
    if end < start or end - start + 1 > limits.excerpt_lines or lines != end - start + 1:
        raise ValueError("excerpts line provenance is invalid")
    language = item.get("language")
    return ContextExcerpt(
        kind=kind,
        path=path,
        text=text,
        commit=_commit(item["commit"], field="commit"),
        start_line=start,
        end_line=end,
        language=_text(language, field="language", maximum=limits.identifier_bytes)
        if language is not None
        else None,
    )


def validate_coding_context(package: object) -> CodingContext:
    """Reject malformed or unsafe caller context without reading any source path."""

    limits = CodingContextLimits()
    item = _mapping(
        package,
        field="package",
        required={"schema_version", "objective", "session_ids"},
        optional={"build", "changed_files", "excerpts", "symbols", "constraints"},
    )
    if type(item["schema_version"]) is not int or item["schema_version"] != 1:
        raise ValueError("unsupported Coding Agent context schema_version")
    objective = _text(item["objective"], field="objective", maximum=limits.objective_bytes)
    ids = tuple(
        _text(value, field="session_ids", maximum=limits.identifier_bytes)
        for value in _sequence(
            item["session_ids"], field="session_ids", maximum=limits.session_ids, nonempty=True
        )
    )
    if len(set(ids)) != len(ids) or any(
        "/" in value
        or "\\" in value
        or value in {".", ".."}
        or any(char.isspace() for char in value)
        for value in ids
    ):
        raise ValueError("session_ids must be distinct path-safe names")
    build_raw = item.get("build")
    build = None
    if "build" in item:
        fields = _mapping(
            build_raw, field="build", required={"commit", "build_id", "board", "configuration"}
        )
        build = BuildContext(
            commit=_commit(fields["commit"], field="build.commit"),
            build_id=_text(
                fields["build_id"], field="build.build_id", maximum=limits.identifier_bytes
            ),
            board=_text(fields["board"], field="build.board", maximum=limits.identifier_bytes),
            configuration=_text(
                fields["configuration"],
                field="build.configuration",
                maximum=limits.identifier_bytes,
            ),
        )
    changed: list[ChangedFile] = []
    for raw in _sequence(
        item.get("changed_files", []), field="changed_files", maximum=limits.changed_files
    ):
        fields = _mapping(raw, field="changed_files", required={"path", "summary"})
        changed.append(
            ChangedFile(
                path=_path(fields["path"], field="changed_files.path", limits=limits),
                summary=_text(
                    fields["summary"],
                    field="changed_files.summary",
                    maximum=limits.auxiliary_text_bytes,
                ),
            )
        )
    excerpts = tuple(
        _excerpt(raw, limits)
        for raw in _sequence(item.get("excerpts", []), field="excerpts", maximum=limits.excerpts)
    )
    total_bytes = sum(len(excerpt.text.encode("utf-8")) for excerpt in excerpts)
    if total_bytes > limits.total_excerpt_bytes:
        raise ValueError("excerpts exceed total text byte limit")
    symbols = tuple(
        _text(raw, field="symbols", maximum=limits.identifier_bytes)
        for raw in _sequence(item.get("symbols", []), field="symbols", maximum=limits.symbols)
    )
    constraints = tuple(
        _text(raw, field="constraints", maximum=limits.auxiliary_text_bytes)
        for raw in _sequence(
            item.get("constraints", []), field="constraints", maximum=limits.constraints
        )
    )
    paths = tuple(
        dict.fromkeys([*(entry.path for entry in changed), *(entry.path for entry in excerpts)])
    )
    return CodingContext(
        schema_version=1,
        objective=objective,
        session_ids=ids,
        build=build,
        changed_files=tuple(changed),
        excerpts=excerpts,
        symbols=symbols,
        constraints=constraints,
        source_paths=paths,
        excerpt_text_bytes=total_bytes,
        limits=limits,
    )
