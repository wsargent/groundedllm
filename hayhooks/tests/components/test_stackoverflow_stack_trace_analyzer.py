import json
import os
import unittest

import pytest
from haystack import Document
from haystack.utils import Secret

from components.stackoverflow import StackOverflowStackTraceAnalyzer

# class TestStackOverflowStackTraceAnalyzer(unittest.TestCase):
#     @patch("components.stackoverflow_search.httpx.get")
#     def test_run_with_valid_api_key(self, mock_httpx_get):
#         # Setup mock response
#         mock_response = MagicMock()
#         mock_response.raise_for_status.return_value = None
#         mock_response.json.return_value = {
#             "items": [
#                 {
#                     "question_id": 12345,
#                     "title": "Test Question",
#                     "body": "Test body",
#                     "score": 10,
#                     "answer_count": 2,
#                     "link": "https://stackoverflow.com/q/12345",
#                     "tags": ["python", "error"]
#                 }
#             ]
#         }
#         mock_httpx_get.return_value = mock_response

#         # Mock answers response
#         with patch.object(StackOverflowStackTraceAnalyzer, "_fetch_answers") as mock_fetch_answers:
#             mock_fetch_answers.return_value = [
#                 {
#                     "answer_id": 67890,
#                     "body": "Test answer",
#                     "score": 5,
#                     "is_accepted": True
#                 }
#             ]

#             # Create component with a valid API key
#             component = StackOverflowStackTraceAnalyzer(api_key=Secret.from_token("valid_api_key"))

#             # Run the component
#             result = component.run(
#                 stack_trace="Error: Test error\nLine 2\nLine 3",
#                 language="python"
#             )

#             # Verify httpx.get was called with correct parameters
#             mock_httpx_get.assert_called_once()
#             call_args = mock_httpx_get.call_args[0]
#             call_kwargs = mock_httpx_get.call_args[1]
#             self.assertEqual(call_args[0], f"{STACKOVERFLOW_API}/search/advanced")
#             self.assertEqual(call_kwargs["params"]["q"], "Error: Test error")
#             self.assertEqual(call_kwargs["params"]["tagged"], "python")
#             self.assertEqual(call_kwargs["params"]["filter"], DEFAULT_FILTER)
#             self.assertEqual(call_kwargs["params"]["key"], "valid_api_key")

#             # Verify fetch_answers was called
#             mock_fetch_answers.assert_called_once_with(12345)

#             # Verify results
#             self.assertEqual(len(result["documents"]), 1)
#             self.assertIsInstance(result["documents"][0], Document)
#             self.assertIn("Test Question", result["documents"][0].content)
#             self.assertIn("Test answer", result["documents"][0].content)
#             self.assertIsInstance(result["results_json"], str)
#             self.assertIsInstance(result["results_markdown"], str)

#     @patch("components.stackoverflow_search.httpx.get")
#     def test_run_with_rate_limit_exceeded(self, mock_httpx_get):
#         # Create component with a valid API key
#         component = StackOverflowStackTraceAnalyzer(api_key=Secret.from_token("valid_api_key"))

#         # Setup mock for successful retry
#         mock_response = MagicMock()
#         mock_response.raise_for_status.return_value = None
#         mock_response.json.return_value = {"items": []}
#         mock_httpx_get.return_value = mock_response

#         # First call to _check_rate_limit returns False, then True
#         check_rate_limit_mock = MagicMock(side_effect=[False, True])

#         with patch.object(component, "_check_rate_limit", side_effect=check_rate_limit_mock):
#             # Mock time.sleep to avoid actual waiting
#             with patch("time.sleep"):
#                 # Run the component
#                 result = component.run(
#                     stack_trace="Error: Test error",
#                     language="python"
#                 )

#                 # Verify _check_rate_limit was called twice
#                 self.assertEqual(check_rate_limit_mock.call_count, 2)

#                 # Verify httpx.get was called once (after retry)
#                 mock_httpx_get.assert_called_once()

#     def test_run_with_no_api_key(self):
#         # Create component with an empty API key
#         component = StackOverflowStackTraceAnalyzer(api_key=Secret.from_env_var(""))

#         # Verify is_enabled is False
#         self.assertFalse(component.is_enabled)

#         # Run the component
#         result = component.run(
#             stack_trace="Error: Test error",
#             language="python"
#         )

#         # Verify empty results are returned
#         self.assertEqual(result["documents"], [])
#         self.assertEqual(result["results_json"], "[]")
#         self.assertEqual(result["results_markdown"], "")

#     @patch("components.stackoverflow_search.httpx.get")
#     def test_run_with_error(self, mock_httpx_get):
#         # Setup mock to raise an exception
#         mock_httpx_get.side_effect = httpx.HTTPError("Test error")

#         # Create component with a valid API key
#         component = StackOverflowStackTraceAnalyzer(api_key=Secret.from_token("valid_api_key"))

#         # Run the component
#         result = component.run(
#             stack_trace="Error: Test error",
#             language="python"
#         )

#         # Verify empty results are returned
#         self.assertEqual(result["documents"], [])
#         self.assertEqual(result["results_json"], "[]")
#         self.assertEqual(result["results_markdown"], "")


@pytest.mark.integration
class TestStackOverflowStackTraceAnalyzerIntegration(unittest.TestCase):
    """Integration tests for StackOverflowStackTraceAnalyzer.

    These tests make actual API calls to Stack Overflow and require valid credentials.
    To run these tests, you need to have a STACKOVERFLOW_API_KEY in your .env file.

    Run with: pytest -m integration
    """

    def setUp(self):
        """Check if STACKOVERFLOW_API_KEY is available in environment."""
        self.api_key = os.environ.get("STACKOVERFLOW_API_KEY")
        if not self.api_key:
            self.skipTest("STACKOVERFLOW_API_KEY not found in environment")

    def test_integration_stack_trace_analyzer(self):
        """Test the StackOverflowStackTraceAnalyzer with a real API call."""
        # Create component with API key from environment
        api_key_secret = Secret.from_env_var("STACKOVERFLOW_API_KEY")
        print(f"api_key_secret = {api_key_secret.resolve_value()}")
        component = StackOverflowStackTraceAnalyzer(api_key=api_key_secret)

        # Verify component is enabled
        self.assertTrue(component.is_enabled)

        # Sample stack trace
        stack_trace = """java.lang.NullPointerException: Cannot invoke "String.length()" because "str" is null
    at com.example.MyClass.processString(MyClass.java:25)
    at com.example.MyClass.main(MyClass.java:10)"""

        # Run the component
        result = component.run(stack_trace=stack_trace, language="java")

        # Verify results
        self.assertIsInstance(result, dict)
        self.assertIn("documents", result)
        self.assertIn("results_json", result)
        self.assertIn("results_markdown", result)

        # Verify we got some results
        self.assertIsInstance(result["documents"], list)
        self.assertGreater(len(result["results_json"]), 2)  # Should be more than just "[]"

        # If we got documents, verify they have the expected structure
        if result["documents"]:
            doc = result["documents"][0]
            self.assertIsInstance(doc, Document)
            self.assertIn("meta", doc.meta)
            self.assertIn("url", doc.meta)
            self.assertIn("score", doc.meta)

            # Verify JSON can be parsed
            json_data = json.loads(result["results_json"])
            self.assertIsInstance(json_data, list)


if __name__ == "__main__":
    unittest.main()
