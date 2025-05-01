"""
Extended Note model with encryption support.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple

from app.models.note import Note
from app.utils.encryption import (
    encrypt_content,
    decrypt_content,
    is_encrypted,
    EncryptionError,
    DecryptionError,
    PasswordError
)

@dataclass
class EncryptedNote(Note):
    """
    Extended Note class with encryption capabilities.
    """
    is_encrypted: bool = False
    encrypted_at: Optional[datetime] = None
    
    @classmethod
    def encrypt(cls, note: Note, password: str) -> 'EncryptedNote':
        """
        Encrypt an existing Note and return an EncryptedNote.
        
        Args:
            note: The Note to encrypt
            password: Password for encryption
            
        Returns:
            An EncryptedNote with encrypted content
            
        Raises:
            EncryptionError: If encryption fails
        """
        # Create metadata for encryption
        encryption_metadata = {
            "title": note.title,
            "tags": note.tags,
            "category": note.category,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "linked_notes": list(note.linked_notes) if note.linked_notes else []
        }
        
        # Encrypt the content
        encrypted_content = encrypt_content(note.content, password, encryption_metadata)
        
        # Create a new EncryptedNote
        return cls(
            title=note.title,
            content=encrypted_content,
            created_at=note.created_at,
            updated_at=note.updated_at,
            tags=note.tags,
            category=note.category,
            metadata=note.metadata,
            filename=note.filename,
            linked_notes=note.linked_notes,
            is_encrypted=True,
            encrypted_at=datetime.now()
        )
    
    @classmethod
    def from_encrypted_content(cls, encrypted_content: str, password: str) -> 'EncryptedNote':
        """
        Create an EncryptedNote from existing encrypted content.
        
        Args:
            encrypted_content: The encrypted content
            password: Password for decryption
            
        Returns:
            An EncryptedNote instance
            
        Raises:
            DecryptionError: If decryption fails
            PasswordError: If the password is incorrect
        """
        # Decrypt to get content and metadata
        content, metadata = decrypt_content(encrypted_content, password)
        
        # Extract metadata
        title = metadata.get("title", "Untitled Encrypted Note")
        tags = metadata.get("tags", [])
        category = metadata.get("category")
        
        # Parse dates
        created_at = datetime.fromisoformat(metadata.get("created_at")) if "created_at" in metadata else datetime.now()
        updated_at = datetime.fromisoformat(metadata.get("updated_at")) if "updated_at" in metadata else datetime.now()
        
        # Extract linked notes
        linked_notes = set(metadata.get("linked_notes", []))
        
        # Create a new EncryptedNote
        return cls(
            title=title,
            content=encrypted_content,  # Keep content encrypted
            created_at=created_at,
            updated_at=updated_at,
            tags=tags,
            category=category,
            metadata=metadata,
            filename=None,  # Filename will be set in post_init
            linked_notes=linked_notes,
            is_encrypted=True,
            encrypted_at=None  # Unknown encryption time for existing content
        )
    
    def decrypt(self, password: str) -> Tuple[Note, Dict[str, Any]]:
        """
        Decrypt this note and return a regular Note.
        
        Args:
            password: Password for decryption
            
        Returns:
            Tuple of (decrypted Note, metadata)
            
        Raises:
            DecryptionError: If the note is not encrypted or decryption fails
            PasswordError: If the password is incorrect
        """
        if not self.is_encrypted or not is_encrypted(self.content):
            raise DecryptionError("Note is not encrypted")
        
        # Decrypt content
        decrypted_content, metadata = decrypt_content(self.content, password)
        
        # Create a regular Note with decrypted content
        regular_note = Note(
            title=self.title,
            content=decrypted_content,
            created_at=self.created_at,
            updated_at=self.updated_at,
            tags=self.tags,
            category=self.category,
            metadata=self.metadata,
            filename=self.filename,
            linked_notes=self.linked_notes
        )
        
        return regular_note, metadata
    
    def change_password(self, current_password: str, new_password: str) -> None:
        """
        Change the encryption password for this note.
        
        Args:
            current_password: The current password
            new_password: The new password
            
        Raises:
            DecryptionError: If the note is not encrypted
            PasswordError: If the current password is incorrect
            EncryptionError: If re-encryption fails
        """
        if not self.is_encrypted:
            raise DecryptionError("Note is not encrypted")
            
        # Decrypt and extract content and metadata
        note, metadata = self.decrypt(current_password)
        
        # Re-encrypt with new password
        new_encrypted_content = encrypt_content(note.content, new_password, metadata)
        
        # Update encrypted content and timestamp
        self.content = new_encrypted_content
        self.encrypted_at = datetime.now()
        
    @property
    def is_valid_encryption(self) -> bool:
        """Check if this note contains validly encrypted content."""
        return self.is_encrypted and is_encrypted(self.content)