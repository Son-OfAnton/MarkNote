"""
Tests for the encryption utility functionality.
"""
import os
import pytest
import base64
from unittest.mock import patch, MagicMock, mock_open

from app.utils.encryption import (
    encrypt_content, 
    decrypt_content, 
    is_encrypted, 
    change_password,
    derive_key,
    EncryptionError,
    DecryptionError,
    AuthenticationError,
    PasswordError,
    MARKER
)

# Sample content for tests
SAMPLE_CONTENT = """
# Test Note

This is a test note with *italic* and **bold** text.

## Secret Information
- Username: testuser
- Password: verysecret

## Important Dates
- 2024-01-15: Important meeting
- 2024-02-20: Project deadline
"""

# Sample metadata for tests
SAMPLE_METADATA = {
    "title": "Secret Note",
    "created_at": "2024-06-26T10:00:00",
    "updated_at": "2024-06-26T11:00:00",
    "tags": ["secret", "important", "credentials"],
    "category": "Confidential"
}


class TestEncryption:
    """Tests for the encryption utility functions."""
    
    def test_encrypt_content_base_case(self):
        """Test successful encryption of content."""
        # Encrypt the content with a password
        encrypted = encrypt_content(SAMPLE_CONTENT, "test-password")
        
        # Check that the result is a non-empty string
        assert encrypted is not None
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        
        # Check that it's base64 encoded
        try:
            decoded = base64.b64decode(encrypted)
            # Verify it starts with the marker
            assert decoded.startswith(MARKER)
        except Exception as e:
            pytest.fail(f"Not valid base64: {e}")
    
    def test_encrypt_with_metadata(self):
        """Test encrypting content with metadata."""
        # Encrypt with metadata
        encrypted = encrypt_content(SAMPLE_CONTENT, "test-password", SAMPLE_METADATA)
        
        # Decrypt to verify metadata was included
        decrypted_content, metadata = decrypt_content(encrypted, "test-password")
        
        # Check content is preserved
        assert decrypted_content == SAMPLE_CONTENT
        
        # Check metadata is preserved
        assert metadata["title"] == SAMPLE_METADATA["title"]
        assert metadata["tags"] == SAMPLE_METADATA["tags"]
        assert metadata["category"] == SAMPLE_METADATA["category"]
        assert metadata["created_at"] == SAMPLE_METADATA["created_at"]
        assert metadata["updated_at"] == SAMPLE_METADATA["updated_at"]
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that content can be encrypted and then decrypted back to the original."""
        # Encrypt
        encrypted = encrypt_content(SAMPLE_CONTENT, "test-password")
        
        # Decrypt
        decrypted, _ = decrypt_content(encrypted, "test-password")
        
        # Verify content matches
        assert decrypted == SAMPLE_CONTENT
    
    def test_encrypt_with_empty_content(self):
        """Test encryption with empty content."""
        encrypted = encrypt_content("", "test-password")
        
        # Verify we get a non-empty encrypted string
        assert encrypted
        assert len(encrypted) > 0
        
        # Decrypt to verify
        decrypted, _ = decrypt_content(encrypted, "test-password")
        assert decrypted == ""
    
    def test_encrypt_with_different_passwords(self):
        """Test that encrypting the same content with different passwords produces different results."""
        encrypted1 = encrypt_content(SAMPLE_CONTENT, "password1")
        encrypted2 = encrypt_content(SAMPLE_CONTENT, "password2")
        
        # Check that the encrypted strings are different
        assert encrypted1 != encrypted2
    
    def test_encrypt_password_validation(self):
        """Test validation of passwords during encryption."""
        # Encrypt with empty password should raise an error or handle it
        with pytest.raises(Exception):
            encrypt_content(SAMPLE_CONTENT, "")
    
    def test_decrypt_wrong_password(self):
        """Test decryption with an incorrect password."""
        # Encrypt with one password
        encrypted = encrypt_content(SAMPLE_CONTENT, "test-password")
        
        # Try to decrypt with a different password
        with pytest.raises(PasswordError):
            decrypt_content(encrypted, "wrong-password")
    
    def test_decrypt_corrupted_data(self):
        """Test decryption with corrupted data."""
        # Create some encrypted content
        encrypted = encrypt_content(SAMPLE_CONTENT, "test-password")
        
        # Corrupt it by adding some characters
        corrupted = encrypted + "abc"
        
        # Try to decrypt
        with pytest.raises((DecryptionError, ValueError)):
            decrypt_content(corrupted, "test-password")
    
    def test_decrypt_invalid_format(self):
        """Test decryption with data in totally wrong format."""
        # Try to decrypt something that isn't encrypted
        with pytest.raises(DecryptionError):
            decrypt_content("This is not encrypted", "test-password")
    
    def test_change_password(self):
        """Test changing encryption password."""
        # Encrypt with initial password
        encrypted = encrypt_content(SAMPLE_CONTENT, "old-password")
        
        # Change password
        new_encrypted = change_password(encrypted, "old-password", "new-password")
        
        # Try to decrypt with new password
        decrypted, _ = decrypt_content(new_encrypted, "new-password")
        
        # Verify content is preserved
        assert decrypted == SAMPLE_CONTENT
        
        # Old password should no longer work
        with pytest.raises(PasswordError):
            decrypt_content(new_encrypted, "old-password")
    
    def test_is_encrypted(self):
        """Test detection of encrypted content."""
        # Create encrypted content
        encrypted = encrypt_content(SAMPLE_CONTENT, "test-password")
        
        # Check that it's detected as encrypted
        assert is_encrypted(encrypted) is True
        
        # Check that regular content is not detected as encrypted
        assert is_encrypted("This is not encrypted") is False
        assert is_encrypted(SAMPLE_CONTENT) is False
        
        # Edge cases
        assert is_encrypted("") is False
        assert is_encrypted(None) is False
    
    def test_derive_key(self):
        """Test key derivation."""
        # Test that the same password and salt produces the same key
        salt = b"1234567890123456"
        key1 = derive_key("test-password", salt)
        key2 = derive_key("test-password", salt)
        assert key1 == key2
        
        # Test that different passwords produce different keys
        key3 = derive_key("different-password", salt)
        assert key1 != key3
        
        # Test that different salts produce different keys
        salt2 = b"abcdefghijklmnop"
        key4 = derive_key("test-password", salt2)
        assert key1 != key4
    
    def test_encryption_error(self, monkeypatch):
        """Test handling of encryption errors."""
        # Mock the AESGCM class to raise an exception
        mock_aesgcm = MagicMock()
        mock_aesgcm.return_value.encrypt.side_effect = Exception("Encryption failed")
        monkeypatch.setattr("app.utils.encryption.AESGCM", mock_aesgcm)
        
        # Attempt to encrypt
        with pytest.raises(EncryptionError):
            encrypt_content(SAMPLE_CONTENT, "test-password")
    
    def test_decryption_error(self, monkeypatch):
        """Test handling of decryption errors."""
        # First create valid encrypted content
        encrypted = encrypt_content(SAMPLE_CONTENT, "test-password")
        
        # Then mock the AESGCM class to raise an exception
        mock_aesgcm = MagicMock()
        mock_aesgcm.return_value.decrypt.side_effect = Exception("Decryption failed")
        monkeypatch.setattr("app.utils.encryption.AESGCM", mock_aesgcm)
        
        # Attempt to decrypt
        with pytest.raises(DecryptionError):
            decrypt_content(encrypted, "test-password")