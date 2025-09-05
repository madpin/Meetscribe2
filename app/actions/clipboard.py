"""
Action: Clean clipboard text content.

This action retrieves text from the clipboard, cleans it up by removing
excess whitespace, normalizing line endings, and optionally removing
special characters, then puts the cleaned text back into the clipboard.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.context import AppContext


def clean(ctx: "AppContext") -> str:
    """
    Clean clipboard text content.

    Retrieves text from clipboard, cleans it up, and puts it back.

    Args:
        ctx: The application's context containing configuration and logging.

    Returns:
        str: Success message with cleaning details.
    """
    ctx.logger.info("Executing action: clipboard.clean")

    import pyperclip

    try:
        # Get text from clipboard
        original_text = pyperclip.paste()
        if not original_text:
            ctx.logger.warning("No text found in clipboard")
            return "No text found in clipboard to clean"

        ctx.logger.debug(f"Original text length: {len(original_text)} characters")

        # Clean the text
        cleaned_text = _clean_text(original_text)

        # Calculate cleaning statistics
        original_length = len(original_text)
        cleaned_length = len(cleaned_text)
        reduction = original_length - cleaned_length
        reduction_percent = (
            (reduction / original_length * 100) if original_length > 0 else 0
        )

        # Put cleaned text back to clipboard
        pyperclip.copy(cleaned_text)

        ctx.logger.info(
            f"Cleaned clipboard: {reduction} chars removed ({reduction_percent:.1f}%)"
        )
        return (
            f"Cleaned clipboard: {reduction} chars removed ({reduction_percent:.1f}%)"
        )

    except Exception as e:
        ctx.logger.error(f"Failed to clean clipboard: {e}")
        raise


def _clean_text(text: str) -> str:
    """
    Clean the provided text by normalizing whitespace and formatting.

    Args:
        text: The text to clean

    Returns:
        str: The cleaned text
    """
    # Remove excessive whitespace and normalize line endings
    text = text.strip()

    # Normalize line endings to Unix style
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize spaces (remove multiple spaces)
    text = re.sub(r" {2,}", " ", text)

    # Clean up spaces around line breaks
    text = re.sub(r" *\n *", "\n", text)

    # Remove trailing/leading whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove empty lines at the beginning and end
    text = text.strip()

    return text
