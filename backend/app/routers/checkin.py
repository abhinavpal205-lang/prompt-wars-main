"""Check-in endpoints (form and voice)."""

from fastapi import APIRouter, Request

from app.deps import CipherDep, GatewayDep, SenderDep, SessionDep, limiter
from app.schemas import CheckinResult, FormResponse, VoiceCheckinRequest
from app.services.checkin_service import run_form_checkin, run_voice_checkin

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


@router.post("/form", response_model=CheckinResult)
@limiter.limit("10/minute")
async def form_checkin(
    request: Request,
    payload: FormResponse,
    session: SessionDep,
    gateway: GatewayDep,
    sender: SenderDep,
    cipher: CipherDep,
) -> CheckinResult:
    """Score the self-report form into a supportive check-in result."""
    return await run_form_checkin(session, gateway, sender, cipher, payload)


@router.post("/voice", response_model=CheckinResult)
@limiter.limit("6/minute")
async def voice_checkin(
    request: Request,
    payload: VoiceCheckinRequest,
    session: SessionDep,
    gateway: GatewayDep,
    sender: SenderDep,
    cipher: CipherDep,
) -> CheckinResult:
    """Fuse voice-session signals into a supportive check-in result.

    Raw audio and frames are processed in memory only and discarded.
    """
    return await run_voice_checkin(session, gateway, sender, cipher, payload)
