"""Crash-recoverable transactions for multi-file session evidence units."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Literal

import dutchmate_core.session_store.persistence as _persistence
from dutchmate_core.session_store.models import SessionPaths, SessionPersistenceError

_MARKER_NAME = ".evidence-transaction.json"
_METADATA_BACKUP_NAME = ".evidence-transaction.metadata.before"
_PATTERNS_BACKUP_NAME = ".evidence-transaction.patterns.before"
_APPEND_FILES = frozenset(
    {
        "uart_raw.log",
        "uart_events.jsonl",
        "hardware_events.jsonl",
    }
)
_TransactionState = Literal["prepared", "evidence_written", "committed"]
TransactionRecovery = Literal["committed", "rolled_back"]


@dataclass(frozen=True, slots=True)
class _TransactionFiles:
    marker: Path
    metadata_backup: Path
    patterns_backup: Path


@dataclass(frozen=True, slots=True)
class _TransactionMarker:
    state: _TransactionState
    append_offsets: dict[str, int]
    replace_detected_patterns: bool
    metadata_before_sha256: str
    patterns_before_sha256: str | None
    expected_metadata_sha256: str | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "state": self.state,
            "append_offsets": self.append_offsets,
            "replace_detected_patterns": self.replace_detected_patterns,
            "metadata_before_sha256": self.metadata_before_sha256,
            "patterns_before_sha256": self.patterns_before_sha256,
            "expected_metadata_sha256": self.expected_metadata_sha256,
        }


class EvidenceTransaction:
    """One prepared cross-file evidence mutation."""

    def __init__(
        self,
        *,
        paths: SessionPaths,
        files: _TransactionFiles,
        marker: _TransactionMarker,
    ) -> None:
        self._paths = paths
        self._files = files
        self._marker = marker

    def prepare_metadata(self, serialized_metadata: bytes) -> None:
        """Durably record the metadata digest before replacing metadata itself."""

        self._marker = replace(
            self._marker,
            state="evidence_written",
            expected_metadata_sha256=_digest_bytes(serialized_metadata),
        )
        _persistence.write_json(self._files.marker, self._marker.as_json())

    def commit(self) -> None:
        """Mark the durable unit committed and remove recoverable bookkeeping."""

        if self._marker.state != "evidence_written":
            raise RuntimeError("evidence transaction metadata was not prepared")
        committed = replace(self._marker, state="committed")
        try:
            _persistence.write_json(self._files.marker, committed.as_json())
        except SessionPersistenceError as marker_error:
            try:
                _cleanup(self._paths, self._files)
            except SessionPersistenceError as cleanup_error:
                raise _unsafe_error(
                    "commit bookkeeping",
                    self._files.marker,
                    str(cleanup_error),
                ) from marker_error
            return
        with suppress(SessionPersistenceError):
            _cleanup(self._paths, self._files)

    def rollback(self) -> None:
        """Restore every pre-transaction file state and remove bookkeeping."""

        try:
            _rollback(self._paths, self._files, self._marker)
        except (SessionPersistenceError, ValueError) as exc:
            raise _unsafe_error("rollback", self._files.marker, str(exc)) from exc


@contextmanager
def evidence_transaction(
    paths: SessionPaths,
    *,
    append_paths: Sequence[Path],
    replace_detected_patterns: bool = False,
) -> Iterator[EvidenceTransaction]:
    """Prepare, commit, or synchronously roll back one evidence mutation."""

    transaction = begin_evidence_transaction(
        paths,
        append_paths=append_paths,
        replace_detected_patterns=replace_detected_patterns,
    )
    try:
        yield transaction
    except BaseException as exc:
        try:
            transaction.rollback()
        except SessionPersistenceError as rollback_error:
            raise rollback_error from exc
        raise
    else:
        transaction.commit()


def recover_evidence_transaction(paths: SessionPaths) -> TransactionRecovery | None:
    """Resolve one interrupted transaction before lifecycle recovery proceeds."""

    files = _transaction_files(paths)
    if not files.marker.exists():
        _cleanup_orphan_backups(paths, files)
        return None
    try:
        marker = _marker_from_json(_persistence.read_json_object(files.marker))
        if marker.state == "committed":
            _cleanup(paths, files)
            return "committed"
        if marker.state == "evidence_written" and _metadata_matches_expected(
            paths,
            marker,
        ):
            _cleanup(paths, files)
            return "committed"
        _rollback(paths, files, marker)
        return "rolled_back"
    except (SessionPersistenceError, ValueError) as exc:
        raise _unsafe_error("recover transaction", files.marker, str(exc)) from exc


def begin_evidence_transaction(
    paths: SessionPaths,
    *,
    append_paths: Sequence[Path],
    replace_detected_patterns: bool = False,
) -> EvidenceTransaction:
    recover_evidence_transaction(paths)
    files = _transaction_files(paths)
    append_offsets = _append_offsets(paths, append_paths)
    marker = _TransactionMarker(
        state="prepared",
        append_offsets=append_offsets,
        replace_detected_patterns=replace_detected_patterns,
        metadata_before_sha256=_digest_file(paths.metadata),
        patterns_before_sha256=(
            _digest_file(paths.detected_patterns) if replace_detected_patterns else None
        ),
    )
    try:
        os.link(paths.metadata, files.metadata_backup, follow_symlinks=False)
        if replace_detected_patterns:
            os.link(
                paths.detected_patterns,
                files.patterns_backup,
                follow_symlinks=False,
            )
        _sync_directory(paths.root)
        _persistence.write_json(files.marker, marker.as_json())
    except (OSError, SessionPersistenceError) as exc:
        try:
            _cleanup(paths, files)
        except SessionPersistenceError as cleanup_error:
            raise _unsafe_error(
                "prepare transaction",
                files.marker,
                str(cleanup_error),
            ) from exc
        if isinstance(exc, SessionPersistenceError):
            raise
        raise _error("prepare transaction", files.marker, exc) from exc
    return EvidenceTransaction(paths=paths, files=files, marker=marker)


def _rollback(
    paths: SessionPaths,
    files: _TransactionFiles,
    marker: _TransactionMarker,
) -> None:
    for name, offset in marker.append_offsets.items():
        _truncate_to(paths.root / name, offset)
    if marker.replace_detected_patterns:
        if marker.patterns_before_sha256 is None:
            raise ValueError("transaction patterns preimage digest is missing")
        _restore_backup(
            target=paths.detected_patterns,
            backup=files.patterns_backup,
            expected_digest=marker.patterns_before_sha256,
        )
    _restore_backup(
        target=paths.metadata,
        backup=files.metadata_backup,
        expected_digest=marker.metadata_before_sha256,
    )
    _sync_directory(paths.root)
    _cleanup(paths, files)


def _cleanup(paths: SessionPaths, files: _TransactionFiles) -> None:
    try:
        files.metadata_backup.unlink(missing_ok=True)
        files.patterns_backup.unlink(missing_ok=True)
        files.marker.unlink(missing_ok=True)
        _sync_directory(paths.root)
    except OSError as exc:
        raise _error("clean transaction", files.marker, exc) from exc


def _cleanup_orphan_backups(paths: SessionPaths, files: _TransactionFiles) -> None:
    if not files.metadata_backup.exists() and not files.patterns_backup.exists():
        return
    try:
        _restore_or_remove_orphan(
            target=paths.metadata,
            backup=files.metadata_backup,
        )
        _restore_or_remove_orphan(
            target=paths.detected_patterns,
            backup=files.patterns_backup,
        )
        _sync_directory(paths.root)
    except OSError as exc:
        raise _error("clean orphan transaction", files.marker, exc) from exc


def _restore_or_remove_orphan(*, target: Path, backup: Path) -> None:
    if not backup.exists():
        return
    if target.exists():
        backup.unlink()
    else:
        os.replace(backup, target)


def _restore_backup(*, target: Path, backup: Path, expected_digest: str) -> None:
    try:
        if backup.exists():
            os.replace(backup, target)
            return
    except OSError as exc:
        raise _error("restore transaction preimage", target, exc) from exc
    if _digest_file(target) != expected_digest:
        raise ValueError(f"transaction preimage for {target.name} is unavailable")


def _truncate_to(path: Path, offset: int) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY)
        if os.fstat(descriptor).st_size < offset:
            raise OSError("transaction append target is shorter than its saved offset")
        os.ftruncate(descriptor, offset)
        os.fsync(descriptor)
    except OSError as exc:
        raise _error("restore append offset", path, exc) from exc
    finally:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)


def _append_offsets(paths: SessionPaths, append_paths: Sequence[Path]) -> dict[str, int]:
    offsets: dict[str, int] = {}
    for path in append_paths:
        if path.parent != paths.root or path.name not in _APPEND_FILES:
            raise ValueError("transaction append target must be a session evidence file")
        if path.name in offsets:
            continue
        try:
            offsets[path.name] = path.stat().st_size
        except OSError as exc:
            raise _error("read append offset", path, exc) from exc
    return offsets


def _marker_from_json(value: dict[str, object]) -> _TransactionMarker:
    schema_version = value.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != 1:
        raise ValueError("unsupported evidence transaction schema")
    state = value.get("state")
    if state not in {"prepared", "evidence_written", "committed"}:
        raise ValueError("evidence transaction state is invalid")
    raw_offsets = value.get("append_offsets")
    if not isinstance(raw_offsets, dict):
        raise ValueError("evidence transaction append_offsets must be an object")
    append_offsets: dict[str, int] = {}
    for name, offset in raw_offsets.items():
        if (
            not isinstance(name, str)
            or name not in _APPEND_FILES
            or isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
        ):
            raise ValueError("evidence transaction append offset is invalid")
        append_offsets[name] = offset
    replace_patterns = value.get("replace_detected_patterns")
    if not isinstance(replace_patterns, bool):
        raise ValueError("evidence transaction pattern flag must be boolean")
    metadata_before = _required_digest(value, "metadata_before_sha256")
    patterns_before = _optional_digest(value, "patterns_before_sha256")
    expected_metadata = _optional_digest(value, "expected_metadata_sha256")
    if replace_patterns != (patterns_before is not None):
        raise ValueError("evidence transaction pattern preimage is inconsistent")
    if state == "prepared" and expected_metadata is not None:
        raise ValueError("prepared evidence transaction has an expected metadata digest")
    if state != "prepared" and expected_metadata is None:
        raise ValueError("advanced evidence transaction lacks an expected metadata digest")
    return _TransactionMarker(
        state=state,
        append_offsets=append_offsets,
        replace_detected_patterns=replace_patterns,
        metadata_before_sha256=metadata_before,
        patterns_before_sha256=patterns_before,
        expected_metadata_sha256=expected_metadata,
    )


def _required_digest(value: dict[str, object], key: str) -> str:
    digest = value.get(key)
    if not isinstance(digest, str) or not _valid_digest(digest):
        raise ValueError(f"evidence transaction {key} is invalid")
    return digest


def _optional_digest(value: dict[str, object], key: str) -> str | None:
    digest = value.get(key)
    if digest is None:
        return None
    if not isinstance(digest, str) or not _valid_digest(digest):
        raise ValueError(f"evidence transaction {key} is invalid")
    return digest


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _metadata_matches_expected(paths: SessionPaths, marker: _TransactionMarker) -> bool:
    expected = marker.expected_metadata_sha256
    if expected is None:
        return False
    return _digest_file(paths.metadata) == expected


def _digest_file(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as file:
            while chunk := file.read(65536):
                digest.update(chunk)
    except OSError as exc:
        raise _error("digest", path, exc) from exc
    return digest.hexdigest()


def _digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sync_directory(path: Path) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as exc:
        raise _error("sync transaction directory", path, exc) from exc
    finally:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)


def _transaction_files(paths: SessionPaths) -> _TransactionFiles:
    return _TransactionFiles(
        marker=paths.root / _MARKER_NAME,
        metadata_backup=paths.root / _METADATA_BACKUP_NAME,
        patterns_backup=paths.root / _PATTERNS_BACKUP_NAME,
    )


def _error(operation: str, path: Path, exc: OSError) -> SessionPersistenceError:
    detail = exc.strerror or str(exc) or type(exc).__name__
    return SessionPersistenceError(operation=operation, path=path, detail=detail)


def _unsafe_error(operation: str, path: Path, detail: str) -> SessionPersistenceError:
    return SessionPersistenceError(
        operation=operation,
        path=path,
        detail=detail,
        terminalization_safe=False,
    )
