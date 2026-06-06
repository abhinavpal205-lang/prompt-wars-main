"""SignalProvider protocol and failure isolation.

Every provider is independently failure-isolated: any error or timeout
degrades to a zero-confidence result, and the check-in still completes.
"""

import logging
from dataclasses import dataclass
from typing import ClassVar, Protocol

from app.schemas import Modality, SignalResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceArtifacts:
    """Client-captured artifacts from a voice check-in (never persisted)."""

    transcript: str
    audio_b64: str | None
    frames_b64: tuple[str, ...]


class SignalProvider(Protocol):
    """A modality that can contribute one ``SignalResult`` to fusion."""

    modality: ClassVar[Modality]

    async def evaluate(self, artifacts: VoiceArtifacts) -> SignalResult:
        """Evaluate the artifacts into a scored, confidence-rated signal."""
        ...


def unavailable(modality: Modality, note: str) -> SignalResult:
    """A zero-confidence result that fusion will drop."""
    return SignalResult(modality=modality, distress_0_100=0.0, confidence_0_1=0.0, notes=note)


async def evaluate_safely(provider: SignalProvider, artifacts: VoiceArtifacts) -> SignalResult:
    """Run a provider, converting any failure into a dropped signal."""
    try:
        return await provider.evaluate(artifacts)
    except Exception as exc:  # noqa: BLE001 — isolation by design: one bad signal never fails a check-in
        logger.warning("signal provider %s failed: %s", provider.modality, type(exc).__name__)
        return unavailable(provider.modality, "signal unavailable")
