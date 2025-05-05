from datetime import date
from typing import Any, Dict, List, Literal, Union

from haystack import Document, component, default_from_dict, default_to_dict, logging
from haystack.utils import Secret, deserialize_secrets_inplace
from linkup import LinkupClient

logger = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS = 5
DEFAULT_SEARCH_DEPTH = "standard"


@component
class LinkupWebSearch:
    """Uses Linkup to search the web for relevant documents."""

    def __init__(self, api_key: Secret = Secret.from_env_var("LINKUP_API_KEY")):
        """Initialize the Linkup component.

        :param api_key: API key.
        """
        self.api_key = api_key
        self.linkup_client = LinkupClient(api_key=self.api_key.resolve_value())

        # Ensure that the API key is resolved.
        _ = self.api_key.resolve_value()

    @component.output_types(documents=List[Document], links=List[str])
    def run(self, query: str, search_depth: Literal["standard", "deep"] = DEFAULT_SEARCH_DEPTH) -> Dict[str, Union[List[Document], List[str]]]:
        """Use Linkup to search the web for relevant documents.

        Bad: "Tell me about AI companies"
        Good: "Describe the #1 AI company in France by revenue for 2024, focusing on their main products and recent partnerships"

        Parameters
        ----------
        query: str
            The query.
        search_depth: str
            The string "standard" or "deep", "standard" by default.

        Returns
        -------
        Dict[str, Union[List[Document], List[str]]]
            A dict of {"documents": documents, "urls": urls}

        """
        response = self._call_linkup(query=query, search_depth=search_depth)
        output = self._process_response(query, response)
        return output

    @staticmethod
    def _process_response(query, response):
        documents = []
        urls = []
        for result in response["results"]:
            doc_dict = {
                "name": result["name"],
                "type": result["type"],
                "content": result["content"],
                "url": result["url"],
                "score": result["score"],
            }
            urls.append(result["url"])
            documents.append(Document.from_dict(doc_dict))
        logger.debug(
            "Linkup returned {number_documents} results for the query '{query}'",
            number_documents=len(documents),
            query=query,
        )
        output = {"documents": documents, "urls": urls}
        return output

    def _call_linkup(
        self,
        query: str,
        search_depth: Literal["standard", "deep"],
        from_date: Union[date, None] = None,
        to_date: Union[date, None] = None,
    ):
        return self.linkup_client.search(query=query, output_type="searchResults", depth=search_depth, from_date=from_date, to_date=to_date)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the component to a dictionary.

        :returns:
              Dictionary with serialized data.
        """
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinkupWebSearch":
        """Deserializes the component from a dictionary.

        :param data:
            The dictionary to deserialize from.
        :returns:
                The deserialized component.
        """
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @staticmethod
    def _validate_search_depth(search_depth: str) -> Literal["standard", "deep"]:
        if search_depth == "standard":
            return "standard"
        else:
            return "deep"
