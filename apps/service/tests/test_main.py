from __future__ import annotations

from typing import Any

from dutchmate_service import main


def test_service_main_passes_host_and_port_to_uvicorn(monkeypatch: Any) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(app: object, *, host: str, port: int) -> None:
        calls.append({"app": app, "host": host, "port": port})

    monkeypatch.setattr(main.uvicorn, "run", fake_run)

    main.main(["--host", "127.0.0.1", "--port", "2041"])

    assert len(calls) == 1
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 2041
