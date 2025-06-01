import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class EventDateTime(BaseModel):
    """
    Represents the start or end time of a Google Calendar event.
    Corresponds to the EventDateTime structure in the Google Calendar API.
    """

    dateTime: Optional[datetime.datetime] = Field(None, description="The time, as a combined date-time value. If a time zone is specified, this is in the specified time zone.")
    date: Optional[datetime.date] = Field(None, description="The date, in YYYY-MM-DD format. The time zone is irrelevant if the event is an all-day event.")
    timeZone: Optional[str] = Field(None, description='The time zone in which the time is specified. (Formatted as an IANA Time Zone Database name, e.g. "Europe/Zurich".)')


class EventAttendee(BaseModel):
    """
    Represents an attendee of a Google Calendar event.
    """

    email: Optional[str] = Field(None, description="The attendee's email address, if available.")
    displayName: Optional[str] = Field(None, description="The attendee's name, if available.")
    organizer: Optional[bool] = Field(None, description="Whether the attendee is the organizer of the event.")
    self: Optional[bool] = Field(None, description="Whether the attendee is the authenticated user.")
    resource: Optional[bool] = Field(None, description="Whether the attendee is a resource (e.g., a room).")
    optional: Optional[bool] = Field(None, description="Whether this is an optional attendee.")
    responseStatus: Optional[str] = Field(None, description='The attendee\'s response status for the event (e.g., "needsAction", "declined", "tentative", "accepted").')
    comment: Optional[str] = Field(None, description="The attendee's response comment, if any.")
    additionalGuests: Optional[int] = Field(None, description="Number of additional guests.")


class EventPerson(BaseModel):
    """
    Represents the creator or organizer of a Google Calendar event.
    """

    email: Optional[str] = Field(None, description="The person's email address.")
    displayName: Optional[str] = Field(None, description="The person's name, if available.")
    self: Optional[bool] = Field(None, description="Whether this is the authenticated user.")


class GoogleCalendarEvent(BaseModel):
    """
    Represents a Google Calendar event.
    Based on the Google Calendar API Event Resource.
    """

    id: str = Field(description="Event ID.")
    status: Optional[str] = Field(None, description='Status of the event (e.g., "confirmed", "tentative", "cancelled").')
    htmlLink: Optional[str] = Field(None, description="Link to the event in Google Calendar.")
    created: Optional[datetime.datetime] = Field(None, description="Creation time of the event.")
    updated: Optional[datetime.datetime] = Field(None, description="Last modification time of the event.")
    summary: Optional[str] = Field(None, description="Title of the event.")
    description: Optional[str] = Field(None, description="Description of the event, can be HTML.")
    location: Optional[str] = Field(None, description="Geographic location of the event as free-form text.")
    creator: Optional[EventPerson] = Field(None, description="The creator of the event.")
    organizer: Optional[EventPerson] = Field(None, description="The organizer of the event.")
    start: Optional[EventDateTime] = Field(None, description="The start time of the event.")
    end: Optional[EventDateTime] = Field(None, description="The end time of the event.")
    attendees: Optional[List[EventAttendee]] = Field(None, description="The attendees of the event.")
    hangoutLink: Optional[str] = Field(None, description="An absolute link to the Google Meet hangout associated with this event.")
    recurringEventId: Optional[str] = Field(None, description="For an instance of a recurring event, this is the ID of the recurring event itself.")
