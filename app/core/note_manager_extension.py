"""
Extension of NoteManager with encryption capabilities.
"""

from typing import Dict, List, Optional, Tuple
import os

from app.core.note_manager import NoteManager
from app.core.encryption_manager import EncryptionManager
from app.utils.encryption import PasswordError, EncryptionError, DecryptionError


class EncryptionNoteManager(NoteManager):
    """Extended NoteManager with encryption capabilities."""
    
    def __init__(self, notes_dir: Optional[str] = None, enable_version_control: bool = True):
        """
        Initialize the EncryptionNoteManager.
        
        Args:
            notes_dir: Optional custom directory for notes
            enable_version_control: Whether to enable version control
        """
        super().__init__(notes_dir, enable_version_control)
        self.encryption_manager = EncryptionManager(notes_dir)
    
    def encrypt_note(self, title: str, password: str, category: Optional[str] = None,
                     output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Encrypt a note.
        
        Args:
            title: Title of the note to encrypt
            password: Password for encryption
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            
        Returns:
            Tuple of (success, message)
        """
        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found."
            
        try:
            # Check if already encrypted
            if self.encryption_manager.is_note_encrypted(note_path):
                return False, f"Note '{title}' is already encrypted."
                
            # Encrypt the note
            self.encryption_manager.encrypt_note(note_path, password)
            return True, f"Note '{title}' encrypted successfully."
            
        except EncryptionError as e:
            return False, f"Error encrypting note: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def decrypt_note(self, title: str, password: str, category: Optional[str] = None,
                     output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Decrypt a note.
        
        Args:
            title: Title of the note to decrypt
            password: Password for decryption
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            
        Returns:
            Tuple of (success, message)
        """
        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found."
            
        try:
            # Check if actually encrypted
            if not self.encryption_manager.is_note_encrypted(note_path):
                return False, f"Note '{title}' is not encrypted."
                
            # Decrypt the note
            self.encryption_manager.decrypt_note(note_path, password)
            return True, f"Note '{title}' decrypted successfully."
            
        except PasswordError as e:
            return False, f"Incorrect password: {str(e)}"
        except DecryptionError as e:
            return False, f"Error decrypting note: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def change_encryption_password(self, title: str, current_password: str, new_password: str,
                                  category: Optional[str] = None, output_dir: Optional[str] = None
                                 ) -> Tuple[bool, str]:
        """
        Change the encryption password for a note.
        
        Args:
            title: Title of the note
            current_password: Current password
            new_password: New password
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            
        Returns:
            Tuple of (success, message)
        """
        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found."
            
        try:
            # Check if actually encrypted
            if not self.encryption_manager.is_note_encrypted(note_path):
                return False, f"Note '{title}' is not encrypted."
                
            # Change the password
            self.encryption_manager.change_password(note_path, current_password, new_password)
            return True, f"Password changed successfully for '{title}'."
            
        except PasswordError:
            return False, "Incorrect current password."
        except DecryptionError as e:
            return False, f"Error decrypting note: {str(e)}"
        except EncryptionError as e:
            return False, f"Error re-encrypting note: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def batch_encrypt_notes(self, titles: List[str], password: str, category: Optional[str] = None,
                           output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Encrypt multiple notes with the same password.
        
        Args:
            titles: List of note titles to encrypt
            password: Password for encryption
            category: Optional category to help find the notes
            output_dir: Optional specific directory to look for the notes
            
        Returns:
            Dictionary mapping note titles to success/error messages
        """
        results = {}
        
        for title in titles:
            # Find the note
            note_path = self.find_note_path(title, category, output_dir)
            if not note_path:
                results[title] = f"Note not found."
                continue
                
            try:
                # Check if already encrypted
                if self.encryption_manager.is_note_encrypted(note_path):
                    results[title] = "Already encrypted."
                    continue
                    
                # Encrypt the note
                self.encryption_manager.encrypt_note(note_path, password)
                results[title] = "Encrypted successfully."
                
            except Exception as e:
                results[title] = f"Error: {str(e)}"
                
        return results
    
    def batch_decrypt_notes(self, titles: List[str], password: str, category: Optional[str] = None,
                           output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Decrypt multiple notes with the same password.
        
        Args:
            titles: List of note titles to decrypt
            password: Password for decryption
            category: Optional category to help find the notes
            output_dir: Optional specific directory to look for the notes
            
        Returns:
            Dictionary mapping note titles to success/error messages
        """
        results = {}
        
        for title in titles:
            # Find the note
            note_path = self.find_note_path(title, category, output_dir)
            if not note_path:
                results[title] = f"Note not found."
                continue
                
            try:
                # Check if actually encrypted
                if not self.encryption_manager.is_note_encrypted(note_path):
                    results[title] = "Not encrypted."
                    continue
                    
                # Decrypt the note
                self.encryption_manager.decrypt_note(note_path, password)
                results[title] = "Decrypted successfully."
                
            except PasswordError:
                results[title] = "Incorrect password."
            except Exception as e:
                results[title] = f"Error: {str(e)}"
                
        return results
    
    def is_note_encrypted(self, title: str, category: Optional[str] = None,
                         output_dir: Optional[str] = None) -> bool:
        """
        Check if a note is encrypted.
        
        Args:
            title: Title of the note
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            
        Returns:
            True if the note is encrypted, False otherwise
        """
        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False
            
        return self.encryption_manager.is_note_encrypted(note_path)