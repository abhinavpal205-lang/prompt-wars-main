"""Consented, student-visible parent/guardian notifications.

Design: opt-in only, framed to help the parent *support* the student (never
a score report or an alarm), and every sent message is stored verbatim so
the student can see exactly what was shared. With no SMTP configured, the
console stub prints the email to stdout so the app fully works without an
email account.
"""

import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

from sqlmodel import Session, desc, select

from app import constants
from app.config import Settings
from app.models import SentNotification, StudentProfile, as_utc, utcnow
from app.schemas import Band, ConsentSettings

logger = logging.getLogger(__name__)

_WEEKLY_INTERVAL = timedelta(days=7)

_BAND_PHRASE: dict[str, str] = {
    "calm": "seems to be feeling fairly steady",
    "mild": "is feeling some of the usual exam-season pressure",
    "elevated": "seems to be carrying quite a lot of pressure right now",
    "high": "seems to be having a really heavy time at the moment",
}

_SUPPORT_TIPS = (
    "- Ask how they're doing before asking about studies or marks.\n"
    "- A short walk, a meal together, or a no-exam-talk break helps a lot.\n"
    "- Remind them that your support doesn't depend on results."
)


class EmailSender(Protocol):
    """Delivery mechanism for notifications."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        """Deliver one message."""
        ...


class ConsoleEmailSender:
    """Stub delivery: prints the email to stdout (no SMTP configured)."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        """Print the email instead of sending it."""
        print(  # noqa: T201 — this stub's documented delivery mechanism IS stdout
            f"\n--- [console email stub] ---\nTo: {to}\nSubject: {subject}\n\n{body}\n--- end ---\n"
        )


class SmtpEmailSender:
    """Real delivery via SMTP (stdlib smtplib)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, *, to: str, subject: str, body: str) -> None:
        """Send one message over SMTP with STARTTLS when credentials exist."""
        message = EmailMessage()
        message["From"] = self._settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=20) as smtp:
            if self._settings.smtp_user:
                smtp.starttls()
                smtp.login(self._settings.smtp_user, self._settings.smtp_password)
            smtp.send_message(message)


def make_email_sender(settings: Settings) -> EmailSender:
    """Choose real SMTP delivery or the console stub."""
    if settings.smtp_configured:
        return SmtpEmailSender(settings)
    logger.info("SMTP not configured - parent notifications will print to stdout")
    return ConsoleEmailSender()


def should_notify(
    *,
    consent: ConsentSettings,
    band: Band,
    crisis: bool,
    last_sent_at: datetime | None,
    now: datetime,
) -> bool:
    """Pure consent/cadence gate for sending a parent notification."""
    if not consent.notify_enabled or not consent.parent_email or consent.cadence == "off":
        return False
    if consent.cadence == "on_elevated":
        return crisis or band in ("elevated", "high")
    # weekly digest: at most one message per interval
    return last_sent_at is None or now - last_sent_at >= _WEEKLY_INTERVAL


def build_parent_email(
    *,
    student_name: str,
    parent_name: str | None,
    band: Band,
    triggers: list[str],
    crisis: bool,
) -> tuple[str, str]:
    """Compose the supportive subject and body (no scores, no verdicts)."""
    student = student_name or "Your child"
    greeting = f"Dear {parent_name}," if parent_name else "Dear parent/guardian,"
    subject = f"A gentle check-in update about {student}"
    paragraphs = [
        greeting,
        (
            f"{student} did a wellbeing check-in on Sahaay and chose to share "
            f"this update with you. Right now, {student} {_BAND_PHRASE[band]}."
        ),
    ]
    if triggers:
        paragraphs.append("Things that seem to be on their mind: " + ", ".join(triggers) + ".")
    paragraphs.append("A few ways to support them this week:\n" + _SUPPORT_TIPS)
    if crisis:
        paragraphs.append(
            "Their check-in suggested they may be going through a particularly "
            "hard moment. Please make time to connect with them today, gently "
            "and without judgment."
        )
    paragraphs.append(
        f"If you'd like professional guidance, {constants.TELE_MANAS_NAME} is "
        f"free and available 24x7: {' or '.join(constants.TELE_MANAS_NUMBERS)}."
    )
    paragraphs.append(
        "This update is a supportive self-check-in summary, not a medical "
        "assessment. Sahaay shows your child every message it sends you."
    )
    return subject, "\n\n".join(paragraphs)


def consent_from_profile(profile: StudentProfile) -> ConsentSettings:
    """Project the stored profile onto the consent schema."""
    return ConsentSettings(
        parent_name=profile.parent_name,
        parent_email=profile.parent_email,
        notify_enabled=profile.notify_enabled,
        cadence=profile.cadence,  # type: ignore[arg-type]  # constrained on write
        student_visible=profile.student_visible,
    )


def notify_parent_if_consented(
    session: Session,
    sender: EmailSender,
    *,
    profile: StudentProfile,
    band: Band,
    triggers: list[str],
    crisis: bool,
    checkin_id: int | None,
) -> SentNotification | None:
    """Send (and record) a parent notification when consent and cadence allow.

    Returns the stored notification, or ``None`` when nothing was sent.
    Delivery failures are logged and swallowed — they never fail a check-in.
    """
    consent = consent_from_profile(profile)
    last = session.exec(
        select(SentNotification).order_by(desc(SentNotification.created_at))
    ).first()
    if not should_notify(
        consent=consent,
        band=band,
        crisis=crisis,
        last_sent_at=as_utc(last.created_at) if last else None,
        now=utcnow(),
    ):
        return None
    assert consent.parent_email is not None  # noqa: S101 — guaranteed by should_notify
    subject, body = build_parent_email(
        student_name=profile.name,
        parent_name=consent.parent_name,
        band=band,
        triggers=triggers,
        crisis=crisis,
    )
    try:
        sender.send(to=str(consent.parent_email), subject=subject, body=body)
    except Exception as exc:  # noqa: BLE001 — delivery failure must not fail the check-in
        logger.warning("parent notification delivery failed: %s", type(exc).__name__)
        return None
    notification = SentNotification(
        checkin_id=checkin_id,
        recipient=str(consent.parent_email),
        subject=subject,
        body=body,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification
