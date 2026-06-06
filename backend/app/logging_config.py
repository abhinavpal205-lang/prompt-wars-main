"""Structured, PII-safe logging configuration.

Policy: log events and error classes, never user content. No transcripts,
notes, emails, frames, audio, or API keys may ever be passed to a logger.
"""

import logging

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging once, idempotently."""
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(format=_FORMAT, level=level)
    # Uvicorn access logs include paths only (no bodies); keep them at INFO.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
