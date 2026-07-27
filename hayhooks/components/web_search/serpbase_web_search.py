from typing import Any, Dict, List, Union

import httpx
from hayhooks import log as logger
from haystack import Document, component, default_from_dict, default_to_dict
from haystack.utils import Secret

DEFAULT_TIMEOUT = 15
SERPBASE_API_URL = "https://api.serpbase.dev/google/search"


@component
class SerpBaseWebSearch:
    """Uses [SerpBase](https://serpbase.dev) to search Google via REST API.

    SerpBase returns structured Google search results (title, link, snippet, position)
    in clean JSON — no scraping maintenance, no CAPTCHAs, no browser overhead.
    """

    def __init__(self, api_key: Secret = Secret.from_env_var("SERPBASE_API_KEY"), timeout: int = DEFAULT_TIMEOUT):
        self.endpoint = SERPBASE_API_URL
        try:
            self.api_key = api_key.resolve_value()
        except Exception:
            self.api_key = None

        self.is_enabled = self.api_key is not None
        if not self.is_enabled:
            logger.info("No SERPBASE_API_KEY provided. SerpBaseWebSearch is disabled.")

        self.timeout = timeout

    @component.output_types(documents=List[Document], links=List[str])
    def run(self, query: str, max_results: int = 5) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Performs a Google web search using SerpBase API.

        :param query: The search query.
        :param max_results: The maximum number of results to return (1–100).
        :return: A dictionary containing a list of Document objects and a list of result URLs.
        """

        if self.is_enabled:
            api_params = self._prepare_api_params(query, max_results)
            try:
                response = httpx.get(self.endpoint, params=api_params, timeout=self.timeout)
                response.raise_for_status()
                api_response_json = response.json()
                response_dict = self._process_response(query, api_response_json, max_results)
                return {"documents": response_dict["documents"], "urls": response_dict["links"]}
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling SerpBase (sync): {e.response.status_code} - {e.response.text} for URL {e.request.url}")
            except httpx.RequestError as e:
                logger.error(f"Request error calling SerpBase (sync): {e} for URL {e.request.url}")
            except Exception as e:
                logger.error(f"Unexpected error during SerpBase call (sync): {e}")

        return {"documents": [], "urls": []}

    def _prepare_api_params(
        self,
        query: str,
        max_results: int,
    ) -> Dict[str, Any]:
        """Prepares the dictionary of parameters for the SerpBase API call."""
        num = max(1, min(max_results, 100))
        return {"q": query, "num": num, "api_key": self.api_key}

    @staticmethod
    def _process_response(query: str, response_json: Dict[str, Any], max_results_requested: int) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Parses the JSON response from SerpBase and converts it into Haystack Documents.
        """
        documents: List[Document] = []
        urls: List[str] = []

        logger.debug(f"SerpBase raw response for query '{query}': {response_json}")
        organic_results = response_json.get("organic_results")

        if not organic_results:
            logger.warning(f"SerpBase returned 0 results for the query '{query}'")
            return {"documents": [], "links": []}

        logger.info(f"SerpBase results: {len(organic_results)} results for query '{query}'")

        for result_item in organic_results[:max_results_requested]:
            title = result_item.get("title")
            url = result_item.get("link")
            content = result_item.get("snippet")

            if not url or not content:
                logger.debug(f"Skipping SerpBase result due to missing URL or snippet: {result_item}")
                continue

            meta = {
                "title": title,
                "url": url,
            }
            cleaned_meta = {k: v for k, v in meta.items() if v is not None}

            documents.append(Document(content=content, meta=cleaned_meta))
            urls.append(url)

        logger.debug(f"Processed {len(documents)} documents from SerpBase for query '{query}'")
        return {"documents": documents, "links": urls}

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the component to a dictionary.
        """
        return default_to_dict(self, endpoint=self.endpoint, timeout=self.timeout)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SerpBaseWebSearch":
        """
        Deserializes the component from a dictionary.
        """
        return default_from_dict(cls, data)
