"""Exact public TX transformations, independent of transport availability."""

import pytest

from dutchmate_core import validation


@pytest.mark.parametrize(
    ("ending", "expected"),
    [
        ("none", b"go"),
        ("lf", b"go\n"),
        ("cr", b"go\r"),
        ("crlf", b"go\r\n"),
        ("profile_default", b"go\r\n"),
    ],
)
def test_text_transformation_is_explicit(ending: str, expected: bytes) -> None:
    payload = validation.prepare_uart_tx_payload(
        text="go", line_ending=ending, profile_default="crlf"
    )
    assert payload.data == expected


@pytest.mark.parametrize("size", [1, 1024])
def test_binary_payload_boundary(size: int) -> None:
    from base64 import b64encode

    raw = b"\x00" * size
    assert validation.prepare_uart_tx_payload(data_b64=b64encode(raw).decode()).data == raw


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"text": "go"},
        {"text": "go", "line_ending": "bad"},
        {"text": "go", "line_ending": "none", "data_b64": "eA=="},
        {"data_b64": "!"},
        {"data_b64": ""},
        {"data_b64": "eA==", "line_ending": "lf"},
        {"text": "", "line_ending": "none"},
        {"text": "x" * 1024, "line_ending": "lf"},
    ],
)
def test_invalid_payload_is_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(validation.UartSendValidationError):
        validation.prepare_uart_tx_payload(**kwargs)
