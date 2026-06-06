"""Deterministic scoring for the self-report form.

The 10-item structure is *inspired by* validated perceived-stress scales
(stress, coping, sleep, overwhelm, outlook) but it is **not a clinical
instrument** and is never presented as one. Pure functions, no I/O.
"""

from dataclasses import dataclass

from app import constants
from app.schemas import Band, FormResponse


@dataclass(frozen=True)
class FormScore:
    """Outcome of deterministic form scoring."""

    composite_0_100: float
    band: Band
    crisis: bool
    triggers: list[str]


def band_for(composite: float) -> Band:
    """Map a 0-100 composite to a supportive wellbeing band."""
    if composite < constants.BAND_CALM_BELOW:
        return "calm"
    if composite < constants.BAND_MILD_BELOW:
        return "mild"
    if composite < constants.BAND_ELEVATED_BELOW:
        return "elevated"
    return "high"


def _item_strain(index: int, answer: int) -> int:
    """An item's strain on the 0-4 scale, reversing positively-worded items."""
    if index in constants.REVERSE_ITEM_INDICES:
        return constants.LIKERT_MAX - answer
    return answer


def derive_triggers(answers: list[int]) -> list[str]:
    """Triggers are areas whose item strain is notable (>= 3 of 4)."""
    return [
        constants.TRIGGER_BY_ITEM[i]
        for i, answer in enumerate(answers)
        if _item_strain(i, answer) >= 3
    ]


def score_form(response: FormResponse) -> FormScore:
    """Score the Likert answers into a banded 0-100 composite.

    Raw strain is 0-40 across 10 items; normalized to 0-100. The explicit
    safety item always sets ``crisis`` regardless of the score.
    """
    raw = sum(_item_strain(i, answer) for i, answer in enumerate(response.answers))
    composite = raw / (constants.FORM_ITEM_COUNT * constants.LIKERT_MAX) * 100.0
    return FormScore(
        composite_0_100=composite,
        band=band_for(composite),
        crisis=response.safety_flag,
        triggers=derive_triggers(response.answers),
    )
