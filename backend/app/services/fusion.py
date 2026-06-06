"""Deterministic, confidence-aware fusion of modality signals.

Pure functions, no I/O. Each signal's weight is its fixed modality prior
times its own confidence; zero-confidence signals are dropped and the
remaining weights renormalized. The self-report form dominates by design —
soft cues (voice tone, frames) can only nudge, never decide.
"""

from dataclasses import dataclass

from app import constants
from app.schemas import Band, SignalResult
from app.services.form_scorer import band_for


class NoUsableSignalsError(ValueError):
    """Raised when every signal was dropped (all zero-confidence)."""


@dataclass(frozen=True)
class FusionOutput:
    """Composite produced by weighted fusion, with the signals actually used."""

    composite_0_100: float
    band: Band
    used: list[SignalResult]
    crisis: bool


def fuse(signals: list[SignalResult]) -> FusionOutput:
    """Fuse available signals into a banded composite.

    Raises:
        NoUsableSignalsError: if no signal has positive confidence.
    """
    usable = [s for s in signals if s.confidence_0_1 > 0]
    if not usable:
        raise NoUsableSignalsError("no signal with positive confidence")

    weights = [constants.MODALITY_PRIORS[s.modality] * s.confidence_0_1 for s in usable]
    total = sum(weights)
    composite = sum(w * s.distress_0_100 for w, s in zip(weights, usable, strict=True)) / total

    return FusionOutput(
        composite_0_100=composite,
        band=band_for(composite),
        used=usable,
        crisis=any(s.crisis_flag for s in signals),
    )
