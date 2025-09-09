"""
Google Calendar Integration for Meetscribe

This module provides integration with Google Calendar API to list past events
with attendees, descriptions, and attachment information.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from app.core.config_models import GoogleConfig
from app.core.exceptions import ConfigurationError, GoogleCalendarError
from app.core.utils import ensure_directory_exists


class GoogleCalendarClient:
    """
    Client for interacting with Google Calendar API.

    Handles OAuth authentication, token caching, and event retrieval.
    """

    def __init__(self, cfg: GoogleConfig, logger):
        """
        Initialize the Google Calendar client.

        Args:
            cfg: Google configuration
            logger: Logger instance

        Raises:
            ConfigurationError: If Google credentials file is missing
            GoogleCalendarError: If service initialization fails
        """
        self.cfg = cfg
        self.logger = logger

        if not self.cfg.credentials_file.exists():
            error_msg = (
                f"Google credentials file not found: {self.cfg.credentials_file}\n"
                "Please download credentials.json from Google Cloud Console and place it at the configured path.\n"
                "See USER_GUIDE.md for setup instructions."
            )
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)

        # Ensure token directory exists
        ensure_directory_exists(self.cfg.token_file.parent, self.logger)

        # Initialize the service
        self.service = self._get_service()

    def _get_service(self):
        """
        Get authenticated Google Calendar service.

        Handles OAuth flow and token refresh/caching.

        Returns:
            Google Calendar API service instance

        Raises:
            ConfigurationError: If authentication fails
        """
        creds = None

        # Load existing token if available
        if self.cfg.token_file.exists():
            try:
                with open(self.cfg.token_file, "r") as token:
                    token_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(
                        token_data, self.cfg.scopes
                    )
                self.logger.debug("Loaded existing token from file")
            except Exception as e:
                self.logger.warning(f"Failed to load existing token: {e}")

        # If no valid credentials available, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info("Refreshed expired token")
                except Exception as e:
                    self.logger.warning(
                        f"Token refresh failed: {e}, running full OAuth flow"
                    )
                    creds = None

            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.cfg.credentials_file), self.cfg.scopes
                    )
                    # Try local server first, fallback to console
                    try:
                        creds = flow.run_local_server(port=0)
                        self.logger.info("OAuth flow completed via local server")
                    except Exception as e:
                        self.logger.warning(
                            f"Local server OAuth failed: {e}, trying console"
                        )
                        creds = flow.run_console()
                        self.logger.info("OAuth flow completed via console")
                except Exception as e:
                    self.logger.error(f"OAuth authentication failed: {e}")
                    raise GoogleCalendarError(
                        f"OAuth authentication failed: {e}"
                    ) from e

            # Save the credentials for future runs
            try:
                token_data = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                }
                with open(self.cfg.token_file, "w") as token:
                    json.dump(token_data, token)
                self.logger.debug("Saved token to file")
            except Exception as e:
                self.logger.warning(f"Failed to save token: {e}")

        # Build the service
        try:
            service = build("calendar", "v3", credentials=creds)
            self.logger.info("Google Calendar service initialized successfully")
            return service
        except Exception as e:
            self.logger.error(f"Failed to build Google Calendar service: {e}")
            raise GoogleCalendarError(
                f"Failed to initialize Google Calendar service: {e}"
            ) from e

    def list_past_events(
        self,
        days: Optional[int] = None,
        limit: Optional[int] = None,
        calendar_id: Optional[str] = None,
        filter_group_events: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        List past events from Google Calendar.

        Args:
            days: Number of past days to look back (uses config default if None)
            limit: Maximum number of events to return (uses config default if None)
            calendar_id: Calendar ID to query (uses config default if None)
            filter_group_events: If True, only return events with 2 or more attendees (uses config default if None)

        Returns:
            List of event dictionaries with attendees, description, attachments

        Raises:
            GoogleCalendarError: If API call fails
        """
        # Use config defaults if parameters not provided
        days = days if days is not None else self.cfg.default_past_days
        limit = limit if limit is not None else self.cfg.max_results
        calendar_id = calendar_id if calendar_id is not None else self.cfg.calendar_id
        filter_group_events = (
            filter_group_events
            if filter_group_events is not None
            else self.cfg.filter_group_events_only
        )

        # Calculate time range
        now = datetime.utcnow()
        time_max = now.isoformat() + "Z"
        time_min = (now - timedelta(days=days)).isoformat() + "Z"

        self.logger.info(
            f"Fetching past events from {time_min} to {time_max}, limit: {limit}"
        )

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=limit,
                    fields="items(id,summary,description,attendees(email,displayName,responseStatus),attachments(fileUrl,title,mimeType,iconLink),start,end,htmlLink),nextPageToken",
                )
                .execute()
            )

            events = events_result.get("items", [])
            self.logger.info(f"Retrieved {len(events)} past events")

            # Filter events based on attendee count if requested
            if filter_group_events:
                filtered_events = []
                for event in events:
                    attendees = event.get("attendees", [])
                    if len(attendees) >= 2:
                        filtered_events.append(event)
                events = filtered_events
                self.logger.info(
                    f"Filtered to {len(events)} group events (2 or more attendees)"
                )

            return events

        except Exception as e:
            self.logger.error(f"Failed to list calendar events: {e}")
            raise GoogleCalendarError(f"Failed to list calendar events: {e}") from e

    def list_events_between(
        self,
        start: datetime,
        end: datetime,
        calendar_id: Optional[str] = None,
        filter_group_events: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List events between two datetime objects from Google Calendar.

        Args:
            start: Start datetime (timezone-aware)
            end: End datetime (timezone-aware)
            calendar_id: Calendar ID to query (uses config default if None)
            filter_group_events: If True, only return events with 2 or more attendees (uses config default if None)
            limit: Maximum number of events to return (uses config default if None)

        Returns:
            List of event dictionaries with attendees, description, attachments

        Raises:
            GoogleCalendarError: If API call fails
        """
        # Use config defaults if parameters not provided
        limit = limit if limit is not None else self.cfg.max_results
        calendar_id = calendar_id if calendar_id is not None else self.cfg.calendar_id
        filter_group_events = (
            filter_group_events
            if filter_group_events is not None
            else self.cfg.filter_group_events_only
        )

        # Convert to UTC and format as ISO8601 with 'Z'
        import datetime

        start_utc = (
            start.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        )
        end_utc = (
            end.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        )

        self.logger.info(
            f"Fetching events between {start_utc} and {end_utc}, limit: {limit}"
        )

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start_utc,
                    timeMax=end_utc,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=limit,
                    fields="items(id,summary,description,attendees(email,displayName,responseStatus),attachments(fileUrl,title,mimeType,iconLink),start,end,htmlLink),nextPageToken",
                )
                .execute()
            )

            events = events_result.get("items", [])
            self.logger.info(f"Retrieved {len(events)} events between specified times")

            # Filter events based on attendee count if requested
            if filter_group_events:
                filtered_events = []
                for event in events:
                    attendees = event.get("attendees", [])
                    if len(attendees) >= 2:
                        filtered_events.append(event)
                events = filtered_events
                self.logger.info(
                    f"Filtered to {len(events)} group events (2 or more attendees)"
                )

            return events

        except Exception as e:
            self.logger.error(f"Failed to list calendar events between times: {e}")
            raise GoogleCalendarError(
                f"Failed to list calendar events between times: {e}"
            ) from e

    def list_upcoming_events(
        self,
        days: Optional[int] = None,
        limit: Optional[int] = None,
        calendar_id: Optional[str] = None,
        filter_group_events: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        List upcoming events from Google Calendar.

        Args:
            days: Number of days to look ahead (uses config default if None)
            limit: Maximum number of events to return (uses config default if None)
            calendar_id: Calendar ID to query (uses config default if None)
            filter_group_events: If True, only return events with 2 or more attendees (uses config default if None)

        Returns:
            List of event dictionaries with attendees, description, attachments

        Raises:
            GoogleCalendarError: If API call fails
        """
        # Use config defaults if parameters not provided
        days = days if days is not None else self.cfg.default_past_days
        limit = limit if limit is not None else self.cfg.max_results
        calendar_id = calendar_id if calendar_id is not None else self.cfg.calendar_id
        filter_group_events = (
            filter_group_events
            if filter_group_events is not None
            else self.cfg.filter_group_events_only
        )

        # Calculate time range from start of today to future
        now = datetime.utcnow()
        # Start from beginning of today to include today's events
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today_start + timedelta(days=days)
        time_max = end.isoformat() + "Z"
        time_min = today_start.isoformat() + "Z"

        self.logger.info(
            f"Fetching upcoming events from {time_min} to {time_max}, limit: {limit}"
        )

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=limit,
                    fields="items(id,summary,description,attendees(email,displayName,responseStatus),attachments(fileUrl,title,mimeType,iconLink),start,end,htmlLink),nextPageToken",
                )
                .execute()
            )

            events = events_result.get("items", [])
            self.logger.info(f"Retrieved {len(events)} upcoming events")

            # Filter events based on attendee count if requested
            if filter_group_events:
                filtered_events = []
                for event in events:
                    attendees = event.get("attendees", [])
                    if len(attendees) >= 2:
                        filtered_events.append(event)
                events = filtered_events
                self.logger.info(
                    f"Filtered to {len(events)} group events (2 or more attendees)"
                )

            return events

        except Exception as e:
            self.logger.error(f"Failed to list upcoming calendar events: {e}")
            raise GoogleCalendarError(
                f"Failed to list upcoming calendar events: {e}"
            ) from e

    def list_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_id: Optional[str] = None,
        filter_group_events: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List events in a specific date range from Google Calendar.

        Args:
            start_date: Start date for the range
            end_date: End date for the range
            calendar_id: Calendar ID to query (uses config default if None)
            filter_group_events: If True, only return events with 2 or more attendees (uses config default if None)
            limit: Maximum number of events to return (uses config default if None)

        Returns:
            List of event dictionaries with attendees, description, attachments

        Raises:
            GoogleCalendarError: If API call fails
        """
        # Use config defaults if parameters not provided
        limit = limit if limit is not None else self.cfg.max_results
        calendar_id = calendar_id if calendar_id is not None else self.cfg.calendar_id
        filter_group_events = (
            filter_group_events
            if filter_group_events is not None
            else self.cfg.filter_group_events_only
        )

        # Convert to UTC and format as ISO8601 with 'Z'
        import datetime

        start_utc = (
            start_date.astimezone(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        end_utc = (
            end_date.astimezone(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        self.logger.info(
            f"Fetching events from {start_utc} to {end_utc}, limit: {limit}"
        )

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start_utc,
                    timeMax=end_utc,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=limit,
                    fields="items(id,summary,description,attendees(email,displayName,responseStatus),attachments(fileUrl,title,mimeType,iconLink),start,end,htmlLink),nextPageToken",
                )
                .execute()
            )

            events = events_result.get("items", [])
            self.logger.info(f"Retrieved {len(events)} events in range")

            # Filter events based on attendee count if requested
            if filter_group_events:
                filtered_events = []
                for event in events:
                    attendees = event.get("attendees", [])
                    if len(attendees) >= 2:
                        filtered_events.append(event)
                events = filtered_events
                self.logger.info(
                    f"Filtered to {len(events)} group events (2 or more attendees)"
                )

            return events

        except Exception as e:
            self.logger.error(f"Failed to list calendar events in range: {e}")
            raise GoogleCalendarError(
                f"Failed to list calendar events in range: {e}"
            ) from e

    @staticmethod
    def parse_event_start_local(event: Dict[str, Any]) -> str:
        """
        Parse event start time and format as local time string.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            Formatted start time string
        """
        start = event.get("start", {})

        if "dateTime" in start:
            # Timed event
            dt_str = start["dateTime"]
            # Handle Python 3.10 compatibility by replacing Z with +00:00
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(dt_str)
            # Convert to local time
            local_dt = dt.astimezone()
            return local_dt.strftime("%Y-%m-%d %H:%M")
        elif "date" in start:
            # All-day event
            return f"{start['date']} (all-day)"
        else:
            return "-"

    @staticmethod
    def extract_attendee_names(event: Dict[str, Any]) -> List[str]:
        """
        Extract attendee names from event.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            List of attendee names (prefer displayName, fallback to email)
        """
        attendees = event.get("attendees", [])
        names = []

        for attendee in attendees:
            # Prefer displayName if available
            name = attendee.get("displayName")

            if not name:
                # If no displayName, use email but check for Indeed domain
                email = attendee.get("email", "")
                if email and "indeed" in email.lower():
                    # For Indeed emails, show only username part before @
                    name = email.split("@")[0]
                else:
                    name = email

            if name:
                names.append(name)

        return names

    @staticmethod
    def extract_attachment_titles(event: Dict[str, Any]) -> List[str]:
        """
        Extract attachment titles from event.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            List of attachment titles
        """
        attachments = event.get("attachments", [])
        titles = []

        for attachment in attachments:
            title = attachment.get("title")
            if not title:
                # Fallback to filename from URL
                file_url = attachment.get("fileUrl", "")
                if "/" in file_url:
                    title = file_url.split("/")[-1]
            if title:
                titles.append(title)

        return titles
