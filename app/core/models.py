"""
Configuration models using dataclasses for type safety and validation.

This module defines strongly-typed configuration structures that replace
the previous dictionary-based configuration approach.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any


@dataclass
class ViewerConfig:
    """Configuration for the live viewer component."""

    log_level: str = "INFO"
    color_theme: str = "default"
    autoscroll: bool = True
    max_lines: int = 1000


@dataclass
class PathsConfig:
    """Configuration for file system paths."""

    screenshots_folder: str = "~/screenshots"
    logs_folder: str = "~/.cache/aio_terminal_template/logs"
    log_retention_days: int = 7

    def get_screenshots_path(self) -> Path:
        """Get the expanded screenshots folder path."""
        return Path(self.screenshots_folder).expanduser()

    def get_logs_path(self) -> Path:
        """Get the expanded logs folder path."""
        return Path(self.logs_folder).expanduser()


@dataclass
class ShortcutDefinition:
    """Configuration for a single keyboard shortcut."""

    keys: str
    action: str
    enabled: bool = True


@dataclass
class ShortcutsConfig:
    """Configuration for global keyboard shortcuts."""

    enabled: bool = True
    shortcuts: Dict[str, ShortcutDefinition] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShortcutsConfig":
        """Create ShortcutsConfig from a dictionary."""
        enabled = data.get("enabled", True)
        shortcuts = {}

        for key, value in data.items():
            if key != "enabled" and isinstance(value, dict):
                shortcuts[key] = ShortcutDefinition(
                    keys=value.get("keys", ""),
                    action=value.get("action", ""),
                    enabled=value.get("enabled", True),
                )

        return cls(enabled=enabled, shortcuts=shortcuts)


@dataclass
class NetworkConfig:
    """Configuration for network requests."""

    api_base_url: str = "https://api.example.com"
    timeout: int = 10
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class UpdatesConfig:
    """Configuration for application updates."""

    github_repo: str = "tpinto/aio_terminal_template"
    executable_name: Optional[str] = None


@dataclass
class DaemonConfig:
    """Configuration for daemon mode."""

    enabled: bool = False
    log_file: str = "/tmp/aio_terminal_template-daemon.log"
    pid_file: str = "/tmp/aio_terminal_template-daemon.pid"


@dataclass
class AppConfig:
    """Main application configuration container."""

    viewer: ViewerConfig = field(default_factory=ViewerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    shortcuts: ShortcutsConfig = field(default_factory=ShortcutsConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    updates: UpdatesConfig = field(default_factory=UpdatesConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create AppConfig from a dictionary (for TOML loading)."""
        return cls(
            viewer=ViewerConfig(**data.get("viewer", {})),
            paths=PathsConfig(**data.get("paths", {})),
            shortcuts=ShortcutsConfig.from_dict(data.get("shortcuts", {})),
            network=NetworkConfig(**data.get("network", {})),
            updates=UpdatesConfig(**data.get("updates", {})),
            daemon=DaemonConfig(**data.get("daemon", {})),
        )
