"""Tests for signal providers, failure isolation, and reflection fallback."""

import pytest

from app.schemas import (
    AudioToneOutput,
    FacialAffectOutput,
    ReflectionOutput,
    SignalResult,
    TranscriptSignalOutput,
)
from app.services.reflection import generate_reflection
from app.services.signals.audio_tone import AudioToneSignalProvider
from app.services.signals.base import VoiceArtifacts, evaluate_safely
from app.services.signals.facial import FacialSignalProvider
from app.services.signals.transcript import TranscriptSignalProvider
from tests.fakes import FakeGateway


def artifacts(
    transcript: str = "",
    audio: str | None = None,
    frames: tuple[str, ...] = (),
) -> VoiceArtifacts:
    return VoiceArtifacts(transcript=transcript, audio_b64=audio, frames_b64=frames)


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


async def test_transcript_empty_is_dropped(gateway: FakeGateway) -> None:
    result = await TranscriptSignalProvider(gateway).evaluate(artifacts(transcript="   "))
    assert result.confidence_0_1 == 0.0


async def test_transcript_offline_heuristic(offline_gateway: FakeGateway) -> None:
    result = await TranscriptSignalProvider(offline_gateway).evaluate(
        artifacts(transcript="I am stressed and exhausted, the pressure is too much")
    )
    assert result.confidence_0_1 == pytest.approx(0.3)
    assert result.distress_0_100 > 10
    assert result.crisis_flag is False
    assert "pressure" in result.triggers


async def test_transcript_offline_detects_crisis(offline_gateway: FakeGateway) -> None:
    result = await TranscriptSignalProvider(offline_gateway).evaluate(
        artifacts(transcript="sometimes I want to hurt myself")
    )
    assert result.crisis_flag is True


async def test_transcript_online_maps_model_output() -> None:
    gateway = FakeGateway(
        outputs={
            TranscriptSignalOutput: TranscriptSignalOutput(
                distress_0_100=72.0,
                confidence_0_1=0.95,
                themes=["results", "sleep", "a", "b", "c", "extra-sixth"],
                crisis_language=False,
                summary="They talked mostly about results and sleep.",
            )
        }
    )
    result = await TranscriptSignalProvider(gateway).evaluate(
        artifacts(transcript="long chat about results")
    )
    assert result.distress_0_100 == 72.0
    assert result.confidence_0_1 == 0.9  # capped
    assert len(result.triggers) == 5  # truncated
    assert result.crisis_flag is False


async def test_transcript_keyword_check_backs_up_model_flag() -> None:
    """Even if the model misses crisis language, the keyword check catches it."""
    gateway = FakeGateway(
        outputs={
            TranscriptSignalOutput: TranscriptSignalOutput(
                distress_0_100=40.0,
                confidence_0_1=0.5,
                themes=[],
                crisis_language=False,
                summary="A short chat.",
            )
        }
    )
    result = await TranscriptSignalProvider(gateway).evaluate(
        artifacts(transcript="I keep thinking about suicide")
    )
    assert result.crisis_flag is True


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------


async def test_audio_absent_is_dropped(gateway: FakeGateway) -> None:
    result = await AudioToneSignalProvider(gateway).evaluate(artifacts(transcript="hi"))
    assert result.confidence_0_1 == 0.0


async def test_audio_offline_is_dropped(offline_gateway: FakeGateway) -> None:
    result = await AudioToneSignalProvider(offline_gateway).evaluate(artifacts(audio="QUJD"))
    assert result.confidence_0_1 == 0.0


async def test_audio_online_maps_and_caps_confidence() -> None:
    gateway = FakeGateway(
        outputs={
            AudioToneOutput: AudioToneOutput(
                tension_0_100=66.0, confidence_0_1=0.9, note="somewhat hurried"
            )
        }
    )
    result = await AudioToneSignalProvider(gateway).evaluate(artifacts(audio="QUJD"))
    assert result.distress_0_100 == 66.0
    assert result.confidence_0_1 == 0.5  # hard cap: soft cue only


# ---------------------------------------------------------------------------
# Facial
# ---------------------------------------------------------------------------


async def test_facial_absent_is_dropped(gateway: FakeGateway) -> None:
    result = await FacialSignalProvider(gateway).evaluate(artifacts())
    assert result.confidence_0_1 == 0.0


async def test_facial_online_maps_caps_and_limits_frames() -> None:
    gateway = FakeGateway(
        outputs={
            FacialAffectOutput: FacialAffectOutput(
                distress_0_100=30.0, confidence_0_1=0.8, note="neutral expressions"
            )
        }
    )
    frames = tuple(f"data:image/jpeg;base64,frame{i}" for i in range(7))
    result = await FacialSignalProvider(gateway).evaluate(artifacts(frames=frames))
    assert result.confidence_0_1 == 0.4  # hard cap: weakest cue
    assert isinstance(gateway.last_content, list)
    images = [part for part in gateway.last_content if part["type"] == "input_image"]
    assert len(images) == 5  # never more than MAX_FRAMES sent


# ---------------------------------------------------------------------------
# Failure isolation
# ---------------------------------------------------------------------------


async def test_evaluate_safely_turns_errors_into_dropped_signals() -> None:
    gateway = FakeGateway(fail_schemas={"TranscriptSignalOutput"})
    result: SignalResult = await evaluate_safely(
        TranscriptSignalProvider(gateway), artifacts(transcript="hello there")
    )
    assert result.modality == "transcript"
    assert result.confidence_0_1 == 0.0


# ---------------------------------------------------------------------------
# Reflection
# ---------------------------------------------------------------------------


async def test_reflection_offline_uses_curated_copy(offline_gateway: FakeGateway) -> None:
    reflection = await generate_reflection(
        offline_gateway, band="elevated", triggers=["sleep"], free_note=None
    )
    assert reflection.supportive_message
    assert 3 <= len(reflection.coping_suggestions) <= 5


async def test_reflection_failure_falls_back_to_curated_copy() -> None:
    gateway = FakeGateway(fail_schemas={"ReflectionOutput"})
    reflection = await generate_reflection(gateway, band="mild", triggers=[], free_note="hi")
    assert reflection.supportive_message
    assert len(reflection.coping_suggestions) >= 3


async def test_reflection_online_passthrough() -> None:
    seeded = ReflectionOutput(
        supportive_message="You showed up for yourself today.",
        coping_suggestions=["Drink water", "Take a walk", "Text a friend"],
    )
    gateway = FakeGateway(outputs={ReflectionOutput: seeded})
    reflection = await generate_reflection(
        gateway, band="calm", triggers=["results"], free_note=None
    )
    assert reflection == seeded
