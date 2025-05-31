import os

import requests

HAYHOOKS_BASE_URL = os.getenv("HAYHOOKS_BASE_URL")


def extract(url: str) -> str:
    """
    Extract page from a URL and returns the full contents.

    This tool will fetch HTML, Markdown, PDF, or a plain text web page from a URL
    and returns the contents as JSON.  If given a youtube URL, it will return the transcript.

    If you want to get a summary of a web page or want specific information, use the excerpt tool instead.

    Parameters
    ----------
    url: str
        The URL of the page to extract.

    Returns
    -------
    str
        A JSON document containing the contents of the pages.
    """

    response = requests.post(
        f"{HAYHOOKS_BASE_URL}/extract/run",
        json={"url": url},
    )
    response.raise_for_status()
    json_body = response.json()
    return json_body["result"]
