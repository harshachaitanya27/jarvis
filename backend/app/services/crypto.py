"""Encryption for users' bring-your-own provider API keys.

Keys are stored ciphertext-at-rest and only decrypted in memory when a
generation run needs to call a provider. The Fernet secret comes from
KEY_ENCRYPTION_KEY and never leaves the server.
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

log = logging.getLogger(__name__)


class KeyVault:
    def __init__(self, secret: str | None = None):
        secret = secret or get_settings().key_encryption_key
        if not secret:
            raise RuntimeError(
                "KEY_ENCRYPTION_KEY is not set; cannot encrypt/decrypt provider keys"
            )
        self._fernet = Fernet(secret.encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            # Wrong/rotated KEY_ENCRYPTION_KEY or corrupted ciphertext.
            log.error("failed to decrypt a provider key (invalid token)")
            raise ValueError("could not decrypt provider key") from exc

    @staticmethod
    def generate_secret() -> str:
        """Convenience for provisioning a new KEY_ENCRYPTION_KEY."""
        return Fernet.generate_key().decode()
