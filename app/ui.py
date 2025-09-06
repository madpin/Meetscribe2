"""
Interactive UI components for Meetscribe.

This module provides interactive user interface components for file selection
and other interactive operations.
"""

from pathlib import Path
from typing import List, Optional
from math import ceil

from rich.console import Console
from rich.live import Live
from rich.table import Table


def interactive_select_files(
    files: List[Path],
    output_folder: Path,
    page_size: int,
    logger
) -> Optional[List[Path]]:
    """
    Interactive file selection with arrow keys and space bar.

    Args:
        files: List of file paths to select from
        output_folder: Output folder path for checking processed status
        page_size: Number of files to show per page
        logger: Logger instance

    Returns:
        List of selected file paths, or None if cancelled.
        Supports multiple file selection with space bar.
    """
    from app.core.utils import format_file_size, get_audio_duration, format_duration, format_time_ago
    from datetime import datetime

    if not files:
        return None

    console = Console()

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
