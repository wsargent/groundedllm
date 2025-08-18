import os
from typing import List

import requests


def excerpt(urls: List[str], question: str) -> str:
    """
    Extract pages from URLs and answers questions about the pages.

    This tool will fetch HTML, Markdown, PDF, or plain text web pages from URLs.
    and sends them to an LLM model that can answer questions about the content of the
    web pages.  If given a URL to a youtube video, it will use the transcript as input
    to the LLM.

    If you want the full text of a web page, use the extract tool instead.

    Args:
        urls (List[str]): The URLs of the pages to extract.
        question str: The instructions to give and questions to ask about the web pages.

    Returns:
        str: The answer from the LLM model.
    """

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    response = requests.post(
        f"{hayhooks_base_url}/excerpt/run",
        json={"urls": urls, "question": question},
    )
    response.raise_for_status()
    json_response = response.json()

    if "result" in json_response:
        result = json_response["result"]
        return result
    else:
        return f"Internal error: {json_response}"
