"""The CLI exposes atomic capabilities and no reset/observe composite."""

from typer.testing import CliRunner

from dutchmate_cli import capture, client, main


def test_boot_test_command_is_not_registered() -> None:
    result = CliRunner().invoke(main.app, ["boot-test"])

    assert result.exit_code == 2
    assert "No such command" in result.output
    assert "boot-test" not in {command.name for command in main.app.registered_commands}


def test_boot_test_client_and_formatter_are_not_public_helpers() -> None:
    assert not hasattr(client, "run_boot_test")
    assert not hasattr(capture, "format_boot_test_result")
