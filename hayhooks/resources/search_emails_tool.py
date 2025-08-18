import json
import os
from typing import Any, Dict, List, Optional

import requests

DEFAULT_MAX_RESULTS_SEARCH = 25


def search_emails(
    email_query: str,
    instruction: Optional[str] = None,
    user_id: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    max_results: int = DEFAULT_MAX_RESULTS_SEARCH,
    page_token: Optional[str] = None,
    include_spam_trash: bool = False,
) -> str:
    """Searches a user's Gmail messages based on a query.

    If an 'instruction' is provided, an LLM will show only the relevant parts of each email. Otherwise, all fetched emails
    (up to max_results) are returned.

    Args:
        email_query (str): Gmail search query string using Gmail operators:
            * from:"sender@domain.com" - emails from specific sender
            * to:"recipient@domain.com" - emails to specific recipient
            * subject:"keyword" - emails with keyword in subject line
            * has:attachment - emails with attachments
            * newer_than:Xd - emails newer than X days (e.g., newer_than:7d for last week)
            * older_than:Xd - emails older than X days
            * after:YYYY/MM/DD - emails after specific date
            * before:YYYY/MM/DD - emails before specific date
            * label:"label-name" - emails with specific label
            * is:unread / is:read - filter by read status
            * "exact phrase" - search for exact phrase
            * keyword1 OR keyword2 - search for either keyword
            * keyword1 AND keyword2 - search for both keywords
            * -keyword - exclude emails containing keyword

            Example queries:
            - from:"amazon.com" subject:shipped newer_than:14d
            - subject:"order confirmation" newer_than:7d
            - from:"support@company.com" has:attachment older_than:30d

            Best practices:
            - Default to searching recent emails (newer_than:14d) unless user specifies otherwise
            - Use specific sender domains when possible (from:"domain.com")
            - Combine multiple operators for precise results
            - Use quotes around exact phrases or email addresses with special characters

        instruction (Optional[str]): Instructions for the email analysis system on what information to extract
            and how to summarize the results. This guides the AI that processes the email content
            to focus on specific aspects.

            Examples:
            * "Find shipping notifications and extract tracking numbers and delivery dates"
            * "Look for order confirmations and summarize items purchased and order numbers"
            * "Find emails about upcoming events and extract dates, times, and locations"
            * "Identify customer support responses and summarize resolution status"

            The instruction helps the system understand the context and purpose of your search
            so it can provide more relevant summaries and highlight the information you need.

        user_id (Optional[str]): The user ID.
        label_ids (Optional[List[str]]): List of label IDs to filter by. Defaults to None.
        max_results (int): Maximum number of messages to return. Defaults to DEFAULT_MAX_RESULTS_SEARCH.
        page_token (Optional[str]): Token for fetching the next page of results. Defaults to None.
        include_spam_trash (bool): Whether to include messages from SPAM and TRASH. Defaults to False.

    Returns:
        str: JSON string containing the search results or error information.
    """
    actual_user_id = user_id if user_id is not None else os.getenv("HAYHOOKS_USER_ID")
    if not actual_user_id:
        # Handle missing user_id: either raise an error or return an RFC 7807 JSON error string
        error_payload = {
            "type": "urn:hayhooks:tool:error:ConfigurationError",
            "title": "Configuration Error",
            "status": 500,  # Or 400 if considered client-configurable
            "detail": "User ID is not provided and HAYHOOKS_USER_ID environment variable is not set.",
            "instance": "/tools/search_emails/errors/missing-user-id",
        }
        return json.dumps(error_payload)

    query = email_query
    if not query:
        # This check can be done client-side for immediate feedback,
        # though the server-side pipeline_wrapper also validates this.
        error_payload = {
            "type": "urn:hayhooks:tool:error:InvalidInputError",
            "title": "Invalid Input",
            "status": 400,
            "detail": "The 'query' parameter is required for searching emails.",
            "instance": "/tools/search_emails/errors/missing-query",
        }
        return json.dumps(error_payload)

    payload: Dict[str, Any] = {
        "user_id": actual_user_id,
        "query": query,
        "instruction": instruction,
        "max_results": max_results,
        "include_spam_trash": include_spam_trash,
    }
    if label_ids is not None:
        payload["label_ids"] = label_ids
    if page_token is not None:
        payload["page_token"] = page_token

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    if not hayhooks_base_url:
        raise EnvironmentError("HAYHOOKS_BASE_URL environment variable is not set.")

    response = requests.post(f"{hayhooks_base_url}/search_emails/run", json=payload)

    response_json = response.json()
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.headers.get("content-type") == "application/json":
            return json.dumps(response_json)
        raise e  # Re-raise if not a JSON error response

    return json.dumps(response_json)
