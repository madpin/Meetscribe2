"""
Meetscribe: Audio to Notes CLI

This module provides the command-line interface for Meetscribe, a tool to
automatically convert audio recordings of meetings into structured notes.
"""

import sys
from typing import Optional

import typer
from rich.table import Table
from rich.console import Console

from app.core.context import AppContext
from app.core.exceptions import ConfigurationError, TranscriptionError, GoogleCalendarError
from app.services.file_processor import FileProcessor
from app.ui import interactive_select_files
from app.transcriber import Transcriber
from app.integrations.google_calendar import GoogleCalendarClient

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

calendar_app = typer.Typer(name="calendar", help="Google Calendar commands.")
app.add_typer(calendar_app)




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

    # Initialize services
    processor = FileProcessor(ctx.config, ctx.logger)
    transcriber = Transcriber(ctx.config.deepgram, ctx.logger)

    # Resolve input folder
    input_dir = processor.resolve_input_folder(audio_directory)
    if not input_dir.is_dir():
        ctx.logger.error(f"The provided path is not a directory: {input_dir}")
        raise typer.Exit(code=1)

    # Discover and sort audio files
    files = processor.discover_audio_files(input_dir)
    if not files:
        ctx.logger.warning(f"No supported audio files found in {input_dir}")
        return

    # Resolve output folder
    output_folder = processor.resolve_output_folder()

    # Determine effective reprocess behavior
    effective_reprocess = reprocess if reprocess is not None else ctx.config.processing.reprocess

    # Determine if we should use select mode
    use_select_mode = select_file

    if not select_file:
        # Get candidate files respecting reprocess setting
        candidates = processor.get_files_to_process(files, effective_reprocess, output_folder)

        # Check limits
        dec = processor.should_use_select_mode(len(candidates))
        if dec is True:
            # Hard limit exceeded - auto enter select mode
            use_select_mode = True
        elif dec is None:
            # Soft limit exceeded - ask user
            if typer.confirm(f"Process all {len(candidates)} files or enter selection mode?", default=False):
                ctx.logger.info("Proceeding with batch processing...")
                use_select_mode = False
            else:
                ctx.logger.info("Entering interactive selection mode...")
                use_select_mode = True
        else:
            # No limit issues
            use_select_mode = False

    if use_select_mode:
        # Interactive selection mode
        selected = interactive_select_files(
            files, output_folder, ctx.config.ui.selection_page_size, ctx.logger
        )
        if selected is None:
            ctx.logger.info("Selection cancelled")
            return

        # Process selected files with reprocess=True (since user chose them)
        processed_count, skipped_count = processor.run_batch(
            selected, True, transcriber, output_folder
        )

        ctx.logger.info(f"Selection summary: Processed={processed_count}, Skipped={skipped_count}, Total selected={len(selected)}")
    else:
        # Batch processing mode
        candidates = processor.get_files_to_process(files, effective_reprocess, output_folder)
        processed_count, skipped_count = processor.run_batch(
            candidates, effective_reprocess, transcriber, output_folder
        )

        ctx.logger.info(f"Summary: Processed={processed_count}, Skipped={skipped_count}, Total candidates={len(candidates)}")


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
    from app.core.utils import format_file_size, get_audio_duration, format_duration, format_time_ago
    from datetime import datetime

    console = Console()

    # Initialize processor
    processor = FileProcessor(ctx.config, ctx.logger)

    # Resolve input folder
    input_dir = processor.resolve_input_folder(audio_directory)
    if not input_dir.is_dir():
        ctx.logger.error(f"The provided path is not a directory: {input_dir}")
        raise typer.Exit(code=1)

    # Discover and sort audio files
    audio_files = processor.discover_audio_files(input_dir)
    if not audio_files:
        ctx.logger.warning(f"No supported audio files found in {input_dir}")
        return

    # Create table
    table = Table(title=f"Audio Files in {input_dir}")
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
    from app.transcriber import SUPPORTED_EXTENSIONS

    if audio_file is None:
        ctx.logger.error("No audio file provided. Please specify a file path or set a default in config.")
        raise typer.Exit(code=1)

    # Initialize services
    processor = FileProcessor(ctx.config, ctx.logger)
    transcriber = Transcriber(ctx.config.deepgram, ctx.logger)

    # Resolve input folder
    input_folder = processor.resolve_input_folder(None)

    # Resolve audio file path
    from pathlib import Path
    audio_path = Path(audio_file)
    if not audio_path.is_absolute():
        audio_path = input_folder / audio_path

    if not audio_path.is_file():
        ctx.logger.error(f"The provided path is not a file: {audio_path}")
        raise typer.Exit(code=1)

    if audio_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        ctx.logger.error(f"Unsupported file extension: {audio_path.suffix}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
        raise typer.Exit(code=1)

    # Resolve output folder
    output_folder = processor.resolve_output_folder()

    # Determine effective reprocess behavior
    effective_reprocess = reprocess if reprocess is not None else ctx.config.processing.reprocess

    try:
        # Process single file
        processed_count, skipped_count = processor.run_batch(
            [audio_path], effective_reprocess, transcriber, output_folder
        )

        if skipped_count > 0:
            ctx.logger.info(f"File was skipped (already exists)")
        else:
            ctx.logger.info(f"File processed successfully")

    except TranscriptionError as e:
        ctx.logger.error(f"Transcription failed: {e}")
        raise typer.Exit(code=1)


def _truncate_description(description: str, max_length: int = 80) -> str:
    """Truncate description to max_length with ellipsis if needed."""
    if len(description) <= max_length:
        return description
    return description[:max_length - 3] + "…"


def _truncate_attendees(attendees: list, max_count: int = 5) -> str:
    """Truncate attendee list to max_count with summary if needed."""
    if not attendees:
        return "-"
    if len(attendees) <= max_count:
        return ", ".join(attendees)
    remaining = len(attendees) - max_count
    return f"{', '.join(attendees[:max_count])} +{remaining} more"


def _truncate_attachments(attachments: list, max_count: int = 3) -> str:
    """Truncate attachment list to max_count with summary if needed."""
    if not attachments:
        return "-"
    if len(attachments) <= max_count:
        return ", ".join(attachments)
    remaining = len(attachments) - max_count
    return f"{', '.join(attachments[:max_count])} +{remaining} more"


@calendar_app.command("past")
def calendar_past(
    days: Optional[int] = typer.Option(None, "--days", "-d", help="Number of past days to list (defaults to config)."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of events (defaults to config)."),
    calendar_id: Optional[str] = typer.Option(None, "--calendar-id", help="Calendar ID (defaults to config)."),
    group_only: Optional[bool] = typer.Option(None, "--group-only/--no-group-only", help="Only show events with 2 or more attendees (defaults to config)."),
):
    """
    List past Google Calendar events with attendees, description, and attachment names.
    """
    ctx = get_app_context()
    console = Console()

    ctx.logger.info(f"Listing past calendar events with parameters: days={days}, limit={limit}, calendar_id={calendar_id}, group_only={group_only}")

    try:
        # Initialize Google Calendar client with new signature
        client = GoogleCalendarClient(ctx.config.google, ctx.logger)
        events = client.list_past_events(
            days=days,
            limit=limit,
            calendar_id=calendar_id,
            filter_group_events=group_only
        )

        if not events:
            console.print("[yellow]No past events found for the specified time range.[/yellow]")
            return

        # Create table
        table = Table(title=f"Past Calendar Events")
        table.add_column("Start (Local)", style="cyan", justify="left")
        table.add_column("Title", style="green")
        table.add_column("Attendees", style="yellow")
        table.add_column("Description", style="blue")
        table.add_column("Attachments", style="magenta")

        # Add rows
        for event in events:
            start_str = GoogleCalendarClient.parse_event_start_local(event)
            title = event.get('summary', '-')
            attendees = GoogleCalendarClient.extract_attendee_names(event)
            attendees_str = _truncate_attendees(attendees)
            description = _truncate_description(event.get('description', '-'))
            attachments = GoogleCalendarClient.extract_attachment_titles(event)
            attachments_str = _truncate_attachments(attachments)

            table.add_row(start_str, title, attendees_str, description, attachments_str)

        console.print(table)

    except GoogleCalendarError as e:
        ctx.logger.error(f"Failed to list calendar events: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
