"""
Audio processing utilities for Meetscribe.

This module provides functionality for audio preprocessing, including silence removal
and format handling.
"""

from pathlib import Path
from typing import Dict

from pydub import AudioSegment
from pydub.silence import split_on_silence


def infer_export_format(ext: str) -> str:
    """
    Infer the correct export format from file extension.

    Args:
        ext: File extension (e.g., '.wav', '.mp3')

    Returns:
        str: Export format string compatible with PyDub
    """
    ext_lower = ext.lower().lstrip('.')

    # Map common extensions to PyDub export formats
    format_map: Dict[str, str] = {
        'wav': 'wav',
        'mp3': 'mp3',
        'm4a': 'mp4',  # AAC files in M4A container
        'aac': 'adts',  # Raw AAC uses ADTS format
    }

    return format_map.get(ext_lower, ext_lower)


def remove_silence(
    input_path: Path,
    output_path: Path,
    min_silence_len: int = 1000,
    silence_thresh: int = -40,
    keep_silence: int = 100,
) -> Path:
    """
    Remove silence from an audio file using PyDub.

    Args:
        input_path: Path to input audio file
        output_path: Path to write processed audio file
        min_silence_len: Minimum length of silence to detect (in milliseconds)
        silence_thresh: Silence threshold in dBFS (negative value)
        keep_silence: Amount of silence to keep around detected segments (in milliseconds)

    Returns:
        Path: Path to the processed output file

    Raises:
        FileNotFoundError: If input file doesn't exist
        Exception: If audio processing fails
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    try:
        # Load audio file
        audio = AudioSegment.from_file(input_path)

        # Split on silence
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=keep_silence,
        )

        # Handle case with no chunks (entirely silence or single segment)
        if not chunks:
            # Export the original audio unchanged
            export_format = infer_export_format(output_path.suffix)
            audio.export(output_path, format=export_format)
        else:
            # Combine non-silent chunks
            combined = AudioSegment.empty()
            for chunk in chunks:
                combined += chunk

            # Export the combined audio
            export_format = infer_export_format(output_path.suffix)
            combined.export(output_path, format=export_format)

        return output_path

    except Exception as e:
        raise Exception(f"Failed to process audio file {input_path}: {e}")
