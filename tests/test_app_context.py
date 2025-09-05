"""
Tests for the AppContext class.

This demonstrates how the new AppContext architecture enables better testing
of the core application components.
"""

import pytest
from unittest.mock import patch, Mock
from app.core.context import AppContext
from app.core.models import AppConfig


class TestAppContext:
    """Test cases for AppContext functionality."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create a temporary config file for testing."""
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[paths]
screenshots_folder = "~/test_screenshots"
logs_folder = "~/.cache/test/logs"

[viewer]
log_level = "INFO"
color_theme = "default"

[shortcuts]
enabled = true

  [shortcuts.test_action]
  keys = "<ctrl>+t"
  action = "test.action"
  enabled = true
        """)
        return config_path

    def test_app_context_initialization(self, temp_config_file):
        """Test successful AppContext initialization."""
        with patch("app.core.context.AppContext._load_action_registry"):
            ctx = AppContext(temp_config_file)

            assert isinstance(ctx.config, AppConfig)
            assert ctx.logger is not None
            assert isinstance(ctx.action_registry, dict)
            assert ctx.config_path == temp_config_file

    def test_app_context_config_loading(self, temp_config_file):
        """Test configuration loading and parsing."""
        with patch("app.core.context.AppContext._load_action_registry"), patch(
            "app.core.context.load_config"
        ) as mock_load_config:
            # Mock the config loading to avoid local config override
            mock_load_config.return_value = {
                "paths": {
                    "screenshots_folder": "~/test_screenshots",
                    "logs_folder": "~/.cache/test/logs",
                },
                "viewer": {"log_level": "INFO", "color_theme": "default"},
                "shortcuts": {
                    "enabled": True,
                    "test_action": {
                        "keys": "<ctrl>+t",
                        "action": "test.action",
                        "enabled": True,
                    },
                },
            }

            ctx = AppContext(temp_config_file)

            assert ctx.config.paths.screenshots_folder == "~/test_screenshots"
            assert ctx.config.viewer.log_level == "INFO"
            assert ctx.config.shortcuts.enabled is True
            assert "test_action" in ctx.config.shortcuts.shortcuts

    def test_app_context_missing_config_file(self, tmp_path):
        """Test error handling when config file doesn't exist."""
        nonexistent_config = tmp_path / "nonexistent.toml"

        with pytest.raises(SystemExit):  # ConfigurationError causes sys.exit
            AppContext(nonexistent_config)

    def test_get_action_success(self, temp_config_file):
        """Test successful action retrieval."""
        with patch("app.core.context.AppContext._load_action_registry"):
            ctx = AppContext(temp_config_file)

            # Mock an action in the registry
            mock_action = Mock(return_value="test result")
            ctx.action_registry = {"test.action": mock_action}

            action = ctx.get_action("test.action")
            assert action == mock_action

    def test_get_action_not_found(self, temp_config_file):
        """Test action retrieval when action doesn't exist."""
        with patch("app.core.context.AppContext._load_action_registry"):
            ctx = AppContext(temp_config_file)
            ctx.action_registry = {}

            action = ctx.get_action("nonexistent.action")
            assert action is None

    def test_execute_action_success(self, temp_config_file):
        """Test successful action execution."""
        with patch("app.core.context.AppContext._load_action_registry"), patch(
            "app.core.context.setup_logging"
        ) as mock_setup_logging:
            mock_logger = Mock()
            mock_setup_logging.return_value = mock_logger

            ctx = AppContext(temp_config_file)
            ctx.logger = mock_logger  # Override the real logger

            # Mock an action
            mock_action = Mock(return_value="success result")
            ctx.action_registry = {"test.action": mock_action}

            result = ctx.execute_action("test.action")

            assert result == "success result"
            mock_action.assert_called_once_with(ctx)
            mock_logger.info.assert_any_call("Executing action: test.action")

    def test_execute_action_not_found(self, temp_config_file):
        """Test action execution when action doesn't exist."""
        with patch("app.core.context.AppContext._load_action_registry"):
            ctx = AppContext(temp_config_file)
            ctx.action_registry = {}

            with pytest.raises(
                ValueError, match="Action 'nonexistent.action' not found"
            ):
                ctx.execute_action("nonexistent.action")

    def test_execute_action_runtime_error(self, temp_config_file):
        """Test action execution when action raises an exception."""
        with patch("app.core.context.AppContext._load_action_registry"), patch(
            "app.core.context.setup_logging"
        ) as mock_setup_logging:
            mock_logger = Mock()
            mock_setup_logging.return_value = mock_logger

            ctx = AppContext(temp_config_file)
            ctx.logger = mock_logger  # Override the real logger

            # Mock an action that raises an exception
            mock_action = Mock(side_effect=Exception("Action failed"))
            ctx.action_registry = {"test.action": mock_action}

            with pytest.raises(Exception, match="Action failed"):
                ctx.execute_action("test.action")

            # Verify error was logged
            mock_logger.error.assert_any_call(
                "Action 'test.action' failed: Action failed"
            )

    def test_registry_centralization(self, temp_config_file):
        """Test that action registry is loaded once during initialization."""
        with patch("app.core.context.AppContext._load_action_registry") as mock_load:
            ctx = AppContext(temp_config_file)

            # Registry should be loaded during __init__
            mock_load.assert_called_once()

            # Multiple calls to get_action should use the same registry
            ctx.action_registry = {"cached.action": Mock()}

            action1 = ctx.get_action("cached.action")
            action2 = ctx.get_action("cached.action")

            assert action1 is action2  # Same object from cache
