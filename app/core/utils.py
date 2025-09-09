"""
Shared utility functions for the terminal application.

This module contains common functionality that can be reused across
different components of the application.
"""

from pathlib import Path
from typing import Optional
import logging


def ensure_directory_exists(
    path: Path, logger: Optional[logging.Logger] = None
) -> None:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        path: Directory path to create
        logger: Optional logger for status messages
    """
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        if logger:
            logger.info(f"Created directory: {path}")
    elif logger:
        logger.debug(f"Directory already exists: {path}")


def get_timestamp_filename(prefix: str = "file", extension: str = "txt") -> str:
    """
    Generate a timestamped filename.

    Args:
        prefix: Filename prefix
        extension: File extension (without dot)

    Returns:
        Timestamped filename string
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{timestamp}.{extension}"


def safe_path_join(base: Path, *parts: str) -> Path:
    """
    Safely join path components, preventing directory traversal attacks.

    Args:
        base: Base directory path
        *parts: Path components to join

    Returns:
        Safe joined path

    Raises:
        ValueError: If path traversal is detected
    """
    resolved_base = base.resolve()
    result = (resolved_base / Path(*parts)).resolve()
    try:
        result.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"Path traversal detected: {result}")
    return result


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_audio_duration(path: Path) -> Optional[float]:
    """
    Get audio duration in seconds for various audio formats including AAC.

    Args:
        path: Path to audio file

    Returns:
        Duration in seconds, or None if unable to determine
    """
    try:
        if path.suffix.lower() == ".wav":
            import wave

            with wave.open(str(path), "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / rate if rate > 0 else None
        else:
            # Try mutagen for other formats (including AAC, MP3, FLAC, etc.)
            try:
                from mutagen import File

                audio = File(str(path))  # Convert Path to string for mutagen
                if (
                    audio is not None
                    and hasattr(audio, "info")
                    and hasattr(audio.info, "length")
                    and audio.info.length is not None
                ):
                    return float(audio.info.length)
            except ImportError:
                # mutagen not available - try alternative approaches
                return _get_duration_fallback(path)
            except Exception:
                # Any other error with mutagen
                # Try fallback method
                return _get_duration_fallback(path)
    except Exception:
        # Any error reading the file
        pass

    return None


def _get_duration_fallback(path: Path) -> Optional[float]:
    """Fallback methods when mutagen is not available or fails."""
    try:
        # Try using ffprobe if available
        import subprocess
        import json

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = data.get("format", {}).get("duration")
            if duration:
                return float(duration)
    except (
        subprocess.SubprocessError,
        json.JSONDecodeError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    return None


def format_duration(seconds: Optional[float]) -> str:
    """
    Format duration in seconds to MM:SS or HH:MM:SS.

    Args:
        seconds: Duration in seconds, or None

    Returns:
        Formatted duration string
    """
    if seconds is None:
        return "-"

    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def format_time_ago(value) -> str:
    """
    Format a timestamp as a short relative time ago string.

    Args:
        value: datetime, UNIX timestamp (float/int), or Path.stat().st_mtime timestamp

    Returns:
        Short relative time string (e.g., '5m', '2h', '3d', '4w', '6mo', '1y')
    """
    from datetime import datetime

    # Convert input to datetime
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value)
    else:
        raise TypeError(f"Unsupported type for value: {type(value)}")

    # Calculate time difference
    now = datetime.now()
    delta = now - dt

    # Handle future timestamps
    if delta.total_seconds() < 0:
        return "0s"

    total_seconds = int(delta.total_seconds())

    # Define time units in descending order
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:  # < 60 minutes
        minutes = total_seconds // 60
        return f"{minutes}m"
    elif total_seconds < 86400:  # < 24 hours
        hours = total_seconds // 3600
        return f"{hours}h"
    elif total_seconds < 604800:  # < 7 days
        days = total_seconds // 86400
        return f"{days}d"
    elif total_seconds < 2419200:  # < ~4 weeks (28 days)
        weeks = total_seconds // 604800
        return f"{weeks}w"
    elif total_seconds < 31536000:  # < 12 months
        months = total_seconds // 2629746  # Average month in seconds
        return f"{max(1, months)}mo"  # Ensure minimum 1
    else:
        years = total_seconds // 31536000
        return f"{max(1, years)}y"


def sanitize_filename(name: str, replacement: str = "_", max_length: int = 80) -> str:
    """
    Sanitize a string to make it safe for use as a filename component.

    Args:
        name: The original string to sanitize
        replacement: Character to replace invalid sequences with
        max_length: Maximum length of the resulting string

    Returns:
        Sanitized string safe for filesystem use
    """
    import re

    if not name:
        return "untitled"

    # Trim whitespace
    name = name.strip()

    # Replace sequences of non-alphanumeric/dash/underscore/space with replacement
    name = re.sub(r"[^a-zA-Z0-9\-_\s]", replacement, name)

    # Convert spaces to replacement
    name = name.replace(" ", replacement)

    # Collapse multiple replacements to single occurrence
    while replacement * 2 in name:
        name = name.replace(replacement * 2, replacement)

    # Strip leading/trailing replacement characters
    name = name.strip(replacement)

    # Ensure non-empty result
    if not name:
        return "untitled"

    # Cap to max_length
    if len(name) > max_length:
        name = name[:max_length].rstrip(replacement)

    return name


def generate_unique_path(base: Path, stem: str, ext: str) -> Path:
    """
    Generate a unique file path, avoiding overwrites by adding suffixes if needed.

    Args:
        base: Base directory path
        stem: Filename stem (without extension)
        ext: File extension (with dot, e.g., ".txt")

    Returns:
        Unique file path that doesn't exist in the base directory
    """
    if not ext.startswith("."):
        ext = "." + ext

    candidate = base / f"{stem}{ext}"
    if not candidate.exists():
        return candidate

    # Add suffixes like " (1)", " (2)", etc.
    counter = 1
    while True:
        candidate = base / f"{stem} ({counter}){ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def truncate_attendees(attendees: list, max_count: int = 5) -> str:
    """
    Truncate attendee list to max_count with summary if needed.

    Args:
        attendees: List of attendee names
        max_count: Maximum number of attendees to show before truncating

    Returns:
        Formatted attendee string
    """
    if not attendees:
        return "-"
    if len(attendees) <= max_count:
        return ", ".join(attendees)
    remaining = len(attendees) - max_count
    return f"{', '.join(attendees[:max_count])} +{remaining} more"


def truncate_attachments(attachments: list, max_count: int = 3) -> str:
    """
    Truncate attachment list to max_count with summary if needed.

    Args:
        attachments: List of attachment titles
        max_count: Maximum number of attachments to show before truncating

    Returns:
        Formatted attachment string
    """
    if not attachments:
        return "-"
    if len(attachments) <= max_count:
        return ", ".join(attachments)
    remaining = len(attachments) - max_count
    return f"{', '.join(attachments[:max_count])} +{remaining} more"
