"""Test notion component."""

from unittest.mock import MagicMock, patch

from haystack.dataclasses import ByteStream, Document

from components.notion import NotionContentResolver


def test_extract_page_ids():
    """Test that page IDs are correctly extracted from Notion URLs."""
    resolver = NotionContentResolver()

    # Test URLs with different formats
    urls = [
        "https://www.notion.so/workspace/12345678abcd1234abcd1234abcd1234",
        "https://www.notion.so/12345678-abcd-1234-abcd-1234abcd1234",
        "https://notion.so/workspace/12345678abcd1234abcd1234abcd1234?v=123",
        "https://www.notion.so/My-Page-12345678abcd1234abcd1234abcd1234",
    ]

    page_ids = resolver._extract_page_ids(urls)

    # All URLs should result in the same page ID (without hyphens)
    assert len(page_ids) == 4
    for page_id in page_ids:
        assert page_id == "12345678abcd1234abcd1234abcd1234"

    # Test URL without a valid page ID
    invalid_urls = ["https://www.notion.so/workspace/invalid-id"]
    invalid_page_ids = resolver._extract_page_ids(invalid_urls)
    assert len(invalid_page_ids) == 0


@patch("components.notion.NotionExporter")
def test_convert_to_streams(mock_exporter):
    """Test that documents are correctly converted to ByteStream objects."""
    resolver = NotionContentResolver()

    # Create mock documents
    doc1 = Document(content="Test content 1", meta={"title": "Test 1"})
    doc2 = Document(content="Test content 2", meta={"title": "Test 2"})

    # Create mock result from exporter
    documents_result = {"documents": [doc1, doc2]}

    # Convert to streams
    streams = resolver._convert_to_streams(documents_result)

    # Check results
    assert len(streams) == 2
    assert isinstance(streams[0], ByteStream)
    assert streams[0].data == b"Test content 1"
    assert streams[0].meta["title"] == "Test 1"
    assert streams[1].data == b"Test content 2"
    assert streams[1].meta["title"] == "Test 2"


@patch("components.notion.NotionExporter")
def test_run(mock_exporter_class):
    """Test the run method of NotionContentResolver."""
    # Setup mock exporter
    mock_exporter = MagicMock()
    mock_exporter_class.return_value = mock_exporter

    # Create mock documents
    doc = Document(content="Test content", meta={"title": "Test"})
    mock_exporter.run.return_value = {"documents": [doc]}

    # Create resolver and run with test URL
    resolver = NotionContentResolver()
    # Manually set the mock exporter on the resolver
    resolver.exporter = mock_exporter
    result = resolver.run(urls=["https://www.notion.so/12345678abcd1234abcd1234abcd1234"])

    # Check that exporter was called with correct page ID
    mock_exporter.run.assert_called_once_with(page_ids=["12345678abcd1234abcd1234abcd1234"])

    # Check result
    assert "streams" in result
    assert len(result["streams"]) == 1
    assert isinstance(result["streams"][0], ByteStream)
    assert result["streams"][0].data == b"Test content"
    assert result["streams"][0].meta["title"] == "Test"
