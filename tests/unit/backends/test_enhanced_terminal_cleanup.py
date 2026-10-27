"""Known terminal read errors and actual serial closure are separate facts."""

import asyncio

import pytest
from enhanced_serial_fixture import PipeSerial
from serial import SerialException

from dutchmate_core.backends import BackendDisconnectedError
from dutchmate_core.backends.enhanced_serial_io import open_async_enhanced_serial_adapter


@pytest.mark.parametrize("close_mode", ["closed", "failed", "incomplete", "unknown"])
async def test_read_failure_preserves_primary_and_only_confirmed_close_succeeds(close_mode):
    resource = PipeSerial(close_mode=close_mode)
    adapter = await open_async_enhanced_serial_adapter(
        port="/test/pipe", segment_id=0, open_connection=resource.open_connection
    )
    try:
        await adapter.receive_event(1)  # Drain initial timestamp/status.
        resource.disconnect()
        with pytest.raises(BackendDisconnectedError) as observed:
            await adapter.receive_event(1)
        assert observed.value.__cause__ is resource.read_error
        # The installed StreamReaderProtocol reuses this precise object in its
        # close waiter. This is a property of our concrete I/O boundary.
        assert resource.protocol._closed.exception() is resource.read_error
        if close_mode == "closed":
            await asyncio.gather(adapter.close(), adapter.close())
            assert resource.is_open is False
            assert resource.transport.get_extra_info("serial") is None
            assert not resource.callback_errors
        else:
            for _ in range(2):
                with pytest.raises(SerialException) as cleanup:
                    await adapter.close()
                assert cleanup.value is resource.read_error
            if close_mode == "failed":
                assert resource.callback_errors[0]["exception"] is resource.close_error
        assert resource.close_calls == 1
        with pytest.raises(BackendDisconnectedError) as retained:
            await adapter.receive_event(0)
        assert retained.value is observed.value
        assert retained.value.__cause__ is resource.read_error
    finally:
        resource.dispose()


async def test_distinct_wait_closed_error_is_not_hidden_even_after_port_closes(monkeypatch):
    resource = PipeSerial()
    adapter = await open_async_enhanced_serial_adapter(
        port="/test/pipe", segment_id=0, open_connection=resource.open_connection
    )
    try:
        await adapter.receive_event(1)
        connection_lost = resource.protocol.connection_lost
        secondary = SerialException(str(resource.read_error))

        def lose_connection(exc):
            resource.protocol._closed.set_exception(secondary)
            connection_lost(exc)

        monkeypatch.setattr(resource.protocol, "connection_lost", lose_connection)
        resource.disconnect()
        with pytest.raises(BackendDisconnectedError) as observed:
            await adapter.receive_event(1)
        assert observed.value.__cause__ is resource.read_error
        with pytest.raises(SerialException) as cleanup:
            await adapter.close()
        assert cleanup.value is secondary
        with pytest.raises(BackendDisconnectedError) as retained:
            await adapter.receive_event(0)
        assert retained.value is observed.value
        assert retained.value.__cause__ is resource.read_error
        assert resource.is_open is False
        assert resource.close_calls == 1
    finally:
        resource.dispose()


@pytest.mark.parametrize("inspection", ["still_owned", "inspection_failed"])
async def test_closed_port_without_confirmed_transport_release_is_not_accepted(
    monkeypatch, inspection
):
    resource = PipeSerial()
    adapter = await open_async_enhanced_serial_adapter(
        port="/test/pipe", segment_id=0, open_connection=resource.open_connection
    )

    def inspect_transport(*args):
        if inspection == "inspection_failed":
            raise OSError("cannot inspect transport")
        return resource

    monkeypatch.setattr(resource.transport, "get_extra_info", inspect_transport)
    try:
        await adapter.receive_event(1)
        resource.disconnect()
        with pytest.raises(BackendDisconnectedError) as observed:
            await adapter.receive_event(1)
        with pytest.raises(SerialException) as cleanup:
            await adapter.close()
        assert cleanup.value is resource.read_error
        assert observed.value.__cause__ is resource.read_error
        assert resource.is_open is False
        assert resource.close_calls == 1
    finally:
        resource.dispose()


@pytest.mark.parametrize("close_mode", ["failed", "incomplete", "unknown"])
async def test_normal_waiter_success_does_not_override_missing_physical_close(close_mode):
    resource = PipeSerial(close_mode=close_mode)
    adapter = await open_async_enhanced_serial_adapter(
        port="/test/pipe", segment_id=0, open_connection=resource.open_connection
    )
    try:
        for _ in range(2):
            with pytest.raises(RuntimeError, match="closure is unconfirmed"):
                await adapter.close()
        assert resource.close_calls == 1
    finally:
        resource.dispose()
