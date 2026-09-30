"""Feedback routes: log listening events and read them back.

An append-only signal log — play/skip/complete/replay/thumb. This is the raw
behavioral signal the V3 personalization model learns from, so it is captured
from day one even though nothing consumes it yet.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_episode_repo, get_feedback_repo
from app.api.schemas import FeedbackCreate, FeedbackEventModel
from app.core.interfaces.database import EpisodeRepository, FeedbackRepository
from app.domain.entities import FeedbackEvent, User

router = APIRouter(prefix="/me", tags=["feedback"])


@router.post(
    "/episodes/{episode_id}/feedback", status_code=status.HTTP_201_CREATED
)
async def log_feedback(
    episode_id: str,
    body: FeedbackCreate,
    user: User = Depends(get_current_user),
    episodes: EpisodeRepository = Depends(get_episode_repo),
    feedback: FeedbackRepository = Depends(get_feedback_repo),
) -> dict:
    episode = await episodes.get(episode_id)
    if episode is None or episode.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="episode not found"
        )
    await feedback.add(
        FeedbackEvent(
            id="",
            user_id=user.id,
            episode_id=episode_id,
            type=body.type,
            position_seconds=body.position_seconds,
        )
    )
    return {"status": "logged"}


@router.get("/feedback", response_model=list[FeedbackEventModel])
async def list_feedback(
    user: User = Depends(get_current_user),
    feedback: FeedbackRepository = Depends(get_feedback_repo),
) -> list[FeedbackEventModel]:
    events = await feedback.list_for_user(user.id)
    return [
        FeedbackEventModel(
            id=e.id,
            episode_id=e.episode_id,
            type=e.type.value,
            position_seconds=e.position_seconds,
            created_at=e.created_at,
        )
        for e in events
    ]
