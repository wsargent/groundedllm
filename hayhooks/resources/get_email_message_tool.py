import json
import os
from typing import Any, Dict

import requests

DEFAULT_MAIL_FORMAT = "full"


def get_email_message(
    message_id: str,
    user_id: str = os.getenv("HAYHOOKS_USER_ID"),
    mail_format: str = DEFAULT_MAIL_FORMAT,
) -> str:
    """
    Fetches a single Google Mail message by its ID.

    Args:
        message_id: The ID of the email message to retrieve. This is required.
        user_id: The user id, or the default user id if not specified. Call "google_auth" if you don't have this.
        mail_format: The format to return the message in ('full', 'metadata', 'raw', 'minimal').

    Returns:
        A JSON string representing a dictionary containing the 'message' (GoogleMailMessage)
        or an RFC 7807 error object.
        Example: {"message": GoogleMailMessage_object_or_None}
    """

    if not message_id:
        # Client-side validation for required parameter
        error_payload = {
            "type": "urn:hayhooks:tool:error:InvalidInputError",
            "title": "Invalid Input",
            "status": 400,
            "detail": "The 'message_id' parameter is required for fetching an email message.",
            "instance": "/tools/get_email_message/errors/missing-message-id",
        }
        return json.dumps(error_payload)

    payload: Dict[str, Any] = {
        "user_id": user_id,
        "message_id": message_id,
        "mail_format": mail_format,
    }

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    if not hayhooks_base_url:
        raise EnvironmentError("HAYHOOKS_BASE_URL environment variable is not set.")

    response = requests.post(f"{hayhooks_base_url}/get_email_message/run", json=payload)

    response_json = response.json()
    # print(f"Response from /get_email_message/run: {response_json}")

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.headers.get("content-type") == "application/json":
            return json.dumps(response_json)
        raise e

    return json.dumps(response_json)
