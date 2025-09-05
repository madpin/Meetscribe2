"""
Custom exceptions for the terminal application.

This module defines application-specific exceptions for better error handling
and more meaningful error messages.
"""


class TerminalAppError(Exception):
    """Base exception for all terminal application errors."""

    pass


class ConfigurationError(TerminalAppError):
    """Raised when there's an issue with configuration loading or parsing."""

    pass


class ActionNotFoundError(TerminalAppError):
    """Raised when a requested action is not found in the registry."""

    pass


class ActionExecutionError(TerminalAppError):
    """Raised when an action fails to execute properly."""

    pass


class ShortcutError(TerminalAppError):
    """Raised when there's an issue with shortcut configuration or execution."""

    pass
