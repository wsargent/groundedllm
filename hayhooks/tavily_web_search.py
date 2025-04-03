from typing import Any, Dict, List, Optional, Union
from typing import Literal

from haystack import (
    Document,
    component,
    default_from_dict,
    default_to_dict,
    logging,
)
from haystack.utils import Secret, deserialize_secrets_inplace

from tavily import TavilyClient

logger = logging.getLogger(__name__)

# https://docs.haystack.deepset.ai/docs/custom-components
TAVILY_BASE_URL = "https://api.tavily.com/search"


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
        max_results: int = 10,
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None 
    ) -> Dict[str, Union[List[Document], List[str]]]:
        """
        Uses [Tavily](https://docs.tavily.com/welcome) to search the web for relevant documents.

        Parameters
        -------------
        query: str
            The query.
        max_results: int
            The maximum number of results to return.
        include_domains: Optional[list[str]]
            The only website domains that should be searched.
        exclude_domains: Optional[list[str]]
            The website domains that should not be searched.
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
            search_depth="basic",
            time_range=None
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
