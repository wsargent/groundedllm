import json
import os

import requests


def google_auth() -> str:
    """
    Checks the user's Google authentication, and provides an authorization URL to display to the user.

    The user_id is hardcoded to "test_user" for now.

    If the user is authenticated, return {"authenticated":true}

    If the user is not authenticated, returns a JSON message in the form

    {
      "authorization_url": authorization_url
      "state": state
    }

    Please use this information to display a Google authorization message to the user, like this:

    "It looks like I need access to Google. Please click this link to authorize:
    [Authorize Google Access]({authorization_url}?user_id={user_id})"

    :return: string indicating the user's authentication status
    """
    user_id = "test_user"

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    response = requests.post(f"{hayhooks_base_url}/google_auth/run", json={"user_id": user_id})

    response.raise_for_status()
    json_body = response.json()
    result = json_body["result"]
    print("result", result)
    authenticated = result.get("authenticated")
    if authenticated:
        return json.dumps(result)
    else:
        # this is a GET because it doesn't go through hayhooks pipeline wrapper
        response = requests.get(f"{hayhooks_base_url}/google-auth-initiate", params={"user_id": user_id})
        response.raise_for_status()
        # XXX return markdown text to the LLM.
        return json.dumps(response.json())
