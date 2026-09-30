"""Authentication service: signup, login, and access-token issuance.

Owns password hashing (bcrypt) and JWT creation. Verification of incoming
tokens is the JWTAuthProvider's job; this is the write side of auth.
"""

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import Settings, get_settings
from app.core.interfaces.database import UserRepository
from app.domain.entities import User

log = logging.getLogger(__name__)


class EmailTaken(Exception):
    """Signup with an email that already exists."""


class InvalidCredentials(Exception):
    """Login with an unknown email or wrong password."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


class AuthService:
    def __init__(self, users: UserRepository, settings: Settings | None = None):
        self.users = users
        self.settings = settings or get_settings()

    def create_access_token(self, user_id: str, email: str | None) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": now + timedelta(minutes=self.settings.access_token_ttl_minutes),
        }
        return jwt.encode(
            claims, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm
        )

    async def signup(
        self, email: str, password: str, topics: list[str] | None = None
    ) -> tuple[User, str]:
        if await self.users.get_by_email(email):
            log.info("signup rejected: email already registered (%s)", email)
            raise EmailTaken(email)
        user = await self.users.create(
            User(
                id="",
                email=email,
                password_hash=hash_password(password),
                onboarding_topics=topics or [],
            )
        )
        token = self.create_access_token(user.id, user.email)
        log.info("new user registered: %s (%s)", user.id, email)
        return user, token

    async def login(self, email: str, password: str) -> str:
        user = await self.users.get_by_email(email)
        if user is None or not user.password_hash:
            log.warning("login failed: no such account (%s)", email)
            raise InvalidCredentials()
        if not verify_password(password, user.password_hash):
            log.warning("login failed: wrong password for %s", user.id)
            raise InvalidCredentials()
        log.info("user logged in: %s", user.id)
        return self.create_access_token(user.id, user.email)
