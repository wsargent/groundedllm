from typing import Any, Dict, List, Optional

from haystack import component
from haystack.dataclasses import ByteStream

from components.fetcher import FallbackLinkContentFetcher


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
