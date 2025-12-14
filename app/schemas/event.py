"""Event schemas."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import Field

from app.models.event import EventType
from app.schemas.base import BaseSchema


class EventCreate(BaseSchema):
    """Schema for creating an event."""

    class_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: EventType
    event_date: date
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    location: Optional[str] = None


class EventUpdate(BaseSchema):
    """Schema for updating an event."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    event_date: Optional[date] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    location: Optional[str] = None


class EventResponse(BaseSchema):
    """Schema for event response."""

    id: str
    class_id: str
    title: str
    description: Optional[str]
    event_type: EventType
    event_date: date
    start_time: Optional[str]
    end_time: Optional[str]
    location: Optional[str]
    created_by: str
    created_at: datetime


class EventListResponse(BaseSchema):
    """Schema for event list response."""

    items: List[EventResponse]
    total: int = 0


class CalendarViewResponse(BaseSchema):
    """Schema for calendar view response."""

    year: int
    month: int
    events: dict  # date -> List[EventResponse]
