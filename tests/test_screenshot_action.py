"""
Simple test for the screenshot action to demonstrate improved testability.
"""

import sys
from unittest.mock import Mock, patch, MagicMock

from app.actions.screenshot import full
from app.core.models import AppConfig, PathsConfig
from app.core.context import AppContext

# Mock pyautogui and pyperclip modules before any imports to handle headless CI
sys.modules["pyautogui"] = MagicMock()
sys.modules["pyperclip"] = MagicMock()


def test_screenshot_action_with_mock_context():
    """Test that screenshot action works with mocked AppContext."""
    # Create mock context
    mock_config = AppConfig(paths=PathsConfig(screenshots_folder="~/test"))
    mock_logger = Mock()
    mock_ctx = Mock(spec=AppContext)
    mock_ctx.config = mock_config
    mock_ctx.logger = mock_logger

    # Mock external dependencies
    with patch("pyautogui.screenshot") as mock_screenshot, patch(
        "pyperclip.copy"
    ) as mock_copy, patch(
        "app.core.utils.get_timestamp_filename", return_value="test.png"
    ):
        mock_image = Mock()
        mock_screenshot.return_value = mock_image

        # Execute action
        result = full(mock_ctx)

        # Verify it worked
        assert "Screenshot saved to" in result
        mock_screenshot.assert_called_once()
        mock_image.save.assert_called_once()
        mock_copy.assert_called_once()
        mock_logger.info.assert_any_call("Executing action: screenshot.full")
