"""Supportive reflection and coping suggestions (gpt-5.4-mini).

A failed or unconfigured AI call must never block a check-in: this module
always returns a reflection, degrading to curated copy when needed.
"""

import logging

from app import constants
from app.schemas import Band, ReflectionOutput
from app.services.openai_client import AIGateway

logger = logging.getLogger(__name__)

_INSTRUCTIONS = (
    "You write a brief supportive reflection for a student in India preparing "
    "for a high-pressure exam, after a wellbeing self-check-in. Use warm, "
    "plain, non-clinical language. supportive_message: 2-4 sentences that "
    "acknowledge how things seem without diagnosing, labeling, or minimizing. "
    "coping_suggestions: 3-5 concrete actions doable today, suited to "
    "exam-stage students (micro-breaks, sleep wind-down, pacing study blocks, "
    "talking to someone, simple breathing). Never be alarmist, never say "
    "'study harder', never mention disorders or treatment."
)


def _canned(band: Band) -> ReflectionOutput:
    """Curated reflection used offline or if the AI call fails."""
    message, suggestions = constants.CANNED_REFLECTIONS[band]
    return ReflectionOutput(supportive_message=message, coping_suggestions=list(suggestions))


async def generate_reflection(
    gateway: AIGateway,
    *,
    band: Band,
    triggers: list[str],
    free_note: str | None,
) -> ReflectionOutput:
    """Generate a personalized reflection, falling back to curated copy."""
    if not gateway.configured:
        return _canned(band)
    prompt = (
        f"Wellbeing band from the check-in: {band}. "
        f"Likely triggers: {', '.join(triggers) if triggers else 'none identified'}."
    )
    if free_note:
        prompt += f' The student also wrote: "{free_note}"'
    try:
        return await gateway.parse_structured(
            model=constants.MINI_MODEL,
            instructions=_INSTRUCTIONS,
            content=prompt,
            schema=ReflectionOutput,
        )
    except Exception as exc:  # noqa: BLE001 — reflection must never block a check-in
        logger.warning("reflection generation failed: %s", type(exc).__name__)
        return _canned(band)
