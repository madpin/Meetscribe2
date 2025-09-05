"""
Application Context for managing shared state and dependencies.

This module provides the central AppContext class that holds configuration,
logging, and the action registry, replacing the global CONFIG variable.
"""

import sys
from pathlib import Path
from typing import Dict, Callable, Optional

from .config import load_config
from .models import AppConfig
from .logging import setup_logging
from .exceptions import ConfigurationError


class AppContext:
    """
    Central application context that manages configuration, logging, and actions.

    This replaces the global CONFIG variable and provides a clean dependency
    injection pattern for all components.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the application context.

        Args:
            config_path: Optional path to configuration file (defaults to config.toml)

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        self.config_path = config_path or Path("config.toml")
        self.config: Optional[AppConfig] = None
        self.logger = None
        self.action_registry: Dict[str, Callable] = {}

        # Initialize components
        self._load_configuration()
        self._setup_logging()
        self._load_action_registry()

    def _load_configuration(self) -> None:
        """Load and parse configuration."""
        try:
            raw_config = load_config(self.config_path)
            self.config = AppConfig.from_dict(raw_config)
            print("Configuration loaded successfully")
        except Exception as e:
            print(f"Failed to load configuration: {e}")
            sys.exit(1)

    def _setup_logging(self) -> None:
        """Initialize the logging system."""
        if not self.config:
            raise ConfigurationError(
                "Configuration must be loaded before logging setup"
            )

        # Set up logging with configuration
        log_level = self.config.viewer.log_level
        log_file = self.config.paths.get_logs_path() / "aio_terminal_template.log"

        self.logger = setup_logging(level=log_level, log_file=log_file)

        self.logger.info("Application context initialized")

    def _load_action_registry(self) -> None:
        """Load all available actions."""
        if not self.logger:
            raise ConfigurationError(
                "Logger must be initialized before loading actions"
            )

        try:
            from ..actions.registry import load_action_registry

            self.action_registry = load_action_registry(self.logger)
            self.logger.info(f"Loaded {len(self.action_registry)} actions")
        except Exception as e:
            self.logger.error(f"Failed to load action registry: {e}")
            raise ConfigurationError(f"Action registry loading failed: {e}")

    def get_action(self, name: str) -> Optional[Callable]:
        """
        Get an action function by name.

        Args:
            name: Action name in format 'module.function'

        Returns:
            Action function or None if not found
        """
        return self.action_registry.get(name)

    def execute_action(self, name: str) -> str:
        """
        Execute an action by name.

        Args:
            name: Action name in format 'module.function'

        Returns:
            Action result string

        Raises:
            ValueError: If action is not found
            Exception: If action execution fails
        """
        if not self.logger:
            raise ConfigurationError("Logger not available")

        action_func = self.get_action(name)
        if not action_func:
            error_msg = f"Action '{name}' not found in registry"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            self.logger.info(f"Executing action: {name}")
            # Pass the AppContext instead of raw config
            result = action_func(self)
            self.logger.info(f"Action '{name}' completed successfully")
            return str(result)
        except Exception as e:
            self.logger.error(f"Action '{name}' failed: {e}")
            raise
