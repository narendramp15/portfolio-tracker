"""Tests for broker encryption functionality."""

import pytest

from portfolio_tracker.encryption import EncryptionManager


class TestEncryptionManager:
    """Test encryption and decryption of sensitive data."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypted data can be decrypted back to original."""
        original_data = "my_secret_api_key_12345"
        
        encrypted = EncryptionManager.encrypt(original_data)
        decrypted = EncryptionManager.decrypt(encrypted)
        
        assert decrypted == original_data
    
    def test_encrypt_different_each_time(self):
        """Test that encryption produces different ciphertext each time."""
        original_data = "my_secret_api_key"
        
        encrypted1 = EncryptionManager.encrypt(original_data)
        encrypted2 = EncryptionManager.encrypt(original_data)
        
        # Due to Fernet's use of IV, ciphertext should be different each time
        # But they should both decrypt to the same value
        assert encrypted1 != encrypted2
        assert EncryptionManager.decrypt(encrypted1) == original_data
        assert EncryptionManager.decrypt(encrypted2) == original_data
    
    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        original_data = ""
        
        encrypted = EncryptionManager.encrypt(original_data)
        decrypted = EncryptionManager.decrypt(encrypted)
        
        assert decrypted == original_data
    
    def test_encrypt_long_string(self):
        """Test encryption of very long string."""
        original_data = "x" * 10000
        
        encrypted = EncryptionManager.encrypt(original_data)
        decrypted = EncryptionManager.decrypt(encrypted)
        
        assert decrypted == original_data
    
    def test_encrypt_special_characters(self):
        """Test encryption of string with special characters."""
        original_data = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        encrypted = EncryptionManager.encrypt(original_data)
        decrypted = EncryptionManager.decrypt(encrypted)
        
        assert decrypted == original_data
    
    def test_encrypt_unicode(self):
        """Test encryption of unicode characters."""
        original_data = "हेलो वर्ल्ड 你好世界 مرحبا بالعالم"
        
        encrypted = EncryptionManager.encrypt(original_data)
        decrypted = EncryptionManager.decrypt(encrypted)
        
        assert decrypted == original_data
    
    def test_decrypt_invalid_format(self):
        """Test decryption of invalid format returns None or empty string."""
        result = EncryptionManager.decrypt("not-a-valid-encrypted-string")
        # Should return empty string or None gracefully
        assert result in ["", None] or result == ""
    
    def test_decrypt_tampered_data(self):
        """Test decryption of tampered data returns None or empty string."""
        original_data = "my_secret_data"
        encrypted = EncryptionManager.encrypt(original_data)
        
        # Tamper with the encrypted data
        tampered = encrypted[:-10] + "0000000000"
        
        result = EncryptionManager.decrypt(tampered)
        # Should return empty string or None gracefully
        assert result in ["", None] or result == ""
