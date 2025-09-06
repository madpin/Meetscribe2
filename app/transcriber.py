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
