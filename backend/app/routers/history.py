"""Trend history and the one-click data wipe."""

from fastapi import APIRouter, Request

from app.deps import SessionDep, limiter
from app.schemas import DeletionResult, TrendsResponse
from app.services.history import delete_all_data, get_trends

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/trends", response_model=TrendsResponse)
async def trends(request: Request, session: SessionDep) -> TrendsResponse:
    """Mood/stress trend over time plus recurring triggers."""
    return get_trends(session)


@router.delete("", response_model=DeletionResult)
@limiter.limit("5/minute")
async def wipe_all_data(request: Request, session: SessionDep) -> DeletionResult:
    """Delete all of the student's data (check-ins, notifications, profile)."""
    return delete_all_data(session)
