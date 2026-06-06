# Sahaay — Architecture

## Data flow

```
                         ┌─────────────────────────────┐
                         │   Mode select: Voice / Form  │
                         └───────────────┬─────────────┘
            ┌──────────────── Voice ─────┴──── Form ────────────────┐
            ▼                                                        ▼
  POST /api/realtime/token  (ephemeral ek_ token)       10 Likert items + 1 safety item
  WebRTC → gpt-realtime-mini (~60s conversation)                  │
  client captures transcript + ~8s WAV + ≤5 frames                │
            │                                                       │
            ▼  POST /api/checkin/voice                              ▼  POST /api/checkin/form
  ┌────────────────────────────────────────┐         ┌────────────────────────────────────┐
  │ signal providers (asyncio.gather, each  │         │ deterministic form scorer (Python)  │
  │ failure-isolated):                      │         │  + gpt-5.4-mini reflection/coping   │
  │  • transcript → gpt-5.4-nano            │         └──────────────────┬──────────────────┘
  │  • audio clip → gpt-audio-mini          │                            │
  │  • frames     → gpt-5.4-nano (vision)   │                            │
  └───────────────────┬─────────────────────┘                           │
                      ▼                                                   │
        FusionScorer (pure Python, weighted, confidence-aware)            │
                      └──────────────────────────┬────────────────────────┘
                                                 ▼
                  CheckinResult { band, supportive message, triggers, coping tips }
                                                 │
                ┌────────────────────────────────┼────────────────────────────────┐
                ▼                                ▼                                ▼
        crisis path (if flagged)         persist CheckinRecord           consented parent
     Tele-MANAS screen, no delay         (no raw media stored)         supportive notification
```

In production, nginx serves the SPA and reverse-proxies `/api/*` to the backend (same-origin, no
CORS at runtime); CORS config exists for local dev (`vite` on :5173 → uvicorn on :8000).

## Signal fusion design

Each modality produces a `SignalResult { distress_0_100, confidence_0_1, notes, crisis_flag,
triggers }`. Fusion (`services/fusion.py`, pure) computes

```
weight_i  = prior(modality_i) × confidence_i        priors: form .60, transcript .20,
composite = Σ weight_i · distress_i / Σ weight_i            audio .10, facial .10
```

Zero-confidence signals are dropped and remaining weights renormalize, so the wall-clock and the
outcome degrade gracefully when providers fail. In form mode the form is the only signal —
effective weight 1.0.

**Why these priors.** Self-report is the only signal a student directly controls and the only one
with decent validity — it dominates by design. Transcript content is what the student *said*, so
it gets moderate weight. Audio tone and facial frames are scientifically unreliable proxies for
feeling; they get the lowest priors **and** hard confidence caps inside their providers (0.5 and
0.4), so even an overconfident model reply cannot make a soft cue decisive. The result card lists
every signal and whether it was used — transparency over magic.

**Crisis is not fused.** `crisis_flag` is OR-ed across all signals (even dropped ones) plus a
deterministic keyword check on transcript and note, plus the explicit form safety item. Crisis
rendering happens before and independent of scoring, and the band never gates it.

**Bands** (heuristic, supportive framing only): calm < 25 ≤ mild < 50 ≤ elevated < 75 ≤ high.
The 10-item form is *inspired by* perceived-stress instruments (stress, sleep, overwhelm, coping,
outlook) with reverse-scored positive items; it is deliberately **not** a validated clinical
scale and is never presented as one.

## Backend layering

```
routers/    thin: parse request → one service call → schema. No SQL, no OpenAI, no logic.
services/   checkin_service  orchestration (score → fuse → crisis → reflect → persist → notify)
            form_scorer, fusion, crisis    PURE (no I/O) → exhaustively unit-tested
            signals/         SignalProvider protocol; one module per modality; failure-isolated
            openai_client    AIGateway protocol + the only OpenAI access point (stubbed in tests)
            reflection       supportive copy w/ curated offline fallback
            notifier         consent/cadence gate (pure) + SMTP/console delivery + stored copies
            profiles, history
models/schemas  SQLModel tables (no raw media) | Pydantic v2 request/response + LLM outputs
config      pydantic-settings; the only env access
errors      custom exceptions → clean JSON handlers (no tracebacks)
security    Fernet note encryption
deps        typed FastAPI dependencies + slowapi limiter
```

Tests inject `FakeGateway` (an `AIGateway` implementation) and an in-memory SQLite engine through
`app.state`, so the entire API surface is tested without network or disk.

## Frontend layering

```
components/  presentational (CSS modules + design tokens, WCAG AA, color-plus-text bands)
hooks/       stateful logic (useVoiceSession: realtime connect + captions; useCheckins: history)
api/         typed fetch wrappers (single error envelope)
lib/         pure, unit-tested helpers (WAV encode/downsample/trailing-buffer, chart points)
```

The form path is the accessibility-first equal of voice: semantic fieldsets/legends, labelled
radios, `aria-live` status and captions, visible focus, reduced-motion support, and a crisis link
in the persistent header. jest-axe asserts zero violations on the main screens.

## Efficiency choices

- Cheapest model per task (`nano` for analysis, `mini` for one short reflection,
  `gpt-audio-mini` for tone) with `reasoning: low` on gpt-5.4 calls.
- Only ~8 s of 16 kHz mono WAV is sent for tone analysis (audio tokens are expensive), never the
  full conversation; frames are downscaled to 320 px JPEG, max 5.
- All scoring math is deterministic Python, not an LLM; providers run concurrently.
- Multi-stage Docker build; ~50 kB gzipped JS bundle (hand-rolled SVG trend chart, no chart lib).
