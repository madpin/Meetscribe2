from pathlib import Path
from typing import Dict, Optional, Set, Tuple, List
import time

from app.core.config_models import AppConfig
from app.services.file_processor import FileProcessor
from app.transcriber import Transcriber, SUPPORTED_EXTENSIONS


class DirectoryWatcher:
    def __init__(
        self,
        cfg: AppConfig,
        logger,
        stable_seconds: Optional[int] = None,
        poll_interval: Optional[float] = None,
        max_filesize_mb: Optional[int] = None,
    ):
        self.cfg = cfg
        self.logger = logger

        # Effective settings with overrides
        self.stable_seconds = int(stable_seconds if stable_seconds is not None else self.cfg.watcher.stable_time_seconds)
        self.poll_interval = float(poll_interval if poll_interval is not None else self.cfg.watcher.poll_interval_seconds)
        self.max_bytes = int((max_filesize_mb if max_filesize_mb is not None else self.cfg.watcher.max_filesize_mb) * 1024 * 1024)

        # Internal state
        self._size_state: Dict[Path, Tuple[int, float]] = {}     # path -> (last_size, last_change_mono)
        self._processed: Set[Path] = set()
        self._skipped_large: Set[Path] = set()

    def _list_audio_files(self, folder: Path) -> List[Path]:
        try:
            return [
                p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
        except FileNotFoundError:
            return []

    def _update_size_state(self, path: Path, size: int, now_mono: float) -> float:
        prev = self._size_state.get(path)
        if prev is None:
            self._size_state[path] = (size, now_mono)
            return 0.0
        prev_size, last_change = prev
        if size != prev_size:
            self._size_state[path] = (size, now_mono)
            return 0.0
        # unchanged
        return now_mono - last_change

    def _is_file_created_after_watch_start(self, path: Path) -> bool:
        """Check if file was created after the watch started."""
        try:
            # Use modification time as a proxy for creation time
            # On most systems, modification time is set when file is created
            file_mtime = path.stat().st_mtime
            return file_mtime > self._watch_start_time
        except (FileNotFoundError, OSError):
            # If we can't get the file stats, assume it's new
            return True

    def watch(
        self,
        input_dir: Path,
        processor: FileProcessor,
        transcriber: Transcriber,
        output_folder: Path,
        llm_generator=None,
        llm_modes=None,
        calendar_linker=None,
        reprocess: Optional[bool] = None,
    ) -> None:
        if not input_dir.is_dir():
            raise ValueError(f"Input path is not a directory: {input_dir}")

        effective_reprocess = reprocess if reprocess is not None else self.cfg.processing.reprocess

        # Record the watch start time - only process files created after this
        self._watch_start_time = time.time()

        self.logger.info(
            f"Directory watcher started: folder={input_dir} | stable_seconds={self.stable_seconds} | "
            f"poll_interval={self.poll_interval}s | max_filesize={self.max_bytes/1024/1024:.0f} MB | "
            f"reprocess={'true' if effective_reprocess else 'false'} | "
            f"only_processing_files_created_after_watch_start"
        )

        try:
            while True:
                now_mono = time.monotonic()
                current_files = self._list_audio_files(input_dir)

                # Cleanup state for removed files
                current_set = set(current_files)
                for stale in list(self._size_state.keys()):
                    if stale not in current_set:
                        self._size_state.pop(stale, None)
                        self._processed.discard(stale)
                        self._skipped_large.discard(stale)

                for path in current_files:
                    # Skip if already processed in this watcher session
                    if path in self._processed:
                        continue

                    # Skip files that were created before the watch started
                    if not self._is_file_created_after_watch_start(path):
                        continue

                    try:
                        size = path.stat().st_size
                    except FileNotFoundError:
                        continue

                    # Enforce max file size
                    if size > self.max_bytes:
                        if path not in self._skipped_large:
                            self.logger.warning(
                                f"Skipping {path.name}: size {size/1024/1024:.1f} MB exceeds limit "
                                f"{self.max_bytes/1024/1024:.0f} MB"
                            )
                            self._skipped_large.add(path)
                        continue

                    # Wait until file has been stable for configured seconds
                    stable_elapsed = self._update_size_state(path, size, now_mono)
                    if stable_elapsed < self.stable_seconds:
                        # still growing or within stability window
                        continue

                    # File is stable - trigger processing
                    try:
                        self.logger.info(f"Detected stable file: {path.name} ({size/1024/1024:.1f} MB) - starting processing")
                        processed_count, skipped_count = processor.run_batch(
                            [path], effective_reprocess, transcriber, output_folder,
                            llm_generator, llm_modes, calendar_linker
                        )
                        # Mark as processed regardless of processed/skipped to avoid repeated attempts
                        self._processed.add(path)
                        self.logger.info(
                            f"Completed handling {path.name}: processed={processed_count}, skipped={skipped_count}"
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to handle {path.name}: {e}")
                        # Avoid tight loop reprocessing on error; mark as processed to prevent hammering
                        self._processed.add(path)

                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self.logger.info("Directory watcher stopped by user (Ctrl+C)")
