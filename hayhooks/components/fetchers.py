from typing import Any, Dict, List, Optional, Tuple

import httpx
from hayhooks import log as logger
from haystack import component
from haystack.components.fetchers import LinkContentFetcher
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from scrapling.fetchers import Fetcher


@component
class ContentFetcherResolver:
    """
    A router that intelligently selects content fetchers based on URL patterns
    and handles dynamic fallbacks when fetchers become unavailable.
    """

    def __init__(
        self,
        fetcher_configs: Optional[List[Dict[str, Any]]] = None,
        default_fetcher: str = "default",
        raise_on_failure: bool = False,
    ):
        """Initialize the ContentFetcherRouter.

        Args:
            fetcher_configs (Optional[List[Dict[str, Any]]]): List of fetcher configurations with patterns and preferences
            default_fetcher (str): Default fetcher to use when no patterns match
            raise_on_failure (bool): Whether to raise exceptions on fetcher failures
        """
        self.raise_on_failure = raise_on_failure
        self.default_fetcher = default_fetcher

        # Default configuration
        if fetcher_configs is None:
            # patterns = ["*news*", "*article*", "*blog*", "*content*", "*post*"]
            # domains = ["medium.com", "substack.com"]
            # scrapling_config = {"name": "scrapling", "patterns": patterns, "domains": domains, "priority": 1}
            default_config = {"name": "default", "patterns": ["*"], "domains": ["*"], "priority": 999}
            fetcher_configs = [
                # scrapling_config,
                default_config,
            ]

        self.fetcher_configs = fetcher_configs
        self._initialize_fetchers()

    def can_handle(self, url: str) -> bool:
        # This can handle any URL
        return True

    def _initialize_fetchers(self):
        """Initialize all configured fetchers."""
        self.fetchers = {}

        # Initialize Scrapling fetcher
        self.fetchers["scrapling"] = ScraplingLinkContentFetcher()

        # Initialize Jina fetcher
        self.fetchers["jina"] = JinaLinkContentFetcher()

        # Initialize default fetcher
        self.fetchers["default"] = HaystackLinkContentFetcher()

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
        """Route URLs to appropriate fetchers with fallback handling.

        Args:
            urls (List[str]): List of URLs to fetch content from.

        Returns:
            Dict[str, List[ByteStream]]: Dictionary with "streams" key containing fetched content.
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
                    logger.debug(f"Successfully fetched {url} using {fetcher_name}")
                    return streams[0]
                else:
                    logger.warning(f"Fetcher {fetcher_name} returned empty content for {url}")

            except Exception as e:
                logger.exception(f"Fetcher {fetcher_name} failed for {url}: {str(e)}")

                # Mark fetcher as unavailable if it has this capability
                if hasattr(fetcher, "_available"):
                    fetcher._available = False

        logger.error(f"All fetchers failed for URL {url}")
        if self.raise_on_failure:
            raise RuntimeError(f"Failed to fetch content from {url}")

        return None


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
        """Initialize the ScraplingLinkContentFetcher.

        Args:
            timeout (int): The timeout for the HTTP request in seconds.
            retry_attempts (int): The number of retry attempts for failed requests.
            raise_on_failure (bool): Whether to raise an exception if fetching fails.
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
        """Fetch content from URLs using Scrapling service.

        Args:
            urls (List[str]): A list of URLs to fetch content from.

        Returns:
            Dict[str, List[ByteStream]]: A dictionary with a "streams" key containing a list of ByteStream objects.
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
        """Fetch content from a URL with retry logic.

        Args:
            url (str): The URL to fetch content from.

        Returns:
            Tuple[Optional[Dict[str, str]], Optional[ByteStream]]: A tuple containing metadata and ByteStream.
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
        """Fetch content from a URL using Scrapling.

        Args:
            url (str): The URL to fetch content from.

        Returns:
            Tuple[Dict[str, str], ByteStream]: A tuple containing metadata and ByteStream.
        """

        # response = StealthyFetcher.fetch(url, timeout=self.timeout, headless=True, block_images=True, disable_resources=True)
        response = Fetcher.get(url, timeout=self.timeout)

        # Check for successful response
        if response.status != 200:
            logger.error(f"Scrapling failure for url {url} status_code={response.status}")
            raise RuntimeError(f"HTTP {response.status}: {response.reason}")

        # Extract text content from the response
        content = str(response.get_all_text())

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
class HaystackLinkContentFetcher:
    """
    A component that tries to fetch content using LinkContentFetcher.
    """

    def __init__(
        self,
        raise_on_failure: bool = False,
        user_agents: Optional[List[str]] = None,
        retry_attempts: int = 2,
        timeout: int = 3,
        http2: bool = False,
        client_kwargs: Optional[Dict] = None,
    ):
        """Initialize the FallbackLinkContentFetcher.

        Args:
            raise_on_failure (bool): Whether to raise an exception if both fetchers fail.
            user_agents (Optional[List[str]]): A list of user agents to use for the primary fetcher.
            retry_attempts (int): The number of retry attempts for the primary fetcher.
            timeout (int): The timeout for the primary fetcher in seconds.
            http2 (bool): Whether to use HTTP/2 for the primary fetcher.
            client_kwargs (Optional[Dict]): Additional kwargs for the primary fetcher's HTTP client.
        """
        self.primary_fetcher = LinkContentFetcher(
            raise_on_failure=False,  # We handle failures ourselves
            user_agents=user_agents,
            retry_attempts=retry_attempts,
            timeout=timeout,
            http2=http2,
            client_kwargs=client_kwargs,
        )
        self.raise_on_failure = raise_on_failure

    def is_available(self) -> bool:
        return True

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        """Fetch content from URLs.

        Args:
            urls (List[str]): A list of URLs to fetch content from.

        Returns:
            Dict[str, List[ByteStream]]: A dictionary with a "streams" key containing a list of ByteStream objects.
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

        return {"streams": successful_streams}


@component
class JinaLinkContentFetcher:
    """
    A component that fetches content from URLs using the jina.ai service.
    This is used as a fallback when LinkContentFetcher fails.
    """

    def __init__(self, timeout: int = 10, retry_attempts: int = 2, api_key: Secret = Secret.from_env_var("JINA_API_KEY")):
        """Initialize the JinaLinkContentFetcher.

        Args:
            timeout (int): The timeout for the HTTP request in seconds.
            retry_attempts (int): The number of retry attempts for failed requests.
            api_key (Secret): Jina API key for authentication.
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
        """Fetch content from URLs using jina.ai service.

        Args:
            urls (List[str]): A list of URLs to fetch content from.

        Returns:
            Dict[str, List[ByteStream]]: A dictionary with a "streams" key containing a list of ByteStream objects.
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
        """Fetch content from a URL with retry logic.

        Args:
            url (str): The URL to fetch content from.

        Returns:
            Tuple[Optional[Dict[str, str]], Optional[ByteStream]]: A tuple containing metadata and ByteStream.
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
        """Fetch content from a URL using jina.ai service.

        Args:
            url (str): The URL to fetch content from.

        Returns:
            Tuple[Dict[str, str], ByteStream]: A tuple containing metadata and ByteStream.
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
