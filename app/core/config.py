"""
Configuration loading and management.

This module handles loading TOML configuration files and validates them
against Pydantic models for type safety and consistency.
"""

import toml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .config_models import AppConfig
import collections.abc


def deep_merge(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively update a dictionary.
    Sub-dictionaries are merged, and other values are overwritten.

    Args:
        d: Base dictionary to update
        u: Dictionary with updates

    Returns:
        Updated dictionary
    """
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_merge(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Loads configuration from TOML files and validates against Pydantic models.

    The base configuration is loaded from `config.toml`. If a `config.local.toml`
    is found in the same directory, its values will be deeply merged into the
    base configuration, overriding any matching settings.

    Args:
        config_path: Optional path to config file (defaults to config.toml)

    Returns:
        AppConfig: The validated, typed configuration.

    Raises:
        FileNotFoundError: If the base `config.toml` does not exist.
        ValidationError: If configuration doesn't match expected schema.
    """
    logger = logging.getLogger("meetscribe")
    config_path = config_path or Path("config.toml")
    local_config_path = Path("config.local.toml")

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Default configuration file not found at: {config_path.resolve()}"
        )

    config = toml.load(config_path)

    if local_config_path.is_file():
        logger.debug(f"Loading local configuration overrides from {local_config_path.resolve()}")
        local_config = toml.load(local_config_path)
        config = deep_merge(config, local_config)

    cfg = AppConfig.model_validate(config)
    cfg.paths = cfg.paths.expand()
    cfg.logging = cfg.logging.expand()
    cfg.google = cfg.google.expand()
    return cfg
