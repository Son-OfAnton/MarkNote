"""
Tests for the EncryptedNote model.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.models.note import Note
from app.models.encrypted_note import EncryptedNote
from app.utils.encryption import EncryptionError, DecryptionError, PasswordError

# Sample note data
SAMPLE_CONTENT = "# Secret Note\n\nThis is a confidential note."
SAMPLE_TAGS = ["secret", "confidential"]
SAMPLE_CATEGORY = "Personal"


@pytest.fixture
def sample_note():
    """Create a sample Note for testing."""
    return Note(
        title="Secret Note",
        content=SAMPLE_CONTENT,
        created_at=datetime(2024, 1, 1, 10, 0, 0),
        updated_at=datetime(2024, 1, 1, 11, 0, 0),
        tags=SAMPLE_TAGS.copy(),
        category=SAMPLE_CATEGORY,
        metadata={"author": "Test User"},
        filename="secret-note.md",
        linked_notes=set(["Related Note"])
    )


class TestEncryptedNote:
    """Tests for the EncryptedNote class."""
    
    def test_create_from_note(self, sample_note):
        """Test creating an EncryptedNote from a regular Note."""
        # Create encrypted note
        encrypted_note = EncryptedNote.from_note(sample_note, reason="For testing")
        
        # Check that it's properly marked as encrypted
        assert encrypted_note.is_encrypted is True
        assert encrypted_note.archived_at is None
        assert encrypted_note.archive_reason == "For testing"
        
        # Check that other fields are copied correctly
        assert encrypted_note.title == sample_note.title
        assert encrypted_note.tags == sample_note.tags
        assert encrypted_note.category == sample_note.category
        assert encrypted_note.created_at == sample_note.created_at
        assert encrypted_note.updated_at == sample_note.updated_at
        assert encrypted_note.metadata == sample_note.metadata
        assert encrypted_note.filename == sample_note.filename
        assert encrypted_note.linked_notes == sample_note.linked_notes
        
        # Content should be different (encrypted)
        assert encrypted_note.content != sample_note.content
    
    @patch("app.models.encrypted_note.encrypt_content")
    def test_encrypt(self, mock_encrypt, sample_note):
        """Test encrypting a note."""
        # Mock encrypt_content to return a known value
        mock_encrypt.return_value = "ENCRYPTED_CONTENT"
        
        # Encrypt the note
        encrypted_note = EncryptedNote.encrypt(sample_note, "password")
        
        # Check that encrypt_content was called with correct parameters
        mock_encrypt.assert_called_once()
        args, kwargs = mock_encrypt.call_args
        
        # First arg should be the content
        assert args[0] == sample_note.content
        
        # Second arg should be the password
        assert args[1] == "password"
        
        # Check that the encrypted note has the mocked encrypted content
        assert encrypted_note.content == "ENCRYPTED_CONTENT"
        assert encrypted_note.is_encrypted is True
        assert encrypted_note.encrypted_at is not None
    
    @patch("app.models.encrypted_note.decrypt_content")
    def test_decrypt(self, mock_decrypt, sample_note):
        """Test decrypting an encrypted note."""
        # Create an encrypted note first
        encrypted_note = EncryptedNote.from_note(sample_note)
        encrypted_note.content = "ENCRYPTED_CONTENT"  # Mock encrypted content
        
        # Mock decrypt_content to return the original content and metadata
        mock_decrypt.return_value = (
            SAMPLE_CONTENT, 
            {
                "title": sample_note.title,
                "tags": sample_note.tags,
                "category": sample_note.category,
                "created_at": sample_note.created_at.isoformat(),
                "updated_at": sample_note.updated_at.isoformat(),
                "author": "Test User"
            }
        )
        
        # Decrypt the note
        decrypted_note, metadata = encrypted_note.decrypt("password")
        
        # Check that decrypt_content was called with correct parameters
        mock_decrypt.assert_called_once_with("ENCRYPTED_CONTENT", "password")
        
        # Check that the decrypted note has the original content
        assert decrypted_note.content == SAMPLE_CONTENT
        assert decrypted_note.title == sample_note.title
        assert decrypted_note.tags == sample_note.tags
        assert decrypted_note.category == sample_note.category
        
        # Check that metadata was properly extracted
        assert metadata["title"] == sample_note.title
        assert metadata["tags"] == sample_note.tags
        assert metadata["category"] == sample_note.category
        assert metadata["author"] == "Test User"
    
    def test_decrypt_not_encrypted(self, sample_note):
        """Test decrypting a note that's not actually encrypted."""
        # Create an encrypted note but set is_encrypted to False
        encrypted_note = EncryptedNote.from_note(sample_note)
        encrypted_note.is_encrypted = False
        
        # Attempt to decrypt
        with pytest.raises(DecryptionError):
            encrypted_note.decrypt("password")
    
    @patch("app.models.encrypted_note.decrypt_content")
    @patch("app.models.encrypted_note.encrypt_content")
    def test_change_password(self, mock_encrypt, mock_decrypt, sample_note):
        """Test changing the password of an encrypted note."""
        # Create an encrypted note
        encrypted_note = EncryptedNote.from_note(sample_note)
        encrypted_note.content = "OLD_ENCRYPTED_CONTENT"
        encrypted_note.is_encrypted = True
        
        # Mock decrypt_content to simulate successful decryption
        mock_decrypt.return_value = (SAMPLE_CONTENT, {"title": sample_note.title})
        
        # Mock encrypt_content to simulate re-encryption with the new password
        mock_encrypt.return_value = "NEW_ENCRYPTED_CONTENT"
        
        # Change the password
        encrypted_note.change_password("old-password", "new-password")
        
        # Check that the content has been re-encrypted
        assert encrypted_note.content == "NEW_ENCRYPTED_CONTENT"
        
        # Check that the appropriate functions were called
        mock_decrypt.assert_called_once_with("OLD_ENCRYPTED_CONTENT", "old-password")
        mock_encrypt.assert_called_once()
    
    def test_change_password_not_encrypted(self, sample_note):
        """Test changing password of a note that's not encrypted."""
        # Create an encrypted note but set is_encrypted to False
        encrypted_note = EncryptedNote.from_note(sample_note)
        encrypted_note.is_encrypted = False
        
        # Attempt to change password
        with pytest.raises(DecryptionError):
            encrypted_note.change_password("old-password", "new-password")
    
    @patch("app.models.encrypted_note.decrypt_content")
    def test_change_password_wrong_password(self, mock_decrypt, sample_note):
        """Test changing password with incorrect current password."""
        # Create an encrypted note
        encrypted_note = EncryptedNote.from_note(sample_note)
        encrypted_note.content = "ENCRYPTED_CONTENT"
        encrypted_note.is_encrypted = True
        
        # Mock decrypt_content to simulate password failure
        mock_decrypt.side_effect = PasswordError("Invalid password")
        
        # Attempt to change password
        with pytest.raises(PasswordError):
            encrypted_note.change_password("wrong-password", "new-password")
    
    def test_is_valid_encryption(self, sample_note):
        """Test is_valid_encryption property."""
        encrypted_note = EncryptedNote.from_note(sample_note)
        
        # When is_encrypted is False, should be False
        encrypted_note.is_encrypted = False
        assert encrypted_note.is_valid_encryption is False
        
        # When is_encrypted is True but content is not actually encrypted
        encrypted_note.is_encrypted = True
        encrypted_note.content = "Not encrypted content"
        assert encrypted_note.is_valid_encryption is False
        
        # When is_encrypted is True and content appears encrypted
        # (Mocking this since it's hard to create valid encrypted content without actual encryption)
        with patch("app.models.encrypted_note.is_encrypted", return_value=True):
            assert encrypted_note.is_valid_encryption is True
    
    def test_to_dict(self, sample_note):
        """Test conversion to dictionary with archiving fields."""
        # Create encrypted note with known values
        encrypted_note = EncryptedNote.from_note(sample_note)
        encrypted_note.is_encrypted = True
        encrypted_note.encrypted_at = datetime(2024, 1, 15)
        
        # Convert to dictionary
        note_dict = encrypted_note.to_dict()
        
        # Check that all required fields are present
        assert "title" in note_dict
        assert "content" in note_dict
        assert "created_at" in note_dict
        assert "updated_at" in note_dict
        assert "tags" in note_dict
        assert "category" in note_dict
        assert "filename" in note_dict
        assert "linked_notes" in note_dict
        
        # Check that archiving fields are included
        assert "is_encrypted" in note_dict
        assert note_dict["is_encrypted"] is True
        assert "encrypted_at" in note_dict
        assert note_dict["encrypted_at"] == encrypted_note.encrypted_at.isoformat()
    
    @patch("app.models.encrypted_note.encrypt_content")
    def test_encrypt_error_handling(self, mock_encrypt, sample_note):
        """Test error handling during encryption."""
        # Mock encrypt_content to raise an exception
        mock_encrypt.side_effect = EncryptionError("Test error")
        
        # This should propagate the error
        with pytest.raises(EncryptionError):
            EncryptedNote.encrypt(sample_note, "password")