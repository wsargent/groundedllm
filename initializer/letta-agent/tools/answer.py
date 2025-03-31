import requests
import json # Import the json module
from typing import Optional # Keep Optional for consistency, though not used here

def answer(question: str) -> str:
    """
    Passes the question to an LLM model that will do a search and extract
    the full content of the web pages, and answer the question.

    Parameters
    ----------
    question: str
        The question to answer.

    Returns
    -------
    str
        The answer to the question from the agent.
    """
    # This assumes hayhooks is running and accessible at this address
    # Consider making the base URL configurable if needed
    hayhooks_url = "http://hayhooks:1416/answer/run"
    try:
        response = requests.post(
            hayhooks_url,
            json={"urls": urls, "question": question},
            timeout=60 # Add a timeout
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()["result"]
    except requests.exceptions.RequestException as e:
        # Log or handle the error appropriately before re-raising or returning an error message
        # For now, returning a simple error message string
        return f"Error calling Hayhooks answer pipeline: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"Error processing Hayhooks answer response: {e}"
