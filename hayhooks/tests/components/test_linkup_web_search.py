import unittest
from unittest.mock import MagicMock, patch

from haystack.utils import Secret
from linkup.types import LinkupSearchResults

from components.web_search.linkup_web_search import LinkupWebSearch


class TestLinkupWebSearch(unittest.TestCase):
    @patch("components.web_search.linkup_web_search.LinkupClient")
    def test_with_valid_api_key(self, mock_linkup_client):
        # Setup mock
        mock_instance = MagicMock()
        mock_linkup_client.return_value = mock_instance
        mock_instance.search.return_value = LinkupSearchResults(results=[])

        # Create component with a valid API key
        component = LinkupWebSearch(api_key=Secret.from_token("valid_api_key"))

        # Verify LinkupClient was initialized
        self.assertIsNotNone(component.linkup_client)
        mock_linkup_client.assert_called_once_with(api_key="valid_api_key")

        # Run the component
        result = component.run(query="test query")

        # Verify search was called
        mock_instance.search.assert_called_once()

        # Verify empty results are returned
        self.assertEqual(result["documents"], [])
        self.assertEqual(result["urls"], [])

    def test_with_no_api_key(self):
        # Create component with an empty API key
        component = LinkupWebSearch(api_key=Secret.from_env_var(""))

        # Verify LinkupClient was not initialized
        self.assertIsNone(component.linkup_client)

        # Run the component
        result = component.run(query="test query")

        # Verify empty results are returned
        self.assertEqual(result["documents"], [])
        self.assertEqual(result["urls"], [])

    @patch("haystack.utils.Secret")
    def test_with_missing_api_key(self, mock_secret):
        # Setup mock to raise an exception when resolve_value is called
        mock_secret_instance = MagicMock()
        mock_secret.from_env_var.return_value = mock_secret_instance
        mock_secret_instance.resolve_value.side_effect = ValueError("No API key")

        # Create component with a missing API key
        component = LinkupWebSearch()

        # Verify LinkupClient was not initialized
        self.assertIsNone(component.linkup_client)

        # Run the component
        result = component.run(query="test query")

        # Verify empty results are returned
        self.assertEqual(result["documents"], [])
        self.assertEqual(result["urls"], [])


if __name__ == "__main__":
    unittest.main()
