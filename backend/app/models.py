"""SQLModel tables.

Data minimization: no raw audio, video, frames, or transcripts are ever
stored — only coarse check-in summaries, the (encrypted) optional note,
profile/consent, and copies of sent notifications for student transparency.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Timezone-aware current time (UTC)."""
    return datetime.now(UTC)


class StudentProfile(SQLModel, table=True):
    """The student's profile and parent-notification consent."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    name: str = ""
    exam: str = ""
    parent_name: str | None = None
    parent_email: str | None = None
    notify_enabled: bool = False
    cadence: str = "weekly"
    student_visible: bool = True


class CheckinRecord(SQLModel, table=True):
    """One completed check-in. Contains no raw media."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    mode: str
    band: str
    composite: float
    triggers_json: str = "[]"
    free_note_encrypted: str | None = None
    crisis: bool = False


class SentNotification(SQLModel, table=True):
    """Exact copy of a parent notification, so the student can see it."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    checkin_id: int | None = Field(default=None, foreign_key="checkinrecord.id")
    recipient: str
    subject: str
    body: str
