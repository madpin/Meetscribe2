"""
Meetscribe: Audio to Notes CLI

This module provides the command-line interface for Meetscribe, a tool to
automatically convert audio recordings of meetings into structured notes.
"""

import sys
from datetime import datetime
from typing import Optional

import typer

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


@process_app.command("dir")
def process_directory(
    audio_directory: str = typer.Argument(
        ..., help="The directory containing audio files to process."
    ),
    reprocess: Optional[bool] = typer.Option(
        None,
        "--reprocess",
        help="Reprocess files even if the output .txt already exists (overwrite).",
    ),
):
    """
    Process all audio files in a directory and generate meeting notes.
    """
    ctx = get_app_context()
    from app.transcriber import Transcriber
    from pathlib import Path

    transcriber = Transcriber(ctx)
    audio_path = Path(audio_directory)

    if not audio_path.is_dir():
        ctx.logger.error(f"The provided path is not a directory: {audio_directory}")
        print(f"Error: The provided path is not a directory: {audio_directory}")
        raise typer.Exit(code=1)

    supported_formats = [".wav", ".mp3", ".m4a", ".aac"]
    audio_files = [
        p for p in audio_path.iterdir() if p.suffix.lower() in supported_formats
    ]

    if not audio_files:
        ctx.logger.warning(f"No supported audio files found in {audio_directory}")
        print(f"No supported audio files found in {audio_directory}")
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

    # Initialize counters
    processed_count = 0
    skipped_count = 0

    for audio_file in audio_files:
        output_file = output_folder / f"{audio_file.stem}.txt"
        if not effective_reprocess and output_file.exists():
            ctx.logger.info(f"Skipping {audio_file.name}: {output_file} already exists")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} INFO     Skipping {audio_file.name}: {output_file} already exists")
            skipped_count += 1
            continue

        ctx.logger.info(f"Processing {audio_file.name}...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} INFO     Processing {audio_file.name}...")
        notes = transcriber.process_audio_file(audio_file)
        with open(output_file, "w") as f:
            f.write(notes)
        ctx.logger.info(f"Notes saved to {output_file}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} INFO     Notes saved to {output_file}")
        processed_count += 1

    # Print summary
    total_count = len(audio_files)
    msg = f"Summary: Processed={processed_count}, Skipped={skipped_count}, Total={total_count}"
    ctx.logger.info(msg)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} INFO     {msg}")


if __name__ == "__main__":
    app()
