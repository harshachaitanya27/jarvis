"""Auth contract: turn a request credential into a verified user identity.

Local dev auth, self-issued JWT, or Supabase Auth each implement this. Routes
depend only on the returned ``Principal`` — never on how it was verified.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Principal:
    """The authenticated caller."""

    user_id: str
    email: str | None = None


class AuthError(Exception):
    """Raised when a credential is missing, invalid, or expired."""


class AuthProvider(ABC):
    @abstractmethod
    async def verify(self, token: str) -> Principal:
        """Verify a bearer token; raise ``AuthError`` if invalid."""
        ...
