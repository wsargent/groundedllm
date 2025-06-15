"""Test content extraction."""

from haystack import Document, Pipeline, tracing
from haystack.tracing.logging_tracer import LoggingTracer

from components.content_extraction import build_content_extraction_component
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
    result = fetcher.run(urls=["http://example.com"])

    assert "streams" in result
    assert isinstance(result["streams"], list)
    assert len(result["streams"]) > 0

    # Check stream properties
    stream = result["streams"][0]
    assert hasattr(stream, "data")
    assert hasattr(stream, "meta")
    assert stream.data is not None
    assert "url" in stream.meta
    assert stream.meta["url"] == "http://example.com"


def test_content_fetcher_router():
    """Test the ContentFetcherRouter component."""
    router = ContentFetcherResolver(raise_on_failure=False)

    # Test that it initializes correctly
    assert "scrapling" in router.fetchers
    assert "fallback" in router.fetchers

    # Test URL pattern matching
    news_url = "https://techcrunch.com/some-article"
    selected_fetcher = router._select_fetcher(news_url)
    assert selected_fetcher == "scrapling"

    # Test generic URL routing
    generic_url = "http://example.com"
    selected_fetcher = router._select_fetcher(generic_url)
    assert selected_fetcher == "fallback"

    # Test actual content fetching
    result = router.run(urls=["http://example.com"])

    assert "streams" in result
    assert isinstance(result["streams"], list)


def test_smart_content_extraction_component():
    """Test the smart content extraction component with Scrapling routing."""
    extraction_component = build_content_extraction_component(raise_on_failure=False)

    # Test that the component can be built
    pipe = Pipeline()
    pipe.add_component("smart_extractor", extraction_component)
    assert "smart_extractor" in pipe.graph.nodes

    # Test running with a news-like URL that should use Scrapling
    result = extraction_component.run(urls=["https://news.ycombinator.com"])

    assert "documents" in result
    assert isinstance(result["documents"], list)
    assert len(result["documents"]) > 0
    assert isinstance(result["documents"][0], Document)


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
