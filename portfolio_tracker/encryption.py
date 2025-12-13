"""Encryption utilities for sensitive data like API credentials."""

import os
from typing import Optional

from cryptography.fernet import Fernet


class EncryptionManager:
    """Manages encryption and decryption of sensitive broker credentials."""

    _cipher: Optional[Fernet] = None

    @classmethod
    def _get_cipher(cls) -> Fernet:
        """Get or create the cipher instance using the encryption key from environment."""
        if cls._cipher is None:
            key = os.getenv("ENCRYPTION_KEY")
            if not key:
                # Generate a default key (WARNING: Use a proper key in production)
                key = Fernet.generate_key().decode()
                print("WARNING: Using generated encryption key. Set ENCRYPTION_KEY in .env for persistence.")
            
            try:
                cls._cipher = Fernet(key.encode() if isinstance(key, str) else key)
            except Exception:
                # If key is invalid, generate a new one
                key = Fernet.generate_key().decode()
                cls._cipher = Fernet(key.encode())
        
        return cls._cipher

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
        """
        if not encrypted_data:
            return ""
        
        try:
            cipher = cls._get_cipher()
            decrypted = cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            # Return empty string if decryption fails
            print(f"Warning: Failed to decrypt data: {str(e)}")
            return ""


def generate_encryption_key() -> str:
    """Generate a new encryption key for use in .env."""
    return Fernet.generate_key().decode()
