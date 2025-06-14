import os
from typing import List, Optional

import requests


def search_stackoverflow(error_message: str, language: Optional[str] = None, technologies: Optional[List[str]] = None, min_score: Optional[int] = None, include_comments: bool = False, limit: int = 10) -> str:
    """
    Uses Stack Overflow to search for error-related questions and returns a summary of results.

    :param error_message: A string representing the error message which will be used
        as the primary search criteria.
    :type error_message: str

    :param language: An optional string specifying the programming language relevant
        to the error message.
    :type language: Optional[str]

    :param technologies: An optional list of strings specifying one or more technologies
        related to the error message.
    :type technologies: Optional[List[str]]

    :param min_score: An optional integer value specifying the minimum score threshold
        for filtering search results.
    :type min_score: Optional[int]

    :param include_comments: A boolean indicating whether to include comments in the
        search results. Defaults to False.
    :type include_comments: bool

    :param limit: An integer specifying the maximum number of results to return, defaults to 10.
    :type limit: int

    :return: A string containing the search results retrieved from the server.
    :rtype: str
    """
    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")

    response = requests.post(f"{hayhooks_base_url}/search_stackoverflow/run", json={"error_message": error_message, "language": language, "technologies": technologies, "min_score": min_score, "include_comments": include_comments, "limit": limit})
    response.raise_for_status()
    json_response = response.json()

    if "result" in json_response:
        result = json_response["result"]
        return result
    else:
        return f"Internal error: {json_response}"
