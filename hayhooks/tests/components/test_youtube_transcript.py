import unittest
from unittest.mock import MagicMock, patch

import pytest
from haystack.dataclasses import ByteStream

from components.google.google_errors import GoogleAuthError
from components.google.google_oauth import GoogleOAuth
from components.youtube_transcript import YouTubeTranscriptResolver


class TestYouTubeTranscriptResolver(unittest.TestCase):
    """Unit tests for YouTubeTranscriptResolver."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_oauth = MagicMock(spec=GoogleOAuth)
        self.resolver = YouTubeTranscriptResolver(
            oauth_provider=self.mock_oauth,
            enable_youtube_transcript_api=True,
            enable_google_api=False,  # Disable Google API for basic tests
        )

    def test_can_handle(self):
        """Test the can_handle method."""

        # Should handle YouTube URLs
        self.assertTrue(self.resolver.can_handle("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(self.resolver.can_handle("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(self.resolver.can_handle("https://www.youtube.com/embed/dQw4w9WgXcQ"))

        # Should not handle non-YouTube URLs
        self.assertFalse(self.resolver.can_handle("https://example.com"))
        self.assertFalse(self.resolver.can_handle("https://vimeo.com/123456"))

    def test_extract_video_id(self):
        """Test the _extract_video_id method."""
        # Test standard YouTube URL
        self.assertEqual(self.resolver._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        # Test short YouTube URL
        self.assertEqual(self.resolver._extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        # Test embed URL
        self.assertEqual(self.resolver._extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        # Test URL with additional parameters
        self.assertEqual(self.resolver._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123"), "dQw4w9WgXcQ")

        # Test invalid URL
        self.assertIsNone(self.resolver._extract_video_id("https://example.com"))

    def test_format_timestamp(self):
        """Test the _format_timestamp method."""
        self.assertEqual(self.resolver._format_timestamp(0), "00:00")
        self.assertEqual(self.resolver._format_timestamp(30), "00:30")
        self.assertEqual(self.resolver._format_timestamp(60), "01:00")
        self.assertEqual(self.resolver._format_timestamp(90), "01:30")
        self.assertEqual(self.resolver._format_timestamp(3600), "60:00")

    @patch("components.youtube_transcript.YouTubeTranscriptApi")
    def test_run(self, mock_api_class):
        """Test the run method."""
        # Mock the transcript API response
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance

        # Create transcript data (dictionaries, not mock objects)
        transcript_data = [{"text": "Hello world", "start": 0.0, "duration": 1.5}, {"text": "This is a test", "start": 1.5, "duration": 2.0}, {"text": "Of the YouTube transcript resolver", "start": 3.5, "duration": 3.0}]

        mock_api_instance.get_transcript.return_value = transcript_data

        # Test with a valid YouTube URL
        result = self.resolver.run(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

        # Verify the API was called with the correct video ID
        mock_api_instance.get_transcript.assert_called_once_with("dQw4w9WgXcQ")

        # Verify the result structure
        self.assertIn("streams", result)
        self.assertEqual(len(result["streams"]), 1)

        # Verify the stream content
        stream = result["streams"][0]
        self.assertIsInstance(stream, ByteStream)
        self.assertEqual(stream.meta["url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(stream.meta["content_type"], "text/markdown")
        self.assertEqual(stream.meta["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(stream.meta["source"], "youtube_transcript_api")

        # Verify the markdown content
        content = stream.data.decode("utf-8")
        self.assertIn("# YouTube Video Transcript", content)
        self.assertIn("**Video URL**:", content)
        self.assertIn("**Video ID**: dQw4w9WgXcQ", content)
        self.assertIn("## Transcript", content)
        self.assertIn("**[00:00]** Hello world", content)
        self.assertIn("**[00:01]** This is a test", content)
        self.assertIn("**[00:03]** Of the YouTube transcript resolver", content)

    @patch("components.youtube_transcript.YouTubeTranscriptApi")
    def test_run_with_error(self, mock_api_class):
        """Test the run method with an error."""
        # Mock the transcript API to raise an exception
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance
        mock_api_instance.get_transcript.side_effect = Exception("Transcript not available")

        # Test with raise_on_failure=False (default)
        result = self.resolver.run(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])

        # Should return empty streams and RFC 7807 errors without raising an exception
        self.assertEqual(len(result["streams"]), 0)
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 1)

        # Test with raise_on_failure=True
        resolver_raise = YouTubeTranscriptResolver(oauth_provider=self.mock_oauth, raise_on_failure=True, enable_youtube_transcript_api=True, enable_google_api=False)
        with self.assertRaises(Exception):
            resolver_raise.run(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])


@pytest.mark.integration
class TestYouTubeTranscriptResolverIntegration(unittest.TestCase):
    """Integration tests for YouTubeTranscriptResolver.

    These tests make actual API calls to YouTube and require internet connection.

    Run with: pytest -m integration
    """

    def test_integration_youtube_transcript(self):
        """Test the YouTubeTranscriptResolver with a real API call."""
        mock_oauth = MagicMock(spec=GoogleOAuth)
        resolver = YouTubeTranscriptResolver(
            oauth_provider=mock_oauth,
            enable_youtube_transcript_api=True,
            enable_google_api=False,  # Use only youtube_transcript_api for integration
        )

        # Use a video that's likely to have transcripts
        # TED talks usually have good transcripts
        url = "https://www.youtube.com/watch?v=8S0FDjFBj8o"  # TED talk

        result = resolver.run([url])

        # Verify results
        self.assertIn("streams", result)
        if len(result["streams"]) > 0:  # May fail if transcript unavailable
            stream = result["streams"][0]
            self.assertIsInstance(stream, ByteStream)
            self.assertEqual(stream.meta["url"], url)
            self.assertEqual(stream.meta["content_type"], "text/markdown")
            self.assertEqual(stream.meta["video_id"], "8S0FDjFBj8o")
            self.assertEqual(stream.meta["source"], "youtube_transcript_api")

            # Verify content is not empty
            content = stream.data.decode("utf-8")
            self.assertGreater(len(content), 100)  # Should have substantial content
            self.assertIn("# YouTube Video Transcript", content)
            self.assertIn("## Transcript", content)
        else:
            # If no streams, should have errors in RFC 7807 format
            self.assertIn("errors", result)
            self.assertGreater(len(result["errors"]), 0)


class TestYouTubeTranscriptResolverAuth(unittest.TestCase):
    """Test authentication scenarios for YouTubeTranscriptResolver."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_oauth = MagicMock(spec=GoogleOAuth)
        self.resolver = YouTubeTranscriptResolver(
            oauth_provider=self.mock_oauth,
            user_id="test_user",
            enable_google_api=True,
            enable_youtube_transcript_api=False,  # Force Google API path
        )

    def test_google_api_not_authenticated_returns_rfc7807(self):
        """Test that unauthenticated user returns RFC 7807 error instead of exception."""
        # Mock check_auth_status to return False (not authenticated)
        self.mock_oauth.check_auth_status.return_value = False

        url = "https://www.youtube.com/watch?v=8JuWdXrCmWg"

        # Run the resolver
        result = self.resolver.run([url], user_id="test_user")

        # Verify it returns RFC 7807 error instead of raising exception
        self.assertIn("streams", result)
        self.assertIn("errors", result)
        self.assertEqual(len(result["streams"]), 0)  # No streams
        self.assertEqual(len(result["errors"]), 1)  # One error

        # Verify RFC 7807 format
        error = result["errors"][0]
        self.assertIn("type", error)
        self.assertIn("title", error)
        self.assertIn("status", error)
        self.assertIn("detail", error)
        self.assertIn("instance", error)

        # Verify specific error details
        self.assertEqual(error["title"], "Google API Skipped")
        self.assertEqual(error["status"], 401)
        self.assertIn("not authenticated", error["detail"])
        self.assertIn("urn:hayhooks:youtube:transcript:error:google-skipped-not-authenticated", error["type"])

        # Verify OAuth was called correctly
        self.mock_oauth.check_auth_status.assert_called_once_with("test_user")

    def test_google_api_missing_user_id_returns_rfc7807(self):
        """Test that missing user_id returns RFC 7807 error instead of exception."""
        # Create resolver without user_id
        resolver = YouTubeTranscriptResolver(
            oauth_provider=self.mock_oauth,
            user_id=None,  # No default user_id
            enable_google_api=True,
            enable_youtube_transcript_api=False,
        )

        url = "https://www.youtube.com/watch?v=8JuWdXrCmWg"

        # Run without providing user_id
        result = resolver.run([url])

        # Verify RFC 7807 error
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 1)

        error = result["errors"][0]
        self.assertEqual(error["title"], "Google API Skipped")
        self.assertEqual(error["status"], 400)
        self.assertIn("missing active_gcp_user_id", error["detail"])
        self.assertIn("google-skipped-no-user-id", error["type"])

    @patch("components.youtube_transcript.GoogleYouTubeTranscriptReader")
    def test_google_api_auth_error_returns_rfc7807(self, mock_google_reader_class):
        """Test that Google API auth errors return RFC 7807 instead of exceptions."""
        # Mock OAuth to return authenticated
        self.mock_oauth.check_auth_status.return_value = True

        # Mock GoogleYouTubeTranscriptReader to raise GoogleAuthError
        mock_reader = MagicMock()
        mock_reader.run.side_effect = GoogleAuthError("Invalid credentials", requires_reauth=True)
        mock_google_reader_class.return_value = mock_reader

        url = "https://www.youtube.com/watch?v=8JuWdXrCmWg"

        # Run the resolver
        result = self.resolver.run([url], user_id="test_user")

        # Verify RFC 7807 error instead of exception
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 1)

        error = result["errors"][0]
        self.assertEqual(error["title"], "Google API Authorization/Permission Error")
        self.assertEqual(error["status"], 401)
        self.assertIn("Invalid credentials", error["detail"])
        self.assertIn("google-auth-permission-error", error["type"])
        self.assertTrue(error.get("requires_reauth", False))

    def test_both_apis_disabled_returns_rfc7807(self):
        """Test that disabling both APIs returns RFC 7807 error."""
        resolver = YouTubeTranscriptResolver(oauth_provider=self.mock_oauth, enable_google_api=False, enable_youtube_transcript_api=False)

        url = "https://www.youtube.com/watch?v=8JuWdXrCmWg"

        result = resolver.run([url])

        # Should return RFC 7807 error for disabled APIs
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 1)

        error = result["errors"][0]
        self.assertEqual(error["title"], "Transcript Fetch Not Attempted")
        self.assertEqual(error["status"], 501)
        self.assertIn("Both youtube_transcript_api and Google API are disabled", error["detail"])
        self.assertIn("apis-disabled", error["type"])


if __name__ == "__main__":
    unittest.main()
