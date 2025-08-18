import os

import requests


def extract(url: str) -> str:
    """Extract page from a URL and returns the full contents.

    This tool will fetch HTML, Markdown, PDF, or a plain text web page from a URL
    and returns the contents as JSON.

    If given a youtube URL, it will return the transcript.
    If given a github issue URL, it will return the contents as Markdown.
    If given a github repository URL to a file, it will return the contents of the file.
    If given a github repository URL to a directory, it will return documents representing the directory listing.

    If you want to get a summary of a web page or want specific information, use the excerpt tool instead.

    Args:
        url (str): The URL of the page to extract.

    Returns:
        str: A JSON document containing the contents of the pages.
    """

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    response = requests.post(
        f"{hayhooks_base_url}/extract/run",
        json={"url": url},
    )
    response.raise_for_status()
    json_response = response.json()

    if "result" in json_response:
        result = json_response["result"]
        return result
    else:
        return f"Internal error: {json_response}"
