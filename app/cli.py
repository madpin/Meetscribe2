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
from app.services.llm_notes import LLMNotesGenerator
from app.services.calendar_linker import CalendarLinker
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
        help="Reprocess files: regenerate LLM notes from existing transcriptions, or run full transcription if none exists.",
    ),
    select_file: bool = typer.Option(
        False,
        "--select",
        help="Interactively choose multiple files with arrows/space/enter and Q/W/E mode toggling.",
    ),
    llm_enabled: Optional[bool] = typer.Option(
        None,
        "--llm/--no-llm",
        help="Enable/disable LLM post-processing (defaults to config).",
    ),
    notes: Optional[str] = typer.Option(
        None,
        "--notes",
        "-n",
        help="LLM notes to generate: any combination of Q, W, E. Example: QWE or QW.",
    ),
    link_calendar: bool = typer.Option(
        False,
        "--link-calendar",
        help="Auto-link files to closest calendar event and rename outputs to YYYY-MM-DD_Title; include event metadata in notes.",
    ),
    select_calendar_event: bool = typer.Option(
        False,
        "--select-calendar-event",
        help="When used with --link-calendar, interactively select which calendar event to link to instead of auto-matching.",
    ),
):
    """
    Process all audio files in a directory and generate meeting notes.

    Use --select for interactive multiple-file selection with Q/W/E mode toggling.
    Use --llm/--no-llm to enable/disable LLM post-processing.
    Use --notes QWE to specify which note types to generate (Q=executive, W=holistic, E=tasks).
    Use --link-calendar to auto-link files to calendar events and rename outputs.
    Use --select-calendar-event with --link-calendar for interactive event selection.
    """
    ctx = get_app_context()

    # Initialize services
    processor = FileProcessor(ctx.config, ctx.logger)
    transcriber = Transcriber(ctx.config.deepgram, ctx.logger)

    # Resolve LLM configuration
    effective_llm = llm_enabled if llm_enabled is not None else ctx.config.llm.enabled
    selected_modes = None
    if notes:
        # Parse notes string and validate against config keys
        parsed_modes = set(notes.upper())
        valid_modes = set(ctx.config.llm.keys.model_dump().values())
        selected_modes = parsed_modes.intersection(valid_modes)
        if not selected_modes:
            ctx.logger.error(f"No valid modes found in '{notes}'. Valid modes: {', '.join(sorted(valid_modes))}")
            raise typer.Exit(code=1)
    else:
        # Use default modes from config
        selected_modes = set(ctx.config.llm.default_modes.upper())

    # Initialize LLM generator if enabled
    llm_generator = None
    if effective_llm:
        try:
            llm_generator = LLMNotesGenerator(ctx.config.llm, ctx.logger)
            mode_str = ''.join(sorted(selected_modes)) if selected_modes else 'None'
            ctx.logger.info(f"LLM post-processing enabled for modes: {mode_str}")
        except Exception as e:
            ctx.logger.error(f"Failed to initialize LLM generator: {e}")
            ctx.logger.warning("Continuing without LLM post-processing")
            effective_llm = False

    # Initialize calendar linker if requested
    calendar_linker = None
    if link_calendar:
        try:
            calendar_linker = CalendarLinker(ctx.config.google, ctx.logger, select_calendar_event)
            if select_calendar_event:
                ctx.logger.info(f"Calendar linking enabled with manual event selection")
            else:
                ctx.logger.info(f"Calendar linking enabled with {ctx.config.google.match_tolerance_minutes} min tolerance")
        except (ConfigurationError, GoogleCalendarError) as e:
            ctx.logger.error(f"Failed to initialize calendar linker: {e}")
            ctx.logger.warning("Continuing without calendar linking")
            link_calendar = False

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
        ctx.logger.debug(f"CLI selected_modes = {selected_modes}")
        ctx.logger.debug(f"CLI note_keys = {ctx.config.llm.keys.model_dump()}")

        # Build LLM output folder map for tri-state UI indicators
        llm_output_map = {
            "Q": ctx.config.llm.paths.q_output_folder,
            "W": ctx.config.llm.paths.w_output_folder,
            "E": ctx.config.llm.paths.e_output_folder,
        }

        result = interactive_select_files(
            files, output_folder, ctx.config.ui.selection_page_size, ctx.logger,
            note_keys=ctx.config.llm.keys.model_dump(), initial_modes=selected_modes,
            llm_output_map=llm_output_map
        )
        if result is None:
            ctx.logger.info("Selection cancelled")
            return

        selected_files, file_modes_dict = result

        # Check if we have any files to process
        if not selected_files:
            ctx.logger.warning("No files selected for processing. Make sure to select files with Space or enable modes on the current file.")
            return

        # Debug logging
        ctx.logger.debug(f"CLI processing {len(selected_files)} files")
        for file in selected_files:
            modes = file_modes_dict.get(file, set())
            ctx.logger.debug(f"CLI {file.name} -> modes: {''.join(sorted(modes)) if modes else 'None'}")

        # Process selected files with reprocess=True (since user chose them)
        # Pass per-file modes to the processor
        try:
            processed_count, skipped_count = processor.run_batch(
                selected_files, True, transcriber, output_folder, llm_generator, file_modes_dict, calendar_linker
            )
        except KeyboardInterrupt:
            ctx.logger.info("Processing cancelled by user (Ctrl+C)")
            raise typer.Exit(130)  # Standard exit code for SIGINT

        # Calculate mode summary for logging
        all_modes = set()
        for file_path, modes in file_modes_dict.items():
            ctx.logger.debug(f"CLI file {file_path.name} has modes: {modes}")
            all_modes.update(modes)

        mode_summary = ''.join(sorted(all_modes)) if all_modes else 'None'
        ctx.logger.debug(f"CLI all modes across files: {all_modes}")
        ctx.logger.debug(f"CLI mode summary: {mode_summary}")

        ctx.logger.info(f"Selection summary: Processed={processed_count}, Skipped={skipped_count}, Total selected={len(selected_files)}, Active modes={mode_summary}")
    else:
        # Batch processing mode
        candidates = processor.get_files_to_process(files, effective_reprocess, output_folder)
        try:
            processed_count, skipped_count = processor.run_batch(
                candidates, effective_reprocess, transcriber, output_folder, llm_generator, selected_modes, calendar_linker
            )
        except KeyboardInterrupt:
            ctx.logger.info("Processing cancelled by user (Ctrl+C)")
            raise typer.Exit(130)  # Standard exit code for SIGINT

        mode_str = ''.join(sorted(selected_modes)) if selected_modes else 'None'
        ctx.logger.info(f"Summary: Processed={processed_count}, Skipped={skipped_count}, Total candidates={len(candidates)}, Modes={mode_str}")


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
        help="Reprocess files: regenerate LLM notes from existing transcriptions, or run full transcription if none exists.",
    ),
    llm_enabled: Optional[bool] = typer.Option(
        None,
        "--llm/--no-llm",
        help="Enable/disable LLM post-processing (defaults to config).",
    ),
    notes: Optional[str] = typer.Option(
        None,
        "--notes",
        "-n",
        help="LLM notes to generate: any combination of Q, W, E. Example: QWE or QW.",
    ),
    link_calendar: bool = typer.Option(
        False,
        "--link-calendar",
        help="Auto-link file to closest calendar event and rename output to YYYY-MM-DD_Title; include event metadata in notes.",
    ),
):
    """
    Process a single audio file and generate meeting notes.

    Use --llm/--no-llm to enable/disable LLM post-processing.
    Use --notes QWE to specify which note types to generate (Q=executive, W=holistic, E=tasks).
    Use --link-calendar to auto-link file to calendar event and rename output.
    """
    ctx = get_app_context()
    from app.transcriber import SUPPORTED_EXTENSIONS

    if audio_file is None:
        ctx.logger.error("No audio file provided. Please specify a file path or set a default in config.")
        raise typer.Exit(code=1)

    # Initialize services
    processor = FileProcessor(ctx.config, ctx.logger)
    transcriber = Transcriber(ctx.config.deepgram, ctx.logger)

    # Resolve LLM configuration
    effective_llm = llm_enabled if llm_enabled is not None else ctx.config.llm.enabled
    selected_modes = None
    if notes:
        # Parse notes string and validate against config keys
        parsed_modes = set(notes.upper())
        valid_modes = set(ctx.config.llm.keys.model_dump().values())
        selected_modes = parsed_modes.intersection(valid_modes)
        if not selected_modes:
            ctx.logger.error(f"No valid modes found in '{notes}'. Valid modes: {', '.join(sorted(valid_modes))}")
            raise typer.Exit(code=1)
    else:
        # Use default modes from config
        selected_modes = set(ctx.config.llm.default_modes.upper())

    # Initialize LLM generator if enabled
    llm_generator = None
    if effective_llm:
        try:
            llm_generator = LLMNotesGenerator(ctx.config.llm, ctx.logger)
            mode_str = ''.join(sorted(selected_modes)) if selected_modes else 'None'
            ctx.logger.info(f"LLM post-processing enabled for modes: {mode_str}")
        except Exception as e:
            ctx.logger.error(f"Failed to initialize LLM generator: {e}")
            ctx.logger.warning("Continuing without LLM post-processing")
            effective_llm = False

    # Initialize calendar linker if requested
    calendar_linker = None
    if link_calendar:
        try:
            calendar_linker = CalendarLinker(ctx.config.google, ctx.logger, select_calendar_event)
            if select_calendar_event:
                ctx.logger.info(f"Calendar linking enabled with manual event selection")
            else:
                ctx.logger.info(f"Calendar linking enabled with {ctx.config.google.match_tolerance_minutes} min tolerance")
        except (ConfigurationError, GoogleCalendarError) as e:
            ctx.logger.error(f"Failed to initialize calendar linker: {e}")
            ctx.logger.warning("Continuing without calendar linking")
            link_calendar = False

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
            [audio_path], effective_reprocess, transcriber, output_folder, llm_generator, selected_modes, calendar_linker
        )

        if skipped_count > 0:
            ctx.logger.info("File was skipped (already exists)")
        else:
            mode_str = ''.join(sorted(selected_modes)) if selected_modes else 'None'
            ctx.logger.info(f"File processed successfully, Modes={mode_str}")

    except KeyboardInterrupt:
        ctx.logger.info("Processing cancelled by user (Ctrl+C)")
        raise typer.Exit(130)  # Standard exit code for SIGINT
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
        table = Table(title="Past Calendar Events")
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
