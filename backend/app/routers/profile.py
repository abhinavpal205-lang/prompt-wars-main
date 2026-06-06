"""Profile, consent, and notification-transparency endpoints."""

from fastapi import APIRouter, Request
from sqlmodel import desc, select

from app.deps import SessionDep, limiter
from app.models import SentNotification, as_utc
from app.schemas import ProfileOut, ProfileUpdate, SentNotificationOut
from app.services.profiles import get_or_create_profile, profile_to_schema, update_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def read_profile(request: Request, session: SessionDep) -> ProfileOut:
    """The student's profile and consent settings."""
    return profile_to_schema(get_or_create_profile(session))


@router.put("", response_model=ProfileOut)
@limiter.limit("20/minute")
async def write_profile(
    request: Request, payload: ProfileUpdate, session: SessionDep
) -> ProfileOut:
    """Update profile and consent (student-controlled, never covert)."""
    return profile_to_schema(update_profile(session, payload))


@router.get("/notifications", response_model=list[SentNotificationOut])
async def list_sent_notifications(
    request: Request, session: SessionDep
) -> list[SentNotificationOut]:
    """Every parent notification exactly as sent — full transparency."""
    notifications = session.exec(
        select(SentNotification).order_by(desc(SentNotification.created_at))
    ).all()
    return [
        SentNotificationOut(
            created_at=as_utc(n.created_at),
            recipient=n.recipient,
            subject=n.subject,
            body=n.body,
        )
        for n in notifications
    ]
