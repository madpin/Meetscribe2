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
from app.core.exceptions import (
    ConfigurationError,
    TranscriptionError,
    GoogleCalendarError,
)
from app.core.utils import truncate_attendees, truncate_attachments
from app.services.file_processor import FileProcessor
from app.services.llm_notes import LLMNotesGenerator
from app.services.calendar_linker import CalendarLinker
from app.services.meeting_notes import EventNotesGenerator
from app.services.dir_watcher import DirectoryWatcher
from app.ui import interactive_select_files, interactive_select_events
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
        None,
        help="The directory containing audio files to process. Uses config input_folder if not provided.",
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
            ctx.logger.error(
                f"No valid modes found in '{notes}'. Valid modes: {', '.join(sorted(valid_modes))}"
            )
            raise typer.Exit(code=1)
    else:
        # Use default modes from config
        selected_modes = set(ctx.config.llm.default_modes.upper())

    # Initialize LLM generator if enabled
    llm_generator = None
    if effective_llm:
        try:
            llm_generator = LLMNotesGenerator(
                ctx.config.llm, ctx.logger, ctx.config.paths.output_extension
            )
            mode_str = "".join(sorted(selected_modes)) if selected_modes else "None"
            ctx.logger.info(f"LLM post-processing enabled for modes: {mode_str}")
        except Exception as e:
            ctx.logger.error(f"Failed to initialize LLM generator: {e}")
            ctx.logger.warning("Continuing without LLM post-processing")
            effective_llm = False

    # Initialize calendar linker if requested
    calendar_linker = None
    if link_calendar:
        try:
            calendar_linker = CalendarLinker(
                ctx.config.google, ctx.logger, select_calendar_event
            )
            if select_calendar_event:
                ctx.logger.info("Calendar linking enabled with manual event selection")
            else:
                ctx.logger.info(
                    f"Calendar linking enabled with {ctx.config.google.match_tolerance_minutes} min tolerance"
                )
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
    effective_reprocess = (
        reprocess if reprocess is not None else ctx.config.processing.reprocess
    )

    # Determine if we should use select mode
    use_select_mode = select_file

    if not select_file:
        # Get candidate files respecting reprocess setting
        candidates = processor.get_files_to_process(
            files, effective_reprocess, output_folder
        )

        # Check limits
        dec = processor.should_use_select_mode(len(candidates))
        if dec is True:
            # Hard limit exceeded - auto enter select mode
            use_select_mode = True
        elif dec is None:
            # Soft limit exceeded - ask user
            if typer.confirm(
                f"Process all {len(candidates)} files or enter selection mode?",
                default=False,
            ):
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
            files,
            output_folder,
            ctx.config.ui.selection_page_size,
            ctx.logger,
            note_keys=ctx.config.llm.keys.model_dump(),
            initial_modes=selected_modes,
            llm_output_map=llm_output_map,
            output_extension=ctx.config.paths.output_extension,
        )
        if result is None:
            ctx.logger.info("Selection cancelled")
            return

        selected_files, file_modes_dict = result

        # Check if we have any files to process
        if not selected_files:
            ctx.logger.warning(
                "No files selected for processing. Make sure to select files with Space or enable modes on the current file."
            )
            return

        # Debug logging
        ctx.logger.debug(f"CLI processing {len(selected_files)} files")
        for file in selected_files:
            modes = file_modes_dict.get(file, set())
            ctx.logger.debug(
                f"CLI {file.name} -> modes: {''.join(sorted(modes)) if modes else 'None'}"
            )

        # Process selected files with reprocess=True (since user chose them)
        # Pass per-file modes to the processor
        try:
            processed_count, skipped_count = processor.run_batch(
                selected_files,
                True,
                transcriber,
                output_folder,
                llm_generator,
                file_modes_dict,
                calendar_linker,
            )
        except KeyboardInterrupt:
            ctx.logger.info("Processing cancelled by user (Ctrl+C)")
            raise typer.Exit(130)  # Standard exit code for SIGINT

        # Calculate mode summary for logging
        all_modes = set()
        for file_path, modes in file_modes_dict.items():
            ctx.logger.debug(f"CLI file {file_path.name} has modes: {modes}")
            all_modes.update(modes)

        mode_summary = "".join(sorted(all_modes)) if all_modes else "None"
        ctx.logger.debug(f"CLI all modes across files: {all_modes}")
        ctx.logger.debug(f"CLI mode summary: {mode_summary}")

        ctx.logger.info(
            f"Selection summary: Processed={processed_count}, Skipped={skipped_count}, Total selected={len(selected_files)}, Active modes={mode_summary}"
        )
    else:
        # Batch processing mode
        candidates = processor.get_files_to_process(
            files, effective_reprocess, output_folder
        )
        try:
            processed_count, skipped_count = processor.run_batch(
                candidates,
                effective_reprocess,
                transcriber,
                output_folder,
                llm_generator,
                selected_modes,
                calendar_linker,
            )
        except KeyboardInterrupt:
            ctx.logger.info("Processing cancelled by user (Ctrl+C)")
            raise typer.Exit(130)  # Standard exit code for SIGINT

        mode_str = "".join(sorted(selected_modes)) if selected_modes else "None"
        ctx.logger.info(
            f"Summary: Processed={processed_count}, Skipped={skipped_count}, Total candidates={len(candidates)}, Modes={mode_str}"
        )


@process_app.command("list")
def process_list(
    audio_directory: Optional[str] = typer.Argument(
        None,
        help="The directory containing audio files to list. Uses config input_folder if not provided.",
    ),
):
    """
    List all supported audio files in a directory with metadata.
    """
    ctx = get_app_context()
    from app.core.utils import (
        format_file_size,
        get_audio_duration,
        format_duration,
        format_time_ago,
    )
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
        modified_str = (
            f"{modified_dt.strftime('%Y-%m-%d %H:%M')} ({format_time_ago(modified_dt)})"
        )
        size_str = format_file_size(stat.st_size)
        duration = get_audio_duration(audio_file)
        duration_str = format_duration(duration)

        table.add_row(str(i), audio_file.name, modified_str, size_str, duration_str)

    console.print(table)


@process_app.command("file")
def process_file(
    audio_file: Optional[str] = typer.Argument(
        None,
        help="The audio file to process. Can be absolute path or relative to config input_folder.",
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
    select_calendar_event: bool = typer.Option(
        False,
        "--select-calendar-event",
        help="When used with --link-calendar, interactively select which calendar event to link to instead of auto-matching.",
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
        ctx.logger.error(
            "No audio file provided. Please specify a file path or set a default in config."
        )
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
            ctx.logger.error(
                f"No valid modes found in '{notes}'. Valid modes: {', '.join(sorted(valid_modes))}"
            )
            raise typer.Exit(code=1)
    else:
        # Use default modes from config
        selected_modes = set(ctx.config.llm.default_modes.upper())

    # Initialize LLM generator if enabled
    llm_generator = None
    if effective_llm:
        try:
            llm_generator = LLMNotesGenerator(
                ctx.config.llm, ctx.logger, ctx.config.paths.output_extension
            )
            mode_str = "".join(sorted(selected_modes)) if selected_modes else "None"
            ctx.logger.info(f"LLM post-processing enabled for modes: {mode_str}")
        except Exception as e:
            ctx.logger.error(f"Failed to initialize LLM generator: {e}")
            ctx.logger.warning("Continuing without LLM post-processing")
            effective_llm = False

    # Initialize calendar linker if requested
    calendar_linker = None
    if link_calendar:
        try:
            calendar_linker = CalendarLinker(
                ctx.config.google, ctx.logger, select_calendar_event
            )
            if select_calendar_event:
                ctx.logger.info("Calendar linking enabled with manual event selection")
            else:
                ctx.logger.info(
                    f"Calendar linking enabled with {ctx.config.google.match_tolerance_minutes} min tolerance"
                )
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
        ctx.logger.error(
            f"Unsupported file extension: {audio_path.suffix}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
        raise typer.Exit(code=1)

    # Resolve output folder
    output_folder = processor.resolve_output_folder()

    # Determine effective reprocess behavior
    effective_reprocess = (
        reprocess if reprocess is not None else ctx.config.processing.reprocess
    )

    try:
        # Process single file
        processed_count, skipped_count = processor.run_batch(
            [audio_path],
            effective_reprocess,
            transcriber,
            output_folder,
            llm_generator,
            selected_modes,
            calendar_linker,
        )

        if skipped_count > 0:
            ctx.logger.info("File was skipped (already exists)")
        else:
            mode_str = "".join(sorted(selected_modes)) if selected_modes else "None"
            ctx.logger.info(f"File processed successfully, Modes={mode_str}")

    except KeyboardInterrupt:
        ctx.logger.info("Processing cancelled by user (Ctrl+C)")
        raise typer.Exit(130)  # Standard exit code for SIGINT
    except TranscriptionError as e:
        ctx.logger.error(f"Transcription failed: {e}")
        raise typer.Exit(code=1)


@process_app.command("watch")
def process_watch(
    audio_directory: Optional[str] = typer.Argument(
        None,
        help="The directory containing audio files to watch. Uses config input_folder if not provided.",
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
        help="Auto-link files to closest calendar event and rename outputs to YYYY-MM-DD_Title; include event metadata in notes.",
    ),
    select_calendar_event: bool = typer.Option(
        False,
        "--select-calendar-event",
        help="When used with --link-calendar, interactively select which calendar event to link to instead of auto-matching.",
    ),
    stable_seconds: Optional[int] = typer.Option(
        None,
        "--stable-seconds",
        help="Seconds file must be stable before processing (defaults to config).",
    ),
    poll_interval: Optional[float] = typer.Option(
        None,
        "--poll-interval",
        help="Seconds between directory polls (defaults to config).",
    ),
    max_size_mb: Optional[int] = typer.Option(
        None,
        "--max-size-mb",
        help="Maximum file size in MB to process (defaults to config).",
    ),
):
    """
    Watch a directory for new audio files and process them automatically when stable.

    This command runs a long-running daemon that monitors the input directory for new audio files.
    Files are processed only after they have been stable (no size changes) for the configured time.
    Only files created AFTER the watcher starts will be processed (existing files are ignored).

    Use --llm/--no-llm to enable/disable LLM post-processing.
    Use --notes QWE to specify which note types to generate (Q=executive, W=holistic, E=tasks).
    Use --link-calendar to auto-link files to calendar events and rename outputs.
    Use --stable-seconds to override the stability window (defaults to 5 seconds).
    Use --poll-interval to override the poll frequency (defaults to 1.0 seconds).
    Use --max-size-mb to override the maximum file size limit (defaults to 500 MB).
    Use Ctrl+C to stop the watcher.
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
            ctx.logger.error(
                f"No valid modes found in '{notes}'. Valid modes: {', '.join(sorted(valid_modes))}"
            )
            raise typer.Exit(code=1)
    else:
        # Use default modes from config
        selected_modes = set(ctx.config.llm.default_modes.upper())

    # Initialize LLM generator if enabled
    llm_generator = None
    if effective_llm:
        try:
            llm_generator = LLMNotesGenerator(
                ctx.config.llm, ctx.logger, ctx.config.paths.output_extension
            )
            mode_str = "".join(sorted(selected_modes)) if selected_modes else "None"
            ctx.logger.info(f"LLM post-processing enabled for modes: {mode_str}")
        except Exception as e:
            ctx.logger.error(f"Failed to initialize LLM generator: {e}")
            ctx.logger.warning("Continuing without LLM post-processing")
            effective_llm = False

    # Initialize calendar linker if requested
    calendar_linker = None
    if link_calendar:
        try:
            calendar_linker = CalendarLinker(
                ctx.config.google, ctx.logger, select_calendar_event
            )
            if select_calendar_event:
                ctx.logger.info("Calendar linking enabled with manual event selection")
            else:
                ctx.logger.info(
                    f"Calendar linking enabled with {ctx.config.google.match_tolerance_minutes} min tolerance"
                )
        except (ConfigurationError, GoogleCalendarError) as e:
            ctx.logger.error(f"Failed to initialize calendar linker: {e}")
            ctx.logger.warning("Continuing without calendar linking")
            link_calendar = False

    # Resolve input directory
    input_dir = processor.resolve_input_folder(audio_directory)
    if not input_dir.is_dir():
        ctx.logger.error(f"The provided path is not a directory: {input_dir}")
        raise typer.Exit(code=1)

    # Resolve output folder
    output_folder = processor.resolve_output_folder()

    # Determine effective overrides
    effective_reprocess = (
        reprocess if reprocess is not None else ctx.config.processing.reprocess
    )

    # Instantiate DirectoryWatcher with overrides
    watcher = DirectoryWatcher(
        cfg=ctx.config,
        logger=ctx.logger,
        stable_seconds=stable_seconds,
        poll_interval=poll_interval,
        max_filesize_mb=max_size_mb,
    )

    # Start watching
    try:
        watcher.watch(
            input_dir=input_dir,
            processor=processor,
            transcriber=transcriber,
            output_folder=output_folder,
            llm_generator=llm_generator,
            llm_modes=selected_modes,
            calendar_linker=calendar_linker,
            reprocess=effective_reprocess,
        )
    except KeyboardInterrupt:
        ctx.logger.info("Watcher stopped by user (Ctrl+C)")
        raise typer.Exit(130)  # Standard exit code for SIGINT


def _truncate_description(description: str, max_length: int = 80) -> str:
    """Truncate description to max_length with ellipsis if needed."""
    if len(description) <= max_length:
        return description
    return description[: max_length - 3] + "…"


@calendar_app.command("past")
def calendar_past(
    days: Optional[int] = typer.Option(
        None, "--days", "-d", help="Number of past days to list (defaults to config)."
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-n", help="Max number of events (defaults to config)."
    ),
    calendar_id: Optional[str] = typer.Option(
        None, "--calendar-id", help="Calendar ID (defaults to config)."
    ),
    group_only: Optional[bool] = typer.Option(
        None,
        "--group-only/--no-group-only",
        help="Only show events with 2 or more attendees (defaults to config).",
    ),
):
    """
    List past Google Calendar events with attendees, description, and attachment names.
    """
    ctx = get_app_context()
    console = Console()

    ctx.logger.info(
        f"Listing past calendar events with parameters: days={days}, limit={limit}, calendar_id={calendar_id}, group_only={group_only}"
    )

    try:
        # Initialize Google Calendar client with new signature
        client = GoogleCalendarClient(ctx.config.google, ctx.logger)
        events = client.list_past_events(
            days=days,
            limit=limit,
            calendar_id=calendar_id,
            filter_group_events=group_only,
        )

        if not events:
            console.print(
                "[yellow]No past events found for the specified time range.[/yellow]"
            )
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
            title = event.get("summary", "-")
            attendees = GoogleCalendarClient.extract_attendee_names(event)
            attendees_str = truncate_attendees(attendees)
            description = _truncate_description(event.get("description", "-"))
            attachments = GoogleCalendarClient.extract_attachment_titles(event)
            attachments_str = truncate_attachments(attachments)

            table.add_row(start_str, title, attendees_str, description, attachments_str)

        console.print(table)

    except GoogleCalendarError as e:
        ctx.logger.error(f"Failed to list calendar events: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@calendar_app.command("upcoming")
def calendar_upcoming(
    days: Optional[int] = typer.Option(
        None, "--days", "-d", help="Number of days to look ahead (defaults to config)."
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-n", help="Max number of events (defaults to config)."
    ),
    calendar_id: Optional[str] = typer.Option(
        None, "--calendar-id", help="Calendar ID (defaults to config)."
    ),
    group_only: Optional[bool] = typer.Option(
        None,
        "--group-only/--no-group-only",
        help="Only show events with 2 or more attendees (defaults to config).",
    ),
    select: bool = typer.Option(
        False, "--select", help="Interactively select events and create meeting notes."
    ),
):
    """
    List upcoming Google Calendar events and optionally create meeting notes.

    Use --select to interactively choose events and generate Obsidian-ready meeting notes.
    """
    ctx = get_app_context()
    console = Console()

    ctx.logger.info(
        f"Listing upcoming calendar events with parameters: days={days}, limit={limit}, calendar_id={calendar_id}, group_only={group_only}, select={select}"
    )

    try:
        # Initialize Google Calendar client
        client = GoogleCalendarClient(ctx.config.google, ctx.logger)
        events = client.list_upcoming_events(
            days=days,
            limit=limit,
            calendar_id=calendar_id,
            filter_group_events=group_only,
        )

        if not events:
            console.print(
                "[yellow]No upcoming events found for the specified time range.[/yellow]"
            )
            return

        if not select:
            # Display table
            table = Table(title="Upcoming Calendar Events")
            table.add_column("Start (Local)", style="cyan", justify="left")
            table.add_column("Title", style="green")
            table.add_column("Attendees", style="yellow")
            table.add_column("Description", style="blue")
            table.add_column("Attachments", style="magenta")

            # Add rows
            for event in events:
                start_str = GoogleCalendarClient.parse_event_start_local(event)
                title = event.get("summary", "-")
                attendees = GoogleCalendarClient.extract_attendee_names(event)
                attendees_str = truncate_attendees(attendees)
                description = _truncate_description(event.get("description", "-"))
                attachments = GoogleCalendarClient.extract_attachment_titles(event)
                attachments_str = truncate_attachments(attachments)

                table.add_row(
                    start_str, title, attendees_str, description, attachments_str
                )

            console.print(table)
        else:
            # Interactive selection mode
            from datetime import datetime, timedelta

            # Calculate initial date range (today to future)
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            days_ahead = (
                days if days is not None else ctx.config.google.default_past_days
            )
            end_date = today_start + timedelta(days=days_ahead)

            # Create reload callback for date navigation
            def reload_events(start_date, end_date):
                try:
                    new_events = client.list_events_in_range(
                        start_date=start_date,
                        end_date=end_date,
                        calendar_id=calendar_id,
                        filter_group_events=group_only,
                    )
                    return new_events, start_date, end_date
                except Exception as e:
                    ctx.logger.error(f"Failed to reload events: {e}")
                    return [], start_date, end_date

            # Interactive selection with navigation
            result = interactive_select_events(
                events,
                ctx.config.ui.selection_page_size,
                ctx.logger,
                reload_callback=reload_events,
                start_date=today_start,
                end_date=end_date,
            )

            if result is None:
                ctx.logger.info("Event selection cancelled")
                console.print("[yellow]Selection cancelled.[/yellow]")
                return

            selected_events, date_info = result

            if not selected_events:
                ctx.logger.warning("No events selected")
                console.print("[yellow]No events selected.[/yellow]")
                return

            # Log navigation if used
            if date_info.get("navigated", False):
                start_str = (
                    date_info["start_date"].strftime("%Y-%m-%d")
                    if date_info["start_date"]
                    else "Unknown"
                )
                end_str = (
                    date_info["end_date"].strftime("%Y-%m-%d")
                    if date_info["end_date"]
                    else "Unknown"
                )
                ctx.logger.info(
                    f"User navigated to date range: {start_str} to {end_str}"
                )

            # Check if meeting notes are enabled
            if not ctx.config.meeting_notes.enabled:
                ctx.logger.warning(
                    "Meeting notes generation is disabled in configuration"
                )
                console.print(
                    "[yellow]Meeting notes generation is disabled. Enable it in config to create notes.[/yellow]"
                )
                return

            # Initialize notes generator
            try:
                notes_generator = EventNotesGenerator(
                    ctx.config.meeting_notes, ctx.logger
                )
            except Exception as e:
                ctx.logger.error(f"Failed to initialize meeting notes generator: {e}")
                console.print(
                    f"[red]Failed to initialize meeting notes generator: {e}[/red]"
                )
                raise typer.Exit(code=1)

            # Create notes for selected events
            created_paths = []
            for event in selected_events:
                try:
                    note_path = notes_generator.create_note_for_event(event)
                    created_paths.append(note_path)
                    console.print(f"[green]✓ Created note:[/green] {note_path}")
                except Exception as e:
                    event_title = event.get("summary", "Unknown Event")
                    ctx.logger.error(
                        f"Failed to create note for event '{event_title}': {e}"
                    )
                    console.print(
                        f"[red]✗ Failed to create note for '{event_title}': {e}[/red]"
                    )

            # Summary
            success_count = len(created_paths)
            total_count = len(selected_events)
            folder_path = ctx.config.meeting_notes.output_folder

            if success_count > 0:
                console.print(
                    f"\n[bold green]Summary:[/bold green] Created {success_count}/{total_count} meeting notes"
                )
                console.print(f"[blue]Output folder:[/blue] {folder_path}")
                if success_count < total_count:
                    console.print(
                        f"[yellow]Note: {total_count - success_count} events failed[/yellow]"
                    )
            else:
                console.print("\n[red]Failed to create any meeting notes[/red]")

    except GoogleCalendarError as e:
        ctx.logger.error(f"Failed to list upcoming calendar events: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
