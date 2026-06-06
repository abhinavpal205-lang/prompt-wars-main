"""Crisis detection and resources. Pure functions, no I/O.

The crisis path overrides everything: detection here is deliberately
high-recall (better a gentle extra offer of help than a missed signal),
and routers surface resources *before and independent of* any scoring.
"""

import re
from collections.abc import Iterable

from app import constants
from app.schemas import CrisisResources

# High-recall indicators of self-harm or suicidal intent, including common
# Hinglish phrasings. Matched case-insensitively on word boundaries.
_CRISIS_PHRASES: tuple[str, ...] = (
    "kill myself",
    "killing myself",
    "suicide",
    "suicidal",
    "end my life",
    "ending my life",
    "end it all",
    "want to die",
    "wish i was dead",
    "wish i were dead",
    "better off dead",
    "no reason to live",
    "don't want to live",
    "dont want to live",
    "hurt myself",
    "hurting myself",
    "harm myself",
    "self harm",
    "self-harm",
    "cut myself",
    "marna chahta",
    "marna chahti",
    "jeena nahi chahta",
    "jeena nahi chahti",
)

_CRISIS_PATTERN = re.compile(
    "|".join(rf"\b{re.escape(phrase)}\b" for phrase in _CRISIS_PHRASES),
    re.IGNORECASE,
)


def detect_crisis_text(text: str | None) -> bool:
    """Whether free text contains explicit crisis language."""
    if not text:
        return False
    return _CRISIS_PATTERN.search(text) is not None


def assess_crisis(
    *,
    safety_flag: bool = False,
    texts: Iterable[str | None] = (),
    signal_flags: Iterable[bool] = (),
) -> bool:
    """Combine all crisis indicators: any positive source means crisis."""
    return safety_flag or any(detect_crisis_text(t) for t in texts) or any(signal_flags)


def crisis_resources() -> CrisisResources:
    """Always-available help information (Tele-MANAS, India)."""
    return CrisisResources(
        helpline_name=constants.TELE_MANAS_NAME,
        phone_numbers=list(constants.TELE_MANAS_NUMBERS),
        message=constants.CRISIS_MESSAGE,
    )
