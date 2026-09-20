from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from test_report_boundary import _request, _response

from dutchmate_debug_agent.ollama_adapter import OllamaAdapter
from dutchmate_debug_agent.provider_boundary import (
    ProviderSelection,
    prepare_analysis,
    submit_approved_analysis,
)


@pytest.mark.asyncio
async def test_ollama_local_chat_receives_exact_prepared_request_and_returns_valid_report(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path)
    captured: list[httpx.Request] = []

    def respond(http_request: httpx.Request) -> httpx.Response:
        captured.append(http_request)
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(_response(request.session_ids[0])),
                },
                "done": True,
            },
        )

    adapter = OllamaAdapter(
        base_url="http://127.0.0.1:11434",
        transport=httpx.MockTransport(respond),
    )
    prepared = prepare_analysis(
        request,
        ProviderSelection(provider_id="ollama", model_id="fixture"),
        {"ollama": adapter},
    )
    report = await submit_approved_analysis(
        prepared,
        approved_digest=prepared.manifest.manifest_digest,
    )

    assert report.metadata.provider_id == "ollama"
    assert report.metadata.remote is False
    assert len(captured) == 1
    sent = captured[0]
    assert sent.method == "POST"
    assert sent.url.path == "/api/chat"
    body = json.loads(sent.content)
    assert body["model"] == "fixture"
    assert body["stream"] is False
    assert body["format"]["type"] == "object"
    assert body["messages"][1]["content"] == prepared.payload.decode("utf-8")


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.com",
        "http://example.com:11434",
        "http://127.0.0.1:11434/other",
        "http://user:secret@127.0.0.1:11434",
    ],
)
def test_ollama_adapter_rejects_nonlocal_or_credential_bearing_urls(url: str) -> None:
    with pytest.raises(ValueError, match="local"):
        OllamaAdapter(base_url=url)


@pytest.mark.asyncio
async def test_ollama_does_not_follow_redirect_or_accept_malformed_response() -> None:
    redirect = OllamaAdapter(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(302, headers={"Location": "https://example.com/collect"})
        )
    )
    with pytest.raises(ValueError):
        await redirect.analyze(b'{"schema_version":1}', model_id="fixture")

    malformed = OllamaAdapter(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"message": {"content": "not json"}, "done": True})
        )
    )
    with pytest.raises(ValueError):
        await malformed.analyze(b'{"schema_version":1}', model_id="fixture")
