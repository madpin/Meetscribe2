from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from app.cli import app


def test_cli_help():
    """Test that the CLI shows help correctly"""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "terminal-first app" in result.stdout.lower()
    assert "run" in result.stdout
    assert "action" in result.stdout
    assert "config" in result.stdout


def test_config_show_command():
    """Test the config show subcommand"""
    runner = CliRunner()

    # Mock AppContext
    mock_ctx = MagicMock()
    mock_ctx.config = {"test": "value"}

    with patch("app.cli.get_app_context", return_value=mock_ctx):
        result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "test" in result.stdout
        assert "value" in result.stdout


def test_action_command_with_valid_action():
    """Test running a valid action"""
    runner = CliRunner()

    # Mock AppContext with action registry
    mock_ctx = MagicMock()
    mock_action = MagicMock(return_value="success")
    mock_ctx.action_registry = {"test.action": mock_action}
    mock_ctx.config = {"test": "config"}
    mock_ctx.execute_action.return_value = "success"

    with patch("app.cli.get_app_context", return_value=mock_ctx):
        result = runner.invoke(app, ["action", "test.action"])

        assert result.exit_code == 0
        assert "success" in result.stdout
        mock_ctx.execute_action.assert_called_once_with("test.action")


def test_action_command_with_invalid_action():
    """Test running an invalid action"""
    runner = CliRunner()

    # Mock AppContext with empty action registry
    mock_ctx = MagicMock()
    mock_ctx.action_registry = {}
    mock_ctx.execute_action.side_effect = ValueError(
        "Action 'nonexistent.action' not found"
    )

    with patch("app.cli.get_app_context", return_value=mock_ctx):
        result = runner.invoke(app, ["action", "nonexistent.action"])

        assert result.exit_code == 1
        assert "not found" in result.stdout


def test_action_command_with_exception():
    """Test action command when action raises an exception"""
    runner = CliRunner()

    # Mock AppContext with action that raises exception
    mock_ctx = MagicMock()
    mock_action = MagicMock(side_effect=ValueError("Something went wrong"))
    mock_ctx.action_registry = {"failing.action": mock_action}
    mock_ctx.config = {}
    mock_ctx.execute_action.side_effect = ValueError("Something went wrong")

    with patch("app.cli.get_app_context", return_value=mock_ctx):
        result = runner.invoke(app, ["action", "failing.action"])

        assert result.exit_code == 1
        assert "Something went wrong" in result.stdout


def test_daemon_subcommands():
    """Test daemon subcommands exist and run"""
    runner = CliRunner()

    # Test daemon start
    result = runner.invoke(app, ["daemon", "start"])
    assert result.exit_code == 0
    assert "Starting daemon" in result.stdout

    # Test daemon stop
    result = runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 0
    assert "Stopping daemon" in result.stdout

    # Test daemon status
    result = runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0
    assert "Checking daemon status" in result.stdout


def test_logs_subcommands():
    """Test logs subcommands exist and run"""
    runner = CliRunner()

    # Test logs tail
    result = runner.invoke(app, ["logs", "tail"])
    assert result.exit_code == 0
    assert "Tailing logs" in result.stdout

    # Test logs open
    result = runner.invoke(app, ["logs", "open"])
    assert result.exit_code == 0
    assert "Opening log folder" in result.stdout

    # Test logs clear
    result = runner.invoke(app, ["logs", "clear"])
    assert result.exit_code == 0
    assert "Clearing logs" in result.stdout


def test_update_command():
    """Test update check command"""
    runner = CliRunner()

    result = runner.invoke(app, ["update", "check"])
    assert result.exit_code == 0
    assert "Checking for updates" in result.stdout


def test_config_subcommands():
    """Test config subcommands"""
    runner = CliRunner()

    # Test config edit
    result = runner.invoke(app, ["config", "edit"])
    assert result.exit_code == 0
    assert "Opening configuration file" in result.stdout

    # Test config reset
    result = runner.invoke(app, ["config", "reset"])
    assert result.exit_code == 0
    assert "Resetting configuration" in result.stdout


@patch("app.cli.time.sleep")  # Mock sleep to avoid actual waiting
def test_run_command_normal_mode(mock_sleep):
    """Test run command in normal mode"""
    runner = CliRunner()

    # Make sleep raise KeyboardInterrupt to simulate Ctrl+C
    mock_sleep.side_effect = KeyboardInterrupt()

    # Mock AppContext
    mock_ctx = MagicMock()
    mock_ctx.logger = MagicMock()
    mock_ctx.execute_action.return_value = None

    with patch("app.cli.get_app_context", return_value=mock_ctx), patch(
        "app.shortcuts.manager.ShortcutManager"
    ) as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        result = runner.invoke(app, ["run"])

        assert result.exit_code == 0
        assert "Starting application" in result.stdout
        assert "Shutdown complete" in result.stdout
        mock_manager_class.assert_called_once()
        mock_manager.start.assert_called_once()
        mock_manager.stop.assert_called_once()


@patch("app.cli.time.sleep")  # Mock sleep to avoid actual waiting
def test_run_command_safe_mode(mock_sleep):
    """Test run command in safe mode"""
    runner = CliRunner()

    # Make sleep raise KeyboardInterrupt to simulate Ctrl+C
    mock_sleep.side_effect = KeyboardInterrupt()

    # Mock AppContext
    mock_ctx = MagicMock()
    mock_ctx.logger = MagicMock()
    mock_ctx.execute_action.return_value = None

    with patch("app.cli.get_app_context", return_value=mock_ctx):
        result = runner.invoke(app, ["run", "--safe-mode"])

        assert result.exit_code == 0
        assert "Safe Mode" in result.stdout
        assert "Shortcuts will not be loaded" in result.stdout
