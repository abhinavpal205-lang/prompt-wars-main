"""Voice tone/arousal cue from a short audio segment (gpt-audio-mini).

A soft, unreliable hint by design: confidence is hard-capped, and the
fusion prior keeps it low-weight. Efficiency: only a short representative
segment is sent (audio tokens are expensive), never the full conversation.
"""

from typing import ClassVar

from app import constants
from app.schemas import AudioToneOutput, Modality, SignalResult
from app.services.openai_client import AIGateway
from app.services.signals.base import VoiceArtifacts, unavailable

_PROMPT = (
    "Listen to this short clip of a student during a wellbeing check-in. "
    "Based ONLY on vocal tone (pace, steadiness, energy), give a coarse "
    "tension estimate. Reply with ONLY a JSON object exactly like "
    '{"tension_0_100": <number>, "confidence_0_1": <number>, "note": "<one short sentence>"}. '
    "Vocal tone is an unreliable cue: keep confidence_0_1 at or below 0.5. "
    "Never guess emotions as facts and never infer any mental-health condition."
)

_MAX_CONFIDENCE = 0.5
_AUDIO_FORMAT = "wav"


class AudioToneSignalProvider:
    """Low-weight supplementary cue from how the student sounded."""

    modality: ClassVar[Modality] = "audio"

    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def evaluate(self, artifacts: VoiceArtifacts) -> SignalResult:
        """Score the audio segment, or drop the modality when absent/offline."""
        if not artifacts.audio_b64:
            return unavailable(self.modality, "no audio segment provided")
        if not self._gateway.configured:
            return unavailable(self.modality, "voice tone analysis unavailable offline")
        output = await self._gateway.audio_json(
            model=constants.AUDIO_MODEL,
            prompt=_PROMPT,
            audio_b64=artifacts.audio_b64,
            audio_format=_AUDIO_FORMAT,
            schema=AudioToneOutput,
        )
        return SignalResult(
            modality=self.modality,
            distress_0_100=output.tension_0_100,
            confidence_0_1=min(output.confidence_0_1, _MAX_CONFIDENCE),
            notes=output.note,
        )
