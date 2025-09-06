"""
Handles audio transcription and analysis using the Deepgram API.
"""

from collections import defaultdict
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

    def _get_mimetype(self, file_path: Path) -> str:
        """
        Get the appropriate MIME type for an audio file based on its extension.

        Args:
            file_path: The path to the audio file.

        Returns:
            The MIME type string for the file.
        """
        extension = file_path.suffix.lower()
        mimetypes = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac"
        }
        return mimetypes.get(extension, "audio/wav")

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
                mimetype = self._get_mimetype(file_path)
                source = {"buffer": audio_file.read(), "mimetype": mimetype}

                # Read config-driven options
                dg_cfg = self.ctx.config.get("deepgram", {})
                model = dg_cfg.get("model", "nova-3")
                language = dg_cfg.get("language", "en-US")
                smart_format = dg_cfg.get("smart_format", True)
                diarize = dg_cfg.get("diarize", True)
                diarize_speakers = dg_cfg.get("diarize_speakers", 0) or 0
                min_speaker_gap = dg_cfg.get("min_speaker_gap", 0.0) or 0.0
                max_speaker_gap = dg_cfg.get("max_speaker_gap", 0.0) or 0.0
                summarize = dg_cfg.get("summarize", "v2")
                detect_topics = dg_cfg.get("detect_topics", True)
                intents = dg_cfg.get("intents", True)

                options_kwargs = {
                    "model": model,
                    "language": language,
                    "smart_format": smart_format,
                    "diarize": diarize,
                    "summarize": summarize,
                    "detect_topics": detect_topics,
                    "intents": intents,
                }
                if diarize_speakers > 0:
                    options_kwargs["diarize_speakers"] = int(diarize_speakers)
                if min_speaker_gap > 0:
                    options_kwargs["min_speaker_gap"] = float(min_speaker_gap)
                if max_speaker_gap > 0:
                    options_kwargs["max_speaker_gap"] = float(max_speaker_gap)

                options = PrerecordedOptions(**options_kwargs)

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
            self.ctx.logger.debug(f"Diarization formatting fallback: {e}")
        return "- None"
