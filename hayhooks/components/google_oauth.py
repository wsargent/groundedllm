import json
import os
from typing import Dict, Optional, Tuple

from fastapi import HTTPException
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from hayhooks import log as logger
from haystack import component


class GoogleOAuth:
    """
    Component for handling Google OAuth2 authentication flow.
    """

    def __init__(
        self,
        client_secrets_file: str = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secret.json"),
        base_url: str = os.getenv("HAYHOOKS_BASE_URL", "http://localhost:8000"),
        token_storage_path: str = os.getenv("GOOGLE_TOKEN_STORAGE_PATH", "google_tokens"),
        scopes: list = None,
    ):
        """
        Initialize the Google OAuth component.

        Args:
            client_secrets_file: Path to the client secrets JSON file downloaded from Google Cloud Console
            base_url: Base URL of the Hayhooks server (must match the authorized redirect URI in Google Cloud Console)
            token_storage_path: Path to store the token files
            scopes: List of Google API scopes to request
        """
        self.client_secrets_file = client_secrets_file
        self.base_url = base_url
        self.token_storage_path = token_storage_path
        self.scopes = scopes or ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/calendar"]

        # Create token storage directory if it doesn't exist
        os.makedirs(self.token_storage_path, exist_ok=True)

        # Validate client secrets file
        if not os.path.exists(self.client_secrets_file):
            logger.warning(f"Google client secrets file not found at {self.client_secrets_file}")

    def create_authorization_url(self, user_id: str = "default_user") -> Tuple[str, str]:
        """
        Create a Google OAuth2 authorization URL.

        Args:
            user_id: Identifier for the user

        Returns:
            Tuple containing the authorization URL and state
        """
        try:
            flow = Flow.from_client_secrets_file(self.client_secrets_file, scopes=self.scopes, redirect_uri=f"{self.base_url}/google-auth-callback")

            authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")

            # Store the state and user_id mapping
            state_with_user = f"{state}|{user_id}"

            return authorization_url, state_with_user
        except Exception as e:
            logger.error(f"Error creating authorization URL: {e}")
            raise HTTPException(status_code=500, detail=f"Error creating authorization URL: {e}")

    def handle_callback(self, authorization_response: str, state: str) -> Dict:
        """
        Handle the OAuth2 callback from Google.

        Args:
            authorization_response: Full callback URL from Google
            state: State parameter from the callback

        Returns:
            Dictionary with user_id and success status
        """
        try:
            # Extract original state and user_id
            if not state or "|" not in state:
                raise HTTPException(status_code=400, detail="Invalid state parameter")

            original_state, user_id = state.split("|", 1)

            flow = Flow.from_client_secrets_file(self.client_secrets_file, scopes=self.scopes, redirect_uri=f"{self.base_url}/google-auth-callback", state=original_state)

            flow.fetch_token(authorization_response=authorization_response)
            credentials = flow.credentials

            # Save the credentials
            self.save_credentials(user_id, credentials)

            return {"user_id": user_id, "success": True}
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            raise HTTPException(status_code=500, detail=f"Error handling OAuth callback: {e}")

    def save_credentials(self, user_id: str, credentials: Credentials) -> None:
        """
        Save user credentials to storage.

        Args:
            user_id: Identifier for the user
            credentials: Google OAuth credentials
        """
        token_path = os.path.join(self.token_storage_path, f"{user_id}.json")

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }

        with open(token_path, "w") as token_file:
            json.dump(token_data, token_file)

    def load_credentials(self, user_id: str) -> Optional[Credentials]:
        """
        Load user credentials from storage.

        Args:
            user_id: Identifier for the user

        Returns:
            Google OAuth credentials if found, None otherwise
        """
        token_path = os.path.join(self.token_storage_path, f"{user_id}.json")

        if not os.path.exists(token_path):
            return None

        try:
            with open(token_path, "r") as token_file:
                token_data = json.load(token_file)

            credentials = Credentials(
                token=token_data["token"], refresh_token=token_data.get("refresh_token"), token_uri=token_data["token_uri"], client_id=token_data["client_id"], client_secret=token_data["client_secret"], scopes=token_data["scopes"]
            )

            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(GoogleRequest())
                self.save_credentials(user_id, credentials)

            return credentials
        except Exception as e:
            logger.error(f"Error loading credentials for user {user_id}: {e}")
            return None

    def check_auth_status(self, user_id: str) -> Dict:
        """
        Check if a user is authenticated.

        Args:
            user_id: Identifier for the user

        Returns:
            Dictionary with authentication status
        """
        credentials = self.load_credentials(user_id)
        return {"authenticated": credentials is not None and not credentials.expired, "user_id": user_id}


@component
class GoogleOAuthComponent:
    """
    Haystack component wrapper for Google OAuth functionality.
    """

    def __init__(
        self,
        client_secrets_file: str = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secret.json"),
        base_url: str = os.getenv("HAYHOOKS_BASE_URL", "http://localhost:8000"),
        token_storage_path: str = os.getenv("GOOGLE_TOKEN_STORAGE_PATH", "google_tokens"),
        scopes: list = None,
    ):
        self.oauth = GoogleOAuth(client_secrets_file=client_secrets_file, base_url=base_url, token_storage_path=token_storage_path, scopes=scopes)

    @component.output_types(authorization_url=str, state=str)
    def create_authorization_url(self, user_id: str = "default_user"):
        """
        Create a Google OAuth2 authorization URL.

        Args:
            user_id: Identifier for the user

        Returns:
            Dictionary with authorization URL and state
        """
        authorization_url, state = self.oauth.create_authorization_url(user_id)
        return {"authorization_url": authorization_url, "state": state}

    @component.output_types(authenticated=bool, user_id=str)
    def check_auth_status(self, user_id: str = "default_user"):
        """
        Check if a user is authenticated.

        Args:
            user_id: Identifier for the user

        Returns:
            Dictionary with authentication status
        """
        status = self.oauth.check_auth_status(user_id)
        return status

    @component.output_types(credentials=dict)
    def get_credentials(self, user_id: str = "default_user"):
        """
        Get user credentials.

        Args:
            user_id: Identifier for the user

        Returns:
            Dictionary with credentials or None
        """
        credentials = self.oauth.load_credentials(user_id)
        if credentials:
            return {
                "credentials": {
                    "token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_uri": credentials.token_uri,
                    "client_id": credentials.client_id,
                    "scopes": credentials.scopes,
                    "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                }
            }
        return {"credentials": None}
