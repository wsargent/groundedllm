from typing import Any, Dict, List, Optional, Union

from exa_py import Exa
from exa_py.api import Result, SearchResponse
from hayhooks import log as logger
from haystack import Document, component, default_from_dict, default_to_dict
from haystack.utils import Secret, deserialize_secrets_inplace

DEFAULT_MAX_RESULTS = 5


@component
class ExaWebSearch:
    """Uses [Exa](https://docs.exa.ai/reference/getting-started) to search the web for relevant documents."""

    def __init__(self, api_key: Secret = Secret.from_env_var("EXA_API_KEY")):
        """Initialize the ExaWebSearch component.

        :param api_key: API key.
        """
        self.exa_client = None
        self.has_valid_client = False
        self.api_key = api_key

        try:
            self.exa_client = Exa(api_key=api_key.resolve_value())
            self.has_valid_client = True
        except ValueError:
            logger.warning("No valid Exa API key provided. ExaWebSearch will not return any results.")

    @component.output_types(documents=List[Document], links=List[str])
    def run(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> Dict[str, Union[List[Document], List[str]]]:
        """Uses [Exa](https://docs.exa.ai/reference/getting-started) to search the web for relevant documents.

        Parameters
        ----------
        query: str
            The query.
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
        if not self.has_valid_client:
            logger.warning(f"No valid Exa client available. Returning empty results for query: '{query}'")
            return {"documents": [], "urls": []}

        response = self._call_exa(query=query, max_results=max_results, include_domains=include_domains, exclude_domains=exclude_domains)
        output = self._process_response(query, response)
        return output

    @component.output_types(documents=List[Document], links=List[str])
    async def run_async(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> Dict[str, Union[List[Document], List[str]]]:
        """Asynchronous version of run method.

        Parameters
        ----------
        query: str
            The query.
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
        if not self.has_valid_client:
            logger.warning(f"No valid Exa client available. Returning empty results for query: '{query}'")
            return {"documents": [], "urls": []}

        response = self._call_exa(query=query, max_results=max_results, include_domains=include_domains, exclude_domains=exclude_domains)
        output = self._process_response(query, response)
        return output

    @staticmethod
    def _process_response(query: str, response: SearchResponse[Result]):
        documents = []
        urls = []
        logger.debug(f"Exa response: {response}")

        for result in response.results:
            # Attributes:
            #     text(str, optional)
            #     highlights(List[str], optional)
            #     highlight_scores(List[float], optional)
            #     summary(str, optional)
            #     title (str): The title of the search result.
            #     url (str): The URL of the search result.
            #     id (str): The temporary ID for the document.
            #     score (float, optional): A number from 0 to 1 representing similarity.
            #     published_date (str, optional): An estimate of the creation date, from parsing HTML content.
            #     author (str, optional): The author of the content (if available).
            #     image (str, optional): A URL to an image associated with the content (if available).
            #     favicon (str, optional): A URL to the favicon (if available).
            #     subpages (List[_Result], optional): Subpages of main page
            #     extras (Dict, optional): Additional metadata; e.g. links, images.
            doc_dict = {
                "title": result.title,
                "content": result.text or result.summary,
                "url": result.url,
                "score": result.score,
            }
            urls.append(result.url)
            documents.append(Document.from_dict(doc_dict))

        number_documents = len(documents)
        if number_documents == 0:
            logger.warning(f"Exa returned 0 results for the query '{query}'")
        else:
            logger.debug(f"Exa returned {number_documents} results for the query '{query}'")
        output = {"documents": documents, "urls": urls}
        return output

    def _call_exa(
        self,
        query: str,
        max_results: int,
        include_domains: Optional[list[str]],
        exclude_domains: Optional[list[str]],
    ) -> SearchResponse:
        # https://github.com/exa-labs/exa-py/tree/master
        #     query (str): The query string.
        #     num_results (int, optional): Number of search results to return (default 10).
        #     include_domains (List[str], optional): Domains to include in the search.
        #     exclude_domains (List[str], optional): Domains to exclude from the search.
        #     start_crawl_date (str, optional): Only links crawled after this date.
        #     end_crawl_date (str, optional): Only links crawled before this date.
        #     start_published_date (str, optional): Only links published after this date.
        #     end_published_date (str, optional): Only links published before this date.
        #     include_text (List[str], optional): Strings that must appear in the page text.
        #     exclude_text (List[str], optional): Strings that must not appear in the page text.
        #     use_autoprompt (bool, optional): Convert query to Exa (default False).
        #     type (str, optional): 'keyword' or 'neural' (default 'neural').
        #     category (str, optional): e.g. 'company'
        #     flags (List[str], optional): Experimental flags for Exa usage.
        #     moderation (bool, optional): If True, the search results will be moderated for safety.
        return self.exa_client.search(query, use_autoprompt=True, num_results=max_results, include_domains=include_domains, exclude_domains=exclude_domains)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the component to a dictionary.

        :returns:
              Dictionary with serialized data.
        """
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            has_valid_client=self.has_valid_client,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExaWebSearch":
        """Deserializes the component from a dictionary.

        :param data:
            The dictionary to deserialize from.
        :returns:
                The deserialized component.
        """
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)
