from typing import Any, Dict, List, Union

import httpx
from hayhooks import log as logger
from haystack import Document, component, default_from_dict, default_to_dict
from haystack.utils import Secret

DEFAULT_TIMEOUT = 10


@component
class BraveWebSearch:
    def __init__(self, api_key: Secret = Secret.from_env_var("BRAVE_API_KEY"), timeout: int = DEFAULT_TIMEOUT):
        self.endpoint = "https://api.search.brave.com/res/v1/web/search"
        try:
            self.api_key = api_key.resolve_value()
        except Exception:
            self.api_key = None

        self.is_enabled = self.api_key is not None
        if not self.is_enabled:
            logger.info("No BRAVE_API_KEY provided.  BraveWebSearch is disabled")

        self.timeout = timeout

    @component.output_types(documents=List[Document], links=List[str])
    def run(self, query: str, max_results: int = 5) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Performs a web search using a Brave instance.

        :param query: The search query.
        :param max_results: The maximum number of results to return.
        :return: A dictionary containing a list of Document objects and a list of result URLs.
        """

        if self.is_enabled:
            api_params = self._prepare_api_params(query, max_results)
            try:
                headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": self.api_key}
                response = httpx.get(self.endpoint, params=api_params, headers=headers, timeout=self.timeout)
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                api_response_json = response.json()
                response_dict = self._process_response(query, api_response_json, max_results)
                return {"documents": response_dict["documents"], "urls": response_dict["links"]}
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling Brave (sync): {e.response.status_code} - {e.response.text} for URL {e.request.url}")
            except httpx.RequestError as e:
                logger.error(f"Request error calling Brave (sync): {e} for URL {e.request.url}")
            except Exception as e:  # Catch any other unexpected errors during the request or JSON parsing
                logger.error(f"Unexpected error during Brave call (sync): {e}")

        return {"documents": [], "urls": []}  # Default

    def _prepare_api_params(
        self,
        query: str,
        max_results: int,
    ) -> Dict[str, Any]:
        """
        Prepares the dictionary of parameters for the Brave API call.
        """
        goggles = ["https://raw.githubusercontent.com/0foo/brave-search-goggles/main/goggles/no_crap.goggle"]
        params: Dict[str, Any] = {"q": query, "format": "json", "result_filter": "web", "goggles": goggles}

        if max_results > 0:
            params["count"] = max_results

        # Freshness gives the date range
        # pd, pw, pm, py

        return params

    @staticmethod
    def _process_response(query: str, response_json: Dict[str, Any], max_results_requested: int) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Parses the JSON response from Brave and converts it into Haystack Documents.
        """
        documents: List[Document] = []
        urls: List[str] = []

        logger.debug(f"Brave raw response for query '{query}': {response_json}")
        web = response_json.get("web")

        if not web:
            logger.warning(f"Brave returned 0 results for the query '{query}'")
            return {"documents": [], "links": []}

        web_results = web.get("results", [])
        logger.info(f"Brave results: {len(web_results)} results for query '{query}'")

        for result_item in web_results[: max_results_requested if max_results_requested > 0 else len(web_results)]:
            title = result_item.get("title")
            url = result_item.get("url")
            logger.debug(f"Brave result: {url} for query {query}")

            # Could use this in re-ranking
            # extra_snippets = result_item.get("extra_snippets")
            content = result_item.get("description")  # Main snippet

            if not url or not content:  # Skip if essential fields are missing
                logger.debug(f"Skipping result due to missing URL or content: {result_item}")
                continue

            meta = {
                "title": title,
                "url": url,
            }
            cleaned_meta = {k: v for k, v in meta.items() if v is not None}

            documents.append(Document(content=content, meta=cleaned_meta))
            urls.append(url)

        logger.debug(f"Processed {len(documents)} documents from Brave for query '{query}'")
        return {"documents": documents, "links": urls}

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the component to a dictionary.
        """
        return default_to_dict(self, endpoint=self.endpoint, timeout=self.timeout)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BraveWebSearch":
        """
        Deserializes the component from a dictionary.
        """
        return default_from_dict(cls, data)
