import re
from typing import Any, Dict, List, Optional

from hayhooks import log as logger
from haystack.core.component import component
from haystack.dataclasses.byte_stream import ByteStream
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from .google.google_errors import (
    GoogleAPIError,
    GoogleAuthError,
    InsufficientPermissionsError,
    RateLimitError,
    ResourceNotFoundError,
)
from .google.google_oauth import GoogleOAuth
from .google.google_youtube_transcript_reader import GoogleYouTubeTranscriptReader

DEFAULT_PROBLEM_TYPE_URI_YOUTUBE = "urn:hayhooks:youtube:transcript:error:"


@component
class YouTubeTranscriptResolver:
    """
    A resolver that extracts transcripts from YouTube videos.
    It first tries to use the Google YouTube Data API (if available and configured)
    and falls back to the youtube_transcript_api library.
    """

    def __init__(
        self,
        oauth_provider: GoogleOAuth,
        raise_on_failure: bool = False,
        user_id: Optional[str] = None,
        enable_google_api: bool = True,
        enable_youtube_transcript_api: bool = True,
    ):
        """Initialize the YouTube transcript resolver.

        Args:
            oauth_provider (GoogleOAuth): The GoogleOAuth provider instance.
            raise_on_failure (bool): Whether to raise an exception if fetching fails and no streams are produced.
            user_id (Optional[str]): Optional default user ID for Google Cloud Platform services.
            enable_google_api (bool): Whether to enable fetching transcripts via the Google YouTube Data API.
            enable_youtube_transcript_api (bool): Whether to enable fetching transcripts via the youtube_transcript_api library.
        """
        self.raise_on_failure = raise_on_failure
        self.oauth_provider = oauth_provider
        self.user_id = user_id
        self.enable_google_api = enable_google_api
        self.enable_youtube_transcript_api = enable_youtube_transcript_api

    def can_handle(self, url: str) -> bool:
        """Check if this resolver can handle the given URL.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if this resolver can handle the URL, False otherwise.
        """
        return "youtube.com" in url or "youtu.be" in url

    @component.output_types(streams=List[ByteStream], errors=Optional[List[Dict]])
    def run(self, urls: List[str], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch transcripts from YouTube URLs.

        Args:
            urls (List[str]): A list of YouTube URLs to fetch transcripts from.
            user_id (Optional[str]): Optional user ID for Google Cloud Platform services.
                     If provided, it's used for the GoogleYouTubeTranscriptReader.
                     Overrides default_gcp_user_id if set during initialization.

        Returns:
            Dict[str, Any]: A dictionary with:
            - "streams": A list of ByteStream objects for successfully fetched transcripts.
            - "errors": An optional list of RFC 7807 problem detail dictionaries for URLs that failed.
        """
        streams: List[ByteStream] = []
        errors_rfc7807: List[Dict[str, Any]] = []

        active_gcp_user_id = user_id or self.user_id

        if not self.enable_google_api and not self.enable_youtube_transcript_api:
            logger.warning("Both Google API and youtube_transcript_api are disabled. No transcripts will be fetched.")
            # Optionally, create a generic error for each URL or a single global error.
            # For now, just returns empty streams and no errors, as per current behavior if all attempts fail.

        for url_item in urls:
            video_id = self._extract_video_id(url_item)
            if not video_id:
                logger.warning(f"Could not extract video ID from {url_item}")
                errors_rfc7807.append(self._create_rfc7807_error_for_invalid_url(url_item))
                continue

            transcript_obtained = False
            stream_result: Optional[ByteStream] = None
            # potential_rfc_error_for_url will store the RFC 7807 error from the last attempted API
            # or an error if an API was skipped when it was the only/last resort.
            potential_rfc_error_for_url: Optional[Dict[str, Any]] = None

            # 1. Try YouTubeTranscriptApi (Primary, if enabled)
            if self.enable_youtube_transcript_api:
                logger.info(f"Attempting youtube_transcript_api for {video_id} (primary).")
                # _fetch_transcript_with_youtube_transcript_api returns (stream, rfc_error_dict_or_none)
                stream_result, ytt_rfc_error = self._fetch_transcript_with_youtube_transcript_api(video_id, url_item)
                if stream_result:
                    streams.append(stream_result)
                    transcript_obtained = True
                elif ytt_rfc_error:
                    potential_rfc_error_for_url = ytt_rfc_error
                    logger.info(f"youtube_transcript_api for {video_id} failed: {ytt_rfc_error.get('title', 'Unknown Error')}")
                # If ytt_rfc_error is None and stream_result is None, it's an unexpected state from
                # _fetch_transcript_with_youtube_transcript_api, but it should always return an error dict on failure.

            # 2. Fallback to GoogleYouTubeTranscriptReader (if YouTubeTranscriptApi failed/disabled, and this is enabled)
            if not transcript_obtained and self.enable_google_api:
                log_msg_prefix = ""
                if self.enable_youtube_transcript_api:  # ytt was enabled
                    if potential_rfc_error_for_url:  # ytt failed
                        log_msg_prefix = f"youtube_transcript_api for {video_id} failed ({potential_rfc_error_for_url.get('title', 'Unknown')}). "
                    else:  # ytt was enabled but didn't get a stream and didn't report an error (should be rare)
                        log_msg_prefix = f"youtube_transcript_api for {video_id} did not yield a transcript. "
                else:  # ytt was disabled
                    log_msg_prefix = "youtube_transcript_api disabled. "
                logger.info(f"{log_msg_prefix}Attempting fallback to Google API for {video_id}.")

                if not active_gcp_user_id:
                    logger.warning(f"Google API (fallback) for {video_id}: Skipping, no active_gcp_user_id.")
                    # If ytt was disabled or failed silently, this skip becomes the error.
                    if not potential_rfc_error_for_url:  # Only set if ytt didn't already provide an error
                        potential_rfc_error_for_url = self._create_rfc7807_problem(
                            title="Google API Skipped",
                            status=400,
                            detail=f"Google API (fallback) for {video_id} skipped: missing active_gcp_user_id.",
                            error_type_suffix="google-skipped-no-user-id",
                            video_id=video_id,
                            meta={"reason": "Missing active_gcp_user_id for fallback Google API"},
                        )
                elif not self.oauth_provider.check_auth_status(active_gcp_user_id):
                    logger.info(f"Google API (fallback) for {video_id}: Skipping, user {active_gcp_user_id} not authenticated.")
                    if not potential_rfc_error_for_url:
                        potential_rfc_error_for_url = self._create_rfc7807_problem(
                            title="Google API Skipped",
                            status=401,
                            detail=f"Google API (fallback) for {video_id} skipped: user not authenticated.",
                            error_type_suffix="google-skipped-not-authenticated",
                            video_id=video_id,
                            meta={"reason": "User not authenticated for fallback Google API"},
                        )
                else:
                    logger.info(f"Google API (fallback) for {video_id}: Attempting _fetch_transcript_with_google_api.")
                    # _fetch_transcript_with_google_api returns (stream, non_rfc_error_detail_dict_or_none)
                    stream_result, google_error_detail = self._fetch_transcript_with_google_api(video_id, url_item, active_gcp_user_id, user_id)
                    if stream_result:
                        streams.append(stream_result)
                        transcript_obtained = True
                        potential_rfc_error_for_url = None  # Fallback succeeded, clear any error from primary.
                    elif google_error_detail and google_error_detail.get("exception"):
                        # Google API (fallback) failed. This error now takes precedence or is the first error.
                        potential_rfc_error_for_url = self._create_rfc7807_error_from_exception(google_error_detail["exception"], url_item, video_id, "GoogleYouTubeTranscriptReader (fallback)")
                        logger.warning(f"Google API (fallback) for {video_id} failed: {google_error_detail.get('type', 'Unknown Error')}")
                    elif not stream_result:  # Google API returned no stream and no specific exception
                        logger.warning(f"Google API (fallback) for {video_id} returned no stream and no specific error.")
                        if not potential_rfc_error_for_url:  # If ytt also didn't set an error
                            potential_rfc_error_for_url = self._create_rfc7807_problem(
                                title="Google API Fallback Failed Silently",
                                status=500,
                                detail=f"Google API (fallback) for {video_id} did not return a transcript or a specific error.",
                                error_type_suffix="google-fallback-silent-failure",
                                video_id=video_id,
                            )

            # After all attempts for this URL:
            if not transcript_obtained and potential_rfc_error_for_url:
                # Check if an error for this video_id with the same type is already in errors_rfc7807 to prevent duplicates
                # This is a safeguard; ideally, logic flow prevents adding the same error instance twice.
                is_duplicate = any(err.get("video_id") == video_id and err.get("type") == potential_rfc_error_for_url.get("type") for err in errors_rfc7807)
                if not is_duplicate:
                    errors_rfc7807.append(potential_rfc_error_for_url)
            elif not transcript_obtained and not self.enable_youtube_transcript_api and not self.enable_google_api:
                # This case should ideally be caught by the global check at the start of the run method (line 91).
                # However, if it reaches here for a specific URL (e.g., if flags were changed mid-process, though unlikely),
                # ensure an error is logged if not already present.
                if not any(err.get("video_id") == video_id for err in errors_rfc7807):
                    apis_disabled_error = self._create_rfc7807_problem(
                        title="Transcript Fetch Not Attempted",
                        status=501,  # Not Implemented / Not Available
                        detail=f"Both youtube_transcript_api and Google API are disabled for video {video_id}.",
                        error_type_suffix="apis-disabled",
                        video_id=video_id,
                    )
                    errors_rfc7807.append(apis_disabled_error)

        output: Dict[str, Any] = {"streams": streams}
        if errors_rfc7807:
            output["errors"] = errors_rfc7807

        if self.raise_on_failure and not streams and errors_rfc7807:
            first_error_detail_msg = errors_rfc7807[0].get("detail", "Unknown error")
            raise Exception(f"Failed to fetch any transcripts. First error: {first_error_detail_msg}")

        return output

    def _create_rfc7807_problem(self, title: str, status: int, detail: str, error_type_suffix: str, instance_suffix: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Creates an RFC 7807 problem details dictionary."""
        problem = {
            "type": f"{DEFAULT_PROBLEM_TYPE_URI_YOUTUBE}{error_type_suffix}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": f"/youtube_transcripts/errors/{instance_suffix or title.lower().replace(' ', '-')}",
        }
        problem.update(kwargs)
        return problem

    def _create_rfc7807_error_for_invalid_url(self, url: str) -> Dict[str, Any]:
        return self._create_rfc7807_problem(
            title="Invalid YouTube URL",
            status=400,
            detail=f"Could not extract video ID from the provided URL: {url}",
            error_type_suffix="invalid-url",
            instance_suffix=f"invalid-url-{url[:50]}",  # Truncate long URLs
            provided_url=url,
        )

    def _create_rfc7807_error_from_exception(self, exception: Exception, url: str, video_id: str, attempted_api: str) -> Dict[str, Any]:
        """Maps common exceptions to RFC 7807 problem details."""
        if isinstance(exception, TranscriptsDisabled):
            return self._create_rfc7807_problem(
                title="Transcripts Disabled",
                status=403,  # Forbidden
                detail=f"Transcripts are disabled for video {video_id} ({url}). API: {attempted_api}. Original error: {exception}",
                error_type_suffix="transcripts-disabled",
                instance_suffix=f"disabled-{video_id}",
                video_id=video_id,
            )
        elif isinstance(exception, NoTranscriptFound):
            return self._create_rfc7807_problem(
                title="No Transcript Found",
                status=404,  # Not Found
                detail=f"No transcript found for video {video_id} ({url}). API: {attempted_api}. Original error: {exception}",
                error_type_suffix="no-transcript-found",
                instance_suffix=f"notfound-{video_id}",
                video_id=video_id,
            )
        elif isinstance(exception, VideoUnavailable):
            return self._create_rfc7807_problem(
                title="Video Unavailable",
                status=404,  # Or 403 depending on why it's unavailable
                detail=f"Video {video_id} ({url}) is unavailable. API: {attempted_api}. Original error: {exception}",
                error_type_suffix="video-unavailable",
                instance_suffix=f"unavailable-{video_id}",
                video_id=video_id,
            )
        # Handle Google-specific errors if they somehow reach here from the fallback path (unlikely but for completeness)
        # Or if the primary Google reader's errors need to be converted to RFC 7807 by this component
        elif isinstance(exception, ResourceNotFoundError):
            return self._create_rfc7807_problem(
                title="Resource Not Found (Google API)",
                status=404,
                detail=f"Google API reported resource not found for {video_id} ({url}). API: {attempted_api}. Original error: {exception}",
                error_type_suffix="google-resource-not-found",
                instance_suffix=f"google-notfound-{video_id}",
                video_id=video_id,
            )
        elif isinstance(exception, (GoogleAuthError, InsufficientPermissionsError)):
            return self._create_rfc7807_problem(
                title="Google API Authorization/Permission Error",
                status=401 if isinstance(exception, GoogleAuthError) else 403,
                detail=f"Google API authorization or permission error for {video_id} ({url}). API: {attempted_api}. Original error: {exception}",
                error_type_suffix="google-auth-permission-error",
                instance_suffix=f"google-auth-{video_id}",
                video_id=video_id,
                requires_reauth=getattr(exception, "requires_reauth", False),
            )
        else:  # Generic fallback
            return self._create_rfc7807_problem(
                title="Transcript Fetch Error",
                status=500,
                detail=f"Failed to fetch transcript for video {video_id} ({url}) using {attempted_api}. Original error: {type(exception).__name__} - {exception}",
                error_type_suffix="generic-fetch-error",
                instance_suffix=f"generic-{video_id}",
                video_id=video_id,
                original_exception_type=type(exception).__name__,
            )

    def _fetch_transcript_with_google_api(self, video_id: str, url_item: str, active_gcp_user_id: str, user_id: Optional[str]) -> tuple[Optional[ByteStream], Optional[Dict[str, Any]]]:
        """Attempts to fetch transcript using Google YouTube Data API."""
        try:
            logger.info(f"Attempting to fetch transcript for {video_id} using GoogleYouTubeTranscriptReader.")
            google_youtube_transcript_reader = GoogleYouTubeTranscriptReader(oauth_provider=self.oauth_provider, user_id=user_id)  # Pass original user_id for reader init
            result = google_youtube_transcript_reader.run(video_id=video_id, user_id=active_gcp_user_id, original_url=url_item)
            if result and result.get("stream"):
                stream_from_google = result["stream"]
                if "url" not in stream_from_google.meta:  # Should be set by reader
                    stream_from_google.meta["url"] = url_item
                logger.info(f"Successfully fetched transcript for {video_id} using YouTube Data API.")
                return stream_from_google, None
        except ResourceNotFoundError as e_google_rnf:
            logger.warning(f"GoogleYouTubeTranscriptReader: Resource not found for {video_id} ({url_item}): {e_google_rnf}. Will attempt fallback if enabled.")
            # This specific error is handled by the caller to decide on fallback, not an RFC error yet.
            return None, {"type": "ResourceNotFoundError", "exception": e_google_rnf}
        except (GoogleAuthError, GoogleAPIError, RateLimitError, InsufficientPermissionsError) as e_google:
            logger.warning(f"GoogleYouTubeTranscriptReader failed for {video_id} ({url_item}): {type(e_google).__name__} - {e_google}. Will attempt fallback if enabled.")
            # These are critical errors, but we still might fallback. The RFC error will be generated if fallback also fails.
            return None, {"type": "GoogleAPIError", "exception": e_google}
        except Exception as e_google_other:
            logger.warning(f"Unexpected error from GoogleYouTubeTranscriptReader for {video_id} ({url_item}): {e_google_other}. Will attempt fallback if enabled.")
            return None, {"type": "GenericGoogleError", "exception": e_google_other}
        return None, None  # Should not be reached if an exception occurs

    def _fetch_transcript_with_youtube_transcript_api(self, video_id: str, url_item: str) -> tuple[Optional[ByteStream], Optional[Dict[str, Any]]]:
        """Attempts to fetch transcript using youtube_transcript_api library."""
        logger.info(f"Attempting to fetch transcript for {video_id} ({url_item}) using youtube_transcript_api.")
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript_snippets = ytt_api.get_transcript(video_id)
            markdown_content = self._format_as_markdown(transcript_snippets, url_item, video_id)
            stream = ByteStream(data=markdown_content.encode("utf-8"))
            stream.meta = {"url": url_item, "content_type": "text/markdown", "video_id": video_id, "source": "youtube_transcript_api"}
            stream.mime_type = "text/markdown"
            logger.info(f"Successfully fetched transcript for {video_id} using youtube_transcript_api.")
            return stream, None
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e_ytt_specific:
            logger.warning(f"youtube_transcript_api specific error for {video_id} ({url_item}): {e_ytt_specific}")
            return None, self._create_rfc7807_error_from_exception(e_ytt_specific, url_item, video_id, "youtube_transcript_api")
        except Exception as e_fallback_other:
            logger.error(f"youtube_transcript_api failed for {video_id} ({url_item}): {e_fallback_other}")
            return None, self._create_rfc7807_error_from_exception(e_fallback_other, url_item, video_id, "youtube_transcript_api")

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract the video ID from a YouTube URL.

        Args:
            url (str): The YouTube URL.

        Returns:
            Optional[str]: The video ID if found, None otherwise.
        """
        # Match patterns like:
        # https://www.youtube.com/watch?v=VIDEO_ID
        # https://youtu.be/VIDEO_ID
        # https://www.youtube.com/embed/VIDEO_ID

        # Standard YouTube URL
        match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)

        return None

    def _format_as_markdown(self, transcript: List[dict], url: str, video_id: str) -> str:
        """Format the transcript as markdown.

        Args:
            transcript (List[dict]): The transcript data from YouTubeTranscriptApi.
            url (str): The original YouTube URL.
            video_id (str): The YouTube video ID.

        Returns:
            str: The transcript formatted as markdown.
        """
        # Create title with link to video
        md = "# YouTube Video Transcript\n\n"
        md += f"**Video URL**: [{url}]({url})\n\n"
        md += f"**Video ID**: {video_id}\n\n"

        # Add transcript content
        md += "## Transcript\n\n"

        for entry in transcript:
            # Each entry has 'text', 'start', and 'duration' keys
            timestamp = self._format_timestamp(entry.get("start", 0))
            text = entry.get("text", "")

            md += f"**[{timestamp}]** {text}\n\n"

        return md

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as a timestamp (MM:SS).

        Args:
            seconds (float): Time in seconds.

        Returns:
            str: Formatted timestamp.
        """
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
