"""
Application Context for managing shared state and dependencies.
"""

import logging
from pathlib import Path
from typing import Optional

from .config import load_config
from .logging import setup_logging
from .exceptions import ConfigurationError
from .config_models import AppConfig


class AppContext:
    """
    Central application context that manages typed configuration and logging.
    Uses lazy initialization to improve startup performance.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the application context with lazy loading.

        Args:
            config_path: Optional path to configuration file (defaults to config.toml)

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        self.config_path = config_path or Path("config.toml")
        self._config: Optional[AppConfig] = None
        self._logger: Optional[logging.Logger] = None

    @property
    def config(self) -> AppConfig:
        """Lazily load and return configuration."""
        if self._config is None:
            try:
                self._config = load_config(self.config_path)
            except Exception as e:
                print(f"Failed to load configuration: {e}")
                raise ConfigurationError(str(e))
        return self._config

    @property
    def logger(self) -> logging.Logger:
        """Lazily setup and return logger."""
        if self._logger is None:
            # Ensure config is loaded first
            config = self.config

            # Setup logging using configuration
            log_file = None
            if config.logging.enable_file_logging:
                if config.logging.log_file:
                    log_file = config.logging.log_file
                else:
                    # Default log file if not specified
                    log_file = Path.home() / ".meetscribe" / "meetscribe.log"

            if log_file:
                log_file.parent.mkdir(parents=True, exist_ok=True)

            self._logger = setup_logging(level=config.logging.level, log_file=log_file)
            self._logger.info("Configuration loaded successfully")

        return self._logger
