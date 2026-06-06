"""Encryption-at-rest for the sensitive free-note field."""

import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class NoteCipher:
    """Symmetric encryption for student notes stored in the database."""

    def __init__(self, key: str) -> None:
        """Use the configured Fernet key, or an ephemeral one if blank.

        With an ephemeral key the app still works, but notes saved before a
        restart can no longer be decrypted (they render as unavailable).
        """
        if key:
            self._fernet = Fernet(key.encode())
        else:
            logger.warning(
                "FERNET_KEY not set - using an ephemeral key; "
                "stored notes will not survive a restart."
            )
            self._fernet = Fernet(Fernet.generate_key())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a note for storage."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a stored note; degrade gracefully on key mismatch."""
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            return "[note unavailable]"
