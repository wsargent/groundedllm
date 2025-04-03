import requests
import json
from typing import List

def answer(question: str, urls: List[str]) -> str:
    """
    Passes the question to an LLM model that will do a search and extract
    the full content of the web pages, and answer the question.

    Parameters
    ----------
    question: str
        The question to answer.
    urls: List[str]
        The urls of the pages to use as context    

    Returns
    -------
    str
        The answer to the question from the agent.
    """
    hayhooks_url = "http://hayhooks:1416/answer/run"
    try:
        response = requests.post(
            hayhooks_url,
            json={"urls": urls, "question": question},
            timeout=60 
        )
        response.raise_for_status()
        return response.json()["result"]
    except requests.exceptions.RequestException as e:
        return f"Error calling Hayhooks answer pipeline: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"Error processing Hayhooks answer response: {e}"
