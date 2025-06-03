import datetime
import json
from typing import Any, Dict, List, Optional, Union

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials as GoogleCredentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError as GoogleHttpError
from hayhooks import log as logger
from haystack.core.component import component

from components.google.dataclasses.google_calendar_models import EventAttendee, EventDateTime, EventPerson, GoogleCalendarEvent
from components.google.google_errors import (
    GoogleAPIError,
    GoogleAuthError,
    InvalidInputError,
)
from components.google.google_oauth import GoogleOAuth

DEFAULT_PROBLEM_TYPE_URI = "urn:hayhooks:google:calendar:error:"  # For RFC 7807 type URI prefix

# Consider moving to a shared config or constants file
DEFAULT_CALENDAR_ID = "primary"
DEFAULT_MAX_RESULTS_GET = 50
DEFAULT_MAX_RESULTS_SEARCH = 10


@component
class GoogleCalendarReader:
    """
    A Haystack component to read events from Google Calendar.

    Handles fetching events by ID, date range, and searching events.
    Uses GoogleOAuth for authentication.
    """

    def __init__(
        self,
        google_oauth_provider: GoogleOAuth = GoogleOAuth(),
        default_user_id: Optional[str] = None,
    ):
        """
        Initializes the GoogleCalendarReader component.

        Args:
            google_oauth_provider: An instance of the GoogleOAuth class from components.google_oauth.
            default_user_id: The default user ID to use for Google API calls if not specified in the run method.
        """
        if not isinstance(google_oauth_provider, GoogleOAuth):
            raise ValueError("google_oauth_provider must be an instance of GoogleOAuth")
        self.google_oauth_provider = google_oauth_provider
        self.default_user_id = default_user_id

    def _get_calendar_service(self, user_id: str) -> Resource:
        """
        Retrieves an authenticated Google Calendar API service client.
        """
        credentials = self.google_oauth_provider.load_credentials(user_id)
        if not credentials or not isinstance(credentials, GoogleCredentials):
            raise GoogleAuthError(f"Failed to load valid Google credentials for user '{user_id}'. Please authenticate.", requires_reauth=True)
        if credentials.expired and credentials.refresh_token:
            try:
                logger.info(f"Google credentials expired for user '{user_id}'. Refreshing...")
                credentials.refresh(GoogleAuthRequest())
                self.google_oauth_provider.save_credentials(user_id, credentials)
                logger.info(f"Successfully refreshed Google credentials for user '{user_id}'.")
            except Exception as e:
                logger.error(f"Failed to refresh Google credentials for user '{user_id}': {e}")
                raise GoogleAuthError(f"Failed to refresh Google credentials for user '{user_id}': {e}. Please re-authenticate.", requires_reauth=True) from e

        try:
            service: Resource = build("calendar", "v3", credentials=credentials, static_discovery=False)
            return service
        except Exception as e:
            logger.error(f"Failed to build Google Calendar service: {e}")
            raise GoogleAPIError(f"Failed to build Google Calendar service: {e}") from e

    def _parse_event_data(self, event_data: Dict[str, Any]) -> GoogleCalendarEvent:
        """Converts raw Google API event data to GoogleCalendarEvent Pydantic model."""

        def parse_event_dt(dt_data: Optional[Dict[str, str]]) -> Optional[EventDateTime]:
            if not dt_data:
                return None

            dt_value = None
            if "dateTime" in dt_data and dt_data["dateTime"]:
                try:
                    # Handle 'Z' for UTC and other timezone offsets
                    dt_str = dt_data["dateTime"]
                    if dt_str.endswith("Z"):
                        dt_str = dt_str[:-1] + "+00:00"
                    dt_value = datetime.datetime.fromisoformat(dt_str)
                except ValueError as ve:
                    logger.warning(f"Could not parse dateTime: {dt_data['dateTime']}. Error: {ve}")

            date_value = None
            if "date" in dt_data and dt_data["date"]:
                try:
                    date_value = datetime.date.fromisoformat(dt_data["date"])
                except ValueError as ve:
                    logger.warning(f"Could not parse date: {dt_data['date']}. Error: {ve}")

            return EventDateTime(dateTime=dt_value, date=date_value, timeZone=dt_data.get("timeZone"))

        def parse_person(person_data: Optional[Dict[str, Any]]) -> Optional[EventPerson]:
            if not person_data:
                return None
            return EventPerson(email=person_data.get("email"), displayName=person_data.get("displayName"), self=person_data.get("self"))

        def parse_attendees(attendees_data: Optional[List[Dict[str, Any]]]) -> Optional[List[EventAttendee]]:
            if not attendees_data:
                return None
            parsed_attendees = []
            for att in attendees_data:
                parsed_attendees.append(
                    EventAttendee(
                        email=att.get("email"),
                        displayName=att.get("displayName"),
                        organizer=att.get("organizer"),
                        self=att.get("self"),
                        resource=att.get("resource"),
                        optional=att.get("optional"),
                        responseStatus=att.get("responseStatus"),
                        comment=att.get("comment"),
                        additionalGuests=att.get("additionalGuests"),
                    )
                )
            return parsed_attendees

        created_dt = None
        if event_data.get("created"):
            try:
                created_str = event_data["created"]
                if created_str.endswith("Z"):
                    created_str = created_str[:-1] + "+00:00"
                created_dt = datetime.datetime.fromisoformat(created_str)
            except ValueError as ve:
                logger.warning(f"Could not parse created timestamp: {event_data['created']}. Error: {ve}")

        updated_dt = None
        if event_data.get("updated"):
            try:
                updated_str = event_data["updated"]
                if updated_str.endswith("Z"):
                    updated_str = updated_str[:-1] + "+00:00"
                updated_dt = datetime.datetime.fromisoformat(updated_str)
            except ValueError as ve:
                logger.warning(f"Could not parse updated timestamp: {event_data['updated']}. Error: {ve}")

        return GoogleCalendarEvent(
            id=event_data["id"],  # id is mandatory
            status=event_data.get("status"),
            htmlLink=event_data.get("htmlLink"),
            created=created_dt,
            updated=updated_dt,
            summary=event_data.get("summary"),
            description=event_data.get("description"),
            location=event_data.get("location"),
            creator=parse_person(event_data.get("creator")),
            organizer=parse_person(event_data.get("organizer")),
            start=parse_event_dt(event_data.get("start")),
            end=parse_event_dt(event_data.get("end")),
            attendees=parse_attendees(event_data.get("attendees")),
            hangoutLink=event_data.get("hangoutLink"),
            recurringEventId=event_data.get("recurringEventId"),
        )

    def _create_rfc7807_problem(self, title: str, status: int, detail: str, error_type: str, instance_suffix: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Creates an RFC 7807 problem details dictionary."""
        problem = {"type": f"{DEFAULT_PROBLEM_TYPE_URI}{error_type}", "title": title, "status": status, "detail": detail, "instance": f"/calendar_events/errors/{instance_suffix or title.lower().replace(' ', '-')}"}
        problem.update(kwargs)  # Add any additional properties
        return problem

    def _handle_google_api_error(self, e: GoogleHttpError, resource_type: Optional[str] = None, resource_id: Optional[str] = None) -> Dict[str, Any]:
        """Handles GoogleHttpError and returns an RFC 7807 problem details dictionary."""
        status_code = e.resp.status

        try:
            error_content = e.content.decode()
            error_details_json = json.loads(error_content)
            message = error_details_json.get("error", {}).get("message", str(e))
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            message = f"Google API error (status {status_code}): {str(e)}"

        logger.error(f"Google API Error. Status: {status_code}, Message: {message}, Original: {e}")

        if status_code == 401:
            return self._create_rfc7807_problem(title="Authentication Error", status=401, detail=message, error_type="GoogleAuthError", instance_suffix=f"auth-{resource_id or 'general'}", requires_reauth=True)
        elif status_code == 403:
            return self._create_rfc7807_problem(title="Insufficient Permissions", status=403, detail=message, error_type="InsufficientPermissionsError", instance_suffix=f"perms-{resource_id or 'general'}")
        elif status_code == 404:
            not_found_message = f"Google {resource_type or 'resource'} '{resource_id or ''}' not found. API detail: {message}"
            return self._create_rfc7807_problem(
                title="Resource Not Found", status=404, detail=not_found_message, error_type="ResourceNotFoundError", instance_suffix=f"notfound-{resource_id or 'general'}", resource_type=resource_type, resource_id=resource_id
            )
        elif status_code == 429:
            return self._create_rfc7807_problem(title="Rate Limit Exceeded", status=429, detail=message, error_type="RateLimitError", instance_suffix=f"ratelimit-{resource_id or 'general'}")
        else:
            return self._create_rfc7807_problem(title="Google API Error", status=status_code, detail=message, error_type="GoogleAPIError", instance_suffix=f"api-{status_code}-{resource_id or 'general'}", original_error_type=type(e).__name__)

    @component.output_types(events=List[GoogleCalendarEvent])  # This output_type might need adjustment if errors are returned directly
    def run(
        self,
        user_id: str,
        calendar_id: str = DEFAULT_CALENDAR_ID,
        event_id: Optional[str] = None,
        start_time: Optional[Union[str, datetime.datetime, datetime.date]] = None,
        end_time: Optional[Union[str, datetime.datetime, datetime.date]] = None,
        query: Optional[str] = None,
        max_results: Optional[int] = None,
        single_events: bool = True,  # For recurring events, return single instances
        order_by: str = "startTime",  # "startTime" or "updated"
    ) -> Dict[str, Any]:  # Changed return type
        """
        Fetches or searches Google Calendar events.

        Args:
            user_id: The user ID for Google authentication.
            calendar_id: The calendar ID. Defaults to "primary".
            event_id: If provided, fetches a specific event by its ID. `start_time`, `end_time`, `query`, `max_results` are ignored.
            start_time: The start of the time range (ISO format string, datetime, or date). Required if `event_id` and `query` are not set.
            end_time: The end of the time range (ISO format string, datetime, or date).
            query: Text search query. If provided, `event_id`, `start_time`, `end_time` are used as filters if also set.
            max_results: Maximum number of events to return.
            single_events: Whether to expand recurring events into instances.
            order_by: Order of the events returned ("startTime" or "updated").

        Returns:
            A dictionary with a list of `GoogleCalendarEvent` objects under the "events" key, or an RFC 7807 error object.
        """
        active_user_id = user_id or self.default_user_id
        if not active_user_id:
            # This is a programming error, not a user input error for RFC 7807
            logger.error("ValueError: No active_user_id found! This indicates a configuration or programming issue.")
            raise ValueError("No active_user_id found!")

        try:
            service = self._get_calendar_service(active_user_id)
        except GoogleAuthError as e:
            logger.warning(f"GoogleAuthError during service acquisition in GoogleCalendarReader: {e}", exc_info=True)
            return self._create_rfc7807_problem(title="Authentication Error", status=401, detail=str(e), error_type="GoogleAuthError", instance_suffix="auth-service-acquisition", requires_reauth=e.requires_reauth)

        events_data: List[Dict[str, Any]] = []

        try:
            if event_id:
                logger.info(f"Fetching event by ID: {event_id} from calendar: {calendar_id} for user: {active_user_id}")
                event_item = service.events().get(calendarId=calendar_id, eventId=event_id).execute()  # type: ignore
                events_data.append(event_item)
            else:
                request_params: Dict[str, Any] = {"calendarId": calendar_id}

                if query:
                    logger.info(f"Searching events with query: '{query}' in calendar: {calendar_id} for user: {active_user_id}")
                    request_params["q"] = query
                    # Google API uses timeMin/timeMax for search query filtering as well
                    if start_time:
                        request_params["timeMin"] = self._format_datetime_for_api(start_time)
                    if end_time:
                        request_params["timeMax"] = self._format_datetime_for_api(end_time)

                elif start_time:  # Date range query if no event_id and no query
                    logger.info(f"Fetching events by date range for calendar: {calendar_id}, user: {active_user_id}")
                    request_params["timeMin"] = self._format_datetime_for_api(start_time, is_start=True)
                    if end_time:
                        request_params["timeMax"] = self._format_datetime_for_api(end_time, is_end=True)
                    else:
                        # If only start_time is provided, Google API might require timeMax or it defaults.
                        # For clarity, let's default to fetching for a single day if end_time is missing.
                        # Or raise error if end_time is strictly required for range.
                        # Google API: If timeMax is not specified, the query returns all events starting after timeMin.
                        # This might be too many. Let's require end_time if start_time is given for range queries.
                        # Design doc implies start_time and end_time for range.
                        raise InvalidInputError("end_time is required when start_time is provided for a date range query (and not using event_id or query).")

                else:  # Neither event_id, query, nor start_time provided
                    raise InvalidInputError("Either event_id, query, or start_time must be provided.")

                request_params["singleEvents"] = single_events
                request_params["orderBy"] = order_by

                if max_results is None:
                    request_params["maxResults"] = DEFAULT_MAX_RESULTS_GET if not query else DEFAULT_MAX_RESULTS_SEARCH
                elif max_results > 0:
                    request_params["maxResults"] = max_results

                    logger.debug(f"Google Calendar API request params: {request_params}")
                    events_result = service.events().list(**request_params).execute()  # type: ignore
                    events_data = events_result.get("items", [])

                # Handle pagination if necessary (simplified for now, gets first page based on max_results)
                # while events_result.get('nextPageToken') and (max_results is None or len(events_data) < max_results):
                #     request_params['pageToken'] = events_result.get('nextPageToken')
                #     events_result = service.events().list(**request_params).execute()
                #     events_data.extend(events_result.get("items", []))
                # if max_results is not None and len(events_data) > max_results:
                #     events_data = events_data[:max_results]

            parsed_events = [self._parse_event_data(event) for event in events_data]
            logger.info(f"Successfully fetched and parsed {len(parsed_events)} events.")
            logger.debug(f"Returning events: {parsed_events}")
            return {"events": parsed_events}

        except GoogleHttpError as e:
            logger.error(f"GoogleHttpError caught in run method: {e}", exc_info=True)
            # _handle_google_api_error now returns a problem dictionary
            problem_details = self._handle_google_api_error(e, resource_type="CalendarEvent", resource_id=event_id or calendar_id)
            return problem_details
        except InvalidInputError as e:
            logger.warning(f"InvalidInputError in GoogleCalendarReader: {e}", exc_info=True)
            return self._create_rfc7807_problem(title="Invalid Input", status=400, detail=str(e), error_type="InvalidInputError", instance_suffix="invalid-input", parameter_name=e.parameter_name)
        except GoogleAuthError as e:  # Should ideally be caught by the service acquisition block, but as a fallback
            logger.warning(f"GoogleAuthError in GoogleCalendarReader main block: {e}", exc_info=True)
            return self._create_rfc7807_problem(title="Authentication Error", status=401, detail=str(e), error_type="GoogleAuthError", instance_suffix="auth-error-main", requires_reauth=e.requires_reauth)
        except GoogleAPIError as e:  # This includes InsufficientPermissionsError, ResourceNotFoundError, RateLimitError if they were raised directly
            logger.error(f"GoogleAPIError in GoogleCalendarReader: {e}", exc_info=True)
            return self._create_rfc7807_problem(title=type(e).__name__, status=e.status_code or 500, detail=str(e), error_type=type(e).__name__, instance_suffix=f"api-error-{type(e).__name__.lower()}-{e.status_code or 'unknown'}")
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error in GoogleCalendarReader: {e}", exc_info=True)
            return self._create_rfc7807_problem(title="Unexpected Server Error", status=500, detail=f"An unexpected error occurred: {str(e)}", error_type="UnexpectedServerError", instance_suffix="unexpected-server-error")

    def _format_datetime_for_api(self, dt_input: Union[str, datetime.datetime, datetime.date], is_start: bool = False, is_end: bool = False) -> str:
        """Formats datetime input to RFC3339 string for Google API."""
        if isinstance(dt_input, str):
            try:
                # Attempt to parse as full datetime first
                dt_obj = datetime.datetime.fromisoformat(dt_input)
            except ValueError:
                # Attempt to parse as date only
                try:
                    dt_obj = datetime.date.fromisoformat(dt_input)
                except ValueError:
                    raise InvalidInputError(f"Invalid date/datetime string format: '{dt_input}'. Use ISO format.")
        elif isinstance(dt_input, datetime.datetime):
            dt_obj = dt_input
        elif isinstance(dt_input, datetime.date):
            dt_obj = dt_input
        else:
            raise InvalidInputError(f"Unsupported datetime type: {type(dt_input)}. Use str, datetime.datetime, or datetime.date.")

        if isinstance(dt_obj, datetime.date) and not isinstance(dt_obj, datetime.datetime):
            # If it's a date object, convert to datetime for timeMin/timeMax
            if is_start:  # For timeMin, use start of the day
                dt_obj_conv = datetime.datetime.combine(dt_obj, datetime.time.min)
            elif is_end:  # For timeMax, use end of the day
                dt_obj_conv = datetime.datetime.combine(dt_obj, datetime.time.max)
            else:  # Default to start of day if context unclear
                dt_obj_conv = datetime.datetime.combine(dt_obj, datetime.time.min)

            # If original was date, assume it's meant to be treated as local time then converted to UTC if naive
            # However, Google API expects UTC. If it's a date, it's usually for an all-day event or local interpretation.
            # For timeMin/timeMax, it's safer to ensure timezone awareness.
            # If the original date was naive, we assume local time and then convert to UTC.
            # This part can be tricky. For simplicity, if it's a date, we'll make it timezone-aware UTC.
            # A better approach might involve knowing the user's local timezone.
            if dt_obj_conv.tzinfo is None:
                dt_obj_conv = dt_obj_conv.replace(tzinfo=datetime.timezone.utc)  # Assume UTC if naive date
            dt_obj = dt_obj_conv

        if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
            # If still naive, assume UTC. This is a common convention for APIs.
            dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)

        return dt_obj.isoformat()
