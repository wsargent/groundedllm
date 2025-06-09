from typing import Dict

from hayhooks import log as logger
from haystack import component

from components.google.google_errors import GoogleAuthError
from components.google.google_oauth import GoogleOAuth


@component
class GoogleOAuthComponent:
    """
    Wrapper for Google OAuth functionality.
    """

    def __init__(self, oauth: GoogleOAuth = GoogleOAuth()):
        self.oauth = oauth

    def create_authorization_url(self, user_id: str):
        """
        Create a Google OAuth2 authorization URL.

        Args:
            user_id: Identifier for the user

        Returns:
            Dictionary with authorization URL and state
        """
        authorization_url, state = self.oauth.create_authorization_url(user_id)
        return {"authorization_url": authorization_url, "state": state}

    def check_auth_status(self, user_id: str):
        """
        Check if a user is authenticated.

        Args:
            user_id: Identifier for the user

        Returns:
            True if authenticated and not expired, False otherwise
        """
        return self.oauth.check_auth_status(user_id)

    def get_credentials(self, user_id: str):
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

    @component.output_types(documents=Dict[str, str])
    def run(self, user_id: str):
        logger.debug(f"Running google_auth for user_id='{user_id}'")

        try:
            is_authenticated = self.check_auth_status(user_id=user_id)
            if is_authenticated:
                logger.info(f"User '{user_id}' is already authenticated.")
                return {"authenticated": True, "user_id": user_id}
            else:
                logger.info(f"User '{user_id}' is not authenticated. Generating authorization URL.")
                auth_url_data = self.create_authorization_url(user_id=user_id)
                return auth_url_data
        except GoogleAuthError as e:  # Example of catching a specific error
            logger.warning(f"GoogleAuthError during google_auth for user '{user_id}': {e.message if hasattr(e, 'message') else str(e)}")
            # Re-raise or convert to HTTPException as per Hayhooks error handling
            raise
        except Exception as e:
            logger.error(f"Unexpected error in google_auth for user '{user_id}': {e}", exc_info=True)
            # Convert to a generic runtime error; Hayhooks will make it a 500.
            raise RuntimeError(f"An unexpected error occurred in GoogleAuth: {str(e)}")
