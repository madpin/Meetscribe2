"""
File processing service for Meetscribe.

This module provides functionality for discovering, filtering, and processing
audio files, including batch operations and output file management.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config_models import AppConfig
from app.core.utils import ensure_directory_exists, generate_unique_path
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

    def run_batch(self, files: List[Path], reprocess: bool, transcriber: Transcriber, output_folder: Path, llm_generator=None, llm_modes=None, calendar_linker=None) -> Tuple[int, int]:
        """
        Process a batch of audio files with optional LLM note generation and calendar linking.

        Args:
            files: List of files to process
            reprocess: Whether to reprocess existing files
            transcriber: Transcriber instance
            output_folder: Output folder path
            llm_generator: Optional LLMNotesGenerator instance for generating Q/W/E notes
            llm_modes: Optional modes configuration. Can be:
                - set[str]: Global modes for all files (backward compatibility)
                - dict[Path, set[str]]: Per-file modes for interactive selection
            calendar_linker: Optional CalendarLinker instance for calendar integration

        Returns:
            Tuple of (processed_count, skipped_count)
        """
        processed = skipped = 0

        # Debug logging for modes
        if llm_modes:
            if isinstance(llm_modes, dict):
                self.logger.debug(f"Processing with per-file modes for {len(llm_modes)} files")
            elif isinstance(llm_modes, set):
                self.logger.debug(f"Processing with global modes: {''.join(sorted(llm_modes))}")

        for file in files:
            # Determine target output path and metadata block
            target_out, metadata_block, original_out = self._determine_output_paths(file, output_folder, calendar_linker)

            # If calendar linking is enabled and user cancelled selection, skip this file
            if calendar_linker and metadata_block is calendar_linker.USER_CANCELLED:
                self.logger.info(f"Skipping {file.name} - user cancelled calendar event selection")
                skipped += 1
                continue

            target_stem = target_out.stem

            # Debug logging for per-file modes
            if llm_modes and isinstance(llm_modes, dict):
                file_modes_debug = self._get_modes_for_file(file, llm_modes)
                self.logger.debug(f"PROC {file.name} modes: {file_modes_debug}")

            # Check if target transcription already exists
            transcription_exists = target_out.exists()

            if transcription_exists and not reprocess:
                # Smart processing: transcription exists and we're not reprocessing
                handled, proc_inc, skip_inc = self._handle_existing_without_reprocess(
                    file, target_out, target_stem, llm_generator, llm_modes, output_folder
                )
                if handled:
                    processed += proc_inc
                    skipped += skip_inc
                    continue
            elif transcription_exists and reprocess:
                # Reprocessing: read existing transcription and regenerate LLM notes only
                self.logger.info(f"Reprocessing {file.name} using existing transcription, regenerating LLM notes")

                try:
                    # Read existing transcription
                    existing_content = target_out.read_text()
                    self.logger.info(f"Loaded existing transcription for {file.name} ({len(existing_content)} chars)")

                    # Generate LLM notes if requested
                    if llm_generator and llm_modes:
                        file_modes = self._get_modes_for_file(file, llm_modes)
                        if file_modes:
                            llm_generator.generate_for_modes(existing_content, file_modes, target_stem, output_folder, reprocess)
                            self.logger.info(f"LLM notes regenerated for {file.name}")
                        else:
                            self.logger.info(f"No LLM modes specified for {file.name}, skipping LLM generation")
                    else:
                        self.logger.info(f"No LLM setup for {file.name}, skipping LLM generation")

                    processed += 1

                except Exception as e:
                    self.logger.error(f"Failed to reprocess {file.name}: {e}")
                    processed += 1  # Still count as processed even if it fails

                continue

            # Handle migration from old naming to new naming
            migrated = False
            if not transcription_exists and original_out and original_out.exists() and not reprocess:
                self.logger.info(f"Migrating existing transcription from {original_out.name} to {target_out.name}")
                try:
                    existing_content = original_out.read_text()

                    # Prepend metadata block if calendar linking was successful
                    if metadata_block and not existing_content.startswith("## Linked Calendar Event"):
                        full_content = metadata_block + "\n\n" + existing_content
                    else:
                        full_content = existing_content

                    # Write to new location
                    with open(target_out, "w") as fp:
                        fp.write(full_content)

                    # Generate LLM notes if requested
                    if llm_generator and llm_modes:
                        try:
                            file_modes = self._get_modes_for_file(file, llm_modes)
                            self.logger.debug(f"Generating LLM for {file.name} with modes: {file_modes}")
                            if file_modes:
                                llm_generator.generate_for_modes(full_content, file_modes, target_stem, output_folder, reprocess)
                                self.logger.info(f"LLM notes generated for migrated {file.name}")
                            else:
                                self.logger.info(f"No LLM modes specified for {file.name}, skipping LLM generation")
                        except Exception as e:
                            self.logger.error(f"Failed to generate LLM notes for migrated {file.name}: {e}")

                    processed += 1
                    migrated = True

                except Exception as e:
                    self.logger.error(f"Failed to migrate {file.name}: {e}")
                    processed += 1  # Still count as processed even if migration fails

            if migrated:
                continue

            # Transcription doesn't exist, process the file normally
            try:
                notes = transcriber.process_audio_file(file)

                # Prepend metadata block if calendar linking was successful
                if metadata_block:
                    full_notes = metadata_block + "\n\n" + notes
                else:
                    full_notes = notes

                with open(target_out, "w") as fp:
                    fp.write(full_notes)
                self.logger.info(f"Transcription completed and saved to {target_out}")

                # Generate LLM notes if requested
                if llm_generator and llm_modes:
                    try:
                        # Get modes for this specific file
                        file_modes = self._get_modes_for_file(file, llm_modes)
                        self.logger.debug(f"Generating LLM for {file.name} with modes: {file_modes}")
                        if file_modes:
                            llm_generator.generate_for_modes(full_notes, file_modes, target_stem, output_folder, reprocess)
                            self.logger.info(f"LLM notes generated for {file.name}")
                        else:
                            self.logger.info(f"No LLM modes specified for {file.name}, skipping LLM generation")
                    except Exception as e:
                        self.logger.error(f"Failed to generate LLM notes for {file.name}: {e}")

                processed += 1
            except Exception as e:
                self.logger.error(f"Failed to process {file}: {e}")
                notes = f"Error: Could not process {file}."

                # Prepend metadata block even for errors if calendar linking was successful
                if metadata_block:
                    full_notes = metadata_block + "\n\n" + notes
                else:
                    full_notes = notes

                with open(target_out, "w") as fp:
                    fp.write(full_notes)

                # Even for errors, try to generate LLM notes if requested (from error message)
                if llm_generator and llm_modes:
                    try:
                        # Get modes for this specific file
                        file_modes = self._get_modes_for_file(file, llm_modes)
                        if file_modes:
                            llm_generator.generate_for_modes(full_notes, file_modes, target_stem, output_folder, reprocess)
                    except Exception as llm_error:
                        self.logger.error(f"Failed to generate LLM notes for error case {file.name}: {llm_error}")

                processed += 1  # Still count as processed (error file created)

        return processed, skipped

    def _get_modes_for_file(self, file: Path, llm_modes):
        """
        Get the modes for a specific file, handling both old and new formats.

        Args:
            file: The file path
            llm_modes: Either a set[str] (global modes) or dict[Path, set[str]] (per-file modes)

        Returns:
            set[str]: The modes for this file
        """
        if llm_modes is None:
            return set()

        # Handle per-file modes (dict format)
        if isinstance(llm_modes, dict):
            # First try exact match
            if file in llm_modes:
                self.logger.debug(f"Found exact match for {file.name} with modes: {''.join(sorted(llm_modes[file]))}")
                return llm_modes[file]

            # Try to find by filename match (more robust)
            file_name = file.name
            for dict_file, modes in llm_modes.items():
                if dict_file.name == file_name:
                    self.logger.debug(f"Found filename match for {file_name} with modes: {''.join(sorted(modes))}")
                    return modes

            # If still not found, log the issue
            self.logger.debug(f"No modes found for {file_name}. Available files: {[f.name for f in llm_modes.keys()]}")
            return set()

        # Handle global modes (set format) for backward compatibility
        if isinstance(llm_modes, set):
            return llm_modes

        # Fallback
        return set()

    def _determine_output_paths(self, file: Path, output_folder: Path, calendar_linker) -> Tuple[Path, Optional[str], Optional[Path]]:
        """
        Determine the output paths and metadata block for a file.

        Args:
            file: Input audio file
            output_folder: Output folder path
            calendar_linker: Optional CalendarLinker instance

        Returns:
            Tuple of (target_output_path, metadata_block, original_output_path)
        """
        default_stem = file.stem
        default_out = output_folder / f"{default_stem}.txt"

        if not calendar_linker:
            return default_out, None, None

        # Try to match file to calendar event
        matched_event = calendar_linker.match_file(file)

        if matched_event is calendar_linker.USER_CANCELLED:
            # User cancelled selection - return special marker
            return default_out, calendar_linker.USER_CANCELLED, None
        elif not matched_event:
            # No match found, use default naming
            return default_out, None, None

        # Match found, compute new stem and paths
        new_stem = calendar_linker.compute_target_stem(matched_event)
        new_out = output_folder / f"{new_stem}.txt"

        # Generate unique path if needed (when not reprocessing)
        if new_out.exists():
            new_out = generate_unique_path(output_folder, new_stem, ".txt")

        # Generate metadata block
        metadata_block = calendar_linker.format_event_metadata(matched_event, file)

        return new_out, metadata_block, default_out

    def _handle_existing_without_reprocess(self, file: Path, target_out: Path, target_stem: str, llm_generator, llm_modes, output_folder: Path) -> tuple[bool, int, int]:
        """
        Handle the case where transcription exists and we're not reprocessing.

        Args:
            file: The audio file being processed
            target_out: The target output path for transcription
            target_stem: The stem of the target output file
            llm_generator: Optional LLM generator instance
            llm_modes: Optional modes configuration
            output_folder: Output folder path

        Returns:
            Tuple of (handled: bool, processed_increment: int, skipped_increment: int)
        """
        if llm_generator and llm_modes:
            # Get modes for this specific file
            file_modes = self._get_modes_for_file(file, llm_modes)

            if file_modes:
                self.logger.info(f"Transcription exists for {file.name}, generating LLM notes from existing content (modes: {''.join(sorted(file_modes))})")

                try:
                    existing_content = target_out.read_text()
                    llm_generator.generate_for_modes(existing_content, file_modes, target_stem, output_folder, False)  # reprocess=False
                    return True, 1, 0  # handled, processed +1, skipped +0
                except Exception as e:
                    self.logger.error(f"Failed to generate LLM notes from existing transcription for {file.name}: {e}")
                    return True, 1, 0  # handled, processed +1, skipped +0 (still count as processed even if LLM fails)
            else:
                self.logger.info(f"Transcription exists for {file.name} but no LLM modes specified for this file, skipping")
                return True, 0, 1  # handled, processed +0, skipped +1
        else:
            # No LLM generator or modes at all
            self.logger.info(f"Transcription exists for {file.name} but no LLM setup, skipping")
            return True, 0, 1  # handled, processed +0, skipped +1
