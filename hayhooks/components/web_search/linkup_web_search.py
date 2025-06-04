from datetime import date
from typing import Dict, List, Literal, Union

from hayhooks import log as logger
from haystack import Document, component
from haystack.utils import Secret
from linkup import LinkupClient
from linkup.types import LinkupSearchResults, LinkupSearchTextResult

DEFAULT_MAX_RESULTS = 5
DEFAULT_SEARCH_DEPTH = "basic"


@component
class LinkupWebSearch:
    """Uses Linkup to search the web for relevant documents."""

    def __init__(self, api_key: Secret = Secret.from_env_var("LINKUP_API_KEY")):
        """Initialize the Linkup component.

        :param api_key: API key.
        """
        self.linkup_client = None

        try:
            api_key_value = api_key.resolve_value()
            if api_key_value:
                self.linkup_client = LinkupClient(api_key=api_key_value)
        except (ValueError, KeyError):
            logger.info("LINKUP_API_KEY not provided. LinkupWebSearch is disabled.")

    @component.output_types(documents=List[Document], links=List[str])
    def run(self, query: str, search_depth: str = DEFAULT_SEARCH_DEPTH) -> Dict[str, Union[List[Document], List[str]]]:
        """Use Linkup to search the web for relevant documents.

        Bad: "Tell me about AI companies"
        Good: "Describe the #1 AI company in France by revenue for 2024, focusing on their main products and recent partnerships"

        Parameters
        ----------
        query: str
            The query.
        search_depth: str
            The string "basic" or "advanced", "basic" by default.

        Returns
        -------
        Dict[str, Union[List[Document], List[str]]]
            A dict of {"documents": documents, "urls": urls}

        """
        valid_search_option = self._validate_search_depth(search_depth)

        if self.linkup_client is None:
            return {"documents": [], "urls": []}

        response = self._call_linkup(query=query, search_depth=valid_search_option)
        output = self._process_response(query, response)
        return output

    def _process_response(self, query, response: LinkupSearchResults):
        documents = []
        urls = []
        results: List[LinkupSearchTextResult] = response.results
        for index, result in enumerate(results):
            # Linkup does not have a score associated with it.
            logger.debug(f"Linkup result {result.url}")
            score: float = 1 - (index * 0.1)
            doc_dict = {"title": result.name, "score": score, "content": result.content, "url": result.url}
            urls.append(result.url)
            documents.append(Document.from_dict(doc_dict))
        number_documents = len(documents)
        if self.linkup_client and number_documents == 0:
            logger.warning(f"Linkup returned 0 results for the query '{query}'")
        else:
            logger.debug(f"Linkup returned {number_documents} results for the query '{query}'")
        output = {"documents": documents, "urls": urls}
        return output

    def _call_linkup(
        self,
        query: str,
        search_depth: Literal["standard", "deep"],
        from_date: Union[date, None] = None,
        to_date: Union[date, None] = None,
    ) -> LinkupSearchResults:
        return self.linkup_client.search(query=query, output_type="searchResults", depth=search_depth, from_date=from_date, to_date=to_date)

    @staticmethod
    def _validate_search_depth(search_depth: str) -> Literal["standard", "deep"]:
        if search_depth == "standard" or search_depth == "basic":
            return "standard"
        else:
            return "deep"
