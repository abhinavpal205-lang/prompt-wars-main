"""Student profile and consent management (single-student deployment)."""

from typing import cast

from sqlmodel import Session, select

from app.models import StudentProfile
from app.schemas import Cadence, ConsentSettings, ProfileOut, ProfileUpdate


def get_or_create_profile(session: Session) -> StudentProfile:
    """Return the singleton profile row, creating it on first access."""
    profile = session.exec(select(StudentProfile)).first()
    if profile is None:
        profile = StudentProfile()
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def update_profile(session: Session, data: ProfileUpdate) -> StudentProfile:
    """Apply onboarding/settings changes, including consent."""
    profile = get_or_create_profile(session)
    profile.name = data.name
    profile.exam = data.exam
    profile.parent_name = data.consent.parent_name
    profile.parent_email = str(data.consent.parent_email) if data.consent.parent_email else None
    profile.notify_enabled = data.consent.notify_enabled
    profile.cadence = data.consent.cadence
    profile.student_visible = data.consent.student_visible
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def profile_to_schema(profile: StudentProfile) -> ProfileOut:
    """Project the stored profile onto the API schema."""
    return ProfileOut(
        name=profile.name,
        exam=profile.exam,
        consent=ConsentSettings(
            parent_name=profile.parent_name,
            parent_email=profile.parent_email,
            notify_enabled=profile.notify_enabled,
            cadence=cast(Cadence, profile.cadence),
            student_visible=profile.student_visible,
        ),
        onboarded=bool(profile.name),
    )
