import os
from typing import Optional

import requests

DEFAULT_CALENDAR_ID = "primary"
DEFAULT_MAX_RESULTS_GET = 50
DEFAULT_MAX_RESULTS_SEARCH = 10


def search_calendars(
    user_id: str = os.getenv("HAYHOOKS_USER_ID"),
    calendar_id: str = DEFAULT_CALENDAR_ID,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    event_id: Optional[str] = None,
    max_results: int = DEFAULT_MAX_RESULTS_GET,
    query: Optional[str] = None,
    single_events: bool = True,
    order_by: str = "startTime",
) -> str:
    """
    Fetches Google Calendar events.  Either event_id, query, or start_time must be provided.

    Make sure to use the user's timezone if specifying a day start time and end time.

    Args:
        user_id: The user ID for Google authentication.  Call "google_auth" if you don't have this.
        calendar_id: Calendar identifier. Defaults to 'primary'.
        start_time: Start time for the event search (ISO format string, e.g., "2024-01-01T00:00:00Z").
        end_time: End time for the event search (ISO format string, e.g., "2024-01-02T00:00:00Z").
        event_id: Specific event ID to fetch. If provided, other filters like time range might be ignored by the API.
        max_results: Maximum number of events to return.
        query: Text query to search events (e.g., "Meeting with John").
        single_events: Whether to expand recurring events into single instances. Defaults to True.
        order_by: Sort order of events. Can be "startTime" or "updated". Defaults to "startTime".

    Returns:
        A dictionary containing a list of GoogleCalendarEvent objects under the key "events".
        Example: {"events": [GoogleCalendarEvent(...), ...]}
    """

    payload = {
        "user_id": user_id,
        "calendar_id": calendar_id,
        "start_time": start_time,
        "end_time": end_time,
        "event_id": event_id,
        "max_results": max_results,
        "query": query,
        "single_events": single_events,
        "order_by": order_by,
    }

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    response = requests.post(f"{hayhooks_base_url}/search_calendars/run", json=payload)

    # response.raise_for_status()
    json_response = response.json()

    if "result" in json_response:
        result = json_response["result"]
        return result
    else:
        return f"Internal error: {json_response}"
