import pytest
from unittest.mock import MagicMock, patch

# Import the refactored PipelineWrapper and other necessities
from pipelines.extract_image.pipeline_wrapper import PipelineWrapper, PIPELINE_NAME
from haystack_experimental.dataclasses import ImageContent

VALID_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

@pytest.fixture
def image_pipeline_wrapper():
    # Returns an instance of the refactored wrapper
    wrapper = PipelineWrapper()
    wrapper.setup() # Call setup to initialize self.pipeline
    return wrapper

# Fixture for a mock pipeline instance that the wrapper would use
@pytest.fixture
def mock_haystack_pipeline():
    mock_pipe = MagicMock()
    # Set up default return value for the pipeline's run method
    mock_pipe.run.return_value = {
        "image_extractor": { # This key must match component name in PipelineWrapper
            "images": [
                ImageContent(base64_image=VALID_PNG_BASE64, mime_type="image/png", meta={"url": "http://example.com/image1.png"}),
                ImageContent(base64_image=VALID_PNG_BASE64, mime_type="image/png", meta={"url": "http://example.com/image2.png"})
            ]
        }
    }
    return mock_pipe

def test_pipeline_name_class_based(): # Renamed to avoid conflict if old tests are still around
    assert PIPELINE_NAME == "extract_image_data" # This should still work if PIPELINE_NAME is global

def test_wrapper_run_method_success(image_pipeline_wrapper, mock_haystack_pipeline):
    # Patch the 'pipeline' attribute of the wrapper instance to use our mock_haystack_pipeline
    with patch.object(image_pipeline_wrapper, 'pipeline', mock_haystack_pipeline):
        # Call the run method directly. The input is now kwargs to run method.
        result = image_pipeline_wrapper.run(urls=["http://example.com/image1.png", "http://example.com/image2.png"])

        assert "base64_images" in result
        assert len(result["base64_images"]) == 2
        assert result["base64_images"][0] == VALID_PNG_BASE64
        assert "processing_errors" not in result

        # Verify that the mocked pipeline's run method was called correctly
        expected_pipeline_input = {"image_extractor": {"urls": ["http://example.com/image1.png", "http://example.com/image2.png"]}}
        mock_haystack_pipeline.run.assert_called_once_with(data=expected_pipeline_input)

def test_wrapper_run_method_empty_urls(image_pipeline_wrapper, mock_haystack_pipeline):
    with patch.object(image_pipeline_wrapper, 'pipeline', mock_haystack_pipeline):
        result = image_pipeline_wrapper.run(urls=[]) # Pass urls directly

        assert "error" in result
        assert "Input 'urls' must be a non-empty list of strings." in result["error"]
        mock_haystack_pipeline.run.assert_not_called() # Pipeline's run should not be called

def test_wrapper_run_method_invalid_urls_type(image_pipeline_wrapper, mock_haystack_pipeline):
    with patch.object(image_pipeline_wrapper, 'pipeline', mock_haystack_pipeline):
        # The run method expects List[str], so this would be a TypeError if not caught by validation
        # The current validation returns a dict error.
        result = image_pipeline_wrapper.run(urls="not_a_list") # type: ignore
        assert "error" in result
        assert "Input 'urls' must be a non-empty list of strings." in result["error"]
        mock_haystack_pipeline.run.assert_not_called()

def test_wrapper_run_method_urls_not_strings(image_pipeline_wrapper, mock_haystack_pipeline):
    with patch.object(image_pipeline_wrapper, 'pipeline', mock_haystack_pipeline):
        result = image_pipeline_wrapper.run(urls=["http://valid.com/image.png", 123]) # type: ignore
        assert "error" in result
        assert "All items in 'urls' must be strings." in result["error"]
        mock_haystack_pipeline.run.assert_not_called()

def test_wrapper_run_method_component_returns_no_base64(image_pipeline_wrapper, mock_haystack_pipeline):
    mock_haystack_pipeline.run.return_value = {
        "image_extractor": {
            "images": [
                ImageContent(base64_image="", mime_type="image/png", meta={"url": "http://example.com/image_no_base64.png"})
            ]
        }
    }
    with patch.object(image_pipeline_wrapper, 'pipeline', mock_haystack_pipeline):
        result = image_pipeline_wrapper.run(urls=["http://example.com/image_no_base64.png"])

        assert "base64_images" in result
        assert len(result["base64_images"]) == 0
        assert "processing_errors" in result
        assert len(result["processing_errors"]) == 1
        assert "Could not extract base64 data for image from http://example.com/image_no_base64.png" in result["processing_errors"][0]

        expected_pipeline_input = {"image_extractor": {"urls": ["http://example.com/image_no_base64.png"]}}
        mock_haystack_pipeline.run.assert_called_once_with(data=expected_pipeline_input)


def test_wrapper_run_method_pipeline_execution_error(image_pipeline_wrapper, mock_haystack_pipeline):
    mock_haystack_pipeline.run.side_effect = RuntimeError("Internal pipeline error!")
    with patch.object(image_pipeline_wrapper, 'pipeline', mock_haystack_pipeline):
        result = image_pipeline_wrapper.run(urls=["http://example.com/image1.png"])

        assert "error" in result
        # The assertion from the user prompt is more specific, let's use that.
        assert "Pipeline execution failed: Internal pipeline error!" in result["error"]

        expected_pipeline_input = {"image_extractor": {"urls": ["http://example.com/image1.png"]}}
        mock_haystack_pipeline.run.assert_called_once_with(data=expected_pipeline_input)


def test_wrapper_run_method_missing_images_in_result(image_pipeline_wrapper, mock_haystack_pipeline):
    mock_haystack_pipeline.run.return_value = {
        "image_extractor": {"unexpected_key": []} # Missing "images"
    }
    with patch.object(image_pipeline_wrapper, 'pipeline', mock_haystack_pipeline):
        result = image_pipeline_wrapper.run(urls=["http://example.com/image1.png"])

        assert "error" in result
        assert "Pipeline did not return the expected 'images' output." in result["error"]
        expected_pipeline_input = {"image_extractor": {"urls": ["http://example.com/image1.png"]}}
        mock_haystack_pipeline.run.assert_called_once_with(data=expected_pipeline_input)

# Ensure that the ImageContent import is correct as per its actual location
# from haystack_experimental.dataclasses import ImageContent (or similar)
# This is already at the top.
