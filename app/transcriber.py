"""
Handles audio transcription and analysis using the Deepgram API.
"""

from collections import defaultdict
from pathlib import Path

from deepgram import DeepgramClient, PrerecordedOptions

from app.core.config_models import DeepgramConfig
from app.core.exceptions import TranscriptionError


# Supported audio file extensions
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac"}

# MIME type mapping for supported extensions
MIMETYPE_BY_EXT = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac"
}


class Transcriber:
    """
    A class to handle transcription and analysis of audio files.
    """

    def __init__(self, cfg: DeepgramConfig, logger):
        """
        Initialize the Transcriber with configuration and logger.

        Args:
            cfg: The Deepgram configuration.
            logger: The logger instance.
        """
        self.cfg = cfg
        self.logger = logger
        self.client = DeepgramClient(self.cfg.api_key)


    def _get_mimetype(self, file_path: Path) -> str:
        """
        Get the appropriate MIME type for an audio file based on its extension.

        Args:
            file_path: The path to the audio file.

        Returns:
            The MIME type string for the file.
        """
        extension = file_path.suffix.lower()
        return MIMETYPE_BY_EXT.get(extension, "audio/wav")

    def process_audio_file(self, file_path: Path) -> str:
        """
        Transcribe and analyze an audio file.

        Args:
            file_path: The path to the audio file.

        Returns:
            A string containing the structured notes.

        Raises:
            TranscriptionError: If transcription fails.
        """
        self.logger.info(f"Processing audio file: {file_path}")

        try:
            with open(file_path, "rb") as audio_file:
                mimetype = self._get_mimetype(file_path)
                source = {"buffer": audio_file.read(), "mimetype": mimetype}

                # Read config-driven options from typed config
                options_kwargs = {
                    "model": self.cfg.model,
                    "language": self.cfg.language,
                    "smart_format": self.cfg.smart_format,
                    "diarize": self.cfg.diarize,
                    "summarize": self.cfg.summarize,
                    "detect_topics": self.cfg.detect_topics,
                    "intents": self.cfg.intents,
                }
                if self.cfg.diarize_speakers > 0:
                    options_kwargs["diarize_speakers"] = int(self.cfg.diarize_speakers)
                if self.cfg.min_speaker_gap > 0:
                    options_kwargs["min_speaker_gap"] = float(self.cfg.min_speaker_gap)
                if self.cfg.max_speaker_gap > 0:
                    options_kwargs["max_speaker_gap"] = float(self.cfg.max_speaker_gap)

                options = PrerecordedOptions(**options_kwargs)

                response = self.client.listen.prerecorded.v("1").transcribe_file(
                    source, options
                )

                return self._format_results(response)

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            raise TranscriptionError(f"Could not process {file_path}") from e

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

            speaker_timeline = self._format_speaker_timeline(results)

            formatted_output = f"""
# Meeting Notes

## Summary
{summary}

## Key Decisions
{self._format_list(key_decisions)}

## Action Items
{self._format_list(action_items)}

## Speaker Timeline
{speaker_timeline}
"""

            # Only include Full Transcript section if diarization is disabled
            # When diarization is enabled, the speaker timeline already provides
            # the transcript content organized by speakers
            if not self.cfg.diarize:
                formatted_output += f"""
---

## Full Transcript
{transcript}
"""

            return formatted_output.strip()

        except Exception as e:
            self.logger.error(f"Error formatting results: {e}")
            return "Error: Could not format the results."

    def _format_list(self, items: list) -> str:
        """Format a list of strings into a markdown list."""
        if not items:
            return "- None"
        return "\n".join(f"- {item}" for item in items)

    def _format_speaker_timeline(self, results) -> str:
        """
        Format speaker timeline from diarization results.

        Args:
            results: The Deepgram results object.

        Returns:
            A formatted string with speaker timeline or "- None" if unavailable.
        """
        try:
            if hasattr(results, "utterances") and results.utterances:
                lines = []
                for u in results.utterances:
                    spk = getattr(u, "speaker", "Unknown")
                    text = getattr(u, "transcript", "") or ""
                    if text:
                        lines.append(f"- Speaker {spk}: {text}")
                return "\n".join(lines) if lines else "- None"

            alt0 = None
            if getattr(results, "channels", None) and results.channels[0].alternatives:
                alt0 = results.channels[0].alternatives[0]

            if alt0 and hasattr(alt0, "paragraphs") and alt0.paragraphs:
                paragraphs = getattr(alt0.paragraphs, "paragraphs", None) or []
                lines = []
                for p in paragraphs:
                    spk = getattr(p, "speaker", "Unknown")
                    text = getattr(p, "transcript", "") or ""
                    if not text and hasattr(p, "sentences"):
                        text = " ".join(getattr(s, "text", "") for s in p.sentences
                                        if getattr(s, "text", ""))
                    if text:
                        lines.append(f"- Speaker {spk}: {text}")
                return "\n".join(lines) if lines else "- None"

            if alt0 and hasattr(alt0, "words") and alt0.words:
                by_spk = defaultdict(list)
                for w in alt0.words:
                    spk = getattr(w, "speaker", "Unknown")
                    word = getattr(w, "word", "")
                    if word:
                        by_spk[spk].append(word)
                lines = [f"- Speaker {spk}: {' '.join(words)}"
                         for spk, words in by_spk.items() if words]
                return "\n".join(lines) if lines else "- None"
        except Exception as e:
            self.logger.debug(f"Diarization formatting fallback: {e}")
        return "- None"
