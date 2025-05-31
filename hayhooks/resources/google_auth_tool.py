import os

import requests

HAYHOOKS_ENDPOINT = os.getenv("HAYHOOKS_BASE_URL")


def google_auth(user_id: str) -> str:
    """
    Checks the user's Google authentication, and provides an authorization URL to display to the user.

    If the user is authenticated, return "Authenticated"

    If the user is not authenticated, returns a JSON message in the form

    {"authorization_url": authorization_url, "state": state}

    Please use this information to display a Google authorization message to the user, like this:

    "It looks like I need access to Google. Please click this link to authorize:
    [Authorize Google Access]({authorization_url}?user_id={user_id})"

    :param user_id: Identifier for the user
    :return: string json indicating the user's authentication status
    """

    response = requests.get(f"{HAYHOOKS_ENDPOINT}/check-google-auth", {"user_id": user_id})
    response.raise_for_status()
    json_body = response.json()
    authenticated = json_body["authenticated"]
    if authenticated:
        return json_body
    else:
        response = requests.get(f"{HAYHOOKS_ENDPOINT}/google-auth-initiate", {"user_id": user_id})
        response.raise_for_status()
        return response.json()
