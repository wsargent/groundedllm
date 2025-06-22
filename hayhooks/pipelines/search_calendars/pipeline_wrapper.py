import os
from typing import Any, Optional

from hayhooks import log as logger
from hayhooks.server.utils.base_pipeline_wrapper import BasePipelineWrapper
from haystack import Pipeline

from components.google.google_calendar_reader import DEFAULT_CALENDAR_ID, DEFAULT_MAX_RESULTS_SEARCH, GoogleCalendarReader  # Use search default
from components.google.google_errors import GoogleAPIError, GoogleAuthError, InvalidInputError
from components.google.google_oauth import GoogleOAuth

# Environment variables for GoogleOAuth configuration (same as get_calendar_events)
GOOGLE_CLIENT_SECRETS_FILE_ENV = "GOOGLE_CLIENT_SECRETS_FILE"
HAYHOOKS_BASE_URL_ENV = "HAYHOOKS_BASE_URL"
GOOGLE_TOKEN_STORAGE_PATH_ENV = "GOOGLE_TOKEN_STORAGE_PATH"
GOOGLE_CALENDAR_SCOPES_ENV = "GOOGLE_CALENDAR_SCOPES"


class PipelineWrapper(BasePipelineWrapper):
    """
    Pipeline wrapper for the 'search_calendars' MCP tool.
    Searches Google Calendar events based on a query.
    """

    def setup(self) -> None:
        logger.info("Setting up SearchCalendarEvents pipeline...")

        client_secrets_file = os.getenv(GOOGLE_CLIENT_SECRETS_FILE_ENV)
        base_url = os.getenv("GOOGLE_AUTH_CALLBACK_URL")
        token_storage_path = os.getenv(GOOGLE_TOKEN_STORAGE_PATH_ENV)

        scopes_str = os.getenv(GOOGLE_CALENDAR_SCOPES_ENV, "https://www.googleapis.com/auth/calendar.readonly")
        scopes = [scope.strip() for scope in scopes_str.split(",") if scope.strip()]

        if not all([client_secrets_file, base_url, token_storage_path]):
            msg = f"Missing one or more Google OAuth environment variables: {GOOGLE_CLIENT_SECRETS_FILE_ENV}, {HAYHOOKS_BASE_URL_ENV}, {GOOGLE_TOKEN_STORAGE_PATH_ENV}"
            logger.error(msg)
            self.oauth_provider = None
            self.calendar_reader = None
            self.pipeline = None
            return
        else:
            logger.info(f"Google OAuth configured with Client Secrets: {client_secrets_file}, Base URL: {base_url}, Token Path: {token_storage_path}, Scopes: {scopes}")

        try:
            self.oauth_provider = GoogleOAuth(
                client_secrets_file=client_secrets_file,  # type: ignore
                base_callback_url=base_url,  # type: ignore
                token_storage_path=token_storage_path,  # type: ignore
                scopes=scopes,
            )
            self.calendar_reader = GoogleCalendarReader(google_oauth_provider=self.oauth_provider)
        except Exception as e:
            logger.error(f"Failed to initialize GoogleOAuth or GoogleCalendarReader: {e}", exc_info=True)
            self.oauth_provider = None
            self.calendar_reader = None
            self.pipeline = None
            return

        pipe = Pipeline()
        pipe.add_component("calendar_reader", self.calendar_reader)
        self.pipeline = pipe
        logger.info("SearchCalendarEvents pipeline setup complete.")

    def run_api(  # type: ignore
        self,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
        calendar_id: str = DEFAULT_CALENDAR_ID,
        max_results: int = DEFAULT_MAX_RESULTS_SEARCH,
        # Parameters from GoogleCalendarReader.run method relevant to search
        start_time: Optional[Any] = None,  # Can be used to filter search
        end_time: Optional[Any] = None,  # Can be used to filter search
        single_events: bool = True,
        order_by: str = "startTime",  # For search, relevance might be implicit, but API supports order_by
    ) -> dict:
        """
        MCP Tool: Searches Google Calendar events.

        Args:
            user_id: The user ID for Google authentication. Defaults to 'default_user'.
            calendar_id: Calendar identifier. Defaults to 'primary'.
            query: Text query to search events.
            max_results: Maximum number of events to return.
            start_time: Optional start time to filter search results.
            end_time: Optional end time to filter search results.
            single_events: Whether to expand recurring events.
            order_by: Sort order ("startTime" or "updated").

        Returns:
            A dictionary containing a list of GoogleCalendarEvent objects under the key "events".

        Raises:
            HTTPException: For errors that should be converted to RFC 7807 by Hayhooks.
        """
        if not self.pipeline or not self.calendar_reader:
            logger.error("SearchCalendarEvents pipeline is not configured correctly. Missing OAuth details or components.")
            raise RuntimeError("Pipeline not configured due to missing Google OAuth environment variables.")

        logger.debug(f"Running search_calendars with user_id='{user_id or self.calendar_reader.default_user_id}', calendar_id='{calendar_id}', query='{query}', max_results={max_results}")

        try:
            pipeline_input = {
                "calendar_reader": {
                    "user_id": user_id,
                    "calendar_id": calendar_id,
                    "query": query,
                    "max_results": max_results,
                    "event_id": None,  # Not used for search query
                    "start_time": start_time,  # Pass through if provided
                    "end_time": end_time,  # Pass through if provided
                    "single_events": single_events,
                    "order_by": order_by,
                }
            }

            result = self.pipeline.run(pipeline_input)
            return {"events": result.get("calendar_reader", {}).get("events", [])}

        except (GoogleAuthError, GoogleAPIError, InvalidInputError) as e:
            logger.warning(f"Error during SearchCalendarEvents execution: {type(e).__name__} - {e.message if hasattr(e, 'message') else str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SearchCalendarEvents pipeline: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred in SearchCalendarEvents: {str(e)}")
