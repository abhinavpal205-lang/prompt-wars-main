# Sahaay — supportive wellbeing check-ins for exam-stage students

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

> **Sahaay is not a diagnostic or medical tool.** It is a self-reflection aid. If you or someone
> you know is struggling, call **Tele-MANAS: 14416 or 1-800-891-4416** (free, 24×7, India).

**Vertical: mental wellness tracker for exam-stage students** (NEET, JEE, CUET, CAT, GATE, UPSC,
boards).

---

## The problem

Every year, millions of Indian students go through high-pressure exam seasons largely alone with
their stress. They won't book a therapist, often can't talk freely at home, and most "wellness"
apps either feel clinical, ignore their context (rank anxiety, comparison, family pressure), or
quietly report on them.

## What Sahaay does

Sahaay (सहाय, *"support"*) is a gentle, **non-clinical** check-in companion:

1. **Check in, two ways.** A ~1-minute **voice conversation** with a warm AI companion, or a
   **quick private form** — ten quiet questions, no mic, no camera. Both are first-class.
2. **Get a kind, honest reflection.** A deterministic scoring engine (not the AI) computes a
   wellbeing band — *steady / a little pressed / carrying a lot / really heavy* — plus likely
   triggers and 3–5 coping suggestions doable today. Never a diagnosis, never "study harder."
3. **See yourself over time.** A dashboard shows the trend, recurring triggers, and past
   reflections — with one-click **delete everything**.
4. **Optionally loop in a parent — on the student's terms.** Opt-in supportive email updates
   (weekly, or only on heavier days) that coach the parent on *how to help*. Every message is
   shown to the student word-for-word. No scores, no surveillance.
5. **A calming minute.** After a check-in, an optional 60-second voice session guides one
   grounding exercise and one kind reframe, hard-capped client- and server-side.
6. **Crisis comes first, always.** A safety question, crisis language in a note or transcript
   (deterministic keyword check + model flag) immediately shows Tele-MANAS — before and
   independent of any scoring. A "Need help now?" link is on every screen.

## Quick start — one command

```bash
cp .env.example .env        # all values optional — see table below
docker compose up --build
# open http://localhost:3000
```

| `.env` value | If set | If blank (default) |
|---|---|---|
| `OPENAI_API_KEY` | Voice check-in, AI signal analysis, personalized reflections | **App still fully works**: form check-in with deterministic scoring + curated reflections; voice shows a friendly notice |
| `SMTP_*` | Real parent/guardian emails | Notifications print to backend logs (console stub) |
| `FERNET_KEY` | Notes decryptable across restarts | Ephemeral key generated at boot |

Local development without Docker: `make setup`, then `make lint` / `make test`.

## Usable by diverse users, in diverse environments

Designed for real students in real Indian contexts, not ideal conditions:

- **No mic? In class? Shared hostel room?** The form path is a private, equal alternative —
  it was built first and works completely offline from AI services.
- **Camera is off by default.** Visual cues are opt-in per session; saying no costs nothing.
- **Low-end devices and patchy networks.** ~50 kB gzipped JS (no chart library — hand-rolled
  SVG), mobile-first responsive layout, and graceful degradation when any AI call fails or times
  out: the check-in always completes.
- **No credentials, no cost barriers.** Runs with a completely blank `.env`; the crisis resource
  (Tele-MANAS) is free and government-run; nothing in the app is paywalled.
- **Language and tone.** Plain, warm English; the voice companion mirrors Hinglish if the student
  uses it; no clinical jargon anywhere.
- **Screen-reader and keyboard users.** Landmarks, one `h1` per screen, labelled
  `fieldset`/`legend` radio groups, skip link, visible focus, SPA focus management +
  per-screen titles, `aria-live` captions/status/alerts, text-based timer. Enforced by
  `eslint-plugin-jsx-a11y` (strict) in CI and **jest-axe zero-violation tests on every screen**.
- **Visual diversity.** WCAG AA contrast tokens; bands always pair color with icon + text;
  `prefers-reduced-motion` respected globally.
- **Parents are users too.** Notifications are written to *help them support* the student —
  band phrasing in plain words, three concrete tips, Tele-MANAS info — never raw scores.
- **Students in crisis.** The help screen is calm, immediate, never gated behind scoring or a
  network call, with large tappable `tel:` links.

## How the scoring works (honest by design)

The **self-report is the primary signal**. AI-derived cues are supplementary hints, each with a
confidence value, and any can be absent:

| Signal | Model | Prior weight | Confidence cap |
|---|---|---|---|
| Form answers (10 Likert items, reverse-scored) | deterministic Python | 0.60 | — |
| Transcript themes/sentiment | `gpt-5.4-nano` | 0.20 | 0.9 |
| Voice tone (~8 s WAV segment) | `gpt-audio-mini` | 0.10 | 0.5 |
| Webcam frames (≤ 5, opt-in) | `gpt-5.4-nano` vision | 0.10 | 0.4 |

`weight = prior × confidence`; zero-confidence signals are dropped and weights renormalize. The
result card lists every signal and whether it was used — transparency over magic. Full rationale
in [ARCHITECTURE.md](ARCHITECTURE.md).

## Responsible-AI commitments

1. **Not a diagnosis, ever** — persistent disclaimer in the footer and on every result.
2. **Honesty about signals** — soft cues can nudge, never decide (see table above).
3. **Consent, not surveillance** — sharing is student-controlled, cadence-limited, revocable,
   and fully transparent ("what we sent" is on the dashboard).
4. **Crisis overrides everything** — help is never delayed behind processing.
5. **Data minimization** — raw audio, video, and transcripts are processed in memory and
   discarded; only coarse summaries + an encrypted note are stored; one-click full wipe.
6. **Privacy by default** — no PII in logs, Fernet-encrypted notes, locked-down CORS, rate
   limits, clean error JSON.

## Security

- The OpenAI key never leaves the server; the browser gets a short-lived `ek_` token (GA
  `/v1/realtime/client_secrets`) with model + instructions pinned server-side. The calming
  session's token expires in 70 s as a backstop to the client's 60 s cap.
- Strict validation and size caps on every input; model output rendered as plain text only;
  `slowapi` rate limits; non-root container; `.env` gitignored with a committed example.

## Quality & testing

| Layer | Enforced in CI |
|---|---|
| Backend | `ruff` (incl. security + bugbear rules), `ruff format`, **`mypy --strict`**, 129 pytest tests |
| Frontend | ESLint (typescript-eslint type-checked + **jsx-a11y strict**), Prettier, `tsc --noEmit` strict, 39 vitest tests |

Tests cover: scoring/banding tables, fusion weighting + renormalization, crisis detection,
endpoint validation, **graceful degradation** (failed providers, offline mode), notifier
consent/cadence gating, encryption at rest, capture/format helpers, countdown behavior,
component rendering, and axe accessibility on every screen. OpenAI is fully mocked — no test
touches the network.

```bash
make test   # everything
make lint   # everything
```

## Architecture at a glance

```
backend/   FastAPI + SQLModel (SQLite). Thin routers → service layer:
           pure scoring/fusion/crisis (no I/O, exhaustively tested),
           AIGateway protocol (single OpenAI access point, offline stubs, test fakes),
           failure-isolated signal providers, consent-gated notifier.
frontend/  React 18 + strict TypeScript + Vite.
           components/ (presentational, CSS modules + shared design tokens)
           hooks/ (voice session, history, countdown) · api/ (typed I/O) · lib/ (pure, tested)
deploy/    Multi-stage Dockerfiles, nginx serving the SPA + proxying /api (same-origin),
           compose with healthcheck-gated startup.
```

Details, data-flow diagram, and design trade-offs: [ARCHITECTURE.md](ARCHITECTURE.md).

## Assumptions & scope

- Signals are soft heuristics for supportive framing; thresholds tuned for gentleness.
- One OpenAI API key powers all AI features; everything degrades gracefully without it.
- India context: Tele-MANAS as the crisis resource; single-student deployment per instance.
- SMTP optional (console stub keeps the full flow demonstrable).
