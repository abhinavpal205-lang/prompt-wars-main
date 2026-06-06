"""Trends over time, recurring triggers, and the one-click data wipe."""

import json
from collections import Counter
from typing import cast

from sqlmodel import Session, col, delete, select

from app.models import CheckinRecord, SentNotification, StudentProfile, as_utc
from app.schemas import Band, CheckinMode, DeletionResult, TrendPoint, TrendsResponse

_RECURRING_MIN_COUNT = 2
_RECURRING_LIMIT = 5


def get_trends(session: Session) -> TrendsResponse:
    """Time-ordered check-in history plus recurring triggers."""
    records = session.exec(select(CheckinRecord).order_by(col(CheckinRecord.created_at))).all()
    points = [
        TrendPoint(
            id=record.id or 0,
            created_at=as_utc(record.created_at),
            mode=cast(CheckinMode, record.mode),
            band=cast(Band, record.band),
            composite_0_100=record.composite,
            triggers=json.loads(record.triggers_json),
            crisis=record.crisis,
        )
        for record in records
    ]
    counts = Counter(trigger for point in points for trigger in point.triggers)
    recurring = [
        trigger
        for trigger, count in counts.most_common(_RECURRING_LIMIT)
        if count >= _RECURRING_MIN_COUNT
    ]
    return TrendsResponse(points=points, recurring_triggers=recurring)


def delete_all_data(session: Session) -> DeletionResult:
    """Wipe everything the student has stored, including the profile."""
    checkins = len(session.exec(select(CheckinRecord)).all())
    notifications = len(session.exec(select(SentNotification)).all())
    session.execute(delete(CheckinRecord))
    session.execute(delete(SentNotification))
    session.execute(delete(StudentProfile))
    session.commit()
    return DeletionResult(deleted_checkins=checkins, deleted_notifications=notifications)
