"""Library routes: list episodes, fetch one with a playable URL, get transcript.

All scoped to the authenticated user — an episode belonging to someone else is
indistinguishable from one that does not exist (404).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_user,
    get_episode_repo,
    get_storage,
    get_transcript_repo,
)
from app.api.schemas import (
    EpisodeSummary,
    TranscriptResponse,
    TranscriptSegmentModel,
)
from app.core.interfaces.database import EpisodeRepository, TranscriptRepository
from app.core.interfaces.storage import StorageProvider
from app.domain.entities import Episode, EpisodeStatus, User

router = APIRouter(prefix="/me/episodes", tags=["episodes"])


async def _summary(episode: Episode, storage: StorageProvider) -> EpisodeSummary:
    audio_url = None
    if episode.status == EpisodeStatus.READY and episode.audio_key:
        audio_url = await storage.url(episode.audio_key)
    return EpisodeSummary(
        id=episode.id,
        title=episode.title,
        status=episode.status.value,
        topics=episode.topics,
        duration_seconds=episode.duration_seconds,
        created_at=episode.created_at,
        audio_url=audio_url,
    )


async def _owned_or_404(
    episode_id: str, user: User, episodes: EpisodeRepository
) -> Episode:
    episode = await episodes.get(episode_id)
    if episode is None or episode.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="episode not found"
        )
    return episode


@router.get("", response_model=list[EpisodeSummary])
async def list_episodes(
    user: User = Depends(get_current_user),
    episodes: EpisodeRepository = Depends(get_episode_repo),
    storage: StorageProvider = Depends(get_storage),
) -> list[EpisodeSummary]:
    items = await episodes.list_for_user(user.id)
    return [await _summary(e, storage) for e in items]


@router.get("/{episode_id}", response_model=EpisodeSummary)
async def get_episode(
    episode_id: str,
    user: User = Depends(get_current_user),
    episodes: EpisodeRepository = Depends(get_episode_repo),
    storage: StorageProvider = Depends(get_storage),
) -> EpisodeSummary:
    episode = await _owned_or_404(episode_id, user, episodes)
    return await _summary(episode, storage)


@router.get("/{episode_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    episode_id: str,
    user: User = Depends(get_current_user),
    episodes: EpisodeRepository = Depends(get_episode_repo),
    transcripts: TranscriptRepository = Depends(get_transcript_repo),
) -> TranscriptResponse:
    await _owned_or_404(episode_id, user, episodes)
    transcript = await transcripts.get_for_episode(episode_id)
    if transcript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="transcript not available"
        )
    return TranscriptResponse(
        episode_id=episode_id,
        segments=[
            TranscriptSegmentModel(
                speaker=s.speaker, text=s.text, start_seconds=s.start_seconds
            )
            for s in transcript.segments
        ],
    )
