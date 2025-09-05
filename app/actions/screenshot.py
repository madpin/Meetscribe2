"""
Action: Take a full-screen screenshot.

This action captures the entire screen, saves it to a file in the configured
screenshots folder, and copies the file path to the clipboard.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.context import AppContext


def full(ctx: "AppContext") -> str:
    """
    Takes a full-screen screenshot.

    Args:
        ctx: The application's context containing configuration and logging.

    Returns:
        str: Success message with file path.
    """
    ctx.logger.info("Executing action: screenshot.full")

    import pyautogui
    import pyperclip

    # Use the new utility function for directory creation
    from ..core.utils import ensure_directory_exists, get_timestamp_filename

    screenshots_folder = ctx.config.paths.get_screenshots_path()
    ensure_directory_exists(screenshots_folder, ctx.logger)

    file_name = get_timestamp_filename("screenshot", "png")
    file_path = screenshots_folder / file_name

    # Take the actual screenshot
    ctx.logger.info("Taking screenshot...")
    screenshot = pyautogui.screenshot()
    screenshot.save(file_path)
    ctx.logger.info(f"Screenshot saved to {file_path}")

    # Copy the file path to clipboard
    pyperclip.copy(str(file_path))
    ctx.logger.info(f"File path copied to clipboard: {file_path}")

    return f"Screenshot saved to {file_path}"
