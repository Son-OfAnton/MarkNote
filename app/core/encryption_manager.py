"""
Encryption management functionality for MarkNote.
"""
import os
from typing import Optional, Dict, Any, Tuple, List, Set, Union
from datetime import datetime
import yaml
import json

from app.models.note import Note
from app.models.encrypted_note import EncryptedNote
from app.utils.encryption import (
    encrypt_content,
    decrypt_content,
    is_encrypted,
    prompt_for_password,
    EncryptionError,
    DecryptionError,
    PasswordError
)
from app.utils.file_handler import (
    ensure_notes_dir,
    read_note_file,
    write_note_file,
    add_frontmatter,
    parse_frontmatter
)


class EncryptionManager:
    """
    Manages the encryption and decryption of notes.
    """
    
    def __init__(self, notes_dir: Optional[str] = None):
        """
        Initialize the EncryptionManager.
        
        Args:
            notes_dir: Optional custom directory path for storing notes.
                      If not provided, the default directory will be used.
        """
        self.notes_dir = ensure_notes_dir(notes_dir)
    
    def encrypt_note(self, note_path: str, password: str, save: bool = True) -> EncryptedNote:
        """
        Encrypt an existing note.
        
        Args:
            note_path: Path to the note file
            password: Password for encryption
            save: Whether to save the encrypted note
            
        Returns:
            An EncryptedNote instance
            
        Raises:
            FileNotFoundError: If the note doesn't exist
            PermissionError: If the note can't be read or written
            EncryptionError: If encryption fails
        """
        # Read the note
        metadata, content = read_note_file(note_path)
        
        # Check if already encrypted
        if is_encrypted(content):
            raise EncryptionError("Note is already encrypted")
            
        # Create a Note instance
        title = metadata.get('title', os.path.splitext(os.path.basename(note_path))[0])
        tags = metadata.get('tags', [])
        category = metadata.get('category')
        
        # Parse timestamps
        try:
            created_at = datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
        except (ValueError, TypeError):
            created_at = datetime.now()
            
        try:
            updated_at = datetime.fromisoformat(metadata.get('updated_at', datetime.now().isoformat()))
        except (ValueError, TypeError):
            updated_at = datetime.now()
        
        # Extract linked notes if available
        linked_notes = set(metadata.get('linked_notes', []))

        # Create a Note instance
        note = Note(
            title=title,
            content=content,
            created_at=created_at,
            updated_at=updated_at,
            tags=tags,
            category=category,
            metadata=metadata,
            filename=os.path.basename(note_path),
            linked_notes=linked_notes
        )
        
        # Encrypt the note
        encrypted_note = EncryptedNote.encrypt(note, password)
        
        # Save the encrypted note if requested
        if save:
            # Add encryption metadata
            save_metadata = {
                **metadata,
                'is_encrypted': True,
                'encrypted_at': encrypted_note.encrypted_at.isoformat() if encrypted_note.encrypted_at else None,
                'encryption_version': 1
            }
            
            # Write the encrypted note
            write_note_file(note_path, save_metadata, encrypted_note.content)
        
        return encrypted_note
    
    def decrypt_note(self, note_path: str, password: str, save: bool = True) -> Note:
        """
        Decrypt an encrypted note.
        
        Args:
            note_path: Path to the encrypted note file
            password: Password for decryption
            save: Whether to save the decrypted note
            
        Returns:
            A Note instance with the decrypted content
            
        Raises:
            FileNotFoundError: If the note doesn't exist
            PermissionError: If the note can't be read or written
            DecryptionError: If the note is not encrypted or decryption fails
            PasswordError: If the password is incorrect
        """
        # Read the note
        metadata, content = read_note_file(note_path)
        
        # Check if actually encrypted
        if not is_encrypted(content):
            raise DecryptionError("Note is not encrypted")
        
        # Create an EncryptedNote instance
        title = metadata.get('title', os.path.splitext(os.path.basename(note_path))[0])
        encrypted_note = EncryptedNote(
            title=title,
            content=content,
            created_at=datetime.now(),  # Placeholder, will be replaced with metadata from decryption
            updated_at=datetime.now(),  # Placeholder
            metadata=metadata,
            filename=os.path.basename(note_path),
            is_encrypted=True
        )
        
        # Decrypt the note
        decrypted_note, decryption_metadata = encrypted_note.decrypt(password)
        
        # Save the decrypted note if requested
        if save:
            # Update the metadata to remove encryption markers
            save_metadata = {
                **metadata,
                'is_encrypted': False,
                'encrypted_at': None,
                'encryption_version': None
            }
            
            # Write the decrypted note
            write_note_file(note_path, save_metadata, decrypted_note.content)
        
        return decrypted_note
    
    def change_password(self, note_path: str, current_password: str, new_password: str) -> bool:
        """
        Change the password for an encrypted note.
        
        Args:
            note_path: Path to the encrypted note file
            current_password: The current password
            new_password: The new password
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileNotFoundError: If the note doesn't exist
            PermissionError: If the note can't be read or written
            DecryptionError: If the note is not encrypted
            PasswordError: If the current password is incorrect
            EncryptionError: If re-encryption fails
        """
        # Read the note
        metadata, content = read_note_file(note_path)
        
        # Check if actually encrypted
        if not is_encrypted(content):
            raise DecryptionError("Note is not encrypted")
            
        # Decrypt with current password and re-encrypt with new password
        decrypted_content, decryption_metadata = decrypt_content(content, current_password)
        new_encrypted_content = encrypt_content(decrypted_content, new_password, decryption_metadata)
        
        # Update encryption timestamp
        metadata['encrypted_at'] = datetime.now().isoformat()
        
        # Write the re-encrypted note
        write_note_file(note_path, metadata, new_encrypted_content)
        
        return True
    
    def batch_encrypt_notes(self, note_paths: List[str], password: str) -> Dict[str, str]:
        """
        Encrypt multiple notes with the same password.
        
        Args:
            note_paths: List of paths to notes
            password: Password for encryption
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        results = {}
        
        for path in note_paths:
            try:
                self.encrypt_note(path, password)
                results[path] = "Successfully encrypted"
            except Exception as e:
                results[path] = f"Failed to encrypt: {str(e)}"
                
        return results
    
    def batch_decrypt_notes(self, note_paths: List[str], password: str) -> Dict[str, str]:
        """
        Decrypt multiple notes with the same password.
        
        Args:
            note_paths: List of paths to encrypted notes
            password: Password for decryption
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        results = {}
        
        for path in note_paths:
            try:
                self.decrypt_note(path, password)
                results[path] = "Successfully decrypted"
            except Exception as e:
                results[path] = f"Failed to decrypt: {str(e)}"
                
        return results
    
    def is_note_encrypted(self, note_path: str) -> bool:
        """
        Check if a note is encrypted.
        
        Args:
            note_path: Path to the note file
            
        Returns:
            True if the note is encrypted, False otherwise
            
        Raises:
            FileNotFoundError: If the note doesn't exist
            PermissionError: If the note can't be read
        """
        try:
            _, content = read_note_file(note_path)
            return is_encrypted(content)
        except Exception:
            return False