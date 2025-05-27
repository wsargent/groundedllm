import re
from typing import List, Optional

from hayhooks import log as logger
from haystack import component
from haystack.dataclasses import ByteStream
from youtube_transcript_api import YouTubeTranscriptApi


@component
class YouTubeTranscriptResolver:
    """A resolver that extracts transcripts from YouTube videos."""

    def __init__(self, raise_on_failure: bool = False):
        """Initialize the YouTube transcript resolver.

        Args:
            raise_on_failure: Whether to raise an exception if fetching fails.
        """
        self.raise_on_failure = raise_on_failure

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Fetch transcripts from YouTube URLs.

        Args:
            urls: A list of YouTube URLs to fetch transcripts from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        streams = []

        for url in urls:
            try:
                # Extract video ID from URL
                video_id = self._extract_video_id(url)
                if not video_id:
                    logger.warning(f"Could not extract video ID from {url}")
                    continue

                # Fetch transcript
                ytt_api = YouTubeTranscriptApi()
                transcript_snippets = ytt_api.fetch(video_id)

                # Convert FetchedTranscriptSnippet objects to dictionaries
                transcript = []
                for snippet in transcript_snippets:
                    # Extract the relevant attributes from the snippet
                    transcript.append({"text": snippet.text, "start": snippet.start, "duration": snippet.duration})

                # Convert transcript to markdown
                markdown_content = self._format_as_markdown(transcript, url, video_id)

                # Create ByteStream
                stream = ByteStream(data=markdown_content.encode("utf-8"))
                stream.meta = {"url": url, "content_type": "text/markdown", "video_id": video_id, "source": "youtube"}
                stream.mime_type = "text/markdown"

                streams.append(stream)

            except Exception as e:
                logger.warning(f"Failed to fetch transcript for {url}: {str(e)}")
                if self.raise_on_failure:
                    raise e

        return {"streams": streams}

    def can_handle(self, url: str) -> bool:
        """Check if this resolver can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this resolver can handle the URL, False otherwise.
        """
        return "youtube.com" in url or "youtu.be" in url

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract the video ID from a YouTube URL.

        Args:
            url: The YouTube URL.

        Returns:
            The video ID if found, None otherwise.
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
            transcript: The transcript data from YouTubeTranscriptApi.
            url: The original YouTube URL.
            video_id: The YouTube video ID.

        Returns:
            The transcript formatted as markdown.
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
            seconds: Time in seconds.

        Returns:
            Formatted timestamp.
        """
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
