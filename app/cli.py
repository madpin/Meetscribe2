"""
Meetscribe: Audio to Notes CLI

This module provides the command-line interface for Meetscribe, a tool to
automatically convert audio recordings of meetings into structured notes.
"""

import sys
from typing import Optional
from pathlib import Path

import typer
from rich.table import Table
from rich.console import Console
from rich.live import Live

from app.core.context import AppContext
from app.core.exceptions import ConfigurationError

# Global AppContext instance - will be initialized on first use
_app_context: Optional[AppContext] = None


def get_app_context() -> AppContext:
    """Get or create the global application context."""
    global _app_context
    if _app_context is None:
        try:
            _app_context = AppContext()
        except ConfigurationError as e:
            print(f"Configuration error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to initialize application: {e}")
            sys.exit(1)
    return _app_context


app = typer.Typer(
    name="meetscribe",
    help="A tool to automatically convert audio recordings of meetings into structured, actionable notes.",
    no_args_is_help=True,
)

process_app = typer.Typer(name="process", help="Process audio files.")
app.add_typer(process_app)


def interactive_select_file(files: list, output_folder: Path) -> Optional[list]:
    """
    Interactive file selection with arrow keys and space bar.

    Returns a list of selected file paths, or None if cancelled.
    Supports multiple file selection with space bar.
    """
    from app.core.utils import format_file_size, get_audio_duration, format_duration, format_time_ago
    from datetime import datetime
    from math import ceil

    ctx = get_app_context()
    if not files:
        return None

    console = Console()

    # Read page size from config
    page_size = ctx.config.get("ui", {}).get("selection_page_size", 10)

    # Pagination state
    current_page = 0
    total_pages = ceil(len(files) / page_size)
    current_index = 0  # Index within current page

    # Track selected files by path (persists across pages)
    selected_paths = set()

    # Cache for metadata to avoid recomputing
    metadata_cache = {}

    # Sort files by last modified (newest first)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    def get_file_info(file_path: Path):
        """Get cached file info, computing duration lazily."""
        if file_path not in metadata_cache:
            stat = file_path.stat()
            modified_dt = datetime.fromtimestamp(stat.st_mtime)
            modified_str = f"{modified_dt.strftime('%Y-%m-%d %H:%M')} ({format_time_ago(modified_dt)})"
            size_str = format_file_size(stat.st_size)

            # Compute duration lazily (expensive operation)
            duration = get_audio_duration(file_path)
            duration_str = format_duration(duration)

            # Check if file has been processed
            output_file = output_folder / f"{file_path.stem}.txt"
            processed = output_file.exists()

            metadata_cache[file_path] = {
                'path': file_path,
                'name': file_path.name,
                'modified_str': modified_str,
                'size_str': size_str,
                'duration_str': duration_str,
                'processed': processed
            }

        return metadata_cache[file_path]

    def get_current_page_files():
        """Get files for current page."""
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(files))
        return files[start_idx:end_idx]

    with Live(console=console, refresh_per_second=10, auto_refresh=False) as live:
        while True:
            # Get current page files and build info
            current_page_files = get_current_page_files()
            file_infos = [get_file_info(f) for f in current_page_files]

            # Create table
            selected_count = len(selected_paths)
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(files))
            title = f"Page {current_page + 1}/{total_pages} — Showing {start_idx + 1}-{end_idx} of {len(files)} — Select with ↑↓/Space, ←→ pages, Enter confirm, Esc/q cancel ({selected_count} selected)"
            table = Table(title=title, title_style="bold blue")
            table.add_column("Sel", style="red", justify="center", width=3)
            table.add_column("Done", style="bright_green", justify="center", width=5)
            table.add_column("Filename", style="green")
            table.add_column("Modified", style="yellow")
            table.add_column("Size", style="magenta", justify="right")
            table.add_column("Duration", style="blue", justify="center")

            # Add rows for current page
            for i, info in enumerate(file_infos):
                sel_marker = "*" if info['path'] in selected_paths else ""
                processed_marker = "✓" if info['processed'] else "-"
                style = "black on cyan" if i == current_index else None
                table.add_row(sel_marker, processed_marker, info['name'], info['modified_str'], info['size_str'], info['duration_str'], style=style)

            live.update(table)
            live.refresh()

            # Get key press
            try:
                from readchar import readkey, key as rkey
                k = readkey()
            except ImportError:
                console.print("[red]readchar not installed. Install with: pip install readchar[/red]")
                return None

            # Handle keys
            if k == rkey.UP:
                current_index = (current_index - 1) % len(current_page_files)
            elif k == rkey.DOWN:
                current_index = (current_index + 1) % len(current_page_files)
            elif k == rkey.LEFT:
                # Previous page
                current_page = (current_page - 1) % total_pages
                current_index = 0
            elif k == rkey.RIGHT:
                # Next page
                current_page = (current_page + 1) % total_pages
                current_index = 0
            elif k == rkey.SPACE:
                # Toggle selection for current file
                current_file = current_page_files[current_index]
                if current_file in selected_paths:
                    selected_paths.remove(current_file)
                else:
                    selected_paths.add(current_file)
            elif k in (rkey.ENTER, rkey.CR):
                # Return selected files, or current file if none selected
                if selected_paths:
                    return list(selected_paths)
                else:
                    return [current_page_files[current_index]]
            elif k in (rkey.ESC, 'q', 'Q'):
                return None


@process_app.command("dir")
def process_directory(
    audio_directory: Optional[str] = typer.Argument(
        None, help="The directory containing audio files to process. Uses config input_folder if not provided."
    ),
    reprocess: Optional[bool] = typer.Option(
        None,
        "--reprocess",
        help="Reprocess files even if the output .txt already exists (overwrite).",
    ),
    select_file: bool = typer.Option(
        False,
        "--select",
        help="Interactively choose multiple files with arrows/space/enter.",
    ),
):
    """
    Process all audio files in a directory and generate meeting notes.
    Use --select for interactive multiple-file selection.
    """
    ctx = get_app_context()
    from app.transcriber import Transcriber, SUPPORTED_EXTENSIONS
    from pathlib import Path

    transcriber = Transcriber(ctx)

    # Use input folder from config if no directory provided
    if audio_directory is None:
        input_folder_str = ctx.config.get("paths", {}).get(
            "input_folder", "~/Audio"
        )
        audio_path = Path(input_folder_str).expanduser()
    else:
        audio_path = Path(audio_directory)

    if not audio_path.is_dir():
        ctx.logger.error(f"The provided path is not a directory: {audio_path}")
        raise typer.Exit(code=1)

    audio_files = [
        p for p in audio_path.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    audio_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    if not audio_files:
        ctx.logger.warning(f"No supported audio files found in {audio_path}")
        return

    output_folder_str = ctx.config.get("paths", {}).get(
        "output_folder", "~/Documents/Meetscribe"
    )
    output_folder = Path(output_folder_str).expanduser()
    output_folder.mkdir(parents=True, exist_ok=True)

    # Determine effective reprocess behavior
    effective_reprocess = reprocess if reprocess is not None else bool(
        ctx.config.get("processing", {}).get("reprocess", False)
    )

    # Determine if we should use select mode (either explicitly requested or due to limits)
    use_select_mode = select_file

    if not select_file:
        # Read limits from config
        soft_limit = int(ctx.config.get("processing", {}).get("soft_limit_files", 10))
        hard_limit = int(ctx.config.get("processing", {}).get("hard_limit_files", 25))

        # Build candidate files (respecting reprocess setting)
        candidate_files = []
        for audio_file in audio_files:
            output_file = output_folder / f"{audio_file.stem}.txt"
            if not effective_reprocess and output_file.exists():
                # Skip existing outputs when not reprocessing
                continue
            candidate_files.append(audio_file)

        # Check hard limit - auto enter select mode
        if len(candidate_files) > hard_limit:
            ctx.logger.warning(f"Found {len(candidate_files)} files (exceeds hard limit of {hard_limit})")
            ctx.logger.warning("Automatically entering interactive selection mode...")
            use_select_mode = True

        # Check soft limit and offer select mode option
        elif len(candidate_files) > soft_limit:
            ctx.logger.warning(f"Found {len(candidate_files)} files (exceeds soft limit of {soft_limit})")
            if typer.confirm(f"Process all {len(candidate_files)} files or enter selection mode?", default=False):
                ctx.logger.info("Proceeding with batch processing...")
                use_select_mode = False
            else:
                ctx.logger.info("Entering interactive selection mode...")
                use_select_mode = True

    if use_select_mode:
        # Interactive selection mode - default to reprocess=True unless explicitly set to False
        effective_reprocess_select = True if reprocess is None else reprocess

        # Interactive selection mode
        chosen_files = interactive_select_file(audio_files, output_folder)
        if chosen_files is None:
            ctx.logger.info("Selection cancelled")
            return

        # Process the selected files
        processed_count = 0
        skipped_count = 0

        for chosen_file in chosen_files:
            output_file = output_folder / f"{chosen_file.stem}.txt"
            if not effective_reprocess_select and output_file.exists():
                ctx.logger.info(f"Skipping {chosen_file.name}: {output_file} already exists")
                skipped_count += 1
                continue

            ctx.logger.info(f"Processing {chosen_file.name}...")
            notes = transcriber.process_audio_file(chosen_file)
            with open(output_file, "w") as f:
                f.write(notes)
            ctx.logger.info(f"Notes saved to {output_file}")
            processed_count += 1

        # Print summary
        total_selected = len(chosen_files)
        ctx.logger.info(f"Selection summary: Processed={processed_count}, Skipped={skipped_count}, Total selected={total_selected}")
    else:
        # Batch processing mode
        # Read limits from config (if not already read above)
        if 'candidate_files' not in locals():
            soft_limit = int(ctx.config.get("processing", {}).get("soft_limit_files", 10))
            hard_limit = int(ctx.config.get("processing", {}).get("hard_limit_files", 25))

            # Build candidate files (respecting reprocess setting)
            candidate_files = []
            for audio_file in audio_files:
                output_file = output_folder / f"{audio_file.stem}.txt"
                if not effective_reprocess and output_file.exists():
                    # Skip existing outputs when not reprocessing
                    continue
                candidate_files.append(audio_file)

        # Initialize counters
        processed_count = 0
        skipped_count = 0

        for audio_file in candidate_files:
            output_file = output_folder / f"{audio_file.stem}.txt"
            if not effective_reprocess and output_file.exists():
                ctx.logger.info(f"Skipping {audio_file.name}: {output_file} already exists")
                skipped_count += 1
                continue

            ctx.logger.info(f"Processing {audio_file.name}...")
            notes = transcriber.process_audio_file(audio_file)
            with open(output_file, "w") as f:
                f.write(notes)
            ctx.logger.info(f"Notes saved to {output_file}")
            processed_count += 1

        # Print summary
        total_candidates = len(candidate_files)
        msg = f"Summary: Processed={processed_count}, Skipped={skipped_count}, Total candidates={total_candidates}"
        ctx.logger.info(msg)


@process_app.command("list")
def process_list(
    audio_directory: Optional[str] = typer.Argument(
        None, help="The directory containing audio files to list. Uses config input_folder if not provided."
    ),
):
    """
    List all supported audio files in a directory with metadata.
    """
    ctx = get_app_context()
    from app.transcriber import SUPPORTED_EXTENSIONS
    from app.core.utils import format_file_size, get_audio_duration, format_duration, format_time_ago
    from pathlib import Path
    from datetime import datetime

    console = Console()

    # Use input folder from config if no directory provided
    if audio_directory is None:
        input_folder_str = ctx.config.get("paths", {}).get(
            "input_folder", "~/Audio"
        )
        audio_path = Path(input_folder_str).expanduser()
    else:
        audio_path = Path(audio_directory)

    if not audio_path.is_dir():
        ctx.logger.error(f"The provided path is not a directory: {audio_path}")
        raise typer.Exit(code=1)

    audio_files = [
        p for p in audio_path.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    audio_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    if not audio_files:
        ctx.logger.warning(f"No supported audio files found in {audio_path}")
        return

    # Create table
    table = Table(title=f"Audio Files in {audio_path}")
    table.add_column("No.", style="cyan", justify="right")
    table.add_column("Filename", style="green")
    table.add_column("Modified", style="yellow")
    table.add_column("Size", style="magenta", justify="right")
    table.add_column("Duration", style="blue", justify="center")

    # Add rows
    for i, audio_file in enumerate(audio_files, 1):
        stat = audio_file.stat()
        modified_dt = datetime.fromtimestamp(stat.st_mtime)
        modified_str = f"{modified_dt.strftime('%Y-%m-%d %H:%M')} ({format_time_ago(modified_dt)})"
        size_str = format_file_size(stat.st_size)
        duration = get_audio_duration(audio_file)
        duration_str = format_duration(duration)

        table.add_row(str(i), audio_file.name, modified_str, size_str, duration_str)

    console.print(table)


@process_app.command("file")
def process_file(
    audio_file: Optional[str] = typer.Argument(
        None, help="The audio file to process. Can be absolute path or relative to config input_folder."
    ),
    reprocess: Optional[bool] = typer.Option(
        None,
        "--reprocess",
        help="Reprocess the file even if the output .txt already exists (overwrite).",
    ),
):
    """
    Process a single audio file and generate meeting notes.
    """
    ctx = get_app_context()
    from app.transcriber import Transcriber, SUPPORTED_EXTENSIONS
    from pathlib import Path

    # Use input folder from config as base directory for relative paths
    input_folder_str = ctx.config.get("paths", {}).get(
        "input_folder", "~/Audio"
    )
    input_folder = Path(input_folder_str).expanduser()

    if audio_file is None:
        ctx.logger.error("No audio file provided. Please specify a file path or set a default in config.")
        raise typer.Exit(code=1)

    audio_path = Path(audio_file)

    # If path is relative, resolve it relative to input folder
    if not audio_path.is_absolute():
        audio_path = input_folder / audio_path

    if not audio_path.is_file():
        ctx.logger.error(f"The provided path is not a file: {audio_path}")
        raise typer.Exit(code=1)

    if audio_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        ctx.logger.error(f"Unsupported file extension: {audio_path.suffix}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
        raise typer.Exit(code=1)

    transcriber = Transcriber(ctx)

    output_folder_str = ctx.config.get("paths", {}).get(
        "output_folder", "~/Documents/Meetscribe"
    )
    output_folder = Path(output_folder_str).expanduser()
    output_folder.mkdir(parents=True, exist_ok=True)

    # Determine effective reprocess behavior
    effective_reprocess = reprocess if reprocess is not None else bool(
        ctx.config.get("processing", {}).get("reprocess", False)
    )

    output_file = output_folder / f"{audio_path.stem}.txt"
    if not effective_reprocess and output_file.exists():
        ctx.logger.info(f"Skipping {audio_path.name}: {output_file} already exists")
        return

    ctx.logger.info(f"Processing {audio_path.name}...")
    notes = transcriber.process_audio_file(audio_path)
    with open(output_file, "w") as f:
        f.write(notes)
    ctx.logger.info(f"Notes saved to {output_file}")


if __name__ == "__main__":
    app()
