"""
CalendarLinker service for Meetscribe.

This module provides functionality to link audio files to Google Calendar events
by matching modification times within a configurable tolerance window.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.core.config_models import GoogleConfig
from app.core.utils import sanitize_filename
from app.integrations.google_calendar import GoogleCalendarClient
from app.core.exceptions import GoogleCalendarError


class CalendarLinker:
    """
    Service for linking audio files to Google Calendar events.

    Matches files to the closest calendar event within a tolerance window
    and provides utilities for generating renamed filenames and metadata blocks.
    """

    # Special sentinel value to indicate user cancelled selection
    USER_CANCELLED = object()

    def __init__(
        self, gcfg: GoogleConfig, logger, select_event_interactively: bool = False
    ):
        """
        Initialize the CalendarLinker with configuration and logger.

        Args:
            gcfg: Google configuration
            logger: Logger instance
            select_event_interactively: Whether to prompt user to select event manually
        """
        self.cfg = gcfg
        self.logger = logger
        self.select_event_interactively = select_event_interactively
        self.client = GoogleCalendarClient(gcfg, logger)

    def match_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Match a file to the closest calendar event within tolerance.

        Only considers events that start BEFORE the file's modification time
        to ensure recordings are matched to past meetings.

        Args:
            file_path: Path to the audio file

        Returns:
            Event dictionary if match found within tolerance, None otherwise
        """
        try:
            # Get file modification time as timezone-aware datetime
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            mtime_local = mtime.astimezone()  # Convert to local timezone

            # Compute tolerance window
            tolerance = timedelta(minutes=self.cfg.match_tolerance_minutes)
            window_start = mtime_local - tolerance
            window_end = mtime_local + tolerance

            # Fetch events in the window
            events = self.client.list_events_between(
                start=window_start, end=window_end, limit=self.cfg.max_results
            )

            if not events:
                self.logger.debug(f"No events found in window for {file_path.name}")
                return None

            # Filter events that start before file modification time
            valid_events = []
            for event in events:
                # Extract event start/end times
                event_start, event_end = self._parse_event_times(event)

                if event_start is None:
                    continue

                # Constraint: Event must start before the file modification time
                # This ensures we're matching recordings to meetings that actually happened
                if event_start >= mtime_local:
                    self.logger.debug(
                        f"Skipping event '{event.get('summary', 'Unknown')}' - starts after file modification time"
                    )
                    continue

                valid_events.append((event, event_start, event_end))

            if not valid_events:
                self.logger.debug(
                    f"No valid events found in window for {file_path.name}"
                )
                return None

            # Handle interactive selection or automatic closest match
            if self.select_event_interactively:
                self.logger.debug(
                    f"Interactive selection enabled for {file_path.name} - {len(valid_events)} valid events found"
                )
                selected_event = self._interactive_event_selection(
                    valid_events, file_path
                )
                if selected_event:
                    # Annotate selected event with computed local times and distance
                    event_start, event_end = self._parse_event_times(selected_event)
                    distance_sec = self._calculate_distance_seconds(
                        mtime_local, event_start, event_end
                    )

                    selected_event["_local_start"] = event_start
                    selected_event["_local_end"] = event_end
                    selected_event["_distance_sec"] = distance_sec

                    event_title = selected_event.get("summary", "Unknown Event")
                    self.logger.info(
                        f"User selected event '{event_title}' for {file_path.name}"
                    )
                    return selected_event
                else:
                    self.logger.info(
                        f"User cancelled event selection for {file_path.name}"
                    )
                    return self.USER_CANCELLED
            else:
                # Find closest event (original behavior)
                closest_event = None
                min_distance_sec = float("inf")

                for event, event_start, event_end in valid_events:
                    # Calculate distance from file mtime to event
                    distance_sec = self._calculate_distance_seconds(
                        mtime_local, event_start, event_end
                    )

                    if distance_sec < min_distance_sec:
                        min_distance_sec = distance_sec
                        closest_event = event

            # Check if closest event is within tolerance
            if closest_event:
                # Annotate event with computed local times and distance
                closest_event["_local_start"] = self._parse_event_times(closest_event)[
                    0
                ]
                closest_event["_local_end"] = self._parse_event_times(closest_event)[1]
                closest_event["_distance_sec"] = min_distance_sec

                event_title = closest_event.get("summary", "Unknown Event")
                self.logger.info(
                    f"Matched {file_path.name} to event '{event_title}' ({min_distance_sec/60:.1f} min away)"
                )
                return closest_event
            else:
                self.logger.debug(
                    f"No events within {self.cfg.match_tolerance_minutes} min tolerance for {file_path.name}"
                )
                return None

        except GoogleCalendarError as e:
            self.logger.warning(
                f"Failed to match {file_path.name} to calendar event: {e}"
            )
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error matching {file_path.name}: {e}")
            return None

    def compute_target_stem(self, event: Dict[str, Any]) -> str:
        """
        Compute the target filename stem for an event.

        Args:
            event: Event dictionary (should have _local_start annotation)

        Returns:
            Filename stem in format YYYY-MM-DD_Title
        """
        local_start = event.get("_local_start")
        if not local_start:
            return "unknown_date_untitled"

        date_str = local_start.strftime("%Y-%m-%d")
        title = event.get("summary", "Untitled Event")
        sanitized_title = sanitize_filename(title)

        return f"{date_str}_{sanitized_title}"

    def format_event_metadata(self, event: Dict[str, Any], source_file: Path) -> str:
        """
        Format event metadata as a Markdown block.

        Args:
            event: Event dictionary
            source_file: Original source file path

        Returns:
            Markdown-formatted metadata block
        """
        lines = []

        # Header
        lines.append("## Linked Calendar Event")
        lines.append("")

        # Title
        title = event.get("summary", "Untitled Event")
        lines.append(f"**Title:** {title}")

        # When (local times)
        local_start = event.get("_local_start")
        local_end = event.get("_local_end")
        if local_start:
            if event.get("start", {}).get("date"):  # All-day event
                when_str = f"{local_start.strftime('%Y-%m-%d')} (all-day)"
            else:
                start_str = local_start.strftime("%Y-%m-%d %H:%M")
                if local_end:
                    end_str = local_end.strftime("%H:%M")
                    when_str = f"{start_str} — {end_str}"
                else:
                    when_str = start_str
            lines.append(f"**When:** {when_str}")
        else:
            lines.append("**When:** Unknown")

        # Attendees
        attendees = GoogleCalendarClient.extract_attendee_names(event)
        if attendees:
            if len(attendees) <= 5:
                attendees_str = ", ".join(attendees)
            else:
                attendees_str = (
                    ", ".join(attendees[:5]) + f" +{len(attendees) - 5} more"
                )
            lines.append(f"**Attendees:** {attendees_str}")
        else:
            lines.append("**Attendees:** None")

        # Attachments
        attachments = GoogleCalendarClient.extract_attachment_titles(event)
        if attachments:
            if len(attachments) <= 3:
                attachments_str = ", ".join(attachments)
            else:
                attachments_str = (
                    ", ".join(attachments[:3]) + f" +{len(attachments) - 3} more"
                )
            lines.append(f"**Attachments:** {attachments_str}")
        else:
            lines.append("**Attachments:** None")

        # Event URL
        html_link = event.get("htmlLink")
        if html_link:
            lines.append(f"**Event Link:** {html_link}")

        # Source file
        lines.append(f"**Source Audio:** {source_file.name}")

        # Calendar ID
        calendar_id = event.get("organizer", {}).get("email", "primary")
        lines.append(f"**Calendar:** {calendar_id}")

        # Description (truncated)
        description = event.get("description", "").strip()
        if description:
            if len(description) > 300:
                description = description[:297] + "..."
            lines.append("")
            lines.append("**Description:**")
            lines.append(description)

        return "\n".join(lines)

    def _parse_event_times(
        self, event: Dict[str, Any]
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Parse event start and end times as local timezone-aware datetimes.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            Tuple of (start_datetime, end_datetime), both timezone-aware in local tz
        """
        start_info = event.get("start", {})
        end_info = event.get("end", {})

        # Handle all-day events
        if "date" in start_info:
            # All-day event
            date_str = start_info["date"]
            start_dt = datetime.fromisoformat(date_str).replace(
                tzinfo=datetime.now().astimezone().tzinfo
            )
            end_date_str = end_info.get("date", date_str)
            end_dt = datetime.fromisoformat(end_date_str).replace(
                tzinfo=datetime.now().astimezone().tzinfo
            )
            return start_dt, end_dt

        # Handle timed events
        if "dateTime" in start_info:
            start_dt_str = start_info["dateTime"]
            end_dt_str = end_info.get("dateTime", start_dt_str)

            # Handle Python 3.10 compatibility by replacing Z with +00:00
            if start_dt_str.endswith("Z"):
                start_dt_str = start_dt_str[:-1] + "+00:00"
            if end_dt_str.endswith("Z"):
                end_dt_str = end_dt_str[:-1] + "+00:00"

            start_dt = datetime.fromisoformat(start_dt_str)
            end_dt = datetime.fromisoformat(end_dt_str)

            # Convert to local timezone
            local_tz = datetime.now().astimezone().tzinfo
            start_dt = start_dt.astimezone(local_tz)
            end_dt = end_dt.astimezone(local_tz)

            return start_dt, end_dt

        return None, None

    def _calculate_distance_seconds(
        self, file_time: datetime, event_start: datetime, event_end: Optional[datetime]
    ) -> float:
        """
        Calculate the distance in seconds from file modification time to an event.

        Args:
            file_time: File modification time (timezone-aware)
            event_start: Event start time (timezone-aware)
            event_end: Event end time (timezone-aware), or None for instantaneous events

        Returns:
            Distance in seconds (0 if file_time is within event boundaries)
        """
        # If event has an end time and file_time is within the event
        if event_end and event_start <= file_time <= event_end:
            return 0.0

        # If event is instantaneous (no end time) or file_time is before event
        if file_time <= event_start:
            return (event_start - file_time).total_seconds()

        # File_time is after event
        if event_end:
            return (file_time - event_end).total_seconds()
        else:
            return (file_time - event_start).total_seconds()

    def _interactive_event_selection(
        self, valid_events: List[tuple], file_path: Path
    ) -> Optional[Dict[str, Any]]:
        """
        Interactively prompt user to select which calendar event to link to.

        Args:
            valid_events: List of tuples (event, event_start, event_end)
            file_path: The audio file being processed

        Returns:
            Selected event dictionary or None if cancelled
        """
        event_count = len(valid_events)
        if event_count == 1:
            print(f"\n📅 One calendar event found for {file_path.name}")
        else:
            print(f"\n📅 {event_count} calendar events found for {file_path.name}")
        print("Please select which event to link to:")
        print("─" * 60)

        for i, (event, event_start, event_end) in enumerate(valid_events, 1):
            title = event.get("summary", "Untitled Event")
            start_time = event_start.strftime("%Y-%m-%d %H:%M")
            attendees = self.client.extract_attendee_names(event)
            attendee_count = len(attendees)

            print(f"{i}. {title}")
            if attendee_count > 0:
                print(f"   Attendees: {attendee_count}")
            print(f"   Time: {start_time}")
            print()

        print("─" * 60)
        print("0. Skip - Don't link this file to any event")
        print()

        event_count = len(valid_events)
        while True:
            try:
                if event_count == 1:
                    choice = input(
                        "Enter your choice (1 to link to this event, or 0 to skip): "
                    )
                else:
                    choice = input(
                        "Enter your choice (1-{}, or 0 to skip): ".format(event_count)
                    )

                if choice == "0":
                    return self.USER_CANCELLED

                choice_num = int(choice)
                if choice_num == 1 and event_count >= 1:
                    selected_event = valid_events[choice_num - 1][0]
                    return selected_event
                elif event_count > 1 and 1 <= choice_num <= event_count:
                    selected_event = valid_events[choice_num - 1][0]
                    return selected_event
                else:
                    if event_count == 1:
                        print("Please enter 1 to link to this event, or 0 to skip.")
                    else:
                        print(
                            f"Please enter a number between 1 and {event_count}, or 0 to skip."
                        )

            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                print("\nSelection cancelled.")
                return self.USER_CANCELLED
