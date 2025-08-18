import json
import os
import uuid  # Added import
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from hayhooks import log as logger

DEFAULT_SCOPES = [
    # https://developers.google.com/workspace/calendar/api/auth
    "https://www.googleapis.com/auth/calendar.readonly",
    # https://developers.google.com/workspace/gmail/api/auth/scopes
    "https://www.googleapis.com/auth/gmail.readonly",
    # https://developers.google.com/youtube/v3/guides/auth/installed-apps#identify-access-scopes
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class GoogleOAuth:
    """
    Handles Google OAuth2 authentication flow.
    """

    def __init__(
        self,
        client_secrets_file: str = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secret.json"),
        base_callback_url: str = os.getenv("GOOGLE_AUTH_CALLBACK_URL", "http://localhost:1416"),
        token_storage_path: str = os.getenv("GOOGLE_TOKEN_STORAGE_PATH", "google_tokens"),
        scopes: Optional[List[str]] = None,
    ):
        """Initialize the Google OAuth component.

        Args:
            client_secrets_file (str): Path to the client secrets JSON file downloaded from Google Cloud Console
            base_callback_url (str): Base callback URL of the Hayhooks server (must match the authorized redirect URI in Google Cloud Console)
            token_storage_path (str): Path to store the token files
            scopes (Optional[List[str]]): List of Google API scopes to request
        """
        self.client_secrets_file = client_secrets_file
        self.base_callback_url = base_callback_url
        self.token_storage_path = token_storage_path
        self.scopes = scopes or DEFAULT_SCOPES

        # Create token storage directory if it doesn't exist
        os.makedirs(self.token_storage_path, exist_ok=True)

        # Validate client secrets file
        if not os.path.exists(self.client_secrets_file):
            logger.warning(f"Google client secrets file not found at {self.client_secrets_file}")

    def create_authorization_url(self, user_id: str) -> Tuple[str, str]:
        """
        Create a Google OAuth2 authorization URL.

        Args:
            user_id: Identifier for the user

        Returns:
            Tuple containing the authorization URL and state
        """
        try:
            flow = Flow.from_client_secrets_file(self.client_secrets_file, scopes=self.scopes, redirect_uri=f"{self.base_callback_url}/google-auth-callback")

            # Create a base state for CSRF protection part
            base_csrf_state = uuid.uuid4().hex

            # Combine base CSRF state with user_id
            composite_state = f"{base_csrf_state}|{user_id}"

            authorization_url, returned_state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                state=composite_state,  # Pass the composite state to Google
            )
            # returned_state will be equal to composite_state

            return authorization_url, composite_state
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
            logger.debug(f"handle_callback: authorization_response: {authorization_response}")

            # state (argument to this method) is composite_state from Google callback
            if not state or "|" not in state:
                logger.error(f"Invalid state parameter received: {state}")
                raise HTTPException(status_code=400, detail="Invalid state parameter: format error")

            # Split the composite state to get user_id for application logic
            # The CSRF part (_csrf_token_from_state) is implicitly verified by the library
            # when the flow is initialized with the full composite state.
            try:
                _csrf_token_from_state, user_id = state.split("|", 1)
            except ValueError:
                logger.error(f"Could not split state parameter: {state}")
                raise HTTPException(status_code=400, detail="Invalid state parameter: split error")

            # Initialize the flow with the *exact state string* received from Google.
            # The library will compare this with the 'state' param in authorization_response.
            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=self.scopes,
                redirect_uri=f"{self.base_callback_url}/google-auth-callback",
                state=state,  # Use the full composite state received from Google
            )

            flow.fetch_token(authorization_response=authorization_response)
            creds_from_flow = flow.credentials

            if not isinstance(creds_from_flow, Credentials):
                logger.error(f"Unexpected credentials type from Google OAuth flow: {type(creds_from_flow)}")
                raise HTTPException(status_code=500, detail="Internal server error: Unexpected credential type from Google.")

            # Save the credentials
            self.save_credentials(user_id, creds_from_flow)

            return {"user_id": user_id, "success": True}
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            raise HTTPException(status_code=500, detail=f"Error handling OAuth callback: {e}")

    def save_credentials(self, user_id: str, credentials: Credentials) -> None:
        """
        Save user credentials to storage.

        Args:
            user_id: Identifier for the user
            credentials: Union[Credentials, ExternalAccountCredentials]
        """
        logger.debug(f"save_credentials: user_id: {user_id}, credentials: {credentials}")

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
        logger.debug(f"load_credentials: user_id: {user_id}")

        token_path = os.path.join(self.token_storage_path, f"{user_id}.json")

        if not os.path.exists(token_path):
            return None

        try:
            with open(token_path, "r") as token_file:
                token_data = json.load(token_file)

            from datetime import datetime

            # Parse expiry if present
            expiry = None
            if token_data.get("expiry"):
                try:
                    expiry = datetime.fromisoformat(token_data["expiry"].replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Could not parse expiry date for user {user_id}: {token_data.get('expiry')}")

            credentials = Credentials(
                token=token_data["token"], refresh_token=token_data.get("refresh_token"), token_uri=token_data["token_uri"], client_id=token_data["client_id"], client_secret=token_data["client_secret"], scopes=token_data["scopes"], expiry=expiry
            )

            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(GoogleRequest())
                self.save_credentials(user_id, credentials)

            return credentials
        except Exception as e:
            logger.error(f"Error loading credentials for user {user_id}: {e}")
            return None

    def check_auth_status(self, user_id: str) -> bool:
        """
        Check if a user is authenticated.

        Args:
            user_id: Identifier for the user

        Returns:
            True if authenticated and not expired, False otherwise
        """
        credentials = self.load_credentials(user_id)
        return credentials is not None and not credentials.expired
