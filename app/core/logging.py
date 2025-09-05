"""
Centralized logging configuration for the terminal application.

This module provides structured logging with Rich console formatting,
configurable log levels, and consistent logging across all components.
"""

import logging
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: Optional[Console] = None,
) -> logging.Logger:
    """
    Configure the application's logging system.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for file output
        console: Optional Rich console instance for custom formatting

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("aio_terminal_template")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler with Rich formatting
    if console is None:
        console = Console()

    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=False,  # Don't show full paths to reduce clutter
        markup=True,  # Enable Rich markup
        rich_tracebacks=True,  # Enhanced tracebacks
    )
    rich_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Create formatter for console output
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    rich_handler.setFormatter(formatter)

    # Add console handler
    logger.addHandler(rich_handler)

    # Add file handler if specified
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "aio_terminal_template") -> logging.Logger:
    """
    Get a logger instance for the specified name.

    Args:
        name: Logger name (defaults to main app logger)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
