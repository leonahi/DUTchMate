"""Host-facing preview and digest-approved Debug Agent analysis."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

from dutchmate_core.session_store.models import SessionQueryError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_debug_agent.analysis_request import build_analysis_request
from dutchmate_debug_agent.ollama_adapter import OllamaAdapter
from dutchmate_debug_agent.provider_boundary import (
    AnalysisManifest,
    AnalysisUnavailable,
    ProviderSelection,
    prepare_analysis,
    submit_approved_analysis,
)
from dutchmate_debug_agent.report_schema import DebugReport

_CONTEXT_FILE_BYTES = 2 * 1024 * 1024


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dutchmate-debug")
    actions = parser.add_subparsers(dest="action", required=True)
    for action in ("preview", "analyze"):
        command = actions.add_parser(action)
        command.add_argument("--session-root", type=Path, default=Path(".dutchmate/sessions"))
        command.add_argument("--session-id", action="append", required=True)
        command.add_argument("--context-file", type=Path)
        command.add_argument("--provider", choices=("ollama",), default="disabled")
        command.add_argument("--model")
        command.add_argument("--timeout", type=float, default=60.0)
        if action == "analyze":
            command.add_argument("--approved-digest", required=True)
    return parser


def _context(path: Path | None) -> object | None:
    if path is None:
        return None
    with path.open("rb") as source:
        raw = source.read(_CONTEXT_FILE_BYTES + 1)
    if len(raw) > _CONTEXT_FILE_BYTES:
        raise ValueError("Coding Agent context file exceeds byte limit")
    parsed: object = json.loads(raw)
    return parsed


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request = build_analysis_request(
            SessionStore(root=args.session_root), args.session_id, _context(args.context_file)
        )
        adapters = {"ollama": OllamaAdapter()} if args.provider == "ollama" else {}
        prepared = prepare_analysis(
            request,
            ProviderSelection(
                provider_id=args.provider,
                model_id=args.model,
                timeout_s=args.timeout,
            ),
            adapters,
        )
        output: AnalysisManifest | DebugReport = (
            prepared.manifest
            if args.action == "preview"
            else asyncio.run(
                submit_approved_analysis(prepared, approved_digest=args.approved_digest)
            )
        )
    except (AnalysisUnavailable, SessionQueryError, ValueError, OSError) as exc:
        print(f"dutchmate-debug: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(output), sort_keys=True))
    return 0
