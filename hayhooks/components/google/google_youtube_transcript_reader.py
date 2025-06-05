import json  # Added import
import re
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials as GoogleCredentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError as GoogleHttpError
from hayhooks import log as logger
from haystack.dataclasses.byte_stream import ByteStream  # Changed import

from .google_errors import (
    GoogleAPIError,
    GoogleAuthError,
    InsufficientPermissionsError,
    InvalidInputError,
    RateLimitError,
    ResourceNotFoundError,
)
from .google_oauth import GoogleOAuth


class GoogleYouTubeTranscriptReader:
    """
    Fetches YouTube video transcripts directly using the YouTube Data API v3.
    Outputs transcripts in Markdown format.
    """

    def __init__(
        self,
        oauth_provider: GoogleOAuth,
        user_id: Optional[str] = None,
        preferred_language: str = "en",
    ):
        """
        Initializes the GoogleYouTubeTranscriptReader component.

        Args:
            google_oauth_provider: An instance of the GoogleOAuth class.
            default_user_id: The default user ID for Google API calls.
            preferred_language: Preferred language code for captions (e.g., "en", "es").
        """
        if not isinstance(oauth_provider, GoogleOAuth):
            raise ValueError("google_oauth_provider must be an instance of GoogleOAuth")
        self.google_oauth_provider = oauth_provider
        self.default_user_id = user_id
        self.preferred_language = preferred_language

    def _get_youtube_service(self, user_id: str) -> Resource:
        """
        Retrieves an authenticated YouTube Data API service client.
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
            service: Resource = build("youtube", "v3", credentials=credentials, static_discovery=False)
            return service
        except Exception as e:
            logger.error(f"Failed to build YouTube Data service: {e}")
            raise GoogleAPIError(f"Failed to build YouTube Data service: {e}") from e

    def _parse_srt_to_transcript_list(self, srt_content: str) -> List[Dict[str, Any]]:
        """
        Parses SRT content into a list of dictionaries.
        Each dictionary has "text", "start" (in seconds), and "duration" (in seconds).
        """
        transcript_entries = []
        # SRT format:
        # 1
        # 00:00:20,000 --> 00:00:24,400
        # Text line 1
        # Text line 2 (optional)
        #
        # Using a simpler regex for broad compatibility, assuming well-formed SRT.
        # More robust parsing might be needed for malformed SRT.
        pattern = re.compile(
            r"\d+\n"  # Sequence number
            r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n"  # Timestamps
            r"([\s\S]*?)\n\n",  # Text block (non-greedy)
            re.MULTILINE,
        )

        for match in pattern.finditer(srt_content):
            start_time_str, end_time_str, text = match.groups()

            def srt_time_to_seconds(time_str: str) -> float:
                h, m, s_ms = time_str.split(":")
                s, ms = s_ms.split(",")
                return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

            start_seconds = srt_time_to_seconds(start_time_str)
            end_seconds = srt_time_to_seconds(end_time_str)
            duration_seconds = round(end_seconds - start_seconds, 3)

            # Clean up text: remove extra newlines within a caption block and leading/trailing whitespace
            cleaned_text = " ".join(text.strip().splitlines())

            transcript_entries.append({"text": cleaned_text, "start": start_seconds, "duration": duration_seconds})
        return transcript_entries

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as a timestamp (MM:SS)."""
        minutes = int(seconds // 60)
        seconds_val = int(seconds % 60)
        return f"{minutes:02d}:{seconds_val:02d}"

    def _format_as_markdown(self, transcript: List[Dict[str, Any]], video_id: str, original_url: Optional[str] = None) -> str:
        """Formats the transcript list into Markdown."""
        md = f"# YouTube Video Transcript: {video_id}\n\n"
        if original_url:
            md += f"**Video URL**: [{original_url}]({original_url})\n\n"
        else:
            md += f"**Video URL**: [https://www.youtube.com/watch?v={video_id}](https://www.youtube.com/watch?v={video_id})\n\n"
        md += f"**Video ID**: {video_id}\n\n"
        md += "## Transcript\n\n"

        for entry in transcript:
            timestamp = self._format_timestamp(entry.get("start", 0.0))
            text = entry.get("text", "")
            md += f"**[{timestamp}]** {text}\n\n"
        return md

    def run(self, video_id: str, user_id: Optional[str] = None, original_url: Optional[str] = None):
        """
        Fetches and formats a YouTube video transcript.

        Args:
            video_id: The ID of the YouTube video.
            user_id: The user ID for Google authentication. If None, uses default_user_id.
            original_url: The original YouTube URL, if available, for inclusion in metadata.

        Returns:
            A dictionary containing:
            - "stream": A ByteStream object with the Markdown transcript.
            OR
            - "error_details": An RFC 7807-like problem detail dictionary if an error occurs
                               that should be handled by the caller (e.g. ResourceNotFoundError).
                               This component will raise GoogleAuthError, GoogleAPIError directly for critical issues.
        """
        active_user_id = user_id or self.default_user_id
        if not active_user_id:
            # This is a configuration error, should not happen if component is set up correctly.
            raise InvalidInputError("User ID must be provided or a default_user_id must be configured for GoogleYouTubeTranscriptReader.")

        try:
            service = self._get_youtube_service(active_user_id)

            # 1. List available captions
            captions_list_response = service.captions().list(part="snippet", videoId=video_id).execute()  # type: ignore
            caption_items = captions_list_response.get("items", [])

            if not caption_items:
                logger.warning(f"No caption tracks found for video_id: {video_id}")
                raise ResourceNotFoundError(f"No caption tracks found for video ID '{video_id}'.", resource_type="CaptionTrack", resource_id=video_id)

            # 2. Select a caption track
            selected_track_id = None
            # Try preferred language
            for item in caption_items:
                if item.get("snippet", {}).get("language") == self.preferred_language:
                    selected_track_id = item.get("id")
                    logger.info(f"Found preferred language '{self.preferred_language}' caption track for video_id: {video_id}")
                    break

            # If preferred not found, take the first available one
            if not selected_track_id and caption_items:
                selected_track_id = caption_items[0].get("id")
                lang = caption_items[0].get("snippet", {}).get("language", "unknown")
                logger.info(f"Preferred language not found. Using first available track (lang: {lang}) for video_id: {video_id}")

            if not selected_track_id:  # Should be redundant due to earlier check, but as a safeguard
                raise ResourceNotFoundError(f"Could not select a caption track ID for video ID '{video_id}'.", resource_type="CaptionTrack", resource_id=video_id)

            # 3. Download the selected caption track (SRT format)
            # Note: The API might return empty content for some tracks even if listed.
            srt_content_bytes = service.captions().download(id=selected_track_id, tfmt="srt").execute()  # type: ignore
            srt_content = srt_content_bytes.decode("utf-8")  # Assuming API returns bytes for download

            if not srt_content.strip():
                logger.warning(f"Downloaded SRT content is empty for video_id: {video_id}, track_id: {selected_track_id}")
                # This could also be a ResourceNotFoundError or a specific "EmptyTranscriptError"
                raise ResourceNotFoundError(f"Downloaded transcript content is empty for video ID '{video_id}'.", resource_type="TranscriptContent", resource_id=selected_track_id)

            # 4. Parse SRT and format as Markdown
            transcript_list = self._parse_srt_to_transcript_list(srt_content)
            if not transcript_list:  # If parsing yields nothing from a non-empty SRT (unlikely with current parser if SRT is valid)
                logger.warning(f"SRT parsing yielded no transcript entries for video_id: {video_id}")
                raise GoogleAPIError(f"Failed to parse transcript content for video ID '{video_id}'.")

            markdown_transcript = self._format_as_markdown(transcript_list, video_id, original_url)

            # 5. Create ByteStream
            byte_stream = ByteStream(data=markdown_transcript.encode("utf-8"))
            byte_stream.meta = {
                "video_id": video_id,
                "source": "youtube_data_api",
                "language": caption_items[0].get("snippet", {}).get("language") if selected_track_id == caption_items[0].get("id") else self.preferred_language,  # Best guess for language
                "content_type": "text/markdown",
            }
            if original_url:
                byte_stream.meta["url"] = original_url
            byte_stream.mime_type = "text/markdown"

            return {"stream": byte_stream, "error_details": None}

        except GoogleHttpError as e:
            # Handle common Google API errors and re-raise as specific exceptions
            status_code = e.resp.status
            error_content = e.content.decode() if e.content else "{}"
            try:
                error_details_json = json.loads(error_content)
                message = error_details_json.get("error", {}).get("message", str(e))
            except json.JSONDecodeError:
                message = str(e)

            logger.error(f"Google API HttpError for video_id {video_id}: Status {status_code}, Message: {message}, Original: {e}")
            if status_code == 401:  # Should be caught by _get_youtube_service, but as a fallback
                raise GoogleAuthError(f"Authentication error with YouTube API: {message}", requires_reauth=True) from e
            elif status_code == 403:
                # Check if it's "captionsNotAvailable" or "forbidden"
                if "captionsNotAvailable" in message or "video's owner has disabled them" in message:
                    raise ResourceNotFoundError(f"Captions are not available or disabled for video ID '{video_id}'. API detail: {message}", resource_type="CaptionTrack", resource_id=video_id) from e
                raise InsufficientPermissionsError(f"Insufficient permissions for YouTube API: {message}") from e
            elif status_code == 404:
                raise ResourceNotFoundError(f"YouTube resource not found (video_id: {video_id}). API detail: {message}", resource_type="VideoOrCaption", resource_id=video_id) from e
            elif status_code == 429:
                raise RateLimitError(f"YouTube API rate limit exceeded: {message}") from e
            else:
                raise GoogleAPIError(f"YouTube API error (status {status_code}): {message}", status_code=status_code) from e
        # GoogleAuthError, ResourceNotFoundError, RateLimitError, InsufficientPermissionsError, InvalidInputError are raised directly
        # Other GoogleAPIError are also raised directly
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error in GoogleYouTubeTranscriptReader for video_id {video_id}: {e}", exc_info=True)
            # Re-raise as a generic GoogleAPIError or allow it to propagate if it's already a custom error
            if not isinstance(e, (GoogleAPIError, GoogleAuthError, ResourceNotFoundError, InvalidInputError)):
                raise GoogleAPIError(f"An unexpected error occurred while fetching transcript for video ID '{video_id}': {str(e)}") from e
            raise e  # Re-raise if it's already one of our specific errors
