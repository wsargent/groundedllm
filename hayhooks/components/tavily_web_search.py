from typing import Any, Dict, List, Optional, Union

from haystack import Document, component, default_from_dict, default_to_dict, logging
from haystack.utils import Secret, deserialize_secrets_inplace
from tavily import TavilyClient

logger = logging.getLogger(__name__)

TAVILY_BASE_URL = "https://api.tavily.com/search"

DEFAULT_MAX_RESULTS = 5
DEFAULT_SEARCH_DEPTH = "basic"


@component
class TavilyWebSearch:
    """
    Uses [Tavily](https://docs.tavily.com/welcome) to search the web for relevant documents.
    """

    def __init__(self, api_key: Secret = Secret.from_env_var("TAVILY_API_KEY")):
        """
        Initialize the TavilySearch component.

        :param api_key: API key.
        """

        self.api_key = api_key

        # Ensure that the API key is resolved.
        _ = self.api_key.resolve_value()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the component to a dictionary.

        :returns:
              Dictionary with serialized data.
        """
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TavilyWebSearch":
        """
        Deserializes the component from a dictionary.

        :param data:
            The dictionary to deserialize from.
        :returns:
                The deserialized component.
        """
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @component.output_types(documents=List[Document], links=List[str])
    def run(
        self,
        query: str,
        search_depth: str = DEFAULT_SEARCH_DEPTH,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Uses [Tavily](https://docs.tavily.com/welcome) to search the web for relevant documents.

        Parameters
        -------------
        query: str
            The query.
        search_depth: str
            The string "basic" or "advanced", "basic" by default.
            Advanced search looks for the most relevant content snippets and sources,
            and uses more sophisticated techniques to filter and rank search results,
            aiming for higher accuracy and relevance compared to the basic search option.
            An advanced search costs 2 API Credits, compared to the lower cost of a basic search.
        max_results: int
            The maximum number of results to return.  5 by default.
        include_domains: Optional[list[str]]
            The only website domains that should be searched, None by default.
        exclude_domains: Optional[list[str]]
            The website domains that should not be searched, None by default.

        Returns
        -------
        Dict[str, Union[List[Document], List[str]]]
            A dict of {"documents": documents, "urls": urls}
        """

        tavily_client = TavilyClient(api_key=self.api_key.resolve_value())
        # https://github.com/tavily-ai/tavily-python?tab=readme-ov-file#api-methods
        response = tavily_client.search(
            query,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            search_depth=search_depth,
            time_range=None,
        )

        documents = []
        urls = []
        for result in response["results"]:
            doc_dict = {
                "title": result["title"],
                "content": result["content"],
                "link": result["url"],
                "score": result["score"],
            }
            urls.append(result["url"])
            documents.append(Document.from_dict(doc_dict))

        logger.debug(
            "Tavily returned {number_documents} results for the query '{query}'",
            number_documents=len(documents),
            query=query,
        )
        return {"documents": documents, "urls": urls}
