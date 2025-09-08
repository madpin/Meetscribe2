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
    output_extension: str = "md"

    def expand(self):
        """Expand user paths to absolute paths."""
        self.input_folder = self.input_folder.expanduser()
        self.output_folder = self.output_folder.expanduser()
        # Normalize output extension: remove leading dot, lowercase, default to md
        self.output_extension = (self.output_extension or "md").strip().lstrip('.').lower() or "md"
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
    match_tolerance_minutes: int = 90

    def expand(self):
        """Expand user paths to absolute paths."""
        self.credentials_file = self.credentials_file.expanduser()
        self.token_file = self.token_file.expanduser()
        return self


class LLMPathsConfig(BaseModel):
    """LLM output folder configuration."""
    q_output_folder: Optional[Path] = None
    w_output_folder: Optional[Path] = None
    e_output_folder: Optional[Path] = None

    def expand(self, default_output: Path) -> "LLMPathsConfig":
        """Expand user paths to absolute paths, using default_output if not set."""
        def normalize_path(path: Optional[Path]) -> Optional[Path]:
            """Normalize path value, treating empty/whitespace strings and '.' as unset."""
            if path is None:
                return None
            # Convert to string and check if it's empty or whitespace-only
            path_str = str(path).strip()
            if not path_str or path_str == ".":
                return None
            return path

        def resolve_path(path: Optional[Path], default: Path) -> Path:
            """Resolve a path, using default if None."""
            if path is None:
                return default
            return path.expanduser()

        # Normalize each path value
        self.q_output_folder = normalize_path(self.q_output_folder)
        self.w_output_folder = normalize_path(self.w_output_folder)
        self.e_output_folder = normalize_path(self.e_output_folder)

        # Resolve to default_output if None, otherwise expanduser
        self.q_output_folder = resolve_path(self.q_output_folder, default_output)
        self.w_output_folder = resolve_path(self.w_output_folder, default_output)
        self.e_output_folder = resolve_path(self.e_output_folder, default_output)

        return self


class LLMPromptsConfig(BaseModel):
    """LLM prompt configuration."""
    q: str = "Write a clear, concise executive summary of the meeting. Include key points, decisions, risks, and next steps."
    w: str = "Provide a holistic analysis of the meeting. Summarize themes, sentiments by participants, points of alignment or tension, and overall tone."
    e: str = "Extract a precise, actionable list of tasks discussed. For each, include assignee (if known), due date (if mentioned), and concise description."


class LLMKeysConfig(BaseModel):
    """LLM mode key mappings."""
    q: str = "Q"
    w: str = "W"
    e: str = "E"


class LLMConfig(BaseModel):
    """LLM post-processing configuration."""
    enabled: bool = True
    dialect: str = "openai"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    default_modes: str = ""
    prompts: LLMPromptsConfig = LLMPromptsConfig()
    paths: LLMPathsConfig = LLMPathsConfig()
    keys: LLMKeysConfig = LLMKeysConfig()


class AppConfig(BaseModel):
    """Root configuration model."""
    deepgram: DeepgramConfig
    paths: PathsConfig = PathsConfig()
    processing: ProcessingConfig = ProcessingConfig()
    ui: UIConfig = UIConfig()
    logging: LoggingConfig = LoggingConfig()
    google: GoogleConfig = GoogleConfig()
    llm: LLMConfig = LLMConfig()
