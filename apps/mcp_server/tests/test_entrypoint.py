from __future__ import annotations

import subprocess
import sys

import pytest

import dutchmate_mcp_server.main as main_module
from dutchmate_mcp_server.service_client import DEFAULT_SERVICE_URL


def test_main_runs_stdio_with_default_service_and_log_level(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.delenv("DUTCHMATE_SERVICE_URL", raising=False)
    monkeypatch.setattr(
        main_module,
        "run_stdio",
        lambda *, service_url, log_level: calls.append((service_url, log_level)),
    )

    main_module.main([])

    assert calls == [(DEFAULT_SERVICE_URL, "INFO")]
    assert capsys.readouterr() == ("", "")


def test_main_uses_service_environment_and_normalizes_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setenv("DUTCHMATE_SERVICE_URL", "http://127.0.0.1:3040")
    monkeypatch.setattr(
        main_module,
        "run_stdio",
        lambda *, service_url, log_level: calls.append((service_url, log_level)),
    )

    main_module.main(["--log-level", "debug"])

    assert calls == [("http://127.0.0.1:3040", "DEBUG")]


def test_main_explicit_service_url_overrides_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setenv("DUTCHMATE_SERVICE_URL", "http://127.0.0.1:3040")
    monkeypatch.setattr(
        main_module,
        "run_stdio",
        lambda *, service_url, log_level: calls.append((service_url, log_level)),
    )

    main_module.main(["--service-url", "http://127.0.0.1:4040", "--log-level", "warning"])

    assert calls == [("http://127.0.0.1:4040", "WARNING")]


def test_real_stdio_entrypoint_keeps_stdout_protocol_clean_on_eof() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from dutchmate_mcp_server.main import main; "
                "main(['--log-level', 'debug'])"
            ),
        ],
        input="",
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
