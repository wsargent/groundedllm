from typing import List

import requests


def extract(urls: List[str], question: str) -> str:
    """
    Extract pages from URLs and answers questions about the pages.

    This tool will fetch HTML, Markdown, PDF, or plain text web pages from URLs.
    and sends them to an LLM model that can answer questions about the content of the
    web pages. It cannot handle audio, video, or binary content.

    Parameters
    ----------
    urls: List[str]
        The URLs of the pages to extract.
    question: str
        The instructions to give and questions to ask about the web pages.
        For verbatim content, use "Give me the contents verbatim" as the question.

    Returns
    -------
    str
        The answer from the LLM model.

    """

    response = requests.post(
        "http://hayhooks:1416/extract/run",
        json={"urls": urls, "question": question},
    )
    return response.json()["result"]
