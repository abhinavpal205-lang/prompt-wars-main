"""Endpoint tests: happy paths, validation, degradation, crisis, privacy."""

from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlmodel import Session, select

from app import constants
from app.models import CheckinRecord
from app.schemas import (
    AudioToneOutput,
    FacialAffectOutput,
    ReflectionOutput,
    TranscriptSignalOutput,
)
from app.security import NoteCipher
from tests.fakes import FakeGateway, RecordingEmailSender
from tests.test_form_scorer import ideal_answers, worst_answers

REFLECTION = ReflectionOutput(
    supportive_message="You did well to check in today.",
    coping_suggestions=["Take a short walk", "Drink water", "Text a friend"],
)


def seed_voice_outputs(gateway: FakeGateway, *, crisis_language: bool = False) -> None:
    gateway.outputs = {
        TranscriptSignalOutput: TranscriptSignalOutput(
            distress_0_100=70.0,
            confidence_0_1=1.0,
            themes=["results", "sleep"],
            crisis_language=crisis_language,
            summary="They talked about results and sleep.",
        ),
        AudioToneOutput: AudioToneOutput(
            tension_0_100=50.0, confidence_0_1=0.5, note="slightly hurried"
        ),
        FacialAffectOutput: FacialAffectOutput(
            distress_0_100=40.0, confidence_0_1=0.4, note="neutral"
        ),
        ReflectionOutput: REFLECTION,
    }


VOICE_PAYLOAD: dict[str, Any] = {
    "transcript": "I am worried about results and not sleeping well.",
    "audio_segment_b64": "QUJDREVGRw==",
    "frames_b64": ["data:image/jpeg;base64,AAAA", "data:image/jpeg;base64,BBBB"],
}


async def test_healthz(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Form check-in
# ---------------------------------------------------------------------------


async def test_form_checkin_calm_happy_path(client: AsyncClient, gateway: FakeGateway) -> None:
    gateway.outputs = {ReflectionOutput: REFLECTION}
    response = await client.post("/api/checkin/form", json={"answers": ideal_answers()})
    assert response.status_code == 200
    body = response.json()
    assert body["band"] == "calm"
    assert body["crisis"] is False
    assert body["crisis_resources"] is None
    assert body["supportive_message"] == REFLECTION.supportive_message
    assert body["disclaimer"] == constants.DISCLAIMER
    assert [s["modality"] for s in body["signals"]] == ["form"]
    assert body["signals"][0]["confidence_0_1"] == 1.0


async def test_form_checkin_offline_still_works(app: FastAPI, client: AsyncClient) -> None:
    """With no OpenAI key at all, the form path must fully work."""
    app.state.gateway = FakeGateway(configured=False)
    response = await client.post("/api/checkin/form", json={"answers": worst_answers()})
    assert response.status_code == 200
    body = response.json()
    assert body["band"] == "high"
    assert len(body["coping_suggestions"]) >= 3


async def test_form_checkin_reflection_failure_degrades_gracefully(
    client: AsyncClient, gateway: FakeGateway
) -> None:
    gateway.fail_schemas = {"ReflectionOutput"}
    response = await client.post("/api/checkin/form", json={"answers": [2] * 10})
    assert response.status_code == 200
    assert response.json()["supportive_message"]  # curated fallback


async def test_form_safety_item_triggers_crisis_path(
    client: AsyncClient, gateway: FakeGateway
) -> None:
    gateway.outputs = {ReflectionOutput: REFLECTION}
    response = await client.post(
        "/api/checkin/form", json={"answers": ideal_answers(), "safety_flag": True}
    )
    body = response.json()
    assert body["crisis"] is True
    assert "14416" in body["crisis_resources"]["phone_numbers"]


async def test_form_free_note_crisis_language_detected(
    client: AsyncClient, gateway: FakeGateway
) -> None:
    gateway.outputs = {ReflectionOutput: REFLECTION}
    response = await client.post(
        "/api/checkin/form",
        json={"answers": ideal_answers(), "free_note": "sometimes I want to end my life"},
    )
    assert response.json()["crisis"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"answers": [0] * 9},  # too few items
        {"answers": [0] * 11},  # too many items
        {"answers": [0] * 9 + [5]},  # out of Likert range
        {"answers": [0] * 9 + [-1]},  # negative
        {"answers": ideal_answers(), "free_note": "x" * 2001},  # note too long
    ],
)
async def test_form_validation_rejects_bad_payloads(
    client: AsyncClient, payload: dict[str, Any]
) -> None:
    response = await client.post("/api/checkin/form", json=payload)
    assert response.status_code == 422


async def test_form_free_note_is_encrypted_at_rest(app: FastAPI, client: AsyncClient) -> None:
    note = "my private worry about boards"
    await client.post("/api/checkin/form", json={"answers": [2] * 10, "free_note": note})
    with Session(app.state.engine) as session:
        record = session.exec(select(CheckinRecord)).one()
    assert record.free_note_encrypted is not None
    assert note not in record.free_note_encrypted
    cipher = cast(NoteCipher, app.state.cipher)
    assert cipher.decrypt(record.free_note_encrypted) == note


# ---------------------------------------------------------------------------
# Voice check-in
# ---------------------------------------------------------------------------


async def test_voice_checkin_fuses_all_signals(client: AsyncClient, gateway: FakeGateway) -> None:
    seed_voice_outputs(gateway)
    response = await client.post("/api/checkin/voice", json=VOICE_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    modalities = [s["modality"] for s in body["signals"]]
    assert modalities == ["transcript", "audio", "facial"]
    # transcript 70 (w .2*0.9=.18), audio 50 (w .05), facial 40 (w .04)
    expected = (0.18 * 70 + 0.05 * 50 + 0.04 * 40) / 0.27
    assert body["composite_0_100"] == pytest.approx(expected, abs=0.1)
    assert "results" in body["likely_triggers"]
    assert body["crisis"] is False


async def test_voice_checkin_survives_failing_providers(
    client: AsyncClient, gateway: FakeGateway
) -> None:
    """A failed signal provider must never fail the check-in."""
    seed_voice_outputs(gateway)
    gateway.fail_schemas = {"AudioToneOutput", "FacialAffectOutput"}
    response = await client.post("/api/checkin/voice", json=VOICE_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    by_modality = {s["modality"]: s for s in body["signals"]}
    assert by_modality["audio"]["confidence_0_1"] == 0.0
    assert by_modality["facial"]["confidence_0_1"] == 0.0
    assert body["composite_0_100"] == pytest.approx(70.0)  # transcript only


async def test_voice_checkin_crisis_from_transcript_keywords(
    client: AsyncClient, gateway: FakeGateway
) -> None:
    """Even if every AI provider fails, keyword crisis detection holds."""
    seed_voice_outputs(gateway)
    gateway.fail_schemas = {"TranscriptSignalOutput", "AudioToneOutput", "FacialAffectOutput"}
    payload = dict(VOICE_PAYLOAD, transcript="I don't want to live anymore")
    response = await client.post("/api/checkin/voice", json=payload)
    body = response.json()
    assert body["crisis"] is True
    assert body["crisis_resources"]["phone_numbers"] == ["14416", "1-800-891-4416"]


async def test_voice_checkin_offline_neutral_fallback(app: FastAPI, client: AsyncClient) -> None:
    """No key, empty transcript: still completes with a gentle neutral result."""
    app.state.gateway = FakeGateway(configured=False)
    response = await client.post("/api/checkin/voice", json={"transcript": ""})
    assert response.status_code == 200
    assert response.json()["band"] == "mild"


@pytest.mark.parametrize(
    "payload",
    [
        {"transcript": "x" * (constants.MAX_TRANSCRIPT_CHARS + 1)},
        {"transcript": "ok", "frames_b64": ["data:image/jpeg;base64,A"] * 6},
        {"transcript": "ok", "audio_segment_b64": "A" * (constants.MAX_AUDIO_B64_CHARS + 1)},
    ],
)
async def test_voice_validation_rejects_oversized_payloads(
    client: AsyncClient, payload: dict[str, Any]
) -> None:
    response = await client.post("/api/checkin/voice", json=payload)
    assert response.status_code == 422


async def test_voice_checkin_never_persists_raw_media(
    app: FastAPI, client: AsyncClient, gateway: FakeGateway
) -> None:
    seed_voice_outputs(gateway)
    await client.post("/api/checkin/voice", json=VOICE_PAYLOAD)
    with Session(app.state.engine) as session:
        record = session.exec(select(CheckinRecord)).one()
    stored = record.model_dump_json()
    assert VOICE_PAYLOAD["audio_segment_b64"] not in stored
    assert "data:image" not in stored
    assert cast(str, VOICE_PAYLOAD["transcript"]) not in stored


# ---------------------------------------------------------------------------
# Realtime token
# ---------------------------------------------------------------------------


async def test_realtime_token_minted(client: AsyncClient) -> None:
    response = await client.post("/api/realtime/token")
    assert response.status_code == 200
    body = response.json()
    assert body["value"].startswith("ek_")
    assert body["model"] == constants.REALTIME_MODEL


async def test_realtime_token_unavailable_without_key(app: FastAPI, client: AsyncClient) -> None:
    app.state.gateway = FakeGateway(configured=False)
    response = await client.post("/api/realtime/token")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "realtime_unavailable"


# ---------------------------------------------------------------------------
# Notifications from check-ins (consent + transparency)
# ---------------------------------------------------------------------------


async def consent_to_alerts(client: AsyncClient) -> None:
    await client.put(
        "/api/profile",
        json={
            "name": "Ravi",
            "exam": "NEET",
            "consent": {
                "parent_name": "Asha",
                "parent_email": "asha@example.com",
                "notify_enabled": True,
                "cadence": "on_elevated",
                "student_visible": True,
            },
        },
    )


async def test_elevated_checkin_notifies_consented_parent(
    client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    await consent_to_alerts(client)
    await client.post("/api/checkin/form", json={"answers": worst_answers()})
    assert len(sent_emails.sent) == 1
    to, subject, body = sent_emails.sent[0]
    assert to == "asha@example.com"
    assert "14416" in body
    # Transparency: the student can see exactly what was sent.
    listing = await client.get("/api/profile/notifications")
    assert listing.json()[0]["body"] == body


async def test_calm_checkin_does_not_notify_on_elevated_cadence(
    client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    await consent_to_alerts(client)
    await client.post("/api/checkin/form", json={"answers": ideal_answers()})
    assert sent_emails.sent == []


async def test_no_consent_means_no_notification_ever(
    client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    await client.post("/api/checkin/form", json={"answers": worst_answers()})
    assert sent_emails.sent == []


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


async def test_token_endpoint_is_rate_limited(app: FastAPI, client: AsyncClient) -> None:
    from app.deps import limiter

    limiter.reset()
    limiter.enabled = True
    try:
        statuses = [(await client.post("/api/realtime/token")).status_code for _ in range(12)]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert statuses.count(200) == 10
    assert 429 in statuses
