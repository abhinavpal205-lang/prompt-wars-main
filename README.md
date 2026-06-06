# Sahaay — supportive wellbeing check-ins for exam-stage students

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

**Vertical: mental wellness tracker for exam-stage students (NEET, JEE, CUET, CAT, GATE, UPSC, boards).**

Sahaay (सहाय, "support") is a gentle, **non-clinical** wellbeing check-in companion. A student
checks in two ways — a ~1-minute **voice conversation** or a **private form** — and gets a warm
reflection with concrete coping suggestions, mood/trigger tracking over time, and (only with the
student's consent) a supportive summary for a parent/guardian. Crisis signals always surface real
help immediately.

> **Sahaay is not a diagnostic or medical tool.** It is a self-reflection aid. If you or someone
> you know is struggling, call **Tele-MANAS: 14416 or 1-800-891-4416** (free, 24×7, India).

## Run it (one command)

```bash
cp .env.example .env        # optional: add OPENAI_API_KEY and/or SMTP_* — see below
docker compose up --build
# open http://localhost:3000
```

The app **fully works with a blank `.env`**:

| Credential | Present | Absent (stub mode) |
|---|---|---|
| `OPENAI_API_KEY` | Voice conversation, AI signals, personalized reflections | Voice disabled with a friendly notice; form check-in fully works with deterministic scoring + curated reflections |
| `SMTP_*` | Real parent/guardian emails | Notifications print to backend logs (console stub) |
| `FERNET_KEY` | Notes decryptable across restarts | Ephemeral key; app still works |

## How it works

**Quick form (private, no mic)** — 10 Likert items inspired by perceived-stress scales (stress,
sleep, overwhelm, coping, outlook — *not a clinical instrument*) plus one explicit safety item and
an optional encrypted note. Scoring is deterministic Python: reverse-scored positive items,
0–100 composite, banded calm / mild / elevated / high. A small model (`gpt-5.4-mini`) writes the
supportive reflection; a curated fallback covers offline mode.

**Talk it out (voice, ~1 min)** — the browser fetches a short-lived ephemeral token (the OpenAI
key never leaves the server) and talks to `gpt-realtime-mini` over WebRTC with live captions.
On "done", the client sends the transcript, an ~8-second WAV snippet, and up to 5 webcam frames
(camera is **off by default**). Three failure-isolated providers score them concurrently:

- transcript → `gpt-5.4-nano` (moderate weight),
- voice tone → `gpt-audio-mini` (low weight, confidence capped),
- frames → `gpt-5.4-nano` vision (lowest weight, confidence capped).

A deterministic, confidence-aware fusion (priors: form 0.60 / transcript 0.20 / audio 0.10 /
facial 0.10, renormalized over available signals) produces the band. Any failed provider is
simply dropped — a check-in never fails because a signal did.

**Dashboard** — trend over time, recurring triggers, past reflections, every parent notification
word-for-word, and one-click **Delete all my data**.

**Crisis path** — a safety-item "yes", crisis language in a note or transcript (deterministic
keyword check + model flag) immediately renders a calm screen with Tele-MANAS numbers, before and
independent of any scoring. A "Need help now?" link is reachable from every screen.

## Responsible AI design

1. **Not a diagnosis, ever.** No clinical labels anywhere; a persistent disclaimer sits in the
   footer and on every result.
2. **Honesty about signals.** Self-report dominates the score. Voice tone and facial frames are
   unreliable; they carry hard confidence caps, the lowest fusion priors, and are presented as
   "soft hints" with full transparency ("signals we considered").
3. **Consent, not surveillance.** Parent sharing is opt-in by the student, cadence-controlled
   (weekly digest / only-on-heavier-days / off), revocable, and every sent message is stored and
   shown to the student verbatim. Messages contain supportive framing and Tele-MANAS info —
   never scores or the student's words.
4. **Crisis overrides everything** — see above; help is never delayed behind processing.
5. **Data minimization.** Raw audio, video, and transcripts are processed in memory and
   discarded; only coarse summaries (band, composite, triggers), the encrypted note, profile, and
   sent notifications are stored. One-click full wipe.
6. **Privacy by default.** No PII in logs, notes encrypted at rest (Fernet), CORS locked to the
   frontend origin, rate-limited endpoints, clean error JSON without stack traces.

## Security notes

- OpenAI key is server-side only; the browser receives a short-lived `ek_` token minted via the
  GA `/v1/realtime/client_secrets` flow with the model and instructions pinned server-side.
- Strict input validation and size caps (10 answers 0–4; transcript ≤ 8k chars; ≤ 5 frames;
  audio ≤ ~1 MB; note ≤ 2k chars). All model-generated text is rendered as plain text (React),
  never raw HTML.
- `slowapi` rate limits on every endpoint; non-root Docker user; `.env` is gitignored.

## Accessibility (WCAG 2.1 AA)

Accessibility is designed in, statically enforced, and tested:

- **Equal-status non-voice path.** The quick form is a first-class alternative to voice — no mic,
  no camera, fully keyboard-operable. Voice failures always offer the form.
- **Semantics & structure.** Landmarks (`header`/`nav`/`main`/`footer`), one `h1` per screen,
  correct heading order, `fieldset`/`legend` radio groups, labels on every input, skip-to-content
  link.
- **SPA navigation.** Each screen change updates `document.title` and moves focus to the `main`
  region, so screen-reader users always know where they are.
- **Live regions.** Voice captions and status use `role="log"`/`aria-live="polite"`; form errors
  use `role="alert"`; the calming timer is a text `role="timer"` (no animation — reduced-motion
  safe, plus a global `prefers-reduced-motion` override).
- **Color is never the only cue.** Wellbeing bands pair color with icon + text label; AA-contrast
  design tokens throughout; visible `:focus-visible` outlines.
- **Crisis help is always reachable** via the persistent "Need help now?" header link; helpline
  numbers are large `tel:` links.
- **Enforced & tested.** `eslint-plugin-jsx-a11y` (strict) runs in lint/CI; **jest-axe asserts
  zero violations on every screen** (mode select, form, result, voice, calming, dashboard,
  settings/onboarding, crisis, and the full app shell), plus a focus-management test.

## Tests

```bash
make setup   # backend venv (Python 3.12) + frontend npm ci
make lint    # ruff + ruff format + mypy --strict | eslint + prettier + tsc
make test    # 121 backend tests (OpenAI fully mocked) + 29 frontend tests incl. jest-axe
```

Backend tests cover scoring/banding tables, fusion weighting and renormalization, crisis
detection, endpoint happy paths and validation, **graceful degradation** (failed AI providers,
offline mode), notifier consent/cadence gating, and encryption at rest. Frontend tests cover the
pure capture/format helpers, form validation, result rendering, and axe accessibility assertions.

## Assumptions

- Signals are soft heuristics for supportive framing — never assessments; thresholds are
  documented in `ARCHITECTURE.md` and tuned for gentleness, not sensitivity.
- One OpenAI API key powers all AI features; the app degrades gracefully without it.
- India context: Tele-MANAS as the crisis resource; English/Hinglish-friendly voice prompts.
- SMTP is optional (console stub); single-student deployment (one profile per instance).

## Repository tour

```
backend/   FastAPI + SQLModel. Thin routers → services (pure scoring/fusion/crisis,
           AI gateway with offline stubs, consent-gated notifier). Tests in backend/tests.
frontend/  React 18 + strict TypeScript + Vite. components/ (presentational),
           hooks/ (stateful), api/ (typed I/O), lib/ (pure, tested helpers).
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the data-flow diagram and design rationale.
