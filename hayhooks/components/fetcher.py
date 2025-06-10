from typing import Dict, List, Optional, Tuple

import httpx
from haystack import component
from haystack.components.fetchers import LinkContentFetcher
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from loguru import logger as logger


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

        self.jina_url = "https://r.jina.ai"

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
