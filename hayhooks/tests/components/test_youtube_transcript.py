import unittest
from unittest.mock import MagicMock, patch

import pytest
from haystack.dataclasses import ByteStream

from components.youtube_transcript import YouTubeTranscriptResolver


class TestYouTubeTranscriptResolver(unittest.TestCase):
    """Unit tests for YouTubeTranscriptResolver."""

    def test_can_handle(self):
        """Test the can_handle method."""
        resolver = YouTubeTranscriptResolver()

        # Should handle YouTube URLs
        self.assertTrue(resolver.can_handle("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(resolver.can_handle("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(resolver.can_handle("https://www.youtube.com/embed/dQw4w9WgXcQ"))

        # Should not handle non-YouTube URLs
        self.assertFalse(resolver.can_handle("https://example.com"))
        self.assertFalse(resolver.can_handle("https://vimeo.com/123456"))

    def test_extract_video_id(self):
        """Test the _extract_video_id method."""
        resolver = YouTubeTranscriptResolver()

        # Test standard YouTube URL
        self.assertEqual(resolver._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        # Test short YouTube URL
        self.assertEqual(resolver._extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        # Test embed URL
        self.assertEqual(resolver._extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        # Test URL with additional parameters
        self.assertEqual(resolver._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123"), "dQw4w9WgXcQ")

        # Test invalid URL
        self.assertIsNone(resolver._extract_video_id("https://example.com"))

    def test_format_timestamp(self):
        """Test the _format_timestamp method."""
        resolver = YouTubeTranscriptResolver()

        self.assertEqual(resolver._format_timestamp(0), "00:00")
        self.assertEqual(resolver._format_timestamp(30), "00:30")
        self.assertEqual(resolver._format_timestamp(60), "01:00")
        self.assertEqual(resolver._format_timestamp(90), "01:30")
        self.assertEqual(resolver._format_timestamp(3600), "60:00")

    @patch("youtube_transcript_api.YouTubeTranscriptApi.fetch")
    def test_run(self, mock_fetch):
        """Test the run method."""
        # Mock the transcript API response
        # Create mock objects that simulate FetchedTranscriptSnippet objects
        mock_snippet1 = MagicMock()
        mock_snippet1.text = "Hello world"
        mock_snippet1.start = 0.0
        mock_snippet1.duration = 1.5

        mock_snippet2 = MagicMock()
        mock_snippet2.text = "This is a test"
        mock_snippet2.start = 1.5
        mock_snippet2.duration = 2.0

        mock_snippet3 = MagicMock()
        mock_snippet3.text = "Of the YouTube transcript resolver"
        mock_snippet3.start = 3.5
        mock_snippet3.duration = 3.0

        mock_fetch.return_value = [mock_snippet1, mock_snippet2, mock_snippet3]

        resolver = YouTubeTranscriptResolver()

        # Test with a valid YouTube URL
        result = resolver.run(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

        # Verify the API was called with the correct video ID
        mock_fetch.assert_called_once_with("dQw4w9WgXcQ")

        # Verify the result structure
        self.assertIn("streams", result)
        self.assertEqual(len(result["streams"]), 1)

        # Verify the stream content
        stream = result["streams"][0]
        self.assertIsInstance(stream, ByteStream)
        self.assertEqual(stream.meta["url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(stream.meta["content_type"], "text/markdown")
        self.assertEqual(stream.meta["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(stream.meta["source"], "youtube")

        # Verify the markdown content
        content = stream.data.decode("utf-8")
        self.assertIn("# YouTube Video Transcript", content)
        self.assertIn("**Video URL**:", content)
        self.assertIn("**Video ID**: dQw4w9WgXcQ", content)
        self.assertIn("## Transcript", content)
        self.assertIn("**[00:00]** Hello world", content)
        self.assertIn("**[00:01]** This is a test", content)
        self.assertIn("**[00:03]** Of the YouTube transcript resolver", content)

    @patch("youtube_transcript_api.YouTubeTranscriptApi.fetch")
    def test_run_with_error(self, mock_fetch):
        """Test the run method with an error."""
        # Mock the transcript API to raise an exception
        mock_fetch.side_effect = Exception("Transcript not available")

        # Test with raise_on_failure=False (default)
        resolver = YouTubeTranscriptResolver(raise_on_failure=False)
        result = resolver.run(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

        # Should return empty streams without raising an exception
        self.assertEqual(len(result["streams"]), 0)

        # Test with raise_on_failure=True
        resolver = YouTubeTranscriptResolver(raise_on_failure=True)
        with self.assertRaises(Exception):
            resolver.run(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])


@pytest.mark.integration
class TestYouTubeTranscriptResolverIntegration(unittest.TestCase):
    """Integration tests for YouTubeTranscriptResolver.

    These tests make actual API calls to YouTube and require internet connection.

    Run with: pytest -m integration
    """

    def test_integration_youtube_transcript(self):
        """Test the YouTubeTranscriptResolver with a real API call."""
        resolver = YouTubeTranscriptResolver()

        # Use a video that's likely to have transcripts
        # TED talks usually have good transcripts
        url = "https://www.youtube.com/watch?v=8S0FDjFBj8o"  # TED talk

        result = resolver.run([url])

        # Verify results
        self.assertIn("streams", result)
        self.assertEqual(len(result["streams"]), 1)

        stream = result["streams"][0]
        self.assertIsInstance(stream, ByteStream)
        self.assertEqual(stream.meta["url"], url)
        self.assertEqual(stream.meta["content_type"], "text/markdown")
        self.assertEqual(stream.meta["video_id"], "8S0FDjFBj8o")
        self.assertEqual(stream.meta["source"], "youtube")

        # Verify content is not empty
        content = stream.data.decode("utf-8")
        self.assertGreater(len(content), 100)  # Should have substantial content
        self.assertIn("# YouTube Video Transcript", content)
        self.assertIn("## Transcript", content)


if __name__ == "__main__":
    unittest.main()
