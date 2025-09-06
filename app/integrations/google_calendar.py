"""
Google Calendar Integration for Meetscribe

This module provides integration with Google Calendar API to list past events
with attendees, descriptions, and attachment information.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from app.core.context import AppContext
from app.core.exceptions import ConfigurationError
from app.core.utils import ensure_directory_exists


class GoogleCalendarClient:
    """
    Client for interacting with Google Calendar API.

    Handles OAuth authentication, token caching, and event retrieval.
    """

    def __init__(self, ctx: AppContext):
        """
        Initialize the Google Calendar client.

        Args:
            ctx: Application context with configuration and logging

        Raises:
            ConfigurationError: If Google configuration is missing or invalid
        """
        self.ctx = ctx
        self.logger = ctx.logger

        # Load Google configuration
        google_config = ctx.config.get("google", {})
        self.credentials_file = Path(google_config.get("credentials_file", "")).expanduser()
        self.token_file = Path(google_config.get("token_file", "")).expanduser()
        self.scopes = google_config.get("scopes", [])

        if not self.credentials_file.exists():
            error_msg = (
                f"Google credentials file not found: {self.credentials_file}\n"
                "Please download credentials.json from Google Cloud Console and place it at the configured path.\n"
                "See USER_GUIDE.md for setup instructions."
            )
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)

        # Ensure token directory exists
        ensure_directory_exists(self.token_file.parent, self.logger)

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
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as token:
                    token_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(token_data, self.scopes)
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
                    self.logger.warning(f"Token refresh failed: {e}, running full OAuth flow")
                    creds = None

            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), self.scopes
                    )
                    # Try local server first, fallback to console
                    try:
                        creds = flow.run_local_server(port=0)
                        self.logger.info("OAuth flow completed via local server")
                    except Exception as e:
                        self.logger.warning(f"Local server OAuth failed: {e}, trying console")
                        creds = flow.run_console()
                        self.logger.info("OAuth flow completed via console")
                except Exception as e:
                    error_msg = f"OAuth authentication failed: {e}"
                    self.logger.error(error_msg)
                    raise ConfigurationError(error_msg)

            # Save the credentials for future runs
            try:
                token_data = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
                with open(self.token_file, 'w') as token:
                    json.dump(token_data, token)
                self.logger.debug("Saved token to file")
            except Exception as e:
                self.logger.warning(f"Failed to save token: {e}")

        # Build the service
        try:
            service = build('calendar', 'v3', credentials=creds)
            self.logger.info("Google Calendar service initialized successfully")
            return service
        except Exception as e:
            error_msg = f"Failed to build Google Calendar service: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def list_past_events(self, days: int, limit: int, calendar_id: str, filter_group_events: bool = True) -> List[Dict[str, Any]]:
        """
        List past events from Google Calendar.

        Args:
            days: Number of past days to look back
            limit: Maximum number of events to return
            calendar_id: Calendar ID to query
            filter_group_events: If True, only return events with 2 or more attendees

        Returns:
            List of event dictionaries with attendees, description, attachments
        """
        # Calculate time range
        now = datetime.utcnow()
        time_max = now.isoformat() + 'Z'
        time_min = (now - timedelta(days=days)).isoformat() + 'Z'

        self.logger.info(f"Fetching past events from {time_min} to {time_max}, limit: {limit}")

        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=limit,
                fields="items(id,summary,description,attendees(email,displayName,responseStatus),attachments(fileUrl,title,mimeType,iconLink),start,end,htmlLink),nextPageToken"
            ).execute()

            events = events_result.get('items', [])
            self.logger.info(f"Retrieved {len(events)} past events")

            # Filter events based on attendee count if requested
            if filter_group_events:
                filtered_events = []
                for event in events:
                    attendees = event.get('attendees', [])
                    if len(attendees) >= 2:
                        filtered_events.append(event)
                events = filtered_events
                self.logger.info(f"Filtered to {len(events)} group events (2 or more attendees)")

            return events

        except Exception as e:
            error_msg = f"Failed to list calendar events: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)

    @staticmethod
    def parse_event_start_local(event: Dict[str, Any]) -> str:
        """
        Parse event start time and format as local time string.

        Args:
            event: Event dictionary from Google Calendar API

        Returns:
            Formatted start time string
        """
        start = event.get('start', {})

        if 'dateTime' in start:
            # Timed event
            dt_str = start['dateTime']
            # Handle Python 3.10 compatibility by replacing Z with +00:00
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(dt_str)
            # Convert to local time
            local_dt = dt.astimezone()
            return local_dt.strftime("%Y-%m-%d %H:%M")
        elif 'date' in start:
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
        attendees = event.get('attendees', [])
        names = []

        for attendee in attendees:
            # Prefer displayName if available
            name = attendee.get('displayName')

            if not name:
                # If no displayName, use email but check for Indeed domain
                email = attendee.get('email', '')
                if email and 'indeed' in email.lower():
                    # For Indeed emails, show only username part before @
                    name = email.split('@')[0]
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
        attachments = event.get('attachments', [])
        titles = []

        for attachment in attachments:
            title = attachment.get('title')
            if not title:
                # Fallback to filename from URL
                file_url = attachment.get('fileUrl', '')
                if '/' in file_url:
                    title = file_url.split('/')[-1]
            if title:
                titles.append(title)

        return titles
