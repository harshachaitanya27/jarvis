"""Onboarding routes for the authenticated user: profile, topics, keys."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_user_service
from app.api.schemas import ProviderKeysRequest, TopicsRequest, UserProfile
from app.domain.entities import User
from app.services.users import UserService

router = APIRouter(prefix="/me", tags=["me"])


def _profile(user: User, svc: UserService) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        topics=user.onboarding_topics,
        configured_providers=svc.configured_providers(user),
        daily_question_quota=user.daily_question_quota,
    )


@router.get("", response_model=UserProfile)
async def get_me(
    user: User = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> UserProfile:
    return _profile(user, svc)


@router.put("/topics", response_model=UserProfile)
async def set_topics(
    body: TopicsRequest,
    user: User = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> UserProfile:
    user = await svc.set_topics(user, body.topics)
    return _profile(user, svc)


@router.put("/keys", response_model=UserProfile)
async def set_keys(
    body: ProviderKeysRequest,
    user: User = Depends(get_current_user),
    svc: UserService = Depends(get_user_service),
) -> UserProfile:
    user = await svc.set_provider_keys(user, body.keys)
    return _profile(user, svc)
