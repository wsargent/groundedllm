"""Test content extraction."""

from haystack import Document, Pipeline, tracing
from haystack.tracing.logging_tracer import LoggingTracer

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


def test_content_extraction_component_github_issue():
    """Test that we can run the extractor and get content."""

    import sys

    from loguru import logger

    logger.add(sys.stdout, level="DEBUG")
    tracing.tracer.is_content_tracing_enabled = True
    tracing.enable_tracing(LoggingTracer())

    extraction_component = build_content_extraction_component(http2=True, raise_on_failure=False)
    result = extraction_component.run(urls=["https://github.com/letta-ai/letta/issues/2681"])

    assert "documents" in result
    assert isinstance(result["documents"], list)
    assert len(result["documents"]) > 0
    assert isinstance(result["documents"][0], Document)
