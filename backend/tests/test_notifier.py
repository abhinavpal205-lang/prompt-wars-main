"""Tests for consent/cadence gating and supportive parent notifications."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.models import SentNotification, StudentProfile
from app.schemas import Band, ConsentSettings
from app.services.notifier import (
    ConsoleEmailSender,
    build_parent_email,
    notify_parent_if_consented,
    should_notify,
)
from tests.fakes import FailingEmailSender, RecordingEmailSender

NOW = datetime(2026, 6, 6, 12, 0, tzinfo=UTC)


def consent(**overrides: object) -> ConsentSettings:
    base: dict[str, object] = {
        "parent_name": "Asha",
        "parent_email": "asha@example.com",
        "notify_enabled": True,
        "cadence": "weekly",
        "student_visible": True,
    }
    base.update(overrides)
    return ConsentSettings.model_validate(base)


# ---------------------------------------------------------------------------
# should_notify — pure gating
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("settings", "band", "crisis", "last_sent_at", "expected"),
    [
        # Consent is the master switch.
        (consent(notify_enabled=False), "high", True, None, False),
        (consent(parent_email=None), "high", True, None, False),
        (consent(cadence="off"), "high", True, None, False),
        # on_elevated: only elevated/high/crisis check-ins notify.
        (consent(cadence="on_elevated"), "calm", False, None, False),
        (consent(cadence="on_elevated"), "mild", False, None, False),
        (consent(cadence="on_elevated"), "elevated", False, None, True),
        (consent(cadence="on_elevated"), "high", False, None, True),
        (consent(cadence="on_elevated"), "calm", True, None, True),
        # weekly: first ever, inside the window, and after the window.
        (consent(cadence="weekly"), "calm", False, None, True),
        (consent(cadence="weekly"), "high", False, NOW - timedelta(days=2), False),
        (consent(cadence="weekly"), "calm", False, NOW - timedelta(days=8), True),
    ],
)
def test_should_notify(
    settings: ConsentSettings,
    band: Band,
    crisis: bool,
    last_sent_at: datetime | None,
    expected: bool,
) -> None:
    assert (
        should_notify(
            consent=settings, band=band, crisis=crisis, last_sent_at=last_sent_at, now=NOW
        )
        is expected
    )


# ---------------------------------------------------------------------------
# build_parent_email — supportive framing
# ---------------------------------------------------------------------------


def test_email_is_supportive_and_transparent() -> None:
    subject, body = build_parent_email(
        student_name="Ravi",
        parent_name="Asha",
        band="elevated",
        triggers=["sleep", "results pressure"],
        crisis=False,
    )
    assert "Ravi" in subject
    assert body.startswith("Dear Asha,")
    assert "sleep" in body
    assert "14416" in body
    assert "support" in body.lower()
    assert "shows your child every message" in body
    # Never a raw score or a verdict.
    assert "elevated" not in body.lower()
    assert not any(
        char.isdigit()
        for char in body.replace("14416", "").replace("1-800-891-4416", "").replace("24x7", "")
    )


def test_email_crisis_paragraph_only_when_crisis() -> None:
    _, calm_body = build_parent_email(
        student_name="Ravi", parent_name=None, band="calm", triggers=[], crisis=False
    )
    _, crisis_body = build_parent_email(
        student_name="Ravi", parent_name=None, band="high", triggers=[], crisis=True
    )
    assert "connect with them today" not in calm_body
    assert "connect with them today" in crisis_body
    assert crisis_body.startswith("Dear parent/guardian,")


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


def test_console_stub_prints_email(capsys: pytest.CaptureFixture[str]) -> None:
    ConsoleEmailSender().send(to="a@example.com", subject="Hello", body="Body text")
    captured = capsys.readouterr().out
    assert "a@example.com" in captured
    assert "Hello" in captured
    assert "Body text" in captured


def make_profile(session: Session, **overrides: object) -> StudentProfile:
    fields: dict[str, object] = {
        "name": "Ravi",
        "exam": "NEET",
        "parent_name": "Asha",
        "parent_email": "asha@example.com",
        "notify_enabled": True,
        "cadence": "on_elevated",
    }
    fields.update(overrides)
    profile = StudentProfile.model_validate(fields)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def test_notify_sends_and_stores_student_visible_copy(session: Session) -> None:
    profile = make_profile(session)
    sender = RecordingEmailSender()
    stored = notify_parent_if_consented(
        session,
        sender,
        profile=profile,
        band="high",
        triggers=["results pressure"],
        crisis=False,
        checkin_id=None,
    )
    assert stored is not None
    assert len(sender.sent) == 1
    saved = session.exec(select(SentNotification)).all()
    assert len(saved) == 1
    assert saved[0].body == sender.sent[0][2]  # exactly what was sent


def test_notify_respects_consent_off(session: Session) -> None:
    profile = make_profile(session, notify_enabled=False)
    sender = RecordingEmailSender()
    assert (
        notify_parent_if_consented(
            session, sender, profile=profile, band="high", triggers=[], crisis=True, checkin_id=None
        )
        is None
    )
    assert sender.sent == []


def test_notify_weekly_window_suppresses_second_send(session: Session) -> None:
    profile = make_profile(session, cadence="weekly")
    sender = RecordingEmailSender()
    first = notify_parent_if_consented(
        session, sender, profile=profile, band="mild", triggers=[], crisis=False, checkin_id=None
    )
    second = notify_parent_if_consented(
        session, sender, profile=profile, band="mild", triggers=[], crisis=False, checkin_id=None
    )
    assert first is not None
    assert second is None
    assert len(sender.sent) == 1


def test_notify_delivery_failure_is_swallowed_and_not_recorded(session: Session) -> None:
    profile = make_profile(session)
    result = notify_parent_if_consented(
        session,
        FailingEmailSender(),
        profile=profile,
        band="high",
        triggers=[],
        crisis=False,
        checkin_id=None,
    )
    assert result is None
    assert session.exec(select(SentNotification)).all() == []
