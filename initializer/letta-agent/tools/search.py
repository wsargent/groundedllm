import requests
import json
from typing import Optional

def search(query: str, include_domains: Optional[list[str]] = None) -> str:
    """
    This tool calls tavily search and returns results.

    Parameters
    ----------
    query: str
        The query for Tavily Search.
    include_domains: Optional[list[str]]
        The only domains to include in the search.

    Returns
    -------
    str
        A markdown list of document results that you can process as necessary.
    """
    # This assumes hayhooks is running and accessible at this address
    hayhooks_url = "http://hayhooks:1416/search/run"
    payload = {"query": query}
    if include_domains:
        payload["include_domains"] = include_domains

    try:
        response = requests.post(
            hayhooks_url,
            json=payload,
            timeout=30 # Add a timeout
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()["result"]
    except requests.exceptions.RequestException as e:
        return f"Error calling Hayhooks search pipeline: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"Error processing Hayhooks search response: {e}"
