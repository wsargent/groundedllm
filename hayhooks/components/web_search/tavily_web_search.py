from typing import Dict, List, Literal, Optional, Union

from hayhooks import log as logger
from haystack import Document, component
from haystack.utils import Secret
from tavily import TavilyClient

TAVILY_BASE_URL = "https://api.tavily.com/search"

DEFAULT_MAX_RESULTS = 5
DEFAULT_SEARCH_DEPTH = "basic"


@component
class TavilyWebSearch:
    """Uses [Tavily](https://docs.tavily.com/welcome) to search the web for relevant documents."""

    def __init__(self, api_key: Secret = Secret.from_env_var("TAVILY_API_KEY")):
        """Initialize the TavilySearch component.

        :param api_key: API key.
        """
        self.tavily_client = None

        try:
            api_key_value = api_key.resolve_value()
            if api_key_value:
                self.tavily_client = TavilyClient(api_key=api_key_value)
        except Exception:
            logger.info("TavilyWebSearch component is disabled.")
            # Continue without a client - will return empty results

    @component.output_types(documents=List[Document], links=List[str])
    def run(
        self,
        query: str,
        search_depth: Literal["basic", "advanced"] = DEFAULT_SEARCH_DEPTH,
        time_range: Optional[Literal["day", "week", "month", "year"]] = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_domains: Optional[Union[str, list[str]]] = None,
        exclude_domains: Optional[Union[str, list[str]]] = None,
    ) -> Dict[str, Union[List[Document], List[str]]]:
        """Uses [Tavily](https://docs.tavily.com/welcome) to search the web for relevant documents.

        Parameters
        ----------
        query: str
            The query.
        search_depth: str
            The string "basic" or "advanced", "basic" by default.
            Advanced search looks for the most relevant content snippets and sources,
            and uses more sophisticated techniques to filter and rank search results,
            aiming for higher accuracy and relevance compared to the basic search option.
            An advanced search costs 2 API Credits, compared to the lower cost of a basic search.
        time_range: str
            The string "day", "week", "month", "year", or None.  None by default.
            Returns only results that match inside the given time range.
        max_results: int
            The maximum number of results to return.  5 by default.
        include_domains: Optional[Union[str, list[str]]]
            The only website domains that should be searched, None by default.
            Can be a comma-separated string or a list of strings.
        exclude_domains: Optional[Union[str, list[str]]]
            The website domains that should not be searched, None by default.
            Can be a comma-separated string or a list of strings.

        Returns
        -------
        Dict[str, Union[List[Document], List[str]]]
            A dict of {"documents": documents, "urls": urls}

        """

        if self.tavily_client is None:
            return {"documents": [], "urls": []}

        # Convert string parameters to lists if needed
        include_domains_list = self._convert_domains_to_list(include_domains)
        exclude_domains_list = self._convert_domains_to_list(exclude_domains)

        try:
            response = self._call_tavily(query=query, search_depth=search_depth, max_results=max_results, include_domains=include_domains_list, exclude_domains=exclude_domains_list, time_range=time_range)
            output = self._process_response(query, response)
            return output
        except Exception as e:
            logger.error(
                f"""Failed on query={query}, search_depth={search_depth}, max_results={max_results},
                                         include_domains={include_domains}, exclude_domains={exclude_domains},
                                         time_range={time_range}""",
                e,
            )
            return {"documents": [], "urls": []}

    def _process_response(self, query: str, response: dict):
        documents = []
        urls = []
        # logger.debug(f"Tavily response: {response}")
        for result in response["results"]:
            url = result["url"]
            doc_dict = {
                "title": result["title"],
                "content": result["content"],
                "url": url,
                "score": result["score"],
            }
            logger.debug(f"Tavily result {url}")
            urls.append(url)
            documents.append(Document.from_dict(doc_dict))

        number_documents = len(documents)
        if self.tavily_client and number_documents == 0:
            logger.warning(f"Tavily returned 0 results for the query '{query}'")
        else:
            logger.debug(f"Tavily returned {number_documents} results for the query '{query}'")
        output = {"documents": documents, "urls": urls}
        return output

    def _call_tavily(
        self,
        query: str,
        search_depth: str,
        max_results: int,
        time_range: Optional[Literal["day", "week", "month", "year"]],
        include_domains: Optional[list[str]],
        exclude_domains: Optional[list[str]],
    ) -> dict:
        # https://github.com/tavily-ai/tavily-python?tab=readme-ov-file#api-methods
        return self.tavily_client.search(query, max_results=max_results, time_range=time_range, include_domains=include_domains, exclude_domains=exclude_domains, search_depth=self._validate_search_depth(search_depth))

    @staticmethod
    def _validate_search_depth(search_depth: str) -> Literal["basic", "advanced"]:
        if search_depth == "advanced":
            return "advanced"
        else:
            return "basic"

    @staticmethod
    def _convert_domains_to_list(domains: Optional[Union[str, list[str]]]) -> Optional[list[str]]:
        """Convert domains parameter to list format."""
        if domains is None:
            return None
        if isinstance(domains, str):
            # Split by comma and strip whitespace
            return [domain.strip() for domain in domains.split(",") if domain.strip()]
        return domains
