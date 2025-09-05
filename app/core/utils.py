"""
Shared utility functions for the terminal application.

This module contains common functionality that can be reused across
different components of the application.
"""

from pathlib import Path
from typing import Optional
import logging


def ensure_directory_exists(
    path: Path, logger: Optional[logging.Logger] = None
) -> None:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        path: Directory path to create
        logger: Optional logger for status messages
    """
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        if logger:
            logger.info(f"Created directory: {path}")
    elif logger:
        logger.debug(f"Directory already exists: {path}")


def get_timestamp_filename(prefix: str = "file", extension: str = "txt") -> str:
    """
    Generate a timestamped filename.

    Args:
        prefix: Filename prefix
        extension: File extension (without dot)

    Returns:
        Timestamped filename string
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{timestamp}.{extension}"


def safe_path_join(base: Path, *parts: str) -> Path:
    """
    Safely join path components, preventing directory traversal attacks.

    Args:
        base: Base directory path
        *parts: Path components to join

    Returns:
        Safe joined path

    Raises:
        ValueError: If any path component contains unsafe characters
    """
    # Resolve the base path to handle any .. or . components
    resolved_base = base.resolve()

    # Check each part for unsafe characters
    unsafe_chars = ["..", "/", "\\"]
    for part in parts:
        if any(char in part for char in unsafe_chars):
            raise ValueError(f"Unsafe path component: {part}")

    # Join and resolve to ensure the result is within the base directory
    result = resolved_base / Path(*parts)
    result = result.resolve()

    # Ensure the result is still within the base directory
    try:
        result.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"Path traversal detected: {result}")

    return result


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return ".1f"
        size_bytes /= 1024.0
    return ".1f"
