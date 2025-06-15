import os
from typing import Any, Dict, List, Optional, Tuple

import httpx
from hayhooks import log as logger
from haystack import Document, Pipeline, SuperComponent, component
from haystack.components.converters import (
    CSVToDocument,
    HTMLToDocument,
    MarkdownToDocument,
    PyPDFToDocument,
    TextFileToDocument,
)
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.joiners import DocumentJoiner
from haystack.components.preprocessors import DocumentCleaner
from haystack.components.routers import FileTypeRouter
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from scrapling.fetchers import Fetcher

from components.github import GithubIssueContentResolver, GithubPRContentResolver, GithubRepoContentResolver
from components.google.google_oauth import GoogleOAuth
from components.notion import NotionContentResolver
from components.stackoverflow import StackOverflowContentResolver
from components.youtube_transcript import YouTubeTranscriptResolver
from components.zotero import ZoteroContentResolver


@component
class GenericURLContentResolver:
    """A resolver that uses the existing FallbackLinkContentFetcher for generic URLs."""

    def __init__(
        self,
        raise_on_failure: bool = False,
        user_agents: Optional[List[str]] = None,
        retry_attempts: int = 2,
        timeout: int = 3,
        http2: bool = False,
        client_kwargs: Optional[Dict] = None,
        jina_timeout: int = 10,
        jina_retry_attempts: int = 2,
    ):
        self.raise_on_failure = raise_on_failure
        self.fetcher = FallbackLinkContentFetcher(
            raise_on_failure=raise_on_failure,
            user_agents=user_agents,
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=http2,
            client_kwargs=client_kwargs,
            jina_timeout=jina_timeout,
            jina_retry_attempts=jina_retry_attempts,
        )

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        return self.fetcher.run(urls)

    def can_handle(self, url: str) -> bool:
        # This is the fallback resolver, so it can handle any URL
        return True


@component
class URLContentRouter:
    """A component that routes URLs to the appropriate resolver."""

    def __init__(self, resolvers: List[Any]):
        """Initialize the URL router.

        Args:
            resolvers: A list of URL content resolvers.
        """
        self.resolvers = resolvers
        # The last resolver should be the generic one that can handle any URL
        self.generic_resolver = resolvers[-1]

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Route URLs to the appropriate resolver and fetch their content.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        # Group URLs by resolver
        resolver_urls: Dict[Any, List[str]] = {}

        for url in urls:
            resolver = self._find_resolver(url)
            if resolver not in resolver_urls:
                resolver_urls[resolver] = []
            resolver_urls[resolver].append(url)

        # Fetch content using each resolver
        all_streams = []

        for resolver, urls in resolver_urls.items():
            try:
                result = resolver.run(urls)
                if "streams" in result:
                    streams = result["streams"]
                    all_streams.extend(streams)
                else:
                    logger.debug(f"No streams found for {resolver}")
            except Exception:
                logger.exception(f"Exception in {resolver} run with {urls}")

        return {"streams": all_streams}

    def _find_resolver(self, url: str) -> Any:
        """Find the appropriate resolver for the given URL.

        Args:
            url: The URL to find a resolver for.

        Returns:
            The resolver that can handle the URL.
        """
        for resolver in self.resolvers:
            if resolver.can_handle(url):
                return resolver

        # This should never happen since the generic resolver can handle any URL
        return self.generic_resolver


@component
class ScraplingLinkContentFetcher:
    """
    A component that fetches content from URLs using https://github.com/D4Vinci/Scrapling.

    Must run `scrapling install` to add browser support.
    """

    def __init__(
        self,
        timeout: int = 30,
        retry_attempts: int = 2,
        raise_on_failure: bool = False,
    ):
        """
        Initialize the ScraplingLinkContentFetcher.

        Args:
            timeout: The timeout for the HTTP request in seconds.
            retry_attempts: The number of retry attempts for failed requests.
            raise_on_failure: Whether to raise an exception if fetching fails.
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.raise_on_failure = raise_on_failure
        self._available: Optional[bool] = None  # Cache availability status
        self._failure_count = 0  # Track consecutive failures

    def is_available(self) -> bool:
        """Check if Scrapling is available and has quota."""
        if self._available is not None:
            return self._available

        # If we've had too many consecutive failures, mark as unavailable
        if self._failure_count >= 3:
            self._available = False
            return False

        # Scrapling is a local library, so it's usually available
        self._available = True
        return True

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """
        Fetch content from URLs using Scrapling service.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        if not self.is_available():
            if self.raise_on_failure:
                raise RuntimeError("Scrapling is not available")
            return {"streams": []}

        streams = []
        for url in urls:
            metadata, stream = self._fetch_with_retries(url)
            if metadata and stream:
                stream.meta.update(metadata)
                stream.mime_type = stream.meta.get("content_type", None)
                streams.append(stream)
                # Reset failure count on successful fetch
                self._failure_count = 0

        return {"streams": streams}

    def _fetch_with_retries(self, url: str) -> Tuple[Optional[Dict[str, str]], Optional[ByteStream]]:
        """
        Fetch content from a URL with retry logic.

        Args:
            url: The URL to fetch content from.

        Returns:
            A tuple containing metadata and ByteStream.
        """
        attempt = 0

        while attempt <= self.retry_attempts:
            try:
                return self._fetch(url)
            except Exception as e:
                attempt += 1
                if attempt <= self.retry_attempts:
                    import time

                    time.sleep(min(2 * 2 ** (attempt - 1), 10))
                else:
                    logger.warning(f"Failed to fetch {url} using Scrapling after {self.retry_attempts} attempts: {str(e)}")
                    self._failure_count += 1
                    # Mark as unavailable on repeated failures
                    if self._failure_count >= 3:
                        self._available = False
                    break

        return None, None

    def _fetch(self, url: str) -> Tuple[Dict[str, str], ByteStream]:
        """
        Fetch content from a URL using Scrapling.

        Args:
            url: The URL to fetch content from.

        Returns:
            A tuple containing metadata and ByteStream.
        """
        # Use Scrapling's basic Fetcher for HTTP requests
        response = Fetcher.get(url, timeout=self.timeout)

        # Check for successful response
        if response.status != 200:
            logger.error(f"Scrapling failure for url {url} status_code={response.status}")
            raise RuntimeError(f"HTTP {response.status}: {response.reason}")

        # Extract text content from the response
        # The .text property returns a TextHandler with the cleaned text content
        content = str(response.text)

        # Get content type from headers, default to text/html
        content_type = response.headers.get("content-type", "text/html")

        # Extract additional metadata if available
        title = ""
        try:
            # Try to get title from HTML if it's an HTML page
            if "text/html" in content_type:
                title_elements = response.css("title")
                if title_elements:
                    # Get the first title element if it exists
                    title_element = title_elements[0] if hasattr(title_elements, "__getitem__") else title_elements.first
                    if title_element:
                        title = str(title_element.text)
        except Exception:
            # If title extraction fails, continue without it
            pass

        # Create ByteStream and metadata
        stream = ByteStream(data=content.encode("utf-8"))
        metadata = {
            "content_type": content_type,
            "url": url,
            "title": title,
            "status": response.status,
        }

        return metadata, stream


@component
class ContentFetcherRouter:
    """
    A router that intelligently selects content fetchers based on URL patterns
    and handles dynamic fallbacks when fetchers become unavailable.
    """

    def __init__(
        self,
        fetcher_configs: Optional[List[Dict[str, Any]]] = None,
        default_fetcher: str = "fallback",
        raise_on_failure: bool = False,
    ):
        """
        Initialize the ContentFetcherRouter.

        Args:
            fetcher_configs: List of fetcher configurations with patterns and preferences
            default_fetcher: Default fetcher to use when no patterns match
            raise_on_failure: Whether to raise exceptions on fetcher failures
        """
        self.raise_on_failure = raise_on_failure
        self.default_fetcher = default_fetcher

        # Default configuration
        if fetcher_configs is None:
            fetcher_configs = [
                {"name": "scrapling", "patterns": ["*news*", "*article*", "*blog*", "*content*", "*post*"], "domains": ["medium.com", "substack.com", "news.*", "*.news", "techcrunch.com", "hackernews.com"], "priority": 1},
                {"name": "fallback", "patterns": ["*"], "domains": ["*"], "priority": 999},
            ]

        self.fetcher_configs = fetcher_configs
        self._initialize_fetchers()

    def _initialize_fetchers(self):
        """Initialize all configured fetchers."""
        self.fetchers = {}

        # Initialize Scrapling fetcher
        self.fetchers["scrapling"] = ScraplingLinkContentFetcher(
            raise_on_failure=False  # We handle failures in the router
        )

        # Initialize Jina fetcher
        self.fetchers["jina"] = JinaLinkContentFetcher()

        # Initialize fallback fetcher
        self.fetchers["fallback"] = FallbackLinkContentFetcher(raise_on_failure=False)

    def _match_url_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches a given pattern."""
        import fnmatch

        return fnmatch.fnmatch(url.lower(), pattern.lower())

    def _match_domain(self, url: str, domain: str) -> bool:
        """Check if URL domain matches a given domain pattern."""
        import fnmatch
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return fnmatch.fnmatch(parsed.netloc.lower(), domain.lower())

    def _select_fetcher(self, url: str) -> str:
        """Select the best fetcher for a given URL."""
        best_fetcher = self.default_fetcher
        best_priority = float("inf")

        for config in self.fetcher_configs:
            name = config["name"]
            patterns = config.get("patterns", [])
            domains = config.get("domains", [])
            priority = config.get("priority", 999)

            # Check if fetcher is available
            fetcher = self.fetchers.get(name)
            if fetcher and hasattr(fetcher, "is_available") and not fetcher.is_available():
                continue

            # Check pattern matches
            pattern_match = any(self._match_url_pattern(url, pattern) for pattern in patterns)
            domain_match = any(self._match_domain(url, domain) for domain in domains)

            if (pattern_match or domain_match) and priority < best_priority:
                best_fetcher = name
                best_priority = priority

        return best_fetcher

    def _get_fallback_fetchers(self, primary_fetcher: str) -> List[str]:
        """Get ordered list of fallback fetchers."""
        fallbacks = []

        # Add other available fetchers in priority order
        for config in sorted(self.fetcher_configs, key=lambda x: x.get("priority", 999)):
            name = config["name"]
            if name != primary_fetcher:
                fetcher = self.fetchers.get(name)
                if fetcher:
                    # Check availability for fetchers that support it
                    if hasattr(fetcher, "is_available"):
                        if fetcher.is_available():
                            fallbacks.append(name)
                    else:
                        fallbacks.append(name)

        return fallbacks

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """
        Route URLs to appropriate fetchers with fallback handling.

        Args:
            urls: List of URLs to fetch content from.

        Returns:
            Dictionary with "streams" key containing fetched content.
        """
        all_streams = []

        for url in urls:
            stream = self._fetch_url_with_fallbacks(url)
            if stream:
                all_streams.append(stream)

        return {"streams": all_streams}

    def _fetch_url_with_fallbacks(self, url: str) -> Optional[ByteStream]:
        """Fetch a single URL with fallback handling."""
        primary_fetcher = self._select_fetcher(url)
        fetchers_to_try = [primary_fetcher] + self._get_fallback_fetchers(primary_fetcher)

        for fetcher_name in fetchers_to_try:
            fetcher = self.fetchers.get(fetcher_name)
            if not fetcher:
                continue

            try:
                logger.debug(f"Trying fetcher {fetcher_name} for URL {url}")
                result = fetcher.run([url])
                streams = result.get("streams", [])

                if streams and streams[0].data:  # Check if content was actually fetched
                    logger.info(f"Successfully fetched {url} using {fetcher_name}")
                    return streams[0]
                else:
                    logger.debug(f"Fetcher {fetcher_name} returned empty content for {url}")

            except Exception as e:
                logger.warning(f"Fetcher {fetcher_name} failed for {url}: {str(e)}")

                # Mark fetcher as unavailable if it has this capability
                if hasattr(fetcher, "_available"):
                    fetcher._available = False

        logger.error(f"All fetchers failed for URL {url}")
        if self.raise_on_failure:
            raise RuntimeError(f"Failed to fetch content from {url}")

        return None


@component
class FallbackLinkContentFetcher:
    """
    A component that tries to fetch content using LinkContentFetcher first,
    and falls back to JinaLinkContentFetcher if it fails.
    """

    def __init__(
        self,
        raise_on_failure: bool = False,
        user_agents: Optional[List[str]] = None,
        retry_attempts: int = 2,
        timeout: int = 3,
        http2: bool = False,
        client_kwargs: Optional[Dict] = None,
        jina_timeout: int = 10,
        jina_retry_attempts: int = 2,
    ):
        """
        Initialize the FallbackLinkContentFetcher.

        Args:
            raise_on_failure: Whether to raise an exception if both fetchers fail.
            user_agents: A list of user agents to use for the primary fetcher.
            retry_attempts: The number of retry attempts for the primary fetcher.
            timeout: The timeout for the primary fetcher in seconds.
            http2: Whether to use HTTP/2 for the primary fetcher.
            client_kwargs: Additional kwargs for the primary fetcher's HTTP client.
            jina_timeout: The timeout for the fallback fetcher in seconds.
            jina_retry_attempts: The number of retry attempts for the fallback fetcher.
        """
        self.primary_fetcher = LinkContentFetcher(
            raise_on_failure=False,  # We handle failures ourselves
            user_agents=user_agents,
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=http2,
            client_kwargs=client_kwargs,
        )
        self.fallback_fetcher = JinaLinkContentFetcher(
            timeout=jina_timeout,
            retry_attempts=jina_retry_attempts,
        )
        self.raise_on_failure = raise_on_failure
        self._available: Optional[bool] = None  # Cache availability status

    def is_available(self) -> bool:
        """Check if the fallback fetcher is available."""
        if self._available is not None:
            return self._available

        # Available if either primary or fallback fetcher is available
        primary_available = True  # LinkContentFetcher is usually always available
        fallback_available = self.fallback_fetcher.is_available()

        self._available = primary_available or fallback_available
        return self._available

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """
        Fetch content from URLs using the primary fetcher first,
        and fall back to the fallback fetcher if it fails.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        primary_result = self.primary_fetcher.run(urls)
        streams = primary_result["streams"]

        # Check if any streams are empty (failed to fetch)
        failed_urls = []
        successful_streams = []

        for stream in streams:
            url = stream.meta.get("url", "")

            # Check if the stream is empty (failed to fetch)
            if stream.data == b"":
                failed_urls.append(url)
                logger.info(f"Primary fetcher failed to fetch {url}, trying fallback fetcher")
            else:
                successful_streams.append(stream)

        # If there are any failed URLs, try the fallback fetcher
        if failed_urls:
            try:
                fallback_result = self.fallback_fetcher.run(failed_urls)
                fallback_streams = fallback_result["streams"]

                # Process fallback streams to match LinkContentFetcher format
                for i, item in enumerate(fallback_streams):
                    if isinstance(item, dict) and "metadata" in item and "stream" in item:
                        # Extract metadata and stream from dictionary
                        metadata = item["metadata"]
                        stream = item["stream"]
                        # Update stream metadata
                        stream.meta.update(metadata)
                        stream.mime_type = stream.meta.get("content_type", None)
                        successful_streams.append(stream)
                        # Log successful fallbacks
                        url = metadata.get("url", "")
                        logger.info(f"Successfully fetched {url} using fallback fetcher")
                    else:
                        # If already in the right format, just add it
                        successful_streams.append(item)
                        # Log successful fallbacks
                        url = item.meta.get("url", "")
                        logger.info(f"Successfully fetched {url} using fallback fetcher")

            except Exception as e:
                logger.warning(f"Fallback fetcher failed: {str(e)}")
                if self.raise_on_failure:
                    raise e

        return {"streams": successful_streams}


@component
class JinaLinkContentFetcher:
    """
    A component that fetches content from URLs using the jina.ai service.
    This is used as a fallback when LinkContentFetcher fails.
    """

    def __init__(self, timeout: int = 10, retry_attempts: int = 2, api_key: Secret = Secret.from_env_var("JINA_API_KEY")):
        """
        Initialize the JinaLinkContentFetcher.

        Args:
            timeout: The timeout for the HTTP request in seconds.
            retry_attempts: The number of retry attempts for failed requests.
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        try:
            self.api_key = api_key.resolve_value()
        except Exception:
            self.api_key = None

        self.jina_url = "https://r.jina.ai"
        self._available: Optional[bool] = None  # Cache availability status
        self._failure_count = 0  # Track consecutive failures

    def is_available(self) -> bool:
        """Check if Jina is available and has quota."""
        if self._available is not None:
            return self._available

        # If we've had too many consecutive failures, mark as unavailable
        if self._failure_count >= 3:
            self._available = False
            return False

        # Always available without API key (public endpoint)
        self._available = True
        return True

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """
        Fetch content from URLs using jina.ai service.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        streams = []

        for url in urls:
            metadata, stream = self._fetch_with_retries(url)
            if metadata and stream:
                # Update stream metadata
                stream.meta.update(metadata)
                stream.mime_type = stream.meta.get("content_type", None)
                streams.append(stream)
                # Reset failure count on successful fetch
                self._failure_count = 0

        return {"streams": streams}

    def _fetch_with_retries(self, url: str) -> Tuple[Optional[Dict[str, str]], Optional[ByteStream]]:
        """
        Fetch content from a URL with retry logic.

        Args:
            url: The URL to fetch content from.

        Returns:
            A tuple containing metadata and ByteStream.
        """
        attempt = 0

        while attempt <= self.retry_attempts:
            try:
                return self._fetch(url)
            except Exception as e:
                attempt += 1
                if attempt <= self.retry_attempts:
                    # Wait before retry using exponential backoff
                    import time

                    time.sleep(min(2 * 2 ** (attempt - 1), 10))
                else:
                    logger.warning(f"Failed to fetch {url} using jina.ai after {self.retry_attempts} attempts: {str(e)}")
                    self._failure_count += 1
                    break

        # If we've exhausted all retries, return None
        return None, None

    def _fetch(self, url: str) -> Tuple[Dict[str, str], ByteStream]:
        """
        Fetch content from a URL using jina.ai service.

        Args:
            url: The URL to fetch content from.

        Returns:
            A tuple containing metadata and ByteStream.
        """
        if self.api_key:
            # https://github.com/jina-ai/reader/tree/main?tab=readme-ov-file#streaming-mode
            headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "text/event-stream"}
        else:
            headers = {}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.jina_url}/{url}", headers=headers)

            if response.status_code != 200:
                logger.error(f"Link failure for url {url} status_code={response.status_code} text={response.text}")
                response.raise_for_status()

            # Extract content from response
            content = response.json().get("content", "")
            content_type = response.json().get("content_type", "text/html")

            # Create ByteStream and metadata
            stream = ByteStream(data=content.encode("utf-8"))
            metadata = {"content_type": content_type, "url": url}

            return metadata, stream


@component
class ExtractUrls:
    @component.output_types(urls=list[str])
    def run(self, documents: list[Document]):
        urls = []
        for doc in documents:
            # Check for both "url" and "link" keys in the document meta
            if "url" in doc.meta:
                urls.append(doc.meta["url"])
            elif "link" in doc.meta:
                urls.append(doc.meta["link"])
        return {"urls": urls}


@component
class JoinWithContent:
    @component.output_types(documents=list[Document])
    def run(self, scored_documents: list[Document], content_documents: list[Document]):
        joined_documents = []
        extracted_content: dict[str, str] = {}

        # Helper function to get URL from document meta
        def get_url(doc):
            if "url" in doc.meta:
                return doc.meta["url"]
            elif "link" in doc.meta:
                return doc.meta["link"]
            return None

        for content_doc in content_documents:
            url = get_url(content_doc)
            if url:
                extracted_content[url] = content_doc.content

        for scored_document in scored_documents:
            url = get_url(scored_document)
            if not url:
                continue  # Skip documents without URL or link

            score = scored_document.score
            logger.debug(f"run: processing document {url} with score {score}")

            if url in extracted_content:
                content = extracted_content[url]
            else:
                content = scored_document.content

            doc = Document.from_dict(
                {
                    "title": scored_document.meta.get("title", "Untitled"),
                    "content": content,
                    "url": url,
                    "score": score,
                }
            )
            joined_documents.append(doc)
        return {"documents": joined_documents}


def build_search_extraction_component(
    raise_on_failure: bool = True,
    user_agents: Optional[list[str]] = None,
    retry_attempts: int = 2,
    timeout: int = 3,
    http2: bool = False,
) -> SuperComponent:
    """Fetches URLs from a list of documents and extract the contents of the pages"""

    pipe = Pipeline()

    content_extraction_component = build_content_extraction_component(raise_on_failure=raise_on_failure, user_agents=user_agents, retry_attempts=retry_attempts, timeout=timeout, http2=http2)

    extract_urls_adapter = ExtractUrls()
    content_joiner = JoinWithContent()

    pipe.add_component("extract_urls_adapter", extract_urls_adapter)
    pipe.add_component("content_extractor", content_extraction_component)
    pipe.add_component("content_joiner", content_joiner)

    # OutputAdapter always has dict with "output" as the key
    pipe.connect("extract_urls_adapter.urls", "content_extractor.urls")
    pipe.connect("content_extractor.documents", "content_joiner.content_documents")

    extraction_component = SuperComponent(
        pipeline=pipe,
        input_mapping={"documents": ["extract_urls_adapter.documents", "content_joiner.scored_documents"]},
        output_mapping={"content_joiner.documents": "documents"},
    )
    return extraction_component


def build_smart_content_extraction_component(
    fetcher_configs: Optional[List[Dict[str, Any]]] = None,
    raise_on_failure: bool = True,
) -> SuperComponent:
    """
    Builds a Haystack SuperComponent with smart content fetcher routing.

    This version uses the ContentFetcherRouter to intelligently select
    fetchers based on URL patterns and handle dynamic fallbacks.

    Args:
        fetcher_configs: Custom fetcher configurations
        raise_on_failure: Whether to raise exceptions on failures

    Returns:
        A SuperComponent ready to be added to a pipeline.
        Input: urls (List[str])
        Output: documents (List[Document])
    """
    preprocessing_pipeline = Pipeline()

    # Use the smart content fetcher router
    content_router = ContentFetcherRouter(
        fetcher_configs=fetcher_configs,
        raise_on_failure=raise_on_failure,
    )

    document_cleaner = DocumentCleaner()

    # Define supported MIME types and any custom mappings
    mime_types = [
        "text/plain",
        "text/html",
        "text/csv",
        "text/markdown",
        "text/mdx",
        "application/pdf",
    ]
    additional_mimetypes = {"text/mdx": ".mdx"}

    file_type_router = FileTypeRouter(mime_types=mime_types, additional_mimetypes=additional_mimetypes)
    text_file_converter = TextFileToDocument()
    html_converter = HTMLToDocument()
    markdown_converter = MarkdownToDocument()
    mdx_converter = MarkdownToDocument()
    pdf_converter = PyPDFToDocument()
    csv_converter = CSVToDocument()
    document_joiner = DocumentJoiner()
    unclassified_file_converter = TextFileToDocument()

    # Add components to the internal pipeline
    preprocessing_pipeline.add_component(instance=content_router, name="content_router")
    preprocessing_pipeline.add_component(instance=file_type_router, name="file_type_router")
    preprocessing_pipeline.add_component(instance=unclassified_file_converter, name="unclassified_file_converter")
    preprocessing_pipeline.add_component(instance=text_file_converter, name="text_file_converter")
    preprocessing_pipeline.add_component(instance=markdown_converter, name="markdown_converter")
    preprocessing_pipeline.add_component(instance=html_converter, name="html_converter")
    preprocessing_pipeline.add_component(instance=pdf_converter, name="pypdf_converter")
    preprocessing_pipeline.add_component(instance=csv_converter, name="csv_converter")
    preprocessing_pipeline.add_component(instance=mdx_converter, name="mdx_converter")
    preprocessing_pipeline.add_component(instance=document_joiner, name="document_joiner")
    preprocessing_pipeline.add_component(instance=document_cleaner, name="document_cleaner")

    # Connect the components
    preprocessing_pipeline.connect("content_router.streams", "file_type_router.sources")

    preprocessing_pipeline.connect("file_type_router.text/plain", "text_file_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/html", "html_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/csv", "csv_converter.sources")
    preprocessing_pipeline.connect("file_type_router.application/pdf", "pypdf_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/markdown", "markdown_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/mdx", "mdx_converter.sources")
    preprocessing_pipeline.connect("file_type_router.unclassified", "unclassified_file_converter.sources")

    preprocessing_pipeline.connect("unclassified_file_converter", "document_joiner")
    preprocessing_pipeline.connect("text_file_converter", "document_joiner")
    preprocessing_pipeline.connect("html_converter", "document_joiner")
    preprocessing_pipeline.connect("csv_converter", "document_joiner")
    preprocessing_pipeline.connect("pypdf_converter", "document_joiner")
    preprocessing_pipeline.connect("markdown_converter", "document_joiner")
    preprocessing_pipeline.connect("mdx_converter", "document_joiner")

    preprocessing_pipeline.connect("document_joiner", "document_cleaner")

    extraction_component = SuperComponent(
        pipeline=preprocessing_pipeline,
        input_mapping={"urls": ["content_router.urls"]},
        output_mapping={"document_cleaner.documents": "documents"},
    )
    return extraction_component


def build_content_extraction_component(
    raise_on_failure: bool = True,
    user_agents: Optional[list[str]] = None,
    retry_attempts: int = 2,
    timeout: int = 3,
    http2: bool = False,
) -> SuperComponent:
    """Builds a Haystack SuperComponent responsible for fetching content from URLs,
    determining file types, converting them to Documents, joining them,
    and cleaning them.

    Returns:
        A SuperComponent ready to be added to a pipeline.
        Input: urls (List[str])
        Output: documents (List[Document])

    """
    preprocessing_pipeline = Pipeline()

    # Create resolvers
    stackoverflow_resolver = StackOverflowContentResolver(
        raise_on_failure=raise_on_failure,
        timeout=timeout,
    )

    zotero_resolver = ZoteroContentResolver(
        raise_on_failure=raise_on_failure,
        timeout=timeout,
    )

    # Add more domain-specific resolvers here as needed
    # github_resolver = GitHubContentResolver(...)
    # medium_resolver = MediumContentResolver(...)

    # Generic resolver as fallback
    generic_resolver = GenericURLContentResolver(
        raise_on_failure=raise_on_failure,
        user_agents=user_agents,
        retry_attempts=retry_attempts,
        timeout=timeout,
        http2=http2,
        jina_timeout=10,
        jina_retry_attempts=2,
    )

    user_id = os.environ.get("HAYHOOKS_USER_ID", "me")
    google_oauth = GoogleOAuth()

    # Create YouTube transcript resolver
    youtube_resolver = YouTubeTranscriptResolver(
        oauth_provider=google_oauth,
        raise_on_failure=raise_on_failure,
        user_id=user_id,
    )

    notion_resolver = NotionContentResolver(raise_on_failure=raise_on_failure)

    github_token = None
    if os.getenv("GITHUB_API_KEY"):
        github_token = Secret.from_env_var("GITHUB_API_KEY")
    github_issue_resolver = GithubIssueContentResolver(
        github_token=github_token,  # use api key to get private content and avoid rate limits
        raise_on_failure=raise_on_failure,
    )

    github_repo_resolver = GithubRepoContentResolver(
        github_token=github_token,  # use api key to get private content and avoid rate limits
        raise_on_failure=raise_on_failure,
    )

    github_pr_resolver = GithubPRContentResolver(
        github_token=github_token,  # use api key to get private content and avoid rate limits
        raise_on_failure=raise_on_failure,
    )

    # Create router with all resolvers (generic resolver must be last)
    url_router = URLContentRouter(
        resolvers=[
            stackoverflow_resolver,
            zotero_resolver,
            youtube_resolver,
            notion_resolver,
            github_issue_resolver,
            github_pr_resolver,
            github_repo_resolver,
            generic_resolver,  # Must be last
        ]
    )

    document_cleaner = DocumentCleaner()

    # Define supported MIME types and any custom mappings
    mime_types = [
        "text/plain",
        "text/html",
        "text/csv",
        "text/markdown",
        "text/mdx",  # Letta uses this sometimes
        "application/pdf",
        # Add other types like docx if needed later
        # "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    additional_mimetypes = {"text/mdx": ".mdx"}

    # This should use MultiFileConverter
    file_type_router = FileTypeRouter(mime_types=mime_types, additional_mimetypes=additional_mimetypes)
    text_file_converter = TextFileToDocument()
    html_converter = HTMLToDocument()
    markdown_converter = MarkdownToDocument()
    mdx_converter = MarkdownToDocument()  # Treat mdx as markdown
    pdf_converter = PyPDFToDocument()
    csv_converter = CSVToDocument()
    # docx_converter = DOCXToDocument() # If needed later
    document_joiner = DocumentJoiner()

    # Should add warnings to this so it doesn't just fall through
    unclassified_file_converter = TextFileToDocument()

    # Add components to the internal pipeline
    preprocessing_pipeline.add_component(instance=url_router, name="url_router")
    preprocessing_pipeline.add_component(instance=file_type_router, name="file_type_router")
    preprocessing_pipeline.add_component(instance=unclassified_file_converter, name="unclassified_file_converter")
    preprocessing_pipeline.add_component(instance=text_file_converter, name="text_file_converter")
    preprocessing_pipeline.add_component(instance=markdown_converter, name="markdown_converter")
    preprocessing_pipeline.add_component(instance=html_converter, name="html_converter")
    preprocessing_pipeline.add_component(instance=pdf_converter, name="pypdf_converter")
    preprocessing_pipeline.add_component(instance=csv_converter, name="csv_converter")
    # preprocessing_pipeline.add_component(instance=docx_converter, name="docx_converter") # If needed later
    preprocessing_pipeline.add_component(instance=mdx_converter, name="mdx_converter")
    preprocessing_pipeline.add_component(instance=document_joiner, name="document_joiner")
    preprocessing_pipeline.add_component(instance=document_cleaner, name="document_cleaner")

    # Connect the components
    preprocessing_pipeline.connect("url_router.streams", "file_type_router.sources")

    preprocessing_pipeline.connect("file_type_router.text/plain", "text_file_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/html", "html_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/csv", "csv_converter.sources")
    preprocessing_pipeline.connect("file_type_router.application/pdf", "pypdf_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/markdown", "markdown_converter.sources")
    preprocessing_pipeline.connect("file_type_router.text/mdx", "mdx_converter.sources")  # Route mdx to markdown converter
    preprocessing_pipeline.connect("file_type_router.unclassified", "unclassified_file_converter.sources")  # Route unclassified to text converter as fallback
    # preprocessing_pipeline.connect("file_type_router.application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx_converter.sources") # If needed later

    preprocessing_pipeline.connect("unclassified_file_converter", "document_joiner")
    preprocessing_pipeline.connect("text_file_converter", "document_joiner")
    preprocessing_pipeline.connect("html_converter", "document_joiner")
    preprocessing_pipeline.connect("csv_converter", "document_joiner")
    preprocessing_pipeline.connect("pypdf_converter", "document_joiner")
    preprocessing_pipeline.connect("markdown_converter", "document_joiner")
    preprocessing_pipeline.connect("mdx_converter", "document_joiner")
    # preprocessing_pipeline.connect("docx_converter", "document_joiner") # If needed later

    preprocessing_pipeline.connect("document_joiner", "document_cleaner")

    extraction_component = SuperComponent(
        pipeline=preprocessing_pipeline,
        input_mapping={"urls": ["url_router.urls"]},
        output_mapping={"document_cleaner.documents": "documents"},
    )
    return extraction_component
