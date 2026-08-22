"""Encryption utilities for sensitive data like API credentials.

Failure policy: this module never silently degrades. A missing or malformed
``ENCRYPTION_KEY`` and a failed decrypt are both loud, because the quiet
versions of those two failures are indistinguishable from "the user never
connected a broker" — the app would keep serving, having permanently orphaned
every stored credential in the database.
"""

from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from portfolio_tracker.config import settings


class EncryptionKeyMissing(RuntimeError):
    """Raised when ENCRYPTION_KEY is absent or not a valid Fernet key."""


class CredentialDecryptError(RuntimeError):
    """Raised when stored ciphertext cannot be decrypted with the current key.

    Almost always means the key changed (a redeploy that regenerated it, or a
    restore from a different environment), not that the data is corrupt.
    """


class EncryptionManager:
    """Manages encryption and decryption of sensitive broker credentials."""

    _cipher: Optional[Fernet] = None

    @classmethod
    def _get_cipher(cls) -> Fernet:
        """Get or create the cipher from the configured key.

        Raises:
            EncryptionKeyMissing: if ENCRYPTION_KEY is unset or unparseable.
                Outside tests we never fabricate a key — a generated key makes
                every previously stored credential unreadable, silently.
        """
        if cls._cipher is None:
            key = settings.ENCRYPTION_KEY

            if not key:
                if settings.TESTING:
                    # Tests encrypt and decrypt within a single process; an
                    # ephemeral key is correct here and never touches real data.
                    cls._cipher = Fernet(Fernet.generate_key())
                    return cls._cipher
                raise EncryptionKeyMissing(
                    "ENCRYPTION_KEY is not set. Generate one with "
                    "`python -c \"from portfolio_tracker.encryption import "
                    "generate_encryption_key as g; print(g())\"` and set it in the "
                    "environment. Do NOT let the platform generate it per-deploy: "
                    "the key must outlive the process or stored broker "
                    "credentials become permanently unreadable."
                )

            try:
                cls._cipher = Fernet(key.encode() if isinstance(key, str) else key)
            except Exception as exc:
                raise EncryptionKeyMissing(
                    "ENCRYPTION_KEY is set but is not a valid Fernet key "
                    "(expected 32 url-safe base64-encoded bytes). Refusing to "
                    "substitute a generated key, which would orphan existing "
                    f"credentials. Underlying error: {exc}"
                ) from exc

        return cls._cipher

    @classmethod
    def reset_cipher(cls) -> None:
        """Drop the cached cipher (used by tests that swap ENCRYPTION_KEY)."""
        cls._cipher = None

    @classmethod
    def encrypt(cls, data: str) -> str:
        """
        Encrypt a string value.

        Args:
            data: Plain text data to encrypt

        Returns:
            Encrypted data as string
        """
        if not data:
            return ""

        cipher = cls._get_cipher()
        encrypted = cipher.encrypt(data.encode())
        return encrypted.decode()

    @classmethod
    def decrypt(cls, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string value.

        Args:
            encrypted_data: Encrypted data as string

        Returns:
            Decrypted plain text

        Raises:
            CredentialDecryptError: if the ciphertext cannot be decrypted with
                the current key. Callers that can degrade gracefully must catch
                this explicitly, so the decision is visible at the call site
                rather than hidden behind a silent empty string.
        """
        if not encrypted_data:
            return ""

        cipher = cls._get_cipher()
        try:
            decrypted = cipher.decrypt(encrypted_data.encode())
        except InvalidToken as exc:
            raise CredentialDecryptError(
                "Stored credential could not be decrypted with the current "
                "ENCRYPTION_KEY. The key has almost certainly changed since the "
                "credential was saved; the affected broker connections must be "
                "re-authorised."
            ) from exc
        return decrypted.decode()


def generate_encryption_key() -> str:
    """Generate a new encryption key for use in .env."""
    return Fernet.generate_key().decode()
