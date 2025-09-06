"""
Pydantic configuration models for Meetscribe.

This module defines strongly-typed configuration models using Pydantic v2,
providing validation, safety, and self-documentation for all configuration sections.
"""

from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Union, Optional


class DeepgramConfig(BaseModel):
    """Deepgram API configuration."""
    api_key: str = Field(..., min_length=1)
    model: str = "nova-3"
    language: str = "en-US"
    smart_format: bool = True
    diarize: bool = True
    diarize_speakers: int = 0
    min_speaker_gap: float = 0.0
    max_speaker_gap: float = 0.0
    summarize: Union[str, bool] = False
    detect_topics: bool = False
    intents: bool = False


class PathsConfig(BaseModel):
    """File system paths configuration."""
    input_folder: Path = Path("~/Audio")
    output_folder: Path = Path("~/Documents/Meetscribe")

    def expand(self):
        """Expand user paths to absolute paths."""
        self.input_folder = self.input_folder.expanduser()
        self.output_folder = self.output_folder.expanduser()
        return self


class ProcessingConfig(BaseModel):
    """Audio processing configuration."""
    reprocess: bool = False
    soft_limit_files: int = 10
    hard_limit_files: int = 25


class UIConfig(BaseModel):
    """User interface configuration."""
    selection_page_size: int = 10


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    log_file: Optional[Path] = None
    enable_file_logging: bool = True

    def expand(self):
        """Expand user paths to absolute paths."""
        if self.log_file:
            self.log_file = self.log_file.expanduser()
        return self


class GoogleConfig(BaseModel):
    """Google Calendar integration configuration."""
    credentials_file: Path = Path("~/.meetscribe/google/credentials.json")
    token_file: Path = Path("~/.meetscribe/google/token.json")
    scopes: List[str] = ["https://www.googleapis.com/auth/calendar.readonly"]
    calendar_id: str = "primary"
    default_past_days: int = 3
    max_results: int = 50
    filter_group_events_only: bool = True

    def expand(self):
        """Expand user paths to absolute paths."""
        self.credentials_file = self.credentials_file.expanduser()
        self.token_file = self.token_file.expanduser()
        return self


class AppConfig(BaseModel):
    """Root configuration model."""
    deepgram: DeepgramConfig
    paths: PathsConfig = PathsConfig()
    processing: ProcessingConfig = ProcessingConfig()
    ui: UIConfig = UIConfig()
    logging: LoggingConfig = LoggingConfig()
    google: GoogleConfig = GoogleConfig()
