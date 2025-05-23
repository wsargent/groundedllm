"""Test content extraction."""

from haystack import Document, Pipeline

from components.content_extraction import build_content_extraction_component


def test_build_content_extraction_component():
    """Test that the content extraction component can be built."""
    extraction_component = build_content_extraction_component(http2=True, raise_on_failure=False)

    pipe = Pipeline()
    pipe.add_component("extractor", extraction_component)
    assert "extractor" in pipe.graph.nodes


def test_content_extraction_component_run():
    """Test that we can run the extractor and get content."""
    extraction_component = build_content_extraction_component(http2=True, raise_on_failure=False)
    result = extraction_component.run(urls=["http://example.com"])

    assert "documents" in result
    assert isinstance(result["documents"], list)
    assert len(result["documents"]) > 0
    assert isinstance(result["documents"][0], Document)
