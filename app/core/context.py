"""
Application Context for managing shared state and dependencies.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .config import load_config
from .logging import setup_logging
from .exceptions import ConfigurationError


class AppContext:
    """
    Central application context that manages configuration and logging.
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
        self.config: Optional[Dict[str, Any]] = None
        self.logger = None

        # Initialize components
        self._load_configuration()
        self._setup_logging()

    def _load_configuration(self) -> None:
        """Load and parse configuration."""
        try:
            self.config = load_config(self.config_path)
            # Use print for startup messages before logging is initialized
            print("Configuration loaded successfully")
        except Exception as e:
            print(f"Failed to load configuration: {e}")
            sys.exit(1)

    def _setup_logging(self) -> None:
        """Initialize the logging system."""
        if self.config is None:
            raise ConfigurationError(
                "Configuration must be loaded before logging setup"
            )

        log_file = Path.home() / ".meetscribe" / "meetscribe.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        self.logger = setup_logging(level="INFO", log_file=log_file)
        self.logger.info("Application context initialized")
