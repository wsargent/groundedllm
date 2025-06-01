import datetime
from typing import Optional, Union

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline

from components.google.google_calendar_reader import DEFAULT_CALENDAR_ID, DEFAULT_MAX_RESULTS_GET, GoogleCalendarReader
from components.google.google_errors import GoogleAPIError, GoogleAuthError, InvalidInputError  # To catch and potentially re-wrap if needed, or let Hayhooks handle RFC 7807


class PipelineWrapper(BasePipelineWrapper):
    """
    Pipeline wrapper for the 'get_calendar_events' MCP tool.
    Fetches Google Calendar events based on specified criteria.
    """

    def setup(self) -> None:
        logger.info("Setting up GetCalendarEvents pipeline...")

        pipe = Pipeline()
        calendar_reader = GoogleCalendarReader()
        pipe.add_component("calendar_reader", calendar_reader)
        self.pipeline = pipe
        logger.info("GetCalendarEvents pipeline setup complete.")

    def run_api(
        self,
        user_id: Optional[str] = None,
        calendar_id: str = DEFAULT_CALENDAR_ID,
        start_time: Optional[Union[str, datetime.datetime, datetime.date]] = None,
        end_time: Optional[Union[str, datetime.datetime, datetime.date]] = None,
        event_id: Optional[str] = None,
        max_results: int = DEFAULT_MAX_RESULTS_GET,
        query: Optional[str] = None,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> dict:
        """
        Fetches Google Calendar events.

        Args:
            user_id: The user ID for Google authentication.
            calendar_id: Calendar identifier. Defaults to 'primary'.
            start_time: Start time for the event search (ISO format string, datetime, or date).
            end_time: End time for the event search (ISO format string, datetime, or date).
            event_id: Specific event ID to fetch.
            max_results: Maximum number of events to return.
            query: Text query to search events.
            single_events: Whether to expand recurring events.
            order_by: Sort order ("startTime" or "updated").

        Returns:
            A dictionary containing a list of GoogleCalendarEvent objects under the key "events".

        Raises:
            HTTPException: For errors that should be converted to RFC 7807 by Hayhooks.
                         Specifically GoogleAuthError, GoogleAPIError, InvalidInputError.
        """
        if not self.pipeline:
            logger.error("GetCalendarEvents pipeline is not configured correctly. Missing OAuth details or components.")
            # This will be caught by Hayhooks and turned into a 500
            raise RuntimeError("Pipeline not configured due to missing Google OAuth environment variables.")

        selected_user_id = user_id or self.calendar_reader.default_user_id
        logger.debug(f"Running get_calendar_events with user_id='{selected_user_id}', calendar_id='{calendar_id}', event_id='{event_id}', start_time='{start_time}', end_time='{end_time}', query='{query}', max_results={max_results}")

        try:
            pipeline_input = {
                "calendar_reader": {
                    "user_id": selected_user_id,  # Will use component's default_user_id if None
                    "calendar_id": calendar_id,
                    "event_id": event_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "query": query,
                    "max_results": max_results,
                    "single_events": single_events,
                    "order_by": order_by,
                }
            }

            result = self.pipeline.run(pipeline_input)

            return {"events": result.get("calendar_reader", {}).get("events", [])}

        except (GoogleAuthError, GoogleAPIError, InvalidInputError) as e:
            logger.warning(f"Error during GetCalendarEvents execution: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GetCalendarEvents pipeline: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in GetCalendarEvents: {str(e)}")
