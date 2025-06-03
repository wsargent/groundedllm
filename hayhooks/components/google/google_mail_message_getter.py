from typing import Any, Dict, Optional

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError as GoogleHttpError
from hayhooks import log as logger
from haystack.core.component import component
from haystack.dataclasses.document import Document  # Added import

from components.google.dataclasses.google_mail_models import GoogleMailMessage
from components.google.google_errors import (
    GoogleAPIError,
    GoogleAuthError,
    InsufficientPermissionsError,
    InvalidInputError,
    RateLimitError,
    ResourceNotFoundError,
)
from components.google.google_oauth import GoogleOAuth


@component
class GoogleMailMessageGetter:
    """
    A Haystack component to fetch a single email message from Google Mail (Gmail).
    Uses GoogleOAuth for authentication.
    """

    def __init__(self, google_oauth_provider: GoogleOAuth = GoogleOAuth()):
        """
        Initializes the GoogleMailMessageGetter component.

        Args:
            google_oauth_provider: An instance of GoogleOAuth.
        """
        self.oauth = google_oauth_provider

    def _get_gmail_service(self, user_id: str) -> Resource:
        """
        Retrieves an authenticated Gmail API service client.
        """
        credentials = self.oauth.load_credentials(user_id)
        if not credentials or not credentials.valid:
            logger.error(f"Authentication failed for user {user_id}. Credentials not found, invalid or expired.")
            raise GoogleAuthError(f"User '{user_id}' is not authenticated or token is invalid/expired. Please re-authenticate.", requires_reauth=True)

        try:
            service = build("gmail", "v1", credentials=credentials, static_discovery=False)
            return service
        except Exception as e:
            logger.error(f"Failed to build Gmail service for user {user_id}: {e}")
            raise GoogleAPIError(f"Failed to initialize Gmail API service: {str(e)}", original_error=e)

    def _handle_google_api_error(self, error: GoogleHttpError, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        """Helper to translate GoogleHttpError to custom exceptions."""
        status_code = error.resp.status
        error_content = getattr(error, "_get_reason", lambda: str(error))()

        if status_code == 400:
            raise InvalidInputError(f"Invalid request to Google API: {error_content}", parameter_name=None)
        elif status_code == 401:
            raise GoogleAuthError(f"Authentication failed with Google API: {error_content}", requires_reauth=True)
        elif status_code == 403:
            raise InsufficientPermissionsError(f"Insufficient permissions for Google API operation: {error_content}")
        elif status_code == 404:
            msg = f"Google API resource not found: {error_content}"
            if resource_type and resource_id:
                msg = f"{resource_type} with ID '{resource_id}' not found."
            elif resource_type:
                msg = f"{resource_type} not found."
            raise ResourceNotFoundError(msg, resource_type=resource_type, resource_id=resource_id)
        elif status_code == 429:
            raise RateLimitError(f"Google API rate limit exceeded: {error_content}")
        else:
            raise GoogleAPIError(f"Google API request failed with status {status_code}: {error_content}", status_code=status_code, original_error=error)

    def get_message(self, user_id: str, message_id: str, mail_format: str = "full") -> Dict[str, Optional[Document]]:
        """
        Fetches a single email message by its ID and returns it as a Haystack Document.

        Args:
            user_id: The user id to indicate the authenticated user.
            message_id: The ID of the email message to retrieve.
            mail_format: The format to return the message in ('full', 'metadata', 'raw', 'minimal').
                         'full' provides payload for body/headers. 'metadata' is also good for most details.

        Returns:
            A dictionary containing the 'message' (Optional[haystack.dataclasses.Document]).
            The Document will be None if the message is not found or an error occurs before conversion.
        """
        if not message_id:
            raise InvalidInputError("message_id cannot be empty.", parameter_name="message_id")

        try:
            service = self._get_gmail_service(user_id)
            # Use 'full' or 'metadata' to ensure payload for parsing, 'raw' might be too minimal for GoogleMailMessage model
            actual_format = mail_format if mail_format in ["full", "metadata", "raw"] else "full"
            request = service.users().messages().get(userId=user_id, id=message_id, format=actual_format)  # type: ignore
            raw_message_dict = request.execute()

            if raw_message_dict:
                msg_instance = GoogleMailMessage(**raw_message_dict)

                doc_meta = {
                    "id": msg_instance.id,
                    "threadId": msg_instance.threadId,
                    "subject": msg_instance.subject,
                    "sender": msg_instance.sender_email,
                    "recipient_emails": msg_instance.recipient_emails,
                    "snippet": msg_instance.snippet,
                    "date": msg_instance.internalDate.isoformat() if msg_instance.internalDate else None,
                    "labelIds": msg_instance.labelIds,
                    "internalDate_raw_ms": msg_instance.payload.headers[0].value
                    if msg_instance.payload and msg_instance.payload.headers and any(h.name == "Date" for h in msg_instance.payload.headers)
                    else msg_instance.internalDate.timestamp() * 1000
                    if msg_instance.internalDate
                    else None,
                    "sent_date_header": msg_instance.sent_date.isoformat() if msg_instance.sent_date else None,
                    "sizeEstimate": msg_instance.sizeEstimate,
                    "historyId": msg_instance.historyId,
                    "raw_available": bool(msg_instance.raw),  # Indicate if raw field was populated
                }
                doc_meta_cleaned = {k: v for k, v in doc_meta.items() if v is not None}

                doc = Document(
                    content=msg_instance.plain_text_body or "",  # Ensure content is not None
                    meta=doc_meta_cleaned,
                )
                return {"message": doc}
            return {"message": None}  # Message not found by API
        except GoogleHttpError as e:
            # If a 404 occurs specifically, ResourceNotFoundError will be raised by _handle_google_api_error
            # and caught below, returning {"message": None} as intended by the original logic for not found.
            self._handle_google_api_error(e, resource_type="Gmail message", resource_id=message_id)
            # This part should be unreachable if _handle_google_api_error always raises.
            return {"message": None}
        except (GoogleAuthError, InsufficientPermissionsError, InvalidInputError) as e:
            # These are specific, handled errors that should propagate to the run method's error handling.
            raise e
        except ResourceNotFoundError:  # Explicitly catch if _handle_google_api_error raises it for 404
            return {"message": None}  # Message not found
        except Exception as e:
            logger.error(f"Unexpected error fetching email {message_id} for user {user_id}: {e}")
            raise GoogleAPIError(f"An unexpected error occurred while fetching email: {str(e)}", original_error=e)

    @component.output_types(message=Optional[Document])  # Output is a dict with key "message"
    def run(self, user_id: str, message_id: str, mail_format: str = "full") -> Dict[str, Any]:
        """
        Main entry point for fetching a single email message as a Haystack Document.

        Args:
            user_id: the required user id
            message_id: The ID of the email message to retrieve.
            mail_format: The format to return the message in ('full', 'metadata', 'raw', 'minimal').
                         'full' or 'metadata' is recommended for complete Document conversion.

        Returns:
            A dictionary with the key 'message' containing the Haystack Document (or None if not found/error).
            In case of other errors, an RFC 7807 problem details dictionary is returned.
        """
        try:
            if not user_id:
                raise InvalidInputError("user_id is required.", parameter_name="user_id")
            if not message_id:
                raise InvalidInputError("message_id is required.", parameter_name="message_id")

            # The get_message method now returns Dict[str, Optional[Document]]
            # or raises specific errors that are caught below.
            result_dict = self.get_message(user_id=user_id, message_id=message_id, mail_format=mail_format)
            return result_dict  # This will be {"message": Document_instance} or {"message": None}

        except InvalidInputError as e:
            logger.warning(f"InvalidInputError in GoogleMailMessageGetter.run for user '{user_id}', message_id '{message_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:InvalidInputError",
                "title": "Invalid Input",
                "status": 400,
                "detail": str(e),
                "parameter_name": e.parameter_name if hasattr(e, "parameter_name") else None,
            }
        except GoogleAuthError as e:
            logger.error(f"GoogleAuthError in GoogleMailMessageGetter.run for user '{user_id}', message_id '{message_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:GoogleAuthError",
                "title": "Authentication Error",
                "status": 401,
                "detail": str(e),
                "requires_reauth": e.requires_reauth if hasattr(e, "requires_reauth") else False,
            }
        except InsufficientPermissionsError as e:
            logger.warning(f"InsufficientPermissionsError in GoogleMailMessageGetter.run for user '{user_id}', message_id '{message_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:InsufficientPermissionsError",
                "title": "Permission Denied",
                "status": 403,
                "detail": str(e),
            }
        except ResourceNotFoundError as e:
            logger.warning(f"ResourceNotFoundError in GoogleMailMessageGetter.run for user '{user_id}', message_id '{message_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:ResourceNotFoundError",
                "title": "Resource Not Found",
                "status": 404,
                "detail": str(e),
            }
        except RateLimitError as e:
            logger.warning(f"RateLimitError in GoogleMailMessageGetter.run for user '{user_id}', message_id '{message_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:RateLimitError",
                "title": "Rate Limit Exceeded",
                "status": 429,
                "detail": str(e),
            }
        except GoogleAPIError as e:
            logger.error(f"GoogleAPIError in GoogleMailMessageGetter.run for user '{user_id}', message_id '{message_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:GoogleAPIError",
                "title": "Google API Error",
                "status": e.status_code if hasattr(e, "status_code") and e.status_code else 500,
                "detail": str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error in GoogleMailMessageGetter.run for user '{user_id}', message_id '{message_id}': {e}")
            return {
                "type": "urn:hayhooks:common:error:InternalServerError",
                "title": "Internal Server Error",
                "status": 500,
                "detail": f"An unexpected error occurred: {str(e)}",
            }
