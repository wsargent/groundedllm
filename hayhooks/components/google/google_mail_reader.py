from typing import Any, Dict, List, Optional

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError as GoogleHttpError
from hayhooks import log as logger
from haystack.core.component import component
from haystack.dataclasses.document import Document  # Corrected import

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
class GoogleMailReader:
    """
    A Haystack component to list email messages from Google Mail (Gmail).
    Uses GoogleOAuth for authentication.
    """

    def __init__(self, google_oauth_provider: GoogleOAuth = GoogleOAuth()):
        """
        Initializes the GoogleMailMessageLister component.

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

    def list_messages(
        self,
        user_id: str,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        max_results: int = 25,
        page_token: Optional[str] = None,
        include_spam_trash: bool = False,
    ) -> Dict[str, Any]:
        """
        Lists email messages, optionally filtered.

        Returns:
            A dictionary with 'messages' (List[haystack.dataclasses.Document])
            and 'next_page_token' (Optional[str]).
        """
        haystack_documents: List[Document] = []

        try:
            service = self._get_gmail_service(user_id)

            list_request_params = {
                "userId": user_id,
                "maxResults": max_results,
                "includeSpamTrash": include_spam_trash,
            }
            if query:
                list_request_params["q"] = query
            if label_ids:
                list_request_params["labelIds"] = label_ids
            if page_token:
                list_request_params["pageToken"] = page_token

            response = service.users().messages().list(**list_request_params).execute()  # type: ignore

            message_ids_dict = response.get("messages", [])
            next_pg_token = response.get("nextPageToken")

            if not message_ids_dict:
                return {"messages": [], "next_page_token": next_pg_token}

            for msg_ref in message_ids_dict:
                msg_id = msg_ref.get("id")
                if msg_id:
                    try:
                        msg_request = service.users().messages().get(userId=user_id, id=msg_id, format="full")  # type: ignore
                        raw_msg = msg_request.execute()
                        if raw_msg:
                            msg_instance = GoogleMailMessage(**raw_msg)

                            # Convert to Haystack Document
                            doc_meta = {
                                "id": msg_instance.id,
                                "threadId": msg_instance.threadId,
                                "subject": msg_instance.subject,
                                "sender": msg_instance.sender_email,  # For prompt template: doc.meta.sender
                                "recipient_emails": msg_instance.recipient_emails,
                                "snippet": msg_instance.snippet,
                                "date": msg_instance.internalDate.isoformat() if msg_instance.internalDate else None,  # For prompt template: doc.meta.date
                                "labelIds": msg_instance.labelIds,
                                # Keep original internalDate if needed for other purposes, though prompt uses 'date'
                                "internalDate_raw_ms": msg_instance.payload.headers[0].value
                                if msg_instance.payload and msg_instance.payload.headers and any(h.name == "Date" for h in msg_instance.payload.headers)
                                else msg_instance.internalDate.timestamp() * 1000
                                if msg_instance.internalDate
                                else None,
                                "sent_date_header": msg_instance.sent_date.isoformat() if msg_instance.sent_date else None,
                            }
                            # Filter out None values from meta to keep it clean
                            doc_meta_cleaned = {k: v for k, v in doc_meta.items() if v is not None}

                            doc = Document(
                                content=msg_instance.plain_text_body or "",  # Ensure content is not None
                                meta=doc_meta_cleaned,
                            )
                            haystack_documents.append(doc)
                    except GoogleHttpError as e_get:
                        logger.warning(f"Error fetching details for message ID {msg_id} for user {user_id}: {e_get}. Skipping.")
                    except Exception as e_detail:
                        logger.warning(f"Unexpected error fetching/processing details for message ID {msg_id}: {e_detail}. Skipping.")

            return {"messages": haystack_documents, "next_page_token": next_pg_token}

        except GoogleHttpError as e:
            self._handle_google_api_error(e)
            # _handle_google_api_error raises, so this part should ideally not be reached.
            # To satisfy type checker if it thinks this path is possible:
            return {"messages": [], "next_page_token": None}
        except (GoogleAuthError, InsufficientPermissionsError, InvalidInputError) as e:
            raise e
        except Exception as e:
            logger.error(f"Unexpected error listing emails for user {user_id}: {e}")
            raise GoogleAPIError(f"An unexpected error occurred while listing emails: {str(e)}", original_error=e)

    @component.output_types(messages=List[Document], next_page_token=Optional[str])
    def run(
        self,
        user_id: str,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        max_results: int = 25,
        page_token: Optional[str] = None,
        include_spam_trash: bool = False,
    ) -> Dict[str, Any]:
        """
        Lists email messages, optionally filtered by a query, labels, and pagination.

        Args:
            user_id: the required user id.
            query: Gmail search query.
            label_ids: List of label IDs to filter by.
            max_results: Maximum number of messages to return.
            page_token: Token for fetching the next page of results.
            include_spam_trash: Whether to include messages from SPAM and TRASH.

        Returns:
            A dictionary with 'messages' (List[haystack.dataclasses.Document])
            and 'next_page_token' (Optional[str]).
            In case of error, an RFC 7807 problem details dictionary is returned.
        """
        try:
            return self.list_messages(
                user_id=user_id,
                query=query,
                label_ids=label_ids,
                max_results=max_results,
                page_token=page_token,
                include_spam_trash=include_spam_trash,
            )
        except InvalidInputError as e:
            logger.warning(f"InvalidInputError in GoogleMailMessageLister.run for user '{user_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:InvalidInputError",
                "title": "Invalid Input",
                "status": 400,
                "detail": str(e),
                "parameter_name": e.parameter_name if hasattr(e, "parameter_name") else None,
            }
        except GoogleAuthError as e:
            logger.error(f"GoogleAuthError in GoogleMailMessageLister.run for user '{user_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:GoogleAuthError",
                "title": "Authentication Error",
                "status": 401,
                "detail": str(e),
                "requires_reauth": e.requires_reauth if hasattr(e, "requires_reauth") else False,
            }
        except InsufficientPermissionsError as e:
            logger.warning(f"InsufficientPermissionsError in GoogleMailMessageLister.run for user '{user_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:InsufficientPermissionsError",
                "title": "Permission Denied",
                "status": 403,
                "detail": str(e),
            }
        except ResourceNotFoundError as e:  # Should not happen in list, but good practice
            logger.warning(f"ResourceNotFoundError in GoogleMailMessageLister.run for user '{user_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:ResourceNotFoundError",
                "title": "Resource Not Found",
                "status": 404,
                "detail": str(e),
            }
        except RateLimitError as e:
            logger.warning(f"RateLimitError in GoogleMailMessageLister.run for user '{user_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:RateLimitError",
                "title": "Rate Limit Exceeded",
                "status": 429,
                "detail": str(e),
            }
        except GoogleAPIError as e:
            logger.error(f"GoogleAPIError in GoogleMailMessageLister.run for user '{user_id}': {e}")
            return {
                "type": "urn:hayhooks:google:mail:error:GoogleAPIError",
                "title": "Google API Error",
                "status": e.status_code if hasattr(e, "status_code") and e.status_code else 500,
                "detail": str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error in GoogleMailMessageLister.run for user '{user_id}': {e}")
            return {
                "type": "urn:hayhooks:common:error:InternalServerError",
                "title": "Internal Server Error",
                "status": 500,
                "detail": f"An unexpected error occurred: {str(e)}",
            }
