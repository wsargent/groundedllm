import requests
import json
from typing import Optional # Keep Optional for consistency

def extract(url: str) -> str:
    """
    This tool takes a URL and returns the markdown of the page.

    Parameters
    ----------
    url: str
        The URL of the page to extract.

    Returns
    -------
    str
        The markdown content of the page, or an error message.
    """
    # This assumes hayhooks is running and accessible at this address
    hayhooks_url = "http://hayhooks:1416/extract/run"
    try:
        response = requests.post(
            hayhooks_url,
            json={"url": url},
            timeout=60 # Add a timeout
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        # The original code returned response.json(), assuming it was the markdown string.
        # Let's be safer and check the response structure if possible,
        # or at least return the text content. Assuming the API returns JSON with a 'markdown' key.
        # If it just returns raw markdown text, use response.text instead.
        # Adjust based on actual Hayhooks API response.
        # For now, sticking to the original assumption of returning the full JSON response text.
        # A better approach might be to extract a specific field like result['markdown']
        return response.text # Or response.json() if it's guaranteed to be JSON
    except requests.exceptions.RequestException as e:
        return f"Error calling Hayhooks extract pipeline: {e}"
    except json.JSONDecodeError as e:
         # If we expect JSON but get something else
         return f"Error decoding Hayhooks extract response: {e}. Response text: {response.text[:200]}" # Show partial response
