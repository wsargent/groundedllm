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

from components.stackoverflow import StackOverflowContentResolver
from components.zotero import ZoteroContentResolver


class URLContentResolver:
    """Base class for URL content resolvers."""

    def __init__(self, raise_on_failure: bool = False):
        """Initialize the URL content resolver.

        Args:
            raise_on_failure: Whether to raise an exception if fetching fails.
        """
        self.raise_on_failure = raise_on_failure

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Fetch content from URLs.

        Args:
            urls: A list of URLs to fetch content from.

        Returns:
            A dictionary with a "streams" key containing a list of ByteStream objects.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def can_handle(self, url: str) -> bool:
        """Check if this resolver can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this resolver can handle the URL, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")


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
        resolver_urls = {}

        for url in urls:
            resolver = self._find_resolver(url)
            if resolver not in resolver_urls:
                resolver_urls[resolver] = []
            resolver_urls[resolver].append(url)

        # Fetch content using each resolver
        all_streams = []

        for resolver, urls in resolver_urls.items():
            result = resolver.run(urls)
            all_streams.extend(result["streams"])

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

        self.jina_url = "https://r.jina.ai/api/v1/fetch"

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
            headers = {"Authentication:": f"Bearer {self.api_key}"}
        else:
            headers = {}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.jina_url, headers=headers, json={"url": url})
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

    # Create router with all resolvers (generic resolver must be last)
    url_router = URLContentRouter(
        resolvers=[
            stackoverflow_resolver,
            zotero_resolver,
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

    file_type_router = FileTypeRouter(mime_types=mime_types, additional_mimetypes=additional_mimetypes)
    text_file_converter = TextFileToDocument()
    html_converter = HTMLToDocument()
    markdown_converter = MarkdownToDocument()
    mdx_converter = MarkdownToDocument()  # Treat mdx as markdown
    pdf_converter = PyPDFToDocument()
    csv_converter = CSVToDocument()
    # docx_converter = DOCXToDocument() # If needed later
    document_joiner = DocumentJoiner()

    # Add components to the internal pipeline
    preprocessing_pipeline.add_component(instance=url_router, name="url_router")
    preprocessing_pipeline.add_component(instance=file_type_router, name="file_type_router")
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
    # preprocessing_pipeline.connect("file_type_router.application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx_converter.sources") # If needed later

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
