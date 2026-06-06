"""Coarse facial affect cue from a few sampled frames (gpt-5.4-nano vision).

Explicitly the weakest signal: appearance does not reliably reflect feeling.
Confidence is hard-capped low and the fusion prior keeps it low-weight.
"""

from typing import ClassVar

from app import constants
from app.schemas import FacialAffectOutput, Modality, SignalResult
from app.services.openai_client import AIGateway
from app.services.signals.base import VoiceArtifacts, unavailable

_INSTRUCTIONS = (
    "You see a few webcam frames sampled during a student's wellbeing "
    "check-in. Give only a coarse visible-strain estimate (distress_0_100) "
    "with low confidence_0_1 (0.4 maximum — appearance is an unreliable cue), "
    "and a one-sentence neutral note. Never claim to know how the person "
    "feels, never mention identity, and never infer any condition."
)

_MAX_CONFIDENCE = 0.4


class FacialSignalProvider:
    """Lowest-weight supplementary cue from sampled webcam frames."""

    modality: ClassVar[Modality] = "facial"

    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def evaluate(self, artifacts: VoiceArtifacts) -> SignalResult:
        """Score the frames, or drop the modality when absent/offline."""
        frames = artifacts.frames_b64[: constants.MAX_FRAMES]
        if not frames:
            return unavailable(self.modality, "no frames provided")
        if not self._gateway.configured:
            return unavailable(self.modality, "frame analysis unavailable offline")
        content: list[dict[str, object]] = [
            {"type": "input_text", "text": "Frames from the check-in follow."}
        ]
        content.extend({"type": "input_image", "image_url": frame} for frame in frames)
        output = await self._gateway.parse_structured(
            model=constants.NANO_MODEL,
            instructions=_INSTRUCTIONS,
            content=content,
            schema=FacialAffectOutput,
        )
        return SignalResult(
            modality=self.modality,
            distress_0_100=output.distress_0_100,
            confidence_0_1=min(output.confidence_0_1, _MAX_CONFIDENCE),
            notes=output.note,
        )
