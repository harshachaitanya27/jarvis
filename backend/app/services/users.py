"""User onboarding: interests and bring-your-own provider keys.

Keys are encrypted with the KeyVault before they touch the repository, so
plaintext secrets never reach the database. Reads never return key material —
only which providers are configured.
"""

import logging

from app.core.interfaces.database import UserRepository
from app.domain.entities import User
from app.services.crypto import KeyVault

log = logging.getLogger(__name__)


class UserService:
    def __init__(self, users: UserRepository, key_vault: KeyVault):
        self.users = users
        self.vault = key_vault

    async def set_topics(self, user: User, topics: list[str]) -> User:
        user.onboarding_topics = topics
        log.info("user %s set %d topic(s)", user.id, len(topics))
        return await self.users.update(user)

    async def set_provider_keys(self, user: User, keys: dict[str, str]) -> User:
        """Encrypt and merge provider keys, e.g. {"openai": "sk-...", ...}."""
        encrypted = dict(user.provider_keys_encrypted)
        for provider, plaintext in keys.items():
            encrypted[provider] = self.vault.encrypt(plaintext)
        user.provider_keys_encrypted = encrypted
        # Log provider names only — never key material.
        log.info("user %s stored keys for %s", user.id, sorted(keys.keys()))
        return await self.users.update(user)

    def configured_providers(self, user: User) -> list[str]:
        """Provider names the user has a key for — never the keys themselves."""
        return sorted(user.provider_keys_encrypted.keys())

    def decrypt_key(self, user: User, provider: str) -> str:
        """Decrypt a stored key for use during generation. Server-side only."""
        token = user.provider_keys_encrypted.get(provider)
        if token is None:
            log.warning("user %s has no stored key for provider %r", user.id, provider)
            raise KeyError(f"no stored key for provider {provider!r}")
        return self.vault.decrypt(token)
