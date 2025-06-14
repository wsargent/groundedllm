import json
import os

import requests


def google_auth(user_id: str = os.getenv("HAYHOOKS_USER_ID")) -> str:
    """
    Checks the user's Google authentication, and provides an authorization URL to display to the user.

    If the user is authenticated, return {"authenticated":true}

    If the user is not authenticated, returns a Markdown link that the user should click on.

    Please use this information to display a Google authorization message to the user, like this:

    "It looks like I need access to Google. Please click this link to authorize:
    [Authorize Google Access]({authorization_url}?user_id={user_id})"

    Parameters
    ----------
    user_id: str
      The user id to use for google authentication, will use default if not set.

    Return
    ------
      str:
        The user's authentication status, or a registration link.
    """
    user_id = os.getenv("HAYHOOKS_USER_ID")

    hayhooks_base_url = os.getenv("HAYHOOKS_BASE_URL")
    response = requests.post(f"{hayhooks_base_url}/google_auth/run", json={"user_id": user_id})

    response.raise_for_status()
    json_response = response.json()
    if "result" in json_response:
        result = json_response["result"]
        authenticated = result.get("authenticated")
        if authenticated:
            return json.dumps(result)
        else:
            # this is a GET because it doesn't go through hayhooks pipeline wrapper
            response = requests.get(f"{hayhooks_base_url}/google-auth-initiate", params={"user_id": user_id})
            response.raise_for_status()
            response_json = response.json()
            url = response_json.get("authorization_url")
            return f"[Register Link]({url})"
    else:
        return f"Internal error: {json_response}"
