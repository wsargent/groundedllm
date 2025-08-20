from typing import Dict, List, Optional, Union

from exa_py import Exa
from exa_py.api import Result, SearchResponse
from hayhooks import log as logger
from haystack import Document, component
from haystack.utils import Secret

DEFAULT_MAX_RESULTS = 5


@component
class ExaWebSearch:
    """Uses [Exa](https://docs.exa.ai/reference/getting-started) to search the web for relevant documents."""

    def __init__(self, api_key: Secret = Secret.from_env_var("EXA_API_KEY")):
        """Initialize the ExaWebSearch component.

        :param api_key: API key.
        """
        self.exa_client = None
        try:
            self.exa_client = Exa(api_key=api_key.resolve_value())
        except ValueError:
            logger.info("EXA_API_KEY not provided. ExaWebSearch is disabled.")

    @component.output_types(documents=List[Document], links=List[str])
    def run(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_domains: Optional[Union[str, list[str]]] = None,
        exclude_domains: Optional[Union[str, list[str]]] = None,
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
        if not self.exa_client:
            return {"documents": [], "urls": []}

        # Convert string parameters to lists if needed
        include_domains_list = self._convert_domains_to_list(include_domains)
        exclude_domains_list = self._convert_domains_to_list(exclude_domains)

        response = self._call_exa(query=query, max_results=max_results, include_domains=include_domains_list, exclude_domains=exclude_domains_list)
        output = self._process_response(query, response)
        return output

    @component.output_types(documents=List[Document], links=List[str])
    async def run_async(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        include_domains: Optional[Union[str, list[str]]] = None,
        exclude_domains: Optional[Union[str, list[str]]] = None,
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
        if not self.exa_client:
            return {"documents": [], "urls": []}

        # Convert string parameters to lists if needed
        include_domains_list = self._convert_domains_to_list(include_domains)
        exclude_domains_list = self._convert_domains_to_list(exclude_domains)

        response = self._call_exa(query=query, max_results=max_results, include_domains=include_domains_list, exclude_domains=exclude_domains_list)
        output = self._process_response(query, response)
        return output

    def _process_response(self, query: str, response: SearchResponse[Result]):
        documents = []
        urls = []
        # logger.debug(f"Exa response: {response}")

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
            logger.debug(f"Exa result {result.url}")
            urls.append(result.url)
            documents.append(Document.from_dict(doc_dict))

        number_documents = len(documents)
        if self.exa_client and number_documents == 0:
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

    @staticmethod
    def _convert_domains_to_list(domains: Optional[Union[str, list[str]]]) -> Optional[list[str]]:
        """Convert domains parameter to list format."""
        if domains is None:
            return None
        if isinstance(domains, str):
            # Split by comma and strip whitespace
            return [domain.strip() for domain in domains.split(",") if domain.strip()]
        return domains
