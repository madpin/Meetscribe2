"""
Meeting Notes Generator for Meetscribe.

This module provides functionality to generate Obsidian-ready meeting notes
from Google Calendar events using configurable markdown templates.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config_models import MeetingNotesConfig
from app.integrations.google_calendar import GoogleCalendarClient
from app.core.utils import sanitize_filename, ensure_directory_exists


class EventNotesGenerator:
    """
    Service for generating meeting notes from Google Calendar events.

    Uses configurable markdown templates with placeholder replacement
    for event data, attendees, and attachments.
    """

    def __init__(self, cfg: MeetingNotesConfig, logger):
        """
        Initialize the EventNotesGenerator with configuration and logger.

        Args:
            cfg: Meeting notes configuration
            logger: Logger instance
        """
        self.cfg = cfg
        self.logger = logger

    def _parse_event_times(self, event: Dict[str, Any]) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Parse event start and end times as local timezone-aware datetimes.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            Tuple of (start_datetime, end_datetime), both timezone-aware in local tz
        """
        start_info = event.get('start', {})
        end_info = event.get('end', {})

        # Handle all-day events
        if 'date' in start_info:
            # All-day event
            date_str = start_info['date']
            start_dt = datetime.fromisoformat(date_str).replace(tzinfo=datetime.now().astimezone().tzinfo)
            end_date_str = end_info.get('date', date_str)
            end_dt = datetime.fromisoformat(end_date_str).replace(tzinfo=datetime.now().astimezone().tzinfo)
            return start_dt, end_dt

        # Handle timed events
        if 'dateTime' in start_info:
            start_dt_str = start_info['dateTime']
            end_dt_str = end_info.get('dateTime', start_dt_str)

            # Handle Python 3.10 compatibility by replacing Z with +00:00
            if start_dt_str.endswith('Z'):
                start_dt_str = start_dt_str[:-1] + '+00:00'
            if end_dt_str.endswith('Z'):
                end_dt_str = end_dt_str[:-1] + '+00:00'

            start_dt = datetime.fromisoformat(start_dt_str)
            end_dt = datetime.fromisoformat(end_dt_str)

            # Convert to local timezone
            local_tz = datetime.now().astimezone().tzinfo
            start_dt = start_dt.astimezone(local_tz)
            end_dt = end_dt.astimezone(local_tz)

            return start_dt, end_dt

        return None, None

    def _render_template(self, event: Dict[str, Any]) -> str:
        """
        Render the meeting notes template with event data.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            Rendered markdown content
        """
        # Get template content
        template_content = self._get_template_content()

        # Parse event times
        local_start, local_end = self._parse_event_times(event)

        # Build replacement values
        replacements = {
            '{{TITLE}}': event.get('summary', 'Untitled Event'),
            '{{WHEN}}': self._format_event_when(local_start, local_end, event),
            '{{ATTENDEES}}': self._format_attendees(event),
            '{{ATTACHMENTS}}': self._format_attachments(event),
            '{{EVENT_LINK}}': event.get('htmlLink', ''),
            '{{CALENDAR_ID}}': event.get('organizer', {}).get('email', 'primary'),
            '{{AUTOMATIC_NOTES}}': '<!-- Add automatic notes here -->'
        }

        # Apply replacements
        content = template_content
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        return content

    def _get_template_content(self) -> str:
        """
        Get template content from file or use built-in default.

        Returns:
            Template content as string
        """
        if self.cfg.template_file.exists():
            try:
                with open(self.cfg.template_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read template file {self.cfg.template_file}: {e}")
                self.logger.warning("Using built-in default template")

        # Simple default template
        return """# {{TITLE}}

**When:** {{WHEN}}
**Attendees:** {{ATTENDEES}}

## Notes

{{AUTOMATIC_NOTES}}
"""

    def _format_event_when(self, local_start: Optional[datetime], local_end: Optional[datetime], event: Dict[str, Any]) -> str:
        """
        Format event time range for display.

        Args:
            local_start: Local start datetime
            local_end: Local end datetime
            event: Event dictionary

        Returns:
            Formatted time string
        """
        if not local_start:
            return "Unknown"

        if event.get('start', {}).get('date'):  # All-day event
            return f"{local_start.strftime('%Y-%m-%d')} (all-day)"
        else:
            start_str = local_start.strftime('%Y-%m-%d %H:%M')
            if local_end:
                end_str = local_end.strftime('%H:%M')
                return f"{start_str} — {end_str}"
            else:
                return start_str

    def _format_attendees(self, event: Dict[str, Any]) -> str:
        """
        Format attendee list for display.

        Args:
            event: Event dictionary

        Returns:
            Formatted attendee string
        """
        attendees = GoogleCalendarClient.extract_attendee_names(event)
        if not attendees:
            return "None"

        if len(attendees) <= 10:
            return ", ".join(attendees)
        else:
            return ", ".join(attendees[:10]) + f" +{len(attendees) - 10} more"

    def _format_attachments(self, event: Dict[str, Any]) -> str:
        """
        Format attachment list for display.

        Args:
            event: Event dictionary

        Returns:
            Formatted attachment string
        """
        attachments = GoogleCalendarClient.extract_attachment_titles(event)
        if not attachments:
            return "None"

        if len(attachments) <= 5:
            return ", ".join(attachments)
        else:
            return ", ".join(attachments[:5]) + f" +{len(attachments) - 5} more"

    def compute_target_stem(self, event: Dict[str, Any]) -> str:
        """
        Compute the target filename stem for an event.

        Args:
            event: Event dictionary

        Returns:
            Filename stem using configured format
        """
        local_start, _ = self._parse_event_times(event)
        if not local_start:
            return "unknown_date_untitled"

        date_str = local_start.strftime(self.cfg.date_format)
        title = event.get('summary', 'Untitled Event')
        sanitized_title = sanitize_filename(title)

        return self.cfg.filename_format.format(date=date_str, title=sanitized_title)

    def create_note_for_event(self, event: Dict[str, Any]) -> Path:
        """
        Create a meeting note file for the given event.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            Path to the created note file

        Raises:
            Exception: If file creation fails
        """
        # Ensure output directory exists
        ensure_directory_exists(self.cfg.output_folder, self.logger)

        # Compute target filename
        stem = self.compute_target_stem(event)
        filename = f"{stem}.{self.cfg.output_extension}"
        target_path = self.cfg.output_folder / filename

        # Handle file conflicts by adding unique suffix
        if target_path.exists():
            counter = 1
            while True:
                unique_filename = f"{stem}_{counter}.{self.cfg.output_extension}"
                unique_path = self.cfg.output_folder / unique_filename
                if not unique_path.exists():
                    target_path = unique_path
                    break
                counter += 1

        # Render template
        content = self._render_template(event)

        # Write file
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Created meeting note: {target_path}")
            return target_path
        except Exception as e:
            self.logger.error(f"Failed to create meeting note {target_path}: {e}")
            raise
