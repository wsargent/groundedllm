"""Test content extraction."""

from haystack import Document, Pipeline, tracing
from haystack.dataclasses import ByteStream
from haystack.tracing.logging_tracer import LoggingTracer

from components.content_extraction import JoinWithContent, build_content_extraction_component
from components.fetchers import ContentFetcherResolver, ScraplingLinkContentFetcher


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
    """Test that we can run the extractor and get content from GitHub issues."""
    extraction_component = build_content_extraction_component(http2=True, raise_on_failure=False)
    result = extraction_component.run(urls=["https://github.com/letta-ai/letta/issues/2681"])

    assert "documents" in result
    assert isinstance(result["documents"], list)
    assert len(result["documents"]) > 0
    assert isinstance(result["documents"][0], Document)


def test_content_extraction_component_github_repo():
    """Test that we can run the extractor and get content from GitHub repository files."""

    import sys

    from loguru import logger

    logger.add(sys.stdout, level="DEBUG")
    tracing.tracer.is_content_tracing_enabled = True
    tracing.enable_tracing(LoggingTracer())

    extraction_component = build_content_extraction_component(http2=True, raise_on_failure=False)
    result = extraction_component.run(urls=["https://github.com/mikeroyal/Self-Hosting-Guide"])

    assert "documents" in result
    assert isinstance(result["documents"], list)
    assert len(result["documents"]) > 0
    assert isinstance(result["documents"][0], Document)


def test_content_extraction_component_github_pr():
    """Test that we can run the extractor and get content from GitHub Pull Request."""

    import sys

    from loguru import logger

    logger.add(sys.stdout, level="DEBUG")
    tracing.tracer.is_content_tracing_enabled = True
    tracing.enable_tracing(LoggingTracer())

    extraction_component = build_content_extraction_component(http2=True, raise_on_failure=False)
    result = extraction_component.run(urls=["https://github.com/deepset-ai/haystack-core-integrations/pull/1000"])

    assert "documents" in result
    assert isinstance(result["documents"], list)
    assert len(result["documents"]) > 0
    assert isinstance(result["documents"][0], Document)


def test_scrapling_link_content_fetcher():
    """Test the ScraplingLinkContentFetcher component directly."""
    fetcher = ScraplingLinkContentFetcher(timeout=10, retry_attempts=1)

    # Test availability check
    assert fetcher.is_available() is True

    # Test fetching a simple URL
    result = fetcher.run(urls=["https://medium.com/data-science-at-microsoft/how-large-language-models-work-91c362f5b78f"])

    assert "streams" in result
    assert isinstance(result["streams"], list)
    assert len(result["streams"]) > 0

    # Check stream properties
    stream: ByteStream = result["streams"][0]
    assert hasattr(stream, "data")
    assert hasattr(stream, "meta")
    assert stream.data is not None
    assert len(stream.data) > 0
    assert stream.data != b"None"
    assert "url" in stream.meta
    assert stream.meta["url"] == "https://medium.com/data-science-at-microsoft/how-large-language-models-work-91c362f5b78f"


def test_content_fetcher_router():
    """Test the ContentFetcherRouter component."""
    router = ContentFetcherResolver(raise_on_failure=False)

    # Test that it initializes correctly
    assert "scrapling" in router.fetchers
    assert "default" in router.fetchers

    # Test generic URL routing
    generic_url = "http://example.com"
    selected_fetcher = router._select_fetcher(generic_url)
    assert selected_fetcher == "default"

    # Test actual content fetching
    result = router.run(urls=["http://example.com"])

    assert "streams" in result
    assert isinstance(result["streams"], list)


def test_smart_content_extraction_component():
    """Test the smart content extraction component with Scrapling routing."""

    import sys

    from loguru import logger

    logger.add(sys.stdout, level="DEBUG")

    extraction_component = build_content_extraction_component(raise_on_failure=False)

    # Test that the component can be built
    pipe = Pipeline()
    pipe.add_component("smart_extractor", extraction_component)
    assert "smart_extractor" in pipe.graph.nodes

    # Test running with a news-like URL that should use Scrapling
    result = extraction_component.run(urls=["https://news.ycombinator.com"])

    assert "documents" in result
    documents = result["documents"]
    assert isinstance(documents, list)
    assert len(documents) > 0

    document = documents[0]
    assert isinstance(document, Document)

    content = document.content
    assert len(content) > 0
    assert content != "None"
    logger.info(content)


def test_scrapling_with_news_content():
    """Test Scrapling specifically with news/article content."""
    # Test with custom configuration for news sites
    fetcher_configs = [{"name": "scrapling", "patterns": ["*article*", "*news*"], "domains": ["example.com"], "priority": 1}, {"name": "fallback", "patterns": ["*"], "domains": ["*"], "priority": 999}]

    router = ContentFetcherResolver(fetcher_configs=fetcher_configs, raise_on_failure=False)

    # Test that news URLs get routed to Scrapling
    news_url = "http://example.com/article/test"
    selected_fetcher = router._select_fetcher(news_url)
    assert selected_fetcher == "scrapling"

    # Test actual fetching with a URL that exists
    result = router.run(urls=["http://example.com"])

    assert "streams" in result
    assert isinstance(result["streams"], list)


def test_join_with_content_no_content_documents():
    """Test JoinWithContent when content_documents is empty."""
    joiner = JoinWithContent()

    # Create scored documents with URLs
    scored_docs = [
        Document(content="Original content 1", meta={"url": "http://example.com/1", "title": "Doc 1"}, score=0.9),
        Document(content="Original content 2", meta={"url": "http://example.com/2", "title": "Doc 2"}, score=0.8),
    ]

    # Empty content documents
    content_docs = []

    result = joiner.run(scored_documents=scored_docs, content_documents=content_docs)

    assert "documents" in result
    assert len(result["documents"]) == 2

    # Should use original content since no extracted content available
    assert result["documents"][0].content == "Original content 1"
    assert result["documents"][1].content == "Original content 2"
    assert result["documents"][0].meta["url"] == "http://example.com/1"
    assert result["documents"][1].meta["url"] == "http://example.com/2"


def test_join_with_content_none_content():
    """Test JoinWithContent when content_documents have None content."""
    joiner = JoinWithContent()

    # Create scored documents
    scored_docs = [
        Document(content="Original content", meta={"url": "http://example.com/1", "title": "Doc 1"}, score=0.9),
    ]

    # Content documents with None content (should be skipped)
    content_docs = [
        Document(content=None, meta={"url": "http://example.com/1"}),
    ]

    result = joiner.run(scored_documents=scored_docs, content_documents=content_docs)

    assert "documents" in result
    assert len(result["documents"]) == 1

    # Should use original content since extracted content is None
    assert result["documents"][0].content == "Original content"
    assert result["documents"][0].meta["url"] == "http://example.com/1"


def test_join_with_content_empty_content():
    """Test JoinWithContent when content_documents have empty string content."""
    joiner = JoinWithContent()

    # Create scored documents
    scored_docs = [
        Document(content="Original content", meta={"url": "http://example.com/1", "title": "Doc 1"}, score=0.9),
    ]

    # Content documents with empty content (should be skipped)
    content_docs = [
        Document(content="   ", meta={"url": "http://example.com/1"}),
    ]

    result = joiner.run(scored_documents=scored_docs, content_documents=content_docs)

    assert "documents" in result
    assert len(result["documents"]) == 1

    # Should use original content since extracted content is empty
    assert result["documents"][0].content == "Original content"
    assert result["documents"][0].meta["url"] == "http://example.com/1"


def test_join_with_content_no_url():
    """Test JoinWithContent when content_documents have no URL in metadata."""
    joiner = JoinWithContent()

    # Create scored documents
    scored_docs = [
        Document(content="Original content", meta={"url": "http://example.com/1", "title": "Doc 1"}, score=0.9),
    ]

    # Content documents with no URL in metadata (should be skipped)
    content_docs = [
        Document(content="Extracted content", meta={"title": "Some doc"}),  # No URL
    ]

    result = joiner.run(scored_documents=scored_docs, content_documents=content_docs)

    assert "documents" in result
    assert len(result["documents"]) == 1

    # Should use original content since extracted content has no URL
    assert result["documents"][0].content == "Original content"
    assert result["documents"][0].meta["url"] == "http://example.com/1"


def test_join_with_content_scored_docs_no_url():
    """Test JoinWithContent when scored_documents have no URL in metadata."""
    joiner = JoinWithContent()

    # Create scored documents without URLs (should be skipped)
    scored_docs = [
        Document(content="Original content 1", meta={"title": "Doc 1"}, score=0.9),  # No URL
        Document(content="Original content 2", meta={"url": "http://example.com/2", "title": "Doc 2"}, score=0.8),
    ]

    # Content documents with valid content
    content_docs = [
        Document(content="Extracted content", meta={"url": "http://example.com/2"}),
    ]

    result = joiner.run(scored_documents=scored_docs, content_documents=content_docs)

    assert "documents" in result
    assert len(result["documents"]) == 1  # Only the one with URL should be processed

    # Should use extracted content for the valid document
    assert result["documents"][0].content == "Extracted content"
    assert result["documents"][0].meta["url"] == "http://example.com/2"
