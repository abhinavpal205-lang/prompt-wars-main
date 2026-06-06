"""Shared constants: model ids, bands, fusion priors, copy, and crisis resources.

Everything user-facing here is deliberately supportive and non-clinical; see
the responsible-design notes in ARCHITECTURE.md.
"""

from typing import Final

# ---------------------------------------------------------------------------
# OpenAI model selection — cheapest model that fits each task (efficiency).
# ---------------------------------------------------------------------------
REALTIME_MODEL: Final = "gpt-realtime-mini"
NANO_MODEL: Final = "gpt-5.4-nano"
MINI_MODEL: Final = "gpt-5.4-mini"
AUDIO_MODEL: Final = "gpt-audio-mini"

# ---------------------------------------------------------------------------
# Crisis resources (India). The crisis path must never be gated by scoring.
# ---------------------------------------------------------------------------
TELE_MANAS_NAME: Final = "Tele-MANAS — Government of India mental health helpline"
TELE_MANAS_NUMBERS: Final[tuple[str, ...]] = ("14416", "1-800-891-4416")
CRISIS_MESSAGE: Final = (
    "You matter, and you don't have to carry this alone. Tele-MANAS is free, "
    "confidential and available 24x7 in your language. Please also consider "
    "reaching out right now to someone you trust — a parent, a friend, a teacher."
)

DISCLAIMER: Final = (
    "Sahaay is a self-reflection companion, not a medical or diagnostic tool. "
    "It cannot assess, label or treat mental health. If you are struggling, "
    "please talk to someone you trust or call Tele-MANAS: 14416 (free, 24x7)."
)

# ---------------------------------------------------------------------------
# Wellbeing bands. Thresholds operate on a 0-100 composite where higher means
# more strain. They are heuristics for supportive framing, not clinical cutoffs.
# ---------------------------------------------------------------------------
BAND_CALM_BELOW: Final = 25.0
BAND_MILD_BELOW: Final = 50.0
BAND_ELEVATED_BELOW: Final = 75.0

# ---------------------------------------------------------------------------
# Fusion priors: the self-report form dominates; transcript content is a
# moderate hint; audio tone and facial frames are weak, low-trust cues.
# Rationale in ARCHITECTURE.md ("Honesty about signals").
# ---------------------------------------------------------------------------
MODALITY_PRIORS: Final[dict[str, float]] = {
    "form": 0.60,
    "transcript": 0.20,
    "audio": 0.10,
    "facial": 0.10,
}

# ---------------------------------------------------------------------------
# Check-in form structure. 10 Likert items (0-4). Items in REVERSE_ITEM_INDICES
# are positively worded and reverse-scored. The PSS-inspired item texts live in
# the frontend; index semantics here are the single source of truth for scoring.
# ---------------------------------------------------------------------------
FORM_ITEM_COUNT: Final = 10
LIKERT_MAX: Final = 4
REVERSE_ITEM_INDICES: Final[frozenset[int]] = frozenset({3, 5, 7, 9})

# Trigger label per item, used when that item signals notable strain.
TRIGGER_BY_ITEM: Final[dict[int, str]] = {
    0: "study load",
    1: "sleep",
    2: "results pressure",
    3: "breaks and rest",
    4: "comparison with peers",
    5: "syllabus confidence",
    6: "irritability",
    7: "joy outside study",
    8: "family pressure",
    9: "outlook",
}

# ---------------------------------------------------------------------------
# Offline-mode reflections, used when no OpenAI key is configured. Curated,
# warm, non-clinical, never alarmist.
# ---------------------------------------------------------------------------
CANNED_REFLECTIONS: Final[dict[str, tuple[str, tuple[str, ...]]]] = {
    "calm": (
        "It sounds like things feel fairly steady right now — that's worth "
        "noticing and appreciating. Checking in even on good days builds a "
        "habit that helps on harder ones.",
        (
            "Keep one small routine that's working for you, exactly as it is.",
            "Take a 10-minute walk without your phone today.",
            "Tell someone about one thing that went well this week.",
        ),
    ),
    "mild": (
        "A bit of pressure seems to be in the mix — completely normal in exam "
        "season, and worth tending to early. Small, kind adjustments now go a "
        "long way.",
        (
            "Try a 5-minute break every 45-50 minutes of study.",
            "Aim to wind down screens 30 minutes before sleep tonight.",
            "Do one short breathing exercise: in for 4, hold 4, out for 6, x5.",
            "Message a friend about something other than the exam.",
        ),
    ),
    "elevated": (
        "It sounds like the last few days have felt heavy. That doesn't mean "
        "anything is wrong with you — it means you're carrying a lot. You "
        "deserve some real rest and support.",
        (
            "Pause for a 10-minute reset now: water, stretch, slow breaths.",
            "Tonight, protect your sleep — notes down an hour earlier than usual.",
            "Share one worry out loud with someone you trust today.",
            "Swap one revision block for lighter review instead of new topics.",
        ),
    ),
    "high": (
        "Thank you for checking in — that took courage. Things sound really "
        "tough right now, and your wellbeing matters more than any exam. "
        "Please be gentle with yourself today and lean on people around you.",
        (
            "Step away from study for the next hour — rest is not falling behind.",
            "Talk to a parent, teacher or friend today about how heavy it feels.",
            "If it ever feels like too much, Tele-MANAS (14416) is free and 24x7.",
            "Eat something, drink water, and get outside for a few minutes.",
        ),
    ),
}

# ---------------------------------------------------------------------------
# Voice session instructions for the realtime model (server-side only).
# ---------------------------------------------------------------------------
VOICE_INSTRUCTIONS: Final = (
    "You are Sahaay, a warm, calm wellbeing check-in companion for a student "
    "preparing for a high-pressure Indian exam. Keep the whole conversation to "
    "about one minute: greet briefly, then gently ask (1) how the last few days "
    "have felt, (2) how sleep has been, (3) what's weighing on them most, and "
    "(4) softly, whether they're feeling safe and supported. Listen more than "
    "you speak; keep each reply to one or two short sentences; use simple, "
    "encouraging language (mirror Hinglish if they use it). Never diagnose, "
    "never label them with a condition, never minimize distress, and never "
    "give study-harder advice. If they mention self-harm, suicide, or feeling "
    "unsafe, immediately and kindly share that Tele-MANAS at 14416 is free and "
    "available 24x7, and encourage them to talk to a trusted adult right now. "
    "Close by thanking them for checking in."
)

# ---------------------------------------------------------------------------
# Input limits (validation / abuse protection).
# ---------------------------------------------------------------------------
MAX_NOTE_CHARS: Final = 2_000
MAX_TRANSCRIPT_CHARS: Final = 8_000
MAX_FRAMES: Final = 5
MAX_FRAME_B64_CHARS: Final = 400_000  # ~300 KB per JPEG frame
MAX_AUDIO_B64_CHARS: Final = 1_400_000  # ~1 MB WAV segment
