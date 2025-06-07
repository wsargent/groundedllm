import pytest
from haystack_experimental.dataclasses import ImageContent
from PIL import Image as PILImage
import io
import base64

from components.multi_image_content_extractor import MultiImageContentExtractor

# A known small, valid base64 encoded PNG image for testing
# This is a 1x1 transparent PNG image.
VALID_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

@pytest.fixture
def sample_image_bytes():
    return base64.b64decode(VALID_PNG_BASE64)

@pytest.fixture
def multi_image_extractor():
    return MultiImageContentExtractor()

def test_multi_image_extractor_run_success(multi_image_extractor, sample_image_bytes, mocker):
    # Mock LinkContentFetcher constructor
    mock_fetcher_instance = mocker.MagicMock()
    mock_fetcher_instance.run.return_value = {
        "streams": [
            mocker.MagicMock(data=sample_image_bytes, meta={"url": "http://example.com/image1.png"}),
            mocker.MagicMock(data=sample_image_bytes, meta={"url": "http://example.com/image2.png"}),
        ]
    }
    mock_link_fetcher_constructor = mocker.patch(
        "components.multi_image_content_extractor.LinkContentFetcher", # Patched here
        return_value=mock_fetcher_instance,
    )

    # Mock ImageFileToImageContent
    # Correctly mock the return value of ImageFileToImageContent.run
    # It should return a dictionary with the "images" key, which contains a list of ImageContent objects.
    # This one is tricky. If ImageFileToImageContent is used as `ImageFileToImageContent()`
    # then we patch its class: `components.multi_image_content_extractor.ImageFileToImageContent`
    # If its .run method is called on an instance that's already created, we patch the method on that instance.
    # The code is: converter = ImageFileToImageContent(); image_contents_result = converter.run(...)
    # So we patch the class to return a mock instance, whose run method is then configured.
    mock_converter_instance = mocker.MagicMock()
    mock_converter_instance.run.return_value = {
            "images": [
                ImageContent(base64_image=VALID_PNG_BASE64, mime_type="image/png", meta={"url": "http://example.com/image1.png"}),
                ImageContent(base64_image=VALID_PNG_BASE64, mime_type="image/png", meta={"url": "http://example.com/image2.png"}),
            ]
    }
    mock_converter_class = mocker.patch(
        "components.multi_image_content_extractor.ImageFileToImageContent", # Patched here
        return_value=mock_converter_instance
    )

    urls = ["http://example.com/image1.png", "http://example.com/image2.png"]
    result = multi_image_extractor.run(urls=urls)

    assert "images" in result
    assert len(result["images"]) == 2
    for img_content in result["images"]:
        assert isinstance(img_content, ImageContent)
        assert img_content.base64_image == VALID_PNG_BASE64
        assert img_content.mime_type == "image/png"

    mock_link_fetcher_constructor.assert_called_once_with(raise_on_failure=True, retry_attempts=3, timeout=10)
    mock_fetcher_instance.run.assert_called_once_with(urls=urls)
    # Check that the 'sources' argument passed to converter.run matches the streams from fetcher
    # And that 'meta' is a list of dicts of the same length as sources
    # Now mock_converter_instance is the one whose run method is called.
    converter_call_args = mock_converter_instance.run.call_args[1] # .kwargs
    assert len(converter_call_args['sources']) == 2
    assert len(converter_call_args['meta']) == 2
    assert all(isinstance(s, mocker.MagicMock) for s in converter_call_args['sources'])
    assert all(m == {} for m in converter_call_args['meta'])


def test_multi_image_extractor_run_fetcher_failure(multi_image_extractor, mocker):
    # Mock LinkContentFetcher constructor to make its run method simulate a failure
    mock_fetcher_instance = mocker.MagicMock()
    mock_fetcher_instance.run.side_effect = RuntimeError("Failed to fetch URL")
    mock_link_fetcher_constructor = mocker.patch(
        "components.multi_image_content_extractor.LinkContentFetcher", # Patched here
        return_value=mock_fetcher_instance,
    )

    urls = ["http://example.com/image_does_not_exist.png"]

    with pytest.raises(RuntimeError, match="Failed to fetch URL"):
        multi_image_extractor.run(urls=urls)

    mock_link_fetcher_constructor.assert_called_once_with(raise_on_failure=True, retry_attempts=3, timeout=10)
    mock_fetcher_instance.run.assert_called_once_with(urls=urls)


def test_multi_image_extractor_run_converter_failure(multi_image_extractor, sample_image_bytes, mocker):
    # Mock LinkContentFetcher to return valid stream
    mock_fetcher_instance = mocker.MagicMock()
    mock_fetcher_instance.run.return_value = {
        "streams": [
            mocker.MagicMock(data=sample_image_bytes, meta={"url": "http://example.com/image1.png"})
        ]
    }
    mock_link_fetcher_constructor = mocker.patch(
        "components.multi_image_content_extractor.LinkContentFetcher", # Patched here
        return_value=mock_fetcher_instance,
    )

    # Mock ImageFileToImageContent to simulate a failure
    mock_converter_instance = mocker.MagicMock()
    mock_converter_instance.run.side_effect = ValueError("Failed to convert image")
    mock_converter_class = mocker.patch(
        "components.multi_image_content_extractor.ImageFileToImageContent", # Patched here
        return_value=mock_converter_instance
    )

    urls = ["http://example.com/image1.png"]

    with pytest.raises(ValueError, match="Failed to convert image"):
        multi_image_extractor.run(urls=urls)

    mock_link_fetcher_constructor.assert_called_once_with(raise_on_failure=True, retry_attempts=3, timeout=10)
    mock_fetcher_instance.run.assert_called_once_with(urls=urls)
    mock_converter_instance.run.assert_called_once() # Check run on the instance

def test_multi_image_extractor_empty_url_list(multi_image_extractor, mocker):
    # Mock LinkContentFetcher
    mock_fetcher_instance = mocker.MagicMock()
    mock_fetcher_instance.run.return_value = {"streams": []} # Return empty streams for empty URLs
    mock_link_fetcher_constructor = mocker.patch(
        "components.multi_image_content_extractor.LinkContentFetcher", # Patched here
        return_value=mock_fetcher_instance,
    )

    # Mock ImageFileToImageContent
    mock_converter_instance = mocker.MagicMock()
    mock_converter_instance.run.return_value = {"images": []} # Return empty images for empty sources
    mock_converter_class = mocker.patch(
        "components.multi_image_content_extractor.ImageFileToImageContent", # Patched here
        return_value=mock_converter_instance
    )

    urls = []
    result = multi_image_extractor.run(urls=urls)

    assert "images" in result
    assert len(result["images"]) == 0
    mock_link_fetcher_constructor.assert_called_once_with(raise_on_failure=True, retry_attempts=3, timeout=10)
    mock_fetcher_instance.run.assert_called_once_with(urls=urls)
    # Converter should be called with empty sources and meta
    mock_converter_instance.run.assert_called_once_with(sources=[], meta=[]) # Check run on the instance
