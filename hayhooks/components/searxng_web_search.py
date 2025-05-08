import os
from typing import Any, Dict, List, Literal, Optional, Union

import httpx
from hayhooks import log as logger
from haystack import Document, component, default_from_dict, default_to_dict

# Default SearXNG instance URL if not provided or set in environment
DEFAULT_SEARXNG_BASE_URL = "http://searxng:8080"
DEFAULT_TIMEOUT = 10


@component
class SearXNGWebSearch:
    """
    Uses a SearXNG instance to search the web for relevant documents.
    SearXNG is a free and open-source metasearch engine, aggregating
    the results of other search engines without storing information about its users.
    """

    def __init__(self, base_url: Optional[str] = None, enabled: bool = (os.getenv("HAYHOOKS_SEARCH_SEARXNG_ENABLED", "true").lower() == "true"), timeout: int = DEFAULT_TIMEOUT):
        """
        Initializes the SearXNGWebSearch component.

        :param base_url: The base URL of the SearXNG instance.
                         If not provided, it attempts to read from the SEARXNG_BASE_URL
                         environment variable. If still not found, it defaults to
                         DEFAULT_SEARXNG_BASE_URL (e.g., "http://searxng:8080").
        :param enabled: A boolean indicating whether the SearXNG search functionality is enabled.
                        If not explicitly provided, the value is determined by the
                        `HAYHOOKS_SEARCH_SEARXNG_ENABLED` environment variable:
                        - If `HAYHOOKS_SEARCH_SEARXNG_ENABLED` is "true" (case-insensitive), this defaults to `True`.
                        - If `HAYHOOKS_SEARCH_SEARXNG_ENABLED` is set to any other string (e.g., "false"), this defaults to `False`.
                        - If `HAYHOOKS_SEARCH_SEARXNG_ENABLED` is not set, this defaults to `True`.
        :param timeout: The HTTP request timeout in seconds. Defaults to DEFAULT_TIMEOUT.
        """
        self.base_url = base_url or os.getenv("SEARXNG_BASE_URL", DEFAULT_SEARXNG_BASE_URL)

        if not (self.base_url.startswith("http://") or self.base_url.startswith("https://")):
            raise ValueError(f"Invalid base_url: '{self.base_url}'. Must start with 'http://' or 'https://'.")

        self.timeout = timeout
        self.is_enabled = enabled

        if self.is_enabled:
            logger.info(f"SearXNGWebSearch initialized with base_url: {self.base_url} and timeout: {self.timeout}s")
        else:
            logger.info("SearXNGWebSearch component is disabled.")

    @component.output_types(documents=List[Document], links=List[str])
    def run(
        self,
        query: str,
        max_results: int = 5,
        time_range: Optional[Literal["day", "week", "month", "year"]] = None,
        language: Optional[str] = None,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        safesearch: Optional[int] = None,
        pageno: Optional[int] = None,
    ) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Performs a web search using a SearXNG instance.

        :param query: The search query.
        :param max_results: The maximum number of results to return.
                            Note: SearXNG's actual result count might depend on its
                            configuration and the `pageno` parameter. This component
                            will try to request this many via `num_results` and will
                            also truncate if more are returned.
        :param time_range: Optional time range to filter results (e.g., "day", "month").
        :param language: Optional language code for the search (e.g., "en", "de").
        :param categories: Optional list of search categories (e.g., ["general", "news"]).
        :param engines: Optional list of specific search engines to use.
        :param safesearch: Optional safe search level (0: off, 1: moderate, 2: strict).
        :param pageno: Optional page number for results.
        :return: A dictionary containing a list of Document objects and a list of result URLs.
        """

        if self.is_enabled:
            api_params = self._prepare_api_params(query, max_results, time_range, language, categories, engines, safesearch, pageno)
            request_url = f"{self.base_url.rstrip('/')}/search"
            try:
                response = httpx.get(request_url, params=api_params, timeout=self.timeout)
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                api_response_json = response.json()
                response_dict = self._process_response(query, api_response_json, max_results)
                return {"documents": response_dict["documents"], "urls": response_dict["links"]}
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling SearXNG (sync): {e.response.status_code} - {e.response.text} for URL {e.request.url}")
            except httpx.RequestError as e:
                logger.error(f"Request error calling SearXNG (sync): {e} for URL {e.request.url}")
            except Exception as e:  # Catch any other unexpected errors during the request or JSON parsing
                logger.error(f"Unexpected error during SearXNG call (sync): {e}")

        return {"documents": [], "urls": []}  # Default

    @component.output_types(documents=List[Document], links=List[str])
    async def run_async(
        self,
        query: str,
        max_results: int = 5,
        time_range: Optional[Literal["day", "week", "month", "year"]] = None,
        language: Optional[str] = None,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        safesearch: Optional[int] = None,
        pageno: Optional[int] = None,
    ) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Performs an asynchronous web search using a SearXNG instance.
        (Parameters and return are the same as the synchronous `run` method)
        """
        if self.is_enabled:
            api_params = self._prepare_api_params(query, max_results, time_range, language, categories, engines, safesearch, pageno)

            request_url = f"{self.base_url.rstrip('/')}/search"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.get(request_url, params=api_params)
                    response.raise_for_status()
                    api_response_json = response.json()
                    response_dict = self._process_response(query, api_response_json, max_results)
                    return {"documents": response_dict["documents"], "urls": response_dict["links"]}
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error calling SearXNG (async): {e.response.status_code} - {e.response.text} for URL {e.request.url}")
                except httpx.RequestError as e:
                    logger.error(f"Request error calling SearXNG (async): {e} for URL {e.request.url}")
                except Exception as e:  # Catch any other unexpected errors
                    logger.error(f"Unexpected error during SearXNG call (async): {e}")

        return {"documents": [], "urls": []}  # Default

    def _prepare_api_params(
        self,
        query: str,
        max_results: int,
        time_range: Optional[Literal["day", "week", "month", "year"]],
        language: Optional[str],
        categories: Optional[List[str]],
        engines: Optional[List[str]],
        safesearch: Optional[int],
        pageno: Optional[int],
    ) -> Dict[str, Any]:
        """
        Prepares the dictionary of parameters for the SearXNG API call.
        """
        params: Dict[str, Any] = {"q": query, "format": "json"}

        if max_results > 0:  # SearXNG might use 'num_results' or it might be controlled by engine settings/pageno
            params["num_results"] = max_results
        if time_range:
            params["time_range"] = time_range
        if language:
            params["language"] = language
        if categories:
            params["categories"] = ",".join(categories)
        if engines:
            params["engines"] = ",".join(engines)
        if safesearch is not None:  # safesearch can be 0
            params["safesearch"] = safesearch
        if pageno is not None and pageno > 0:
            params["pageno"] = pageno
        return params

    @staticmethod
    def _process_response(query: str, response_json: Dict[str, Any], max_results_requested: int) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Parses the JSON response from SearXNG and converts it into Haystack Documents.
        """
        documents: List[Document] = []
        urls: List[str] = []

        # logger.debug(f"SearXNG raw response for query '{query}': {response_json}")
        raw_results = response_json.get("results", [])

        if not raw_results:
            logger.warning(f"SearXNG returned 0 results for the query '{query}'")
            return {"documents": [], "links": []}

        logger.info(f"SearXNG results: {len(raw_results)} results for query '{query}'")

        # If num_results was respected by API, raw_results might already be limited.
        # Slicing here ensures we don't exceed max_results_requested if API returned more for some reason.
        for result_item in raw_results[: max_results_requested if max_results_requested > 0 else len(raw_results)]:
            title = result_item.get("title")
            url = result_item.get("url")
            logger.info(f"SearXNG result: {url} for query {query}")

            content = result_item.get("content")  # Main snippet

            if not url or not content:  # Skip if essential fields are missing
                logger.debug(f"Skipping result due to missing URL or content: {result_item}")
                continue

            meta = {
                "title": title,
                "url": url,
                "category": result_item.get("category"),
                "engine": result_item.get("engine"),
                "score": result_item.get("score"),
                "language": result_item.get("language"),
                "img_src": result_item.get("img_src"),
                "publishedDate": result_item.get("publishedDate"),  # Common in news
                "thumbnail": result_item.get("thumbnail"),  # Common in images/videos
                "template": result_item.get("template"),
            }
            # Remove None values from meta for cleaner Document object
            cleaned_meta = {k: v for k, v in meta.items() if v is not None}

            documents.append(Document(content=content, meta=cleaned_meta))
            urls.append(url)

        logger.debug(f"Processed {len(documents)} documents from SearXNG for query '{query}'")
        return {"documents": documents, "links": urls}

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the component to a dictionary.
        """
        return default_to_dict(self, base_url=self.base_url, timeout=self.timeout)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearXNGWebSearch":
        """
        Deserializes the component from a dictionary.
        """
        return default_from_dict(cls, data)
