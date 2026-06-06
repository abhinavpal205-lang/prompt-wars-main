"""Tests for profile/consent CRUD, trends, and the one-click data wipe."""

from typing import Any

import pytest
from httpx import AsyncClient

from tests.test_form_scorer import ideal_answers, worst_answers

PROFILE: dict[str, Any] = {
    "name": "Ravi",
    "exam": "JEE",
    "consent": {
        "parent_name": "Asha",
        "parent_email": "asha@example.com",
        "notify_enabled": True,
        "cadence": "weekly",
        "student_visible": True,
    },
}


async def test_profile_defaults_to_not_onboarded(client: AsyncClient) -> None:
    response = await client.get("/api/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["onboarded"] is False
    assert body["consent"]["notify_enabled"] is False


async def test_profile_roundtrip(client: AsyncClient) -> None:
    put = await client.put("/api/profile", json=PROFILE)
    assert put.status_code == 200
    got = (await client.get("/api/profile")).json()
    assert got["onboarded"] is True
    assert got["name"] == "Ravi"
    assert got["consent"]["parent_email"] == "asha@example.com"
    assert got["consent"]["cadence"] == "weekly"


@pytest.mark.parametrize(
    "bad",
    [
        {**PROFILE, "consent": {**PROFILE["consent"], "parent_email": "not-an-email"}},
        {**PROFILE, "consent": {**PROFILE["consent"], "cadence": "hourly"}},
        {**PROFILE, "name": "x" * 121},
    ],
)
async def test_profile_validation(client: AsyncClient, bad: dict[str, Any]) -> None:
    response = await client.put("/api/profile", json=bad)
    assert response.status_code == 422


async def test_trends_accumulate_and_surface_recurring_triggers(client: AsyncClient) -> None:
    await client.post("/api/checkin/form", json={"answers": worst_answers()})
    await client.post("/api/checkin/form", json={"answers": worst_answers()})
    await client.post("/api/checkin/form", json={"answers": ideal_answers()})
    trends = (await client.get("/api/history/trends")).json()
    assert len(trends["points"]) == 3
    assert [p["band"] for p in trends["points"]] == ["high", "high", "calm"]
    assert "sleep" in trends["recurring_triggers"]
    assert all(p["composite_0_100"] is not None for p in trends["points"])


async def test_delete_wipes_everything(client: AsyncClient) -> None:
    await client.put("/api/profile", json=PROFILE)
    await client.post("/api/checkin/form", json={"answers": worst_answers()})
    deleted = (await client.delete("/api/history")).json()
    assert deleted["deleted_checkins"] == 1
    trends = (await client.get("/api/history/trends")).json()
    assert trends["points"] == []
    profile = (await client.get("/api/profile")).json()
    assert profile["onboarded"] is False
    assert profile["consent"]["parent_email"] is None
