"""Transcript sentiment/theme signal (gpt-5.4-nano, structured output).

With no OpenAI key, falls back to a transparent low-confidence keyword
heuristic so voice check-ins still complete offline.
"""

from typing import ClassVar

from app import constants
from app.schemas import Modality, SignalResult, TranscriptSignalOutput
from app.services.crisis import detect_crisis_text
from app.services.openai_client import AIGateway
from app.services.signals.base import VoiceArtifacts, unavailable

_INSTRUCTIONS = (
    "You analyze the transcript of a short wellbeing check-in with a student "
    "preparing for a high-pressure exam. Estimate distress_0_100 (overall "
    "strain the student expresses) and confidence_0_1 (how clearly the "
    "transcript supports that estimate; short or ambiguous transcripts mean "
    "low confidence). List up to 5 short lowercase themes the student raised "
    "(e.g. 'results', 'sleep', 'comparison', 'family pressure'). Set "
    "crisis_language true ONLY if the student expresses self-harm or suicidal "
    "thoughts, or says they feel unsafe — never minimize such statements. "
    "Write summary as one gentle sentence about what the student talked "
    "about. Never diagnose, never use clinical labels."
)

# Offline heuristic lexicon — a transparent, deliberately rough stand-in.
_STRESS_WORDS: tuple[str, ...] = (
    "stressed",
    "anxious",
    "scared",
    "panic",
    "exhausted",
    "tired",
    "pressure",
    "worried",
    "overwhelmed",
    "sad",
    "crying",
    "hopeless",
    "alone",
    "behind",
    "fail",
)
_HEURISTIC_CONFIDENCE = 0.3
_MAX_LLM_CONFIDENCE = 0.9
_MAX_THEMES = 5


class TranscriptSignalProvider:
    """Moderate-weight signal from what the student actually said."""

    modality: ClassVar[Modality] = "transcript"

    def __init__(self, gateway: AIGateway) -> None:
        self._gateway = gateway

    async def evaluate(self, artifacts: VoiceArtifacts) -> SignalResult:
        """Score the transcript; degrade to the keyword heuristic offline."""
        text = artifacts.transcript.strip()
        if not text:
            return unavailable(self.modality, "no transcript captured")
        if not self._gateway.configured:
            return self._heuristic(text)
        output = await self._gateway.parse_structured(
            model=constants.NANO_MODEL,
            instructions=_INSTRUCTIONS,
            content=text,
            schema=TranscriptSignalOutput,
        )
        return SignalResult(
            modality=self.modality,
            distress_0_100=output.distress_0_100,
            confidence_0_1=min(output.confidence_0_1, _MAX_LLM_CONFIDENCE),
            notes=output.summary,
            # The deterministic keyword check always backs up the model flag.
            crisis_flag=output.crisis_language or detect_crisis_text(text),
            triggers=output.themes[:_MAX_THEMES],
        )

    def _heuristic(self, text: str) -> SignalResult:
        """Keyword-count estimate used only in offline stub mode."""
        lowered = text.lower()
        hits = sorted({word for word in _STRESS_WORDS if word in lowered})
        distress = min(100.0, 10.0 + 15.0 * len(hits))
        return SignalResult(
            modality=self.modality,
            distress_0_100=distress,
            confidence_0_1=_HEURISTIC_CONFIDENCE,
            notes="offline keyword estimate (no AI key configured)",
            crisis_flag=detect_crisis_text(text),
            triggers=hits[:_MAX_THEMES],
        )
