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

from app.integrations.google_calendar import GoogleCalendarClient
from app.core.utils import truncate_attendees, truncate_attachments


def interactive_select_files(
    files: List[Path],
    output_folder: Path,
    page_size: int,
    logger,
    note_keys: dict[str, str],
    initial_modes: Optional[set[str]] = None,
    llm_output_map: Optional[dict[str, Path]] = None,
    output_extension: str = "txt"
) -> Optional[tuple[list[Path], dict[Path, set[str]]]]:
    """
    Interactive file selection with arrow keys, space bar, and per-file Q/W/E mode toggling.

    Args:
        files: List of file paths to select from
        output_folder: Output folder path for checking processed status
        page_size: Number of files to show per page
        logger: Logger instance
        note_keys: Dictionary mapping mode letters to key strings (e.g., {'q': 'Q', 'w': 'W', 'e': 'E'})
        initial_modes: Initial set of active modes for all files, defaults to all modes if None
        llm_output_map: Optional mapping of mode to output folder (e.g., {'Q': Path, 'W': Path, 'E': Path})
        output_extension: File extension for output files (without leading dot)

    Returns:
        Tuple of (selected_files, file_modes_dict), or None if cancelled.
        file_modes_dict maps each file to its set of active modes.
        Supports multiple file selection with space bar and per-file mode toggling with Q/W/E keys.
        Shows tri-state indicators: ✓ processed, o queued to process, - not selected.
    """
    from app.core.utils import format_file_size, get_audio_duration, format_duration, format_time_ago
    from datetime import datetime

    if not files:
        return None

    console = Console()

    # Compute extension with leading dot
    dot_ext = f".{output_extension.lstrip('.')}"

    # Pagination state
    current_page = 0
    total_pages = ceil(len(files) / page_size)
    current_index = 0  # Index within current page

    # Track selected files by path (persists across pages)
    selected_paths = set()

    # Mode toggling state - per-file modes (dict[file_path, set[modes]])
    logger.debug(f"UI note_keys = {note_keys}")
    file_modes = {}

    # Initialize modes for all files
    # Ensure consistent case: use lowercase keys for internal storage
    if initial_modes is not None:
        # Convert uppercase modes from CLI to lowercase for internal use
        default_modes = {mode.lower() for mode in initial_modes}
    else:
        # Default to none selected
        default_modes = set()

    logger.debug(f"UI initial_modes = {initial_modes}")
    logger.debug(f"UI default_modes = {default_modes}")
    for file_path in files:
        file_modes[file_path] = default_modes.copy()
        logger.debug(f"UI {file_path.name} initialized with modes: {file_modes[file_path]}")

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
            output_file = output_folder / f"{file_path.stem}{dot_ext}"
            processed = output_file.exists()

            # Get mode status for this file
            modes_status = {}
            processed_modes = {}
            for mode in sorted(note_keys.keys()):
                modes_status[mode] = mode in file_modes[file_path]

                # Check if LLM output file exists for this mode
                if llm_output_map:
                    mode_upper = note_keys[mode]  # e.g., 'Q', 'W', 'E'
                    if mode_upper in llm_output_map:
                        llm_output_file = llm_output_map[mode_upper] / f"{file_path.stem}.{mode_upper}{dot_ext}"
                        processed_modes[mode] = llm_output_file.exists()
                    else:
                        processed_modes[mode] = False
                else:
                    processed_modes[mode] = False

            metadata_cache[file_path] = {
                'path': file_path,
                'name': file_path.name,
                'modified_str': modified_str,
                'size_str': size_str,
                'duration_str': duration_str,
                'processed': processed,
                'modes': modes_status,
                'processed_modes': processed_modes
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

            # Build title without global mode status (now per-file)
            title = f"Page {current_page + 1}/{total_pages} — Showing {start_idx + 1}-{end_idx} of {len(files)} — ↑↓/Space select, Q/W/E toggle current file, ←→ pages, Enter confirm, Esc cancel ({selected_count} selected) — ✓ processed, o queued, - off"
            table = Table(title=title, title_style="bold blue")
            table.add_column("Sel", style="red", justify="center", width=3)
            table.add_column("Done", style="bright_green", justify="center", width=5)
            table.add_column("Q", style="cyan", justify="center", width=3)
            table.add_column("W", style="cyan", justify="center", width=3)
            table.add_column("E", style="cyan", justify="center", width=3)
            table.add_column("Filename", style="green")
            table.add_column("Modified", style="yellow")
            table.add_column("Size", style="magenta", justify="right")
            table.add_column("Duration", style="blue", justify="center")

            # Add rows for current page
            for i, info in enumerate(file_infos):
                sel_marker = "*" if info['path'] in selected_paths else ""
                processed_marker = "✓" if info['processed'] else "-"

                # Mode status indicators - tri-state: ✓ processed, o queued, - off
                def get_mode_marker(mode_key: str) -> str:
                    if info['processed_modes'].get(mode_key, False):
                        return "✓"  # processed
                    elif info['modes'].get(mode_key, False):
                        return "o"  # queued to process
                    else:
                        return "-"  # not selected

                q_marker = get_mode_marker('q')
                w_marker = get_mode_marker('w')
                e_marker = get_mode_marker('e')

                style = "black on cyan" if i == current_index else None
                table.add_row(sel_marker, processed_marker, q_marker, w_marker, e_marker, info['name'], info['modified_str'], info['size_str'], info['duration_str'], style=style)

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
                # Return selected files with their individual mode configurations
                if selected_paths:
                    # Build result with per-file mode configurations
                    result_files = list(selected_paths)
                    # Convert lowercase modes back to uppercase for CLI compatibility
                    result_modes = {file: {mode.upper() for mode in file_modes[file]} for file in result_files}
                    # Debug logging for selected files
                    for file in result_files:
                        modes = result_modes[file]
                        logger.debug(f"UI selected: {file.name} -> modes: {''.join(sorted(modes)) if modes else 'None'}")
                    return result_files, result_modes
                else:
                    # No files explicitly selected - return the highlighted file with its current modes (may be empty)
                    current_file = current_page_files[current_index]
                    modes = file_modes[current_file]
                    # Convert lowercase modes back to uppercase for CLI compatibility
                    uppercase_modes = {mode.upper() for mode in modes}
                    logger.debug(f"UI current: {current_file.name} -> modes: {''.join(sorted(uppercase_modes)) if uppercase_modes else 'None'}")
                    return [current_file], {current_file: uppercase_modes}
            elif k in (rkey.ESC,):
                return None
            elif k.upper() in note_keys.values():
                # Toggle mode for the current file
                pressed_key = k.upper()
                current_file = current_page_files[current_index]

                for mode, key in note_keys.items():
                    if key == pressed_key:
                        old_modes = file_modes[current_file].copy()
                        if mode in file_modes[current_file]:
                            file_modes[current_file].remove(mode)
                            logger.debug(f"UI removed {mode} from {current_file.name}")
                        else:
                            file_modes[current_file].add(mode)
                            logger.debug(f"UI added {mode} to {current_file.name}")

                        logger.debug(f"UI {current_file.name} modes changed from {old_modes} to {file_modes[current_file]}")

                        # Update cache to reflect the change
                        if current_file in metadata_cache:
                            metadata_cache[current_file]['modes'][mode] = mode in file_modes[current_file]
                        break


def interactive_select_events(events: list[dict], page_size: int, logger, reload_callback=None, start_date=None, end_date=None) -> Optional[tuple[list[dict], dict]]:
    """
    Interactive event selection with arrow keys and space bar.

    Similar to interactive_select_files but for Google Calendar events.
    Displays events in a table format with pagination support.
    Supports date range navigation with 'P' key for previous day.

    Args:
        events: List of event dictionaries from Google Calendar API
        page_size: Number of events to show per page
        logger: Logger instance
        reload_callback: Optional callback function to reload events for different date range.
                        Should accept (start_date, end_date) and return (events, new_start, new_end)
        start_date: Current start date for the range
        end_date: Current end date for the range

    Returns:
        Tuple of (selected_events, date_info), or None if cancelled.
        selected_events: List of selected events
        date_info: Dict with 'start_date', 'end_date', 'navigated' (True if user used navigation)
        Supports single event selection (current) or multiple selection with space bar.
    """
    if not events:
        return None

    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from math import ceil

    console = Console()

    # Navigation state
    navigated = False
    current_start_date = start_date
    current_end_date = end_date

    # Pagination state
    current_page = 0
    total_pages = ceil(len(events) / page_size)
    current_index = 0  # Index within current page

    # Track selected events by index in original list
    selected_indices = set()

    # Cache for event info to avoid recomputing
    event_cache = {}

    def get_event_info(event: dict):
        """Get cached event info, computing metadata lazily."""
        event_id = id(event)
        if event_id not in event_cache:
            start_str = GoogleCalendarClient.parse_event_start_local(event)
            title = event.get('summary', '-')
            attendees = GoogleCalendarClient.extract_attendee_names(event)
            attendees_str = truncate_attendees(attendees)
            attachments = GoogleCalendarClient.extract_attachment_titles(event)
            attachments_str = truncate_attachments(attachments)

            event_cache[event_id] = {
                'start_str': start_str,
                'title': title,
                'attendees_str': attendees_str,
                'attachments_str': attachments_str
            }

        return event_cache[event_id]

    def get_current_page_events():
        """Get events for current page."""
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(events))
        return events[start_idx:end_idx]

    with Live(console=console, refresh_per_second=10, auto_refresh=False) as live:
        while True:
            # Get current page events and build info
            current_page_events = get_current_page_events()
            event_infos = [get_event_info(event) for event in current_page_events]

            # Create table
            selected_count = len(selected_indices)
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(events))

            # Build title with date range info if available
            date_info = ""
            if current_start_date and current_end_date:
                start_str = current_start_date.strftime("%Y-%m-%d")
                end_str = current_end_date.strftime("%Y-%m-%d")
                date_info = f" ({start_str} to {end_str})"

            nav_info = "P previous day, " if reload_callback else ""
            title = f"Page {current_page + 1}/{total_pages} — Showing {start_idx + 1}-{end_idx} of {len(events)}{date_info} — ↑↓/Space select, ←→ pages, {nav_info}Enter confirm, Esc cancel ({selected_count} selected)"
            table = Table(title=title, title_style="bold blue")
            table.add_column("Sel", style="red", justify="center", width=3)
            table.add_column("Start (Local)", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("Attendees", style="yellow")
            table.add_column("Attachments", style="magenta")

            # Add rows for current page
            for i, info in enumerate(event_infos):
                global_index = start_idx + i
                sel_marker = "*" if global_index in selected_indices else ""
                style = "black on cyan" if i == current_index else None
                table.add_row(sel_marker, info['start_str'], info['title'], info['attendees_str'], info['attachments_str'], style=style)

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
                current_index = (current_index - 1) % len(current_page_events)
            elif k == rkey.DOWN:
                current_index = (current_index + 1) % len(current_page_events)
            elif k == rkey.LEFT:
                # Previous page
                current_page = (current_page - 1) % total_pages
                current_index = 0
            elif k == rkey.RIGHT:
                # Next page
                current_page = (current_page + 1) % total_pages
                current_index = 0
            elif k.upper() == 'P' and reload_callback and current_start_date:
                # Previous day navigation
                from datetime import timedelta
                new_start_date = current_start_date - timedelta(days=1)
                new_end_date = current_end_date - timedelta(days=1) if current_end_date else new_start_date + timedelta(days=1)

                logger.info(f"Loading previous day: {new_start_date.strftime('%Y-%m-%d')} to {new_end_date.strftime('%Y-%m-%d')}")

                # Call the reload callback
                try:
                    new_events, actual_start, actual_end = reload_callback(new_start_date, new_end_date)

                    if new_events:
                        # Update state with new events
                        events[:] = new_events  # Replace the events list
                        current_start_date = actual_start
                        current_end_date = actual_end
                        navigated = True

                        # Reset pagination and selection
                        current_page = 0
                        current_index = 0
                        selected_indices.clear()
                        total_pages = ceil(len(events) / page_size)
                        event_cache.clear()  # Clear cache for new events

                        logger.info(f"Loaded {len(new_events)} events for previous day")
                    else:
                        logger.info("No events found for previous day")
                except Exception as e:
                    logger.error(f"Failed to load previous day events: {e}")

                # Refresh the display
                continue
            elif k == rkey.SPACE:
                # Toggle selection for current event
                global_index = start_idx + current_index
                if global_index in selected_indices:
                    selected_indices.remove(global_index)
                else:
                    selected_indices.add(global_index)
            elif k in (rkey.ENTER, rkey.CR):
                # Return selected events with date info
                if selected_indices:
                    selected_events = [events[i] for i in selected_indices]
                    logger.debug(f"UI selected {len(selected_events)} events")
                    date_info = {
                        'start_date': current_start_date,
                        'end_date': current_end_date,
                        'navigated': navigated
                    }
                    return selected_events, date_info
                else:
                    # No events explicitly selected - return the highlighted event
                    current_event = current_page_events[current_index]
                    logger.debug(f"UI current event: {current_event.get('summary', 'Unknown')}")
                    date_info = {
                        'start_date': current_start_date,
                        'end_date': current_end_date,
                        'navigated': navigated
                    }
                    return [current_event], date_info
            elif k in (rkey.ESC,):
                return None
