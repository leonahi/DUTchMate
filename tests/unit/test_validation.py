import pytest

from dutchmate_core.validation import (
    GpioIdentifierValidationError,
    UartSendValidationError,
    prepare_uart_send_payload,
    session_evidence_budget_bytes,
    validate_capture_duration,
    validate_gpio_configuration,
    validate_gpio_identifier,
    validate_gpio_mode_configuration,
    validate_session_max_size_mb,
    validate_wait_pattern,
    validate_wait_timeout,
)


@pytest.mark.parametrize(
    ("cmd", "append_newline", "expected"),
    [
        ("", True, b"\n"),
        ("é", True, "é\n".encode()),
        ("go\n", True, b"go\n"),
        ("go\r\n", True, b"go\r\n"),
        ("go\r", True, b"go\r\n"),
        ("go", False, b"go"),
    ],
)
def test_uart_send_payload_applies_exact_text_terminator_rules(
    cmd: str,
    append_newline: bool,
    expected: bytes,
) -> None:
    assert prepare_uart_send_payload(cmd, append_newline=append_newline) == expected


def test_uart_send_payload_accepts_exact_1024_byte_boundary() -> None:
    assert len(prepare_uart_send_payload("x" * 1023)) == 1024
    assert len(prepare_uart_send_payload("x" * 1024, append_newline=False)) == 1024


@pytest.mark.parametrize(
    ("cmd", "append_newline", "actual_bytes"),
    [
        ("", False, 0),
        ("x" * 1024, True, 1025),
        ("é" * 512, True, 1025),
    ],
)
def test_uart_send_payload_rejects_empty_or_oversized_final_bytes(
    cmd: str,
    append_newline: bool,
    actual_bytes: int,
) -> None:
    with pytest.raises(UartSendValidationError) as raised:
        prepare_uart_send_payload(cmd, append_newline=append_newline)

    assert raised.value.actual_bytes == actual_bytes
    assert raised.value.max_bytes == 1024


@pytest.mark.parametrize("duration_s", [1, 0.1, 300])
def test_capture_duration_accepts_phase_one_range(duration_s: int | float) -> None:
    assert validate_capture_duration(duration_s) == float(duration_s)


@pytest.mark.parametrize(
    "duration_s",
    [0, -1, 300.0001, float("inf"), float("-inf"), float("nan"), True, "1"],
)
def test_capture_duration_rejects_values_outside_exact_contract(duration_s: object) -> None:
    with pytest.raises(ValueError, match="positive finite.*300"):
        validate_capture_duration(duration_s)


@pytest.mark.parametrize("pattern", ["x", "x" * 256, "é" * 128, ".*[]?"])
def test_wait_pattern_accepts_exact_bounded_literals(pattern: str) -> None:
    assert validate_wait_pattern(pattern) == pattern


@pytest.mark.parametrize("pattern", ["", "x" * 257, "é" * 129, "bad\r", "bad\n", 1])
def test_wait_pattern_rejects_invalid_literals(pattern: object) -> None:
    with pytest.raises(ValueError):
        validate_wait_pattern(pattern)


@pytest.mark.parametrize("timeout_s", [0.1, 1, 300])
def test_wait_timeout_accepts_phase_one_range(timeout_s: int | float) -> None:
    assert validate_wait_timeout(timeout_s) == float(timeout_s)


@pytest.mark.parametrize(
    "timeout_s",
    [0, -1, 300.1, True, float("inf"), float("nan"), "1"],
)
def test_wait_timeout_rejects_values_outside_contract(timeout_s: object) -> None:
    with pytest.raises(ValueError, match="positive finite.*300"):
        validate_wait_timeout(timeout_s)


@pytest.mark.parametrize("max_size_mb", [1, 10, 50])
def test_session_max_size_accepts_positive_mib_values(max_size_mb: int) -> None:
    assert validate_session_max_size_mb(max_size_mb) == max_size_mb
    assert session_evidence_budget_bytes(max_size_mb) == max_size_mb * 1024 * 1024


@pytest.mark.parametrize("max_size_mb", [0, -1, True, 1.5, "10"])
def test_session_max_size_rejects_non_positive_integers(max_size_mb: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        validate_session_max_size_mb(max_size_mb)


@pytest.mark.parametrize(
    "value",
    ["r", "r" * 64, "é" * 32, "reset role", "Reset"],
)
def test_gpio_identifier_accepts_and_preserves_exact_utf8_value(value: str) -> None:
    assert validate_gpio_identifier(value, field="role") == value


def test_gpio_identifier_counts_utf8_bytes_instead_of_characters() -> None:
    with pytest.raises(GpioIdentifierValidationError) as error:
        validate_gpio_identifier("é" * 33, field="role")

    assert error.value.field == "role"
    assert error.value.reason == "invalid_length"
    assert error.value.actual_bytes == 66
    assert error.value.max_bytes == 64


@pytest.mark.parametrize("value", [" reset", "reset\u00a0", "\u2003reset"])
def test_gpio_identifier_rejects_unicode_edge_whitespace(value: str) -> None:
    with pytest.raises(GpioIdentifierValidationError) as error:
        validate_gpio_identifier(value, field="role")

    assert error.value.reason == "edge_whitespace"


@pytest.mark.parametrize("value", ["re\x00set", "reset\x7f", "re\u0080set"])
def test_gpio_identifier_rejects_unicode_control_characters(value: str) -> None:
    with pytest.raises(GpioIdentifierValidationError) as error:
        validate_gpio_identifier(value, field="role")

    assert error.value.reason == "control_character"


def test_gpio_configuration_preserves_canonically_distinct_identifiers() -> None:
    request = validate_gpio_configuration(
        channel="CTRL2",
        role="Re\u0301set",
        dut_signal="RÉSET_N",
        mode="push_pull",
        active_level="high",
        idle_level="low",
    )

    assert request.role == "Re\u0301set"
    assert request.dut_signal == "RÉSET_N"


@pytest.mark.parametrize(
    ("mode", "active_level", "idle_level", "message"),
    [
        ("open_drain", "high", None, "active_level must be 'low'"),
        ("open_drain", "low", "high", "idle_level must be omitted"),
        ("push_pull", "high", None, "idle_level is required"),
        ("push_pull", "high", "high", "idle_level must be opposite"),
        ("push_pull", "low", "low", "idle_level must be opposite"),
    ],
)
def test_gpio_mode_matrix_rejects_unsafe_combinations(
    mode: str,
    active_level: str,
    idle_level: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_gpio_mode_configuration(
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
