from __future__ import annotations

from typing import Any

from dutchmate_service import main


def test_service_main_passes_host_port_and_session_root_to_uvicorn(monkeypatch: Any) -> None:
    calls: list[dict[str, object]] = []
    session_roots: list[object] = []

    def fake_create_app(*, session_root: object) -> object:
        session_roots.append(session_root)
        return object()

    def fake_run(app: object, *, host: str, port: int) -> None:
        calls.append({"app": app, "host": host, "port": port})

    monkeypatch.setattr(main, "create_app", fake_create_app)
    monkeypatch.setattr(main.uvicorn, "run", fake_run)

    main.main(
        [
            "--host",
            "127.0.0.1",
            "--port",
            "2041",
            "--session-root",
            ".dutchmate/custom-sessions",
        ]
    )

    assert len(calls) == 1
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 2041
    assert [str(path) for path in session_roots] == [".dutchmate/custom-sessions"]
