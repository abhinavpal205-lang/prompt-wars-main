"""Pydantic request/response schemas and structured LLM output models.

LLM output models use ``extra="forbid"`` so unexpected model output fails
validation instead of silently passing through.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app import constants

Band = Literal["calm", "mild", "elevated", "high"]
Modality = Literal["form", "transcript", "audio", "facial"]
Cadence = Literal["off", "weekly", "on_elevated"]
CheckinMode = Literal["form", "voice"]

# ---------------------------------------------------------------------------
# Profile & consent
# ---------------------------------------------------------------------------


class ConsentSettings(BaseModel):
    """Student-controlled parent/guardian notification consent."""

    parent_name: str | None = Field(default=None, max_length=120)
    parent_email: EmailStr | None = None
    notify_enabled: bool = False
    cadence: Cadence = "weekly"
    student_visible: bool = True


class ProfileUpdate(BaseModel):
    """Editable profile fields (onboarding and settings)."""

    name: str = Field(max_length=120)
    exam: str = Field(default="", max_length=60)
    consent: ConsentSettings = Field(default_factory=ConsentSettings)


class ProfileOut(ProfileUpdate):
    """Profile as returned to the client."""

    onboarded: bool


# ---------------------------------------------------------------------------
# Check-in requests
# ---------------------------------------------------------------------------


class FormResponse(BaseModel):
    """The 10-item Likert self-report plus the explicit safety item."""

    answers: list[int] = Field(
        min_length=constants.FORM_ITEM_COUNT, max_length=constants.FORM_ITEM_COUNT
    )
    safety_flag: bool = False
    free_note: str | None = Field(default=None, max_length=constants.MAX_NOTE_CHARS)

    @field_validator("answers")
    @classmethod
    def _answers_in_likert_range(cls, answers: list[int]) -> list[int]:
        if any(a < 0 or a > constants.LIKERT_MAX for a in answers):
            msg = f"each answer must be between 0 and {constants.LIKERT_MAX}"
            raise ValueError(msg)
        return answers


class VoiceCheckinRequest(BaseModel):
    """Artifacts captured client-side after the realtime conversation.

    Raw media is processed in memory for signal extraction and never persisted.
    """

    transcript: str = Field(max_length=constants.MAX_TRANSCRIPT_CHARS)
    audio_segment_b64: str | None = Field(default=None, max_length=constants.MAX_AUDIO_B64_CHARS)
    frames_b64: list[str] = Field(default_factory=list, max_length=constants.MAX_FRAMES)

    @field_validator("frames_b64")
    @classmethod
    def _frames_size_capped(cls, frames: list[str]) -> list[str]:
        if any(len(f) > constants.MAX_FRAME_B64_CHARS for f in frames):
            msg = "frame too large"
            raise ValueError(msg)
        return frames


# ---------------------------------------------------------------------------
# Signals & results
# ---------------------------------------------------------------------------


class SignalResult(BaseModel):
    """One modality's contribution to the composite, with its confidence.

    ``crisis_flag`` lets any provider surface crisis language (spec: if any
    provider sets crisis, the check-in is a crisis). ``triggers`` carries
    modality-detected themes for transparency.
    """

    modality: Modality
    distress_0_100: float = Field(ge=0, le=100)
    confidence_0_1: float = Field(ge=0, le=1)
    notes: str = ""
    crisis_flag: bool = False
    triggers: list[str] = Field(default_factory=list)


class CrisisResources(BaseModel):
    """Always-available help information (India)."""

    helpline_name: str
    phone_numbers: list[str]
    message: str


class CheckinResult(BaseModel):
    """The supportive outcome of a check-in, shown to the student."""

    band: Band
    composite_0_100: float = Field(ge=0, le=100)
    supportive_message: str
    likely_triggers: list[str]
    coping_suggestions: list[str]
    crisis: bool
    crisis_resources: CrisisResources | None = None
    signals: list[SignalResult]
    disclaimer: str = constants.DISCLAIMER


# ---------------------------------------------------------------------------
# History / trends
# ---------------------------------------------------------------------------


class TrendPoint(BaseModel):
    """One past check-in, summarized for the dashboard."""

    id: int
    created_at: datetime
    mode: CheckinMode
    band: Band
    composite_0_100: float
    triggers: list[str]
    crisis: bool


class TrendsResponse(BaseModel):
    """Time series plus recurring triggers for the dashboard."""

    points: list[TrendPoint]
    recurring_triggers: list[str]


class SentNotificationOut(BaseModel):
    """A parent notification exactly as it was sent (student transparency)."""

    created_at: datetime
    recipient: str
    subject: str
    body: str


class DeletionResult(BaseModel):
    """Acknowledgement of a full data wipe."""

    deleted_checkins: int
    deleted_notifications: int


# ---------------------------------------------------------------------------
# Realtime token
# ---------------------------------------------------------------------------


class RealtimeTokenResponse(BaseModel):
    """Ephemeral client secret for the browser's realtime session."""

    value: str
    expires_at: int
    model: str


# ---------------------------------------------------------------------------
# Structured LLM outputs (extra="forbid")
# ---------------------------------------------------------------------------


class TranscriptSignalOutput(BaseModel):
    """gpt-5.4-nano transcript analysis."""

    model_config = ConfigDict(extra="forbid")

    distress_0_100: float = Field(ge=0, le=100)
    confidence_0_1: float = Field(ge=0, le=1)
    themes: list[str]
    crisis_language: bool
    summary: str


class AudioToneOutput(BaseModel):
    """gpt-audio-mini coarse tone/arousal cue."""

    model_config = ConfigDict(extra="forbid")

    tension_0_100: float = Field(ge=0, le=100)
    confidence_0_1: float = Field(ge=0, le=1)
    note: str


class FacialAffectOutput(BaseModel):
    """gpt-5.4-nano coarse facial affect cue from sampled frames."""

    model_config = ConfigDict(extra="forbid")

    distress_0_100: float = Field(ge=0, le=100)
    confidence_0_1: float = Field(ge=0, le=1)
    note: str


class ReflectionOutput(BaseModel):
    """gpt-5.4-mini supportive reflection."""

    model_config = ConfigDict(extra="forbid")

    supportive_message: str
    coping_suggestions: list[str] = Field(min_length=3, max_length=5)
