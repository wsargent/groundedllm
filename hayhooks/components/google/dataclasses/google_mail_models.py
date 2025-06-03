import base64
import re
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class EmailBody(BaseModel):
    attachmentId: Optional[str] = None
    size: int
    data: Optional[str] = None  # Base64url encoded content


class EmailHeader(BaseModel):
    name: str
    value: str


class EmailPayload(BaseModel):
    partId: Optional[str] = None
    mimeType: Optional[str] = None
    filename: Optional[str] = None
    headers: Optional[List[EmailHeader]] = None
    body: Optional[EmailBody] = None
    parts: Optional[List["EmailPayload"]] = None  # Recursive for multipart messages


# Forward reference for EmailPayload
EmailPayload.update_forward_refs()


class GoogleMailMessage(BaseModel):
    id: str
    threadId: str
    labelIds: Optional[List[str]] = Field(default_factory=list)
    snippet: Optional[str] = None
    historyId: Optional[str] = None
    internalDate: Optional[datetime] = None  # Timestamp in milliseconds epoch, needs conversion
    payload: Optional[EmailPayload] = None
    sizeEstimate: Optional[int] = None
    raw: Optional[str] = None  # Raw email content, base64url encoded

    # Helper Properties
    subject: Optional[str] = None
    sender_email: Optional[EmailStr] = None
    recipient_emails: Optional[List[EmailStr]] = Field(default_factory=list)
    sent_date: Optional[datetime] = None
    plain_text_body: Optional[str] = None

    @validator("internalDate", pre=True)
    def convert_internal_date(cls, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        try:
            # Google API returns internalDate as a string representing milliseconds since epoch
            return datetime.fromtimestamp(int(value) / 1000.0)
        except (ValueError, TypeError):
            return None  # Or raise a more specific error

    def __init__(self, **data: Any):
        super().__init__(**data)
        if self.payload and self.payload.headers:
            self.subject = self._extract_header_value("Subject")
            self.sender_email = self._extract_email_from_header("From")
            self.recipient_emails = self._extract_emails_from_header(["To", "Cc"])
            self.sent_date = self._extract_date_from_header("Date")

        if self.payload:
            self.plain_text_body = self._extract_plain_text_body(self.payload)

    def _extract_header_value(self, header_name: str) -> Optional[str]:
        if self.payload and self.payload.headers:
            for header in self.payload.headers:
                if header.name.lower() == header_name.lower():
                    return header.value
        return None

    def _extract_email_from_header(self, header_name: str) -> Optional[str]:
        header_value = self._extract_header_value(header_name)
        if header_value:
            # Simple regex to extract email, can be improved for more complex "From" fields
            match = re.search(r"[\w\.-]+@[\w\.-]+", header_value)
            if match:
                return match.group(0)  # Pydantic will validate on assignment
        return None

    def _extract_emails_from_header(self, header_names: List[str]) -> List[str]:
        emails_str: List[str] = []
        for header_name in header_names:
            header_value = self._extract_header_value(header_name)
            if header_value:
                # Split by comma for multiple recipients and extract each email
                found_emails = re.findall(r"[\w\.-]+@[\w\.-]+", header_value)
                for email_s in found_emails:
                    emails_str.append(email_s)  # Pydantic will validate on assignment
        return list(set(emails_str))  # Return unique email strings

    def _extract_date_from_header(self, header_name: str) -> Optional[datetime]:
        header_value = self._extract_header_value(header_name)
        if header_value:
            try:
                # Attempt to parse common date formats. This might need to be more robust.
                # Example: "Tue, 18 Jul 2023 10:30:00 -0700 (PDT)"
                # Removing timezone name in parentheses if present
                header_value = re.sub(r"\s*\([A-Z]+\)$", "", header_value.strip())
                # Common formats
                formats_to_try = [
                    "%a, %d %b %Y %H:%M:%S %z",  # RFC 5322 format
                    "%d %b %Y %H:%M:%S %z",  # Another common variant
                    "%a, %d %b %Y %H:%M:%S",  # Without timezone (assume UTC or local)
                    "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 like
                ]
                for fmt in formats_to_try:
                    try:
                        return datetime.strptime(header_value, fmt)
                    except ValueError:
                        continue
                # Fallback for simpler date strings if needed, or log a warning
            except Exception:
                # Log parsing error or handle as needed
                return None
        return None

    def _extract_plain_text_body(self, payload: EmailPayload) -> Optional[str]:
        """
        Recursively searches for the plain text body in the email payload.
        """
        if payload.mimeType == "text/plain" and payload.body and payload.body.data:
            try:
                return base64.urlsafe_b64decode(payload.body.data).decode("utf-8")
            except Exception:
                return None  # Or log error

        if payload.mimeType and payload.mimeType.startswith("multipart/") and payload.parts:
            for part in payload.parts:
                # In multipart/alternative, prefer text/plain over text/html
                if payload.mimeType == "multipart/alternative":
                    if part.mimeType == "text/plain":
                        body = self._extract_plain_text_body(part)
                        if body:
                            return body
                else:  # For other multipart types, recurse
                    body = self._extract_plain_text_body(part)
                    if body:  # Return the first one found in other multipart types
                        return body
            # If multipart/alternative and no text/plain found, could optionally look for text/html here
            # and strip tags, but design doc focuses on plain text for Phase 2.

        # If it's a single part message that's not text/plain but has a body (e.g. simple HTML email)
        # and we are strictly looking for text/plain, this will return None.
        # If the top-level payload itself is text/plain (not common for complex emails but possible for simple ones)
        if payload.body and payload.body.data and payload.mimeType == "text/plain":
            try:
                return base64.urlsafe_b64decode(payload.body.data).decode("utf-8")
            except Exception:
                return None

        return None
