"""
File processing service for Meetscribe.

This module provides functionality for discovering, filtering, and processing
audio files, including batch operations and output file management.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config_models import AppConfig
from app.core.utils import ensure_directory_exists
from app.transcriber import SUPPORTED_EXTENSIONS, Transcriber


class FileProcessor:
    """
    Service for processing audio files and managing file operations.
    """

    def __init__(self, cfg: AppConfig, logger):
        """
        Initialize the FileProcessor with configuration and logger.

        Args:
            cfg: Application configuration
            logger: Logger instance
        """
        self.cfg = cfg
        self.logger = logger

    def resolve_input_folder(self, arg: Optional[str]) -> Path:
        """
        Resolve the input folder path.

        Args:
            arg: Optional path argument, uses config default if None

        Returns:
            Resolved input folder path
        """
        return (Path(arg).expanduser() if arg else self.cfg.paths.input_folder)

    def resolve_output_folder(self) -> Path:
        """
        Resolve and ensure the output folder exists.

        Returns:
            Resolved output folder path
        """
        folder = self.cfg.paths.output_folder
        ensure_directory_exists(folder, self.logger)
        return folder

    def discover_audio_files(self, input_dir: Path) -> List[Path]:
        """
        Discover audio files in the input directory.

        Args:
            input_dir: Directory to scan for audio files

        Returns:
            List of audio file paths, sorted by modification time (newest first)
        """
        if not input_dir.is_dir():
            raise ValueError(f"Input path is not a directory: {input_dir}")

        files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def get_files_to_process(self, files: List[Path], reprocess: bool, output_folder: Path) -> List[Path]:
        """
        Filter files to process based on reprocess flag and existing outputs.

        Args:
            files: List of candidate audio files
            reprocess: Whether to reprocess files that already have outputs
            output_folder: Output folder path

        Returns:
            List of files that should be processed
        """
        candidates = []
        for file in files:
            out = output_folder / f"{file.stem}.txt"
            if not reprocess and out.exists():
                self.logger.debug(f"Skipping {file.name}: output already exists")
                continue
            candidates.append(file)
        return candidates

    def should_use_select_mode(self, candidate_count: int) -> Optional[bool]:
        """
        Determine if interactive selection mode should be used.

        Args:
            candidate_count: Number of candidate files

        Returns:
            True if selection is required (exceeds hard limit),
            False if selection not needed,
            None if soft limit exceeded (caller should prompt user)
        """
        hard = int(self.cfg.processing.hard_limit_files)
        soft = int(self.cfg.processing.soft_limit_files)

        if candidate_count > hard:
            self.logger.warning(f"Found {candidate_count} files (exceeds hard limit of {hard})")
            return True
        if candidate_count > soft:
            return None  # Caller should prompt user
        return False

    def run_batch(self, files: List[Path], reprocess: bool, transcriber: Transcriber, output_folder: Path) -> Tuple[int, int]:
        """
        Process a batch of audio files.

        Args:
            files: List of files to process
            reprocess: Whether to reprocess existing files
            transcriber: Transcriber instance
            output_folder: Output folder path

        Returns:
            Tuple of (processed_count, skipped_count)
        """
        processed = skipped = 0
        for file in files:
            out = output_folder / f"{file.stem}.txt"
            if not reprocess and out.exists():
                self.logger.info(f"Skipping {file.name}: {out} already exists")
                skipped += 1
                continue

            try:
                notes = transcriber.process_audio_file(file)
                with open(out, "w") as fp:
                    fp.write(notes)
                self.logger.info(f"Notes saved to {out}")
                processed += 1
            except Exception as e:
                self.logger.error(f"Failed to process {file}: {e}")
                notes = f"Error: Could not process {file}."
                with open(out, "w") as fp:
                    fp.write(notes)
                processed += 1  # Still count as processed (error file created)

        return processed, skipped
