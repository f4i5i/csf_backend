"""Events API endpoints."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from app.models.event import Event
from app.models.user import Role, User
from app.schemas.event import (
    CalendarViewResponse,
    EventCreate,
    EventListResponse,
    EventResponse,
    EventUpdate,
)
from core.db import get_db
from core.exceptions.base import ForbiddenException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """Create event. Coach only."""
    if current_user.role not in [Role.COACH, Role.ADMIN, Role.OWNER]:
        raise ForbiddenException(message="Only coaches can create events")

    event = Event(**data.model_dump(), created_by=current_user.id)
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    return EventResponse.model_validate(event)


@router.get("/class/{class_id}", response_model=EventListResponse)
async def list_events(
    class_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventListResponse:
    """List events for a class."""
    if start_date and end_date:
        events = await Event.get_by_class_and_date_range(
            db_session, class_id, start_date, end_date
        )
    else:
        events = await Event.get_by_class(db_session, class_id)

    return EventListResponse(items=[EventResponse.model_validate(e) for e in events])


@router.get("/calendar", response_model=CalendarViewResponse)
async def get_calendar_view(
    class_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarViewResponse:
    """Get calendar view for a specific month."""
    events = await Event.get_calendar_view(db_session, class_id, year, month)

    calendar_data = {}
    for event in events:
        date_str = event.event_date.isoformat()
        if date_str not in calendar_data:
            calendar_data[date_str] = []
        calendar_data[date_str].append(EventResponse.model_validate(event))

    return CalendarViewResponse(year=year, month=month, events=calendar_data)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """Get event details."""
    event = await Event.get_by_id(db_session, event_id)
    if not event:
        raise NotFoundException(message="Event not found")
    return EventResponse.model_validate(event)


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    data: EventUpdate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """Update event. Creator or admin only."""
    event = await Event.get_by_id(db_session, event_id)
    if not event:
        raise NotFoundException(message="Event not found")

    if (
        event.created_by != current_user.id
        and current_user.role not in [Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    updated = await event.update(db_session, **data.model_dump(exclude_unset=True))
    return EventResponse.model_validate(updated)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete event. Creator or admin only."""
    event = await Event.get_by_id(db_session, event_id)
    if not event:
        raise NotFoundException(message="Event not found")

    if (
        event.created_by != current_user.id
        and current_user.role not in [Role.ADMIN, Role.OWNER]
    ):
        raise ForbiddenException(message="Not authorized")

    event.is_active = False
    await db_session.commit()
