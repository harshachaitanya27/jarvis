"""FastAPI dependency wiring.

Turns a request into the collaborators a route needs: a DB session, repositories
over it, services, and the authenticated user. Routes declare what they need and
stay ignorant of construction.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import (
    SqlEpisodeRepository,
    SqlTranscriptRepository,
    SqlUserRepository,
)
from app.adapters.db.session import get_session
from app.core.interfaces.auth import AuthError, AuthProvider, Principal
from app.core.interfaces.database import (
    EpisodeRepository,
    TranscriptRepository,
    UserRepository,
)
from app.core.interfaces.storage import StorageProvider
from app.core.providers import build_auth, build_storage
from app.domain.entities import User
from app.services.auth import AuthService
from app.services.crypto import KeyVault
from app.services.users import UserService

_bearer = HTTPBearer(auto_error=True)


def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return SqlUserRepository(session)


def get_episode_repo(
    session: AsyncSession = Depends(get_session),
) -> EpisodeRepository:
    return SqlEpisodeRepository(session)


def get_transcript_repo(
    session: AsyncSession = Depends(get_session),
) -> TranscriptRepository:
    return SqlTranscriptRepository(session)


def get_storage() -> StorageProvider:
    return build_storage()


def get_auth_provider() -> AuthProvider:
    return build_auth()


def get_key_vault() -> KeyVault:
    return KeyVault()


def get_auth_service(
    users: UserRepository = Depends(get_user_repo),
) -> AuthService:
    return AuthService(users)


def get_user_service(
    users: UserRepository = Depends(get_user_repo),
    vault: KeyVault = Depends(get_key_vault),
) -> UserService:
    return UserService(users, vault)


async def get_principal(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    auth: AuthProvider = Depends(get_auth_provider),
) -> Principal:
    try:
        return await auth.verify(creds.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


async def get_current_user(
    principal: Principal = Depends(get_principal),
    users: UserRepository = Depends(get_user_repo),
) -> User:
    user = await users.get(principal.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found"
        )
    return user
