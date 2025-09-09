"""
Application Context for managing shared state and dependencies.
"""

from pathlib import Path
from typing import Optional

from .config import load_config
from .logging import setup_logging
from .exceptions import ConfigurationError
from .config_models import AppConfig


class AppContext:
    """
    Central application context that manages typed configuration and logging.
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

        # Load typed configuration first (minimal config for logging)
        try:
            self.config: AppConfig = load_config(self.config_path)
        except Exception as e:
            # If config loading fails, use default logging config
            print(f"Failed to load configuration: {e}")
            raise ConfigurationError(str(e))

        # Setup logging using configuration
        log_file = None
        if self.config.logging.enable_file_logging:
            if self.config.logging.log_file:
                log_file = self.config.logging.log_file
            else:
                # Default log file if not specified
                log_file = Path.home() / ".meetscribe" / "meetscribe.log"

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

        self.logger = setup_logging(level=self.config.logging.level, log_file=log_file)

        self.logger.info("Configuration loaded successfully")
