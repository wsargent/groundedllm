import datetime
from typing import Any, Dict, Optional, Union  # Added Dict, Any

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline

from components.google.google_calendar_reader import DEFAULT_CALENDAR_ID, DEFAULT_MAX_RESULTS_GET, GoogleCalendarReader

# Define a default URI for problem details, similar to the component
DEFAULT_PROBLEM_TYPE_URI = "https://example.com/probs/"


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
        user_id: str,
        calendar_id: str = DEFAULT_CALENDAR_ID,
        start_time: Optional[Union[str, datetime.datetime, datetime.date]] = None,
        end_time: Optional[Union[str, datetime.datetime, datetime.date]] = None,
        event_id: Optional[str] = None,
        max_results: int = DEFAULT_MAX_RESULTS_GET,
        query: Optional[str] = None,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> Dict[str, Any]:  # Adjusted return type to reflect it can be success or RFC 7807
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

        selected_user_id = user_id
        logger.debug(f"Running get_calendar_events with user_id='{selected_user_id}', calendar_id='{calendar_id}', event_id='{event_id}', start_time='{start_time}', end_time='{end_time}', query='{query}', max_results={max_results}")

        try:
            pipeline_input = {
                "calendar_reader": {
                    "user_id": selected_user_id,
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

            component_result = self.pipeline.run(pipeline_input)
            logger.debug(f"Raw result from pipeline run: {component_result}")

            calendar_reader_output = component_result.get("calendar_reader", {})

            # Check if the output is an RFC 7807 problem details dictionary
            # A simple check could be for the presence of 'status' and 'title' keys,
            # which are common in RFC 7807 but not in the success response.
            if isinstance(calendar_reader_output, dict) and "status" in calendar_reader_output and "title" in calendar_reader_output:
                logger.warning(f"GetCalendarEvents component returned an RFC 7807 problem: {calendar_reader_output}")
                # The component itself now returns the RFC 7807 JSON.
                # The pipeline wrapper should return this directly.
                return calendar_reader_output
            elif "events" in calendar_reader_output:  # Success case
                final_response = {"events": calendar_reader_output.get("events", [])}
                logger.info(f"GetCalendarEvents pipeline successfully processed request. Returning {len(final_response.get('events', []))} events.")
                logger.debug(f"GetCalendarEvents pipeline returning: {final_response}")
                return final_response
            else:  # Unexpected structure from component
                logger.error(f"Unexpected output structure from calendar_reader: {calendar_reader_output}", exc_info=True)
                # Fallback to a generic server error if the component's output is unrecognized
                return {
                    "type": f"{DEFAULT_PROBLEM_TYPE_URI}internal-server-error",  # Assuming DEFAULT_PROBLEM_TYPE_URI is accessible or define a local one
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "The calendar component returned an unexpected response structure.",
                    "instance": "/calendar_events/errors/unexpected-component-response",
                }
        # The specific Google errors should no longer be raised by the component to this level.
        # If they are, it's an issue in the component's error handling.
        except Exception as e:  # Catch truly unexpected errors in the pipeline wrapper itself or if component still raises
            logger.error(f"Unexpected error in GetCalendarEvents pipeline execution: {e}", exc_info=True)
            # Return a generic RFC 7807 error
            return {
                "type": f"{DEFAULT_PROBLEM_TYPE_URI}internal-server-error",  # Assuming DEFAULT_PROBLEM_TYPE_URI is accessible
                "title": "Internal Server Error",
                "status": 500,
                "detail": f"An unexpected error occurred in the GetCalendarEvents pipeline: {str(e)}",
                "instance": "/calendar_events/errors/pipeline-unexpected-error",
            }
