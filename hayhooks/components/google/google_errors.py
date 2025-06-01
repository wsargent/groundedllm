from typing import List, Optional


class GoogleIntegrationError(Exception):
    """Base class for Google integration errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class GoogleAPIError(GoogleIntegrationError):
    """Raised for general errors from the Google API."""

    def __init__(self, message: str, status_code: Optional[int] = None, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.status_code = status_code
        self.original_error = original_error


class GoogleAuthError(GoogleIntegrationError):
    """Raised for authentication problems with Google services."""

    def __init__(self, message: str, requires_reauth: bool = False):
        super().__init__(message)
        self.requires_reauth = requires_reauth


class InsufficientPermissionsError(GoogleAPIError):
    """Raised for 403 errors due to lack of permissions."""

    def __init__(self, message: str, missing_scopes: Optional[List[str]] = None, status_code: int = 403):
        super().__init__(message, status_code=status_code)
        self.missing_scopes = missing_scopes


class ResourceNotFoundError(GoogleIntegrationError):
    """Raised for 404 errors when a Google resource is not found."""

    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


class InvalidInputError(GoogleIntegrationError):
    """Raised for issues with input provided to a component."""

    def __init__(self, message: str, parameter_name: Optional[str] = None):
        super().__init__(message)
        self.parameter_name = parameter_name


class RateLimitError(GoogleAPIError):
    """Raised for 429 errors when Google API rate limits are exceeded."""

    def __init__(self, message: str, status_code: int = 429):
        super().__init__(message, status_code=status_code)
