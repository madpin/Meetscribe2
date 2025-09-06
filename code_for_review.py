# --- app/transcriber.py ---
"""
Handles audio transcription and analysis using the Deepgram API.
"""

from pathlib import Path

from deepgram import DeepgramClient, PrerecordedOptions

from app.core.context import AppContext


class Transcriber:
    """
    A class to handle transcription and analysis of audio files.
    """

    def __init__(self, ctx: AppContext):
        """
        Initialize the Transcriber with the application context.

        Args:
            ctx: The application context.
        """
        self.ctx = ctx
        self.deepgram_api_key = self._get_api_key()
        self.client = DeepgramClient(self.deepgram_api_key)

    def _get_api_key(self) -> str:
        """
        Get the Deepgram API key from the configuration.

        Returns:
            The Deepgram API key.

        Raises:
            ValueError: If the API key is not found in the configuration.
        """
        api_key = self.ctx.config.get("deepgram", {}).get("api_key")
        if not api_key:
            raise ValueError("Deepgram API key not found in config.toml")
        return api_key

    def process_audio_file(self, file_path: Path) -> str:
        """
        Transcribe and analyze an audio file.

        Args:
            file_path: The path to the audio file.

        Returns:
            A string containing the structured notes.
        """
        self.ctx.logger.info(f"Processing audio file: {file_path}")

        try:
            with open(file_path, "rb") as audio_file:
                source = {"buffer": audio_file.read(), "mimetype": "audio/wav"}
                options = PrerecordedOptions(
                    model="nova-2",
                    smart_format=True,
                    summarize="v2",
                    detect_topics=True,
                    intents=True,
                )

                response = self.client.listen.prerecorded.v("1").transcribe_file(
                    source, options
                )

                return self._format_results(response)

        except Exception as e:
            self.ctx.logger.error(f"Error processing {file_path}: {e}")
            return f"Error: Could not process {file_path}."

    def _format_results(self, response) -> str:
        """
        Format the transcription results into structured notes.

        Args:
            response: The response from the Deepgram API.

        Returns:
            A formatted string with the summary, action items, and transcript.
        """
        try:
            results = response.results
            summary = "No summary available."
            if results.summary:
                summary = results.summary.short

            transcript = "No transcript available."
            if results.channels and results.channels[0].alternatives:
                transcript = results.channels[0].alternatives[0].transcript

            topics = []
            if results.topics:
                topics = [topic.topic for topic in results.topics.segments]

            intents = []
            if results.intents:
                intents = [
                    intent.intent
                    for segment in results.intents.segments
                    for intent in segment.intents
                ]

            # For now, I'll use intents as action items and topics as key decisions
            action_items = intents
            key_decisions = topics

            formatted_output = f"""
# Meeting Notes

## Summary
{summary}

## Key Decisions
{self._format_list(key_decisions)}

## Action Items
{self._format_list(action_items)}

---

## Full Transcript
{transcript}
"""
            return formatted_output.strip()

        except Exception as e:
            self.ctx.logger.error(f"Error formatting results: {e}")
            return "Error: Could not format the results."

    def _format_list(self, items: list) -> str:
        """Format a list of strings into a markdown list."""
        if not items:
            return "- None"
        return "\n".join(f"- {item}" for item in items)


# --- app/cli.py ---
"""
Meetscribe: Audio to Notes CLI

This module provides the command-line interface for Meetscribe, a tool to
automatically convert audio recordings of meetings into structured notes.
"""

import sys
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

    supported_formats = [".wav", ".mp3", ".m4a"]
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

    for audio_file in audio_files:
        ctx.logger.info(f"Processing {audio_file.name}...")
        print(f"Processing {audio_file.name}...")
        notes = transcriber.process_audio_file(audio_file)
        output_file = output_folder / f"{audio_file.stem}.txt"
        with open(output_file, "w") as f:
            f.write(notes)
        ctx.logger.info(f"Notes saved to {output_file}")
        print(f"Notes saved to {output_file}")


if __name__ == "__main__":
    app()
