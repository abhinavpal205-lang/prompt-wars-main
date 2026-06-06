"""Ephemeral realtime token endpoint."""

from fastapi import APIRouter, Request

from app.deps import GatewayDep, limiter
from app.schemas import RealtimeTokenResponse

router = APIRouter(prefix="/api/realtime", tags=["realtime"])


@router.post("/token", response_model=RealtimeTokenResponse)
@limiter.limit("10/minute")
async def mint_token(request: Request, gateway: GatewayDep) -> RealtimeTokenResponse:
    """Mint a short-lived client secret for the browser's voice session.

    The OpenAI API key never leaves the server; the session model and
    instructions are pinned server-side.
    """
    return await gateway.mint_realtime_secret()
