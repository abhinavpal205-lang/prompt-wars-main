"""Ephemeral realtime token endpoint (intake and calming profiles)."""

from fastapi import APIRouter, Request

from app.deps import GatewayDep, limiter
from app.errors import CalmingContextError
from app.schemas import RealtimeTokenRequest, RealtimeTokenResponse
from app.services.realtime_profiles import build_calming_instructions, intake_instructions

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

_INTAKE_TTL_SECONDS = 600
# Hard server-side backstop to the calming companion's 1-minute cap.
_CALMING_TTL_SECONDS = 70


@router.post("/token", response_model=RealtimeTokenResponse)
@limiter.limit("10/minute")
async def mint_token(
    request: Request,
    gateway: GatewayDep,
    payload: RealtimeTokenRequest | None = None,
) -> RealtimeTokenResponse:
    """Mint a short-lived client secret for the browser's voice session.

    The OpenAI API key never leaves the server; model and instructions are
    pinned server-side. The calming profile requires a non-crisis band —
    crisis check-ins must use the crisis resources (Tele-MANAS 14416), never
    the companion.
    """
    body = payload or RealtimeTokenRequest()
    if body.profile == "calming":
        if body.band is None:
            raise CalmingContextError(
                "Calming sessions need a check-in band. If you need help now, "
                "call Tele-MANAS: 14416."
            )
        return await gateway.mint_realtime_secret(
            instructions=build_calming_instructions(body.band, body.triggers),
            ttl_seconds=_CALMING_TTL_SECONDS,
        )
    return await gateway.mint_realtime_secret(
        instructions=intake_instructions(), ttl_seconds=_INTAKE_TTL_SECONDS
    )
