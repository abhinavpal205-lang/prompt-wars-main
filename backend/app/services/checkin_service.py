"""Check-in orchestration: score, fuse, detect crisis, reflect, persist, notify.

The crisis assessment runs deterministically and is attached to the result
regardless of any AI call succeeding; raw media never reaches persistence.
"""

import asyncio
import json

from sqlmodel import Session

from app.models import CheckinRecord
from app.schemas import (
    Band,
    CheckinMode,
    CheckinResult,
    FormResponse,
    ReflectionOutput,
    SignalResult,
    VoiceCheckinRequest,
)
from app.security import NoteCipher
from app.services import crisis, form_scorer, fusion
from app.services.notifier import EmailSender, notify_parent_if_consented
from app.services.openai_client import AIGateway
from app.services.profiles import get_or_create_profile
from app.services.reflection import generate_reflection
from app.services.signals.audio_tone import AudioToneSignalProvider
from app.services.signals.base import SignalProvider, VoiceArtifacts, evaluate_safely
from app.services.signals.facial import FacialSignalProvider
from app.services.signals.transcript import TranscriptSignalProvider

# When every voice signal is unavailable we report a gentle midpoint rather
# than failing the check-in (band "mild": we simply don't know more).
_NEUTRAL_COMPOSITE = 40.0


def _merge_triggers(signals: list[SignalResult]) -> list[str]:
    """Order-preserving union of triggers across signals."""
    seen: dict[str, None] = {}
    for signal in signals:
        for trigger in signal.triggers:
            seen.setdefault(trigger)
    return list(seen)


def _build_result(
    *,
    band: Band,
    composite: float,
    signals: list[SignalResult],
    triggers: list[str],
    reflection: ReflectionOutput,
    is_crisis: bool,
) -> CheckinResult:
    return CheckinResult(
        band=band,
        composite_0_100=round(composite, 1),
        supportive_message=reflection.supportive_message,
        likely_triggers=triggers,
        coping_suggestions=reflection.coping_suggestions,
        crisis=is_crisis,
        crisis_resources=crisis.crisis_resources() if is_crisis else None,
        signals=signals,
    )


def _persist_and_notify(
    session: Session,
    sender: EmailSender,
    cipher: NoteCipher,
    *,
    mode: CheckinMode,
    result: CheckinResult,
    free_note: str | None,
) -> None:
    """Store the coarse check-in record and run the consent-gated notifier."""
    record = CheckinRecord(
        mode=mode,
        band=result.band,
        composite=result.composite_0_100,
        triggers_json=json.dumps(result.likely_triggers),
        free_note_encrypted=cipher.encrypt(free_note) if free_note else None,
        crisis=result.crisis,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    notify_parent_if_consented(
        session,
        sender,
        profile=get_or_create_profile(session),
        band=result.band,
        triggers=result.likely_triggers,
        crisis=result.crisis,
        checkin_id=record.id,
    )


async def run_form_checkin(
    session: Session,
    gateway: AIGateway,
    sender: EmailSender,
    cipher: NoteCipher,
    payload: FormResponse,
) -> CheckinResult:
    """Deterministic form scoring plus a supportive reflection."""
    score = form_scorer.score_form(payload)
    is_crisis = crisis.assess_crisis(safety_flag=score.crisis, texts=[payload.free_note])
    form_signal = SignalResult(
        modality="form",
        distress_0_100=score.composite_0_100,
        confidence_0_1=1.0,
        notes="self-report form (primary signal)",
        crisis_flag=is_crisis,
        triggers=score.triggers,
    )
    reflection = await generate_reflection(
        gateway, band=score.band, triggers=score.triggers, free_note=payload.free_note
    )
    result = _build_result(
        band=score.band,
        composite=score.composite_0_100,
        signals=[form_signal],
        triggers=score.triggers,
        reflection=reflection,
        is_crisis=is_crisis,
    )
    _persist_and_notify(
        session, sender, cipher, mode="form", result=result, free_note=payload.free_note
    )
    return result


async def run_voice_checkin(
    session: Session,
    gateway: AIGateway,
    sender: EmailSender,
    cipher: NoteCipher,
    payload: VoiceCheckinRequest,
) -> CheckinResult:
    """Concurrent, failure-isolated signal extraction fused into one result."""
    artifacts = VoiceArtifacts(
        transcript=payload.transcript,
        audio_b64=payload.audio_segment_b64,
        frames_b64=tuple(payload.frames_b64),
    )
    providers: list[SignalProvider] = [
        TranscriptSignalProvider(gateway),
        AudioToneSignalProvider(gateway),
        FacialSignalProvider(gateway),
    ]
    signals = list(
        await asyncio.gather(*(evaluate_safely(provider, artifacts) for provider in providers))
    )
    # Crisis is assessed deterministically on the transcript as well, so a
    # failed transcript provider can never hide crisis language.
    is_crisis = crisis.assess_crisis(
        texts=[payload.transcript], signal_flags=[s.crisis_flag for s in signals]
    )
    try:
        fused = fusion.fuse(signals)
        composite, band = fused.composite_0_100, fused.band
    except fusion.NoUsableSignalsError:
        composite, band = _NEUTRAL_COMPOSITE, form_scorer.band_for(_NEUTRAL_COMPOSITE)
    triggers = _merge_triggers(signals)
    reflection = await generate_reflection(gateway, band=band, triggers=triggers, free_note=None)
    result = _build_result(
        band=band,
        composite=composite,
        signals=signals,
        triggers=triggers,
        reflection=reflection,
        is_crisis=is_crisis,
    )
    _persist_and_notify(session, sender, cipher, mode="voice", result=result, free_note=None)
    return result
