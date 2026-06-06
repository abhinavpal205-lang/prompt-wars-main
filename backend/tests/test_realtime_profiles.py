"""Tests for the calming companion: pure instruction builder + token route."""

import pytest
from httpx import AsyncClient

from app.schemas import Band
from app.services.realtime_profiles import build_calming_instructions
from tests.fakes import FakeGateway


@pytest.mark.parametrize(
    ("band", "triggers"),
    [
        ("calm", []),
        ("mild", ["sleep"]),
        ("elevated", ["results pressure", "comparison with peers"]),
        ("high", ["sleep", "family pressure", "outlook"]),
    ],
)
def test_calming_instructions_include_band_triggers_and_helpline(
    band: Band, triggers: list[str]
) -> None:
    text = build_calming_instructions(band, triggers)
    assert band in text
    for trigger in triggers:
        assert trigger in text
    assert "14416" in text
    assert "60 seconds" in text
    assert "never diagnose" in text


def test_calming_instructions_without_triggers_stay_natural() -> None:
    assert "exam pressure in general" in build_calming_instructions("mild", [])


async def test_calming_token_minted_with_short_ttl(
    client: AsyncClient, gateway: FakeGateway
) -> None:
    response = await client.post(
        "/api/realtime/token",
        json={"profile": "calming", "band": "elevated", "triggers": ["sleep"]},
    )
    assert response.status_code == 200
    assert response.json()["value"].startswith("ek_")
    assert "mint:70" in gateway.calls  # 70s server-side backstop to the 1-min cap
    assert isinstance(gateway.last_content, str)
    assert "sleep" in gateway.last_content


async def test_calming_token_requires_band(client: AsyncClient) -> None:
    response = await client.post("/api/realtime/token", json={"profile": "calming"})
    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "calming_context_required"
    assert "14416" in body["message"]


async def test_intake_token_still_default(client: AsyncClient, gateway: FakeGateway) -> None:
    response = await client.post("/api/realtime/token")
    assert response.status_code == 200
    assert "mint:600" in gateway.calls
