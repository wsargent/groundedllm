import os

import requests


def search(
    question: str,
    max_results: int = 5,
    search_depth: str = "basic",
    time_range: str = "",
    include_domains: str = "",
    exclude_domains: str = "",
) -> str:
    """
    This method takes a user's question, performs a web search using Tavily,
    constructs a prompt with the search results, and generates an answer
    using an LLM. It allows customization of the search parameters.

    Parameters
    ----------
    question : str
        The user's query to search for and answer.
    max_results : int
        The maximum number of search results to retrieve from Tavily.
        Set this to 5 unless you specifically want more documents.
    search_depth : str
        The depth of the web search: "basic" or "advanced".
        Using "basic" provides standard results.
        Using "advanced" is higher relevance at a higher cost (2 API credits vs 1).
    time_range: str
        The range of time to search for: "day", "week", "month", "year", or "" to ignore.
        Use this when recent results are desired.
    include_domains : str
        A list of domains to specifically include in the search results.
        Use "" to ignore this argument.
    exclude_domains : str
        A list of domains to specifically exclude from the search results.
        Use "" to ignore this argument.

    Returns
    -------
    str
        The generated answer based on the web search results.

    Raises
    ------
    RuntimeError
        If the pipeline fails to retrieve an answer from the LLM.
    """

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    response = requests.post(
        f"{hayhooks_base_url}/search/run",
        json={"question": question, "max_results": max_results, "search_depth": search_depth, "time_range": time_range, "include_domains": include_domains, "exclude_domains": exclude_domains},
    )
    response.raise_for_status()
    json_response = response.json()

    if "result" in json_response:
        result = json_response["result"]
        return result
    else:
        return f"Internal error: {json_response}"
