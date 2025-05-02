"""
Extension of NoteManager with archiving capabilities.
"""

from typing import Dict, List, Optional, Tuple
import os

from app.core.note_manager import NoteManager
from app.core.archive_manager import ArchiveManager


class ArchiveNoteManager(NoteManager):
    """Extended NoteManager with archiving capabilities."""
    
    def __init__(self, notes_dir: Optional[str] = None, enable_version_control: bool = True):
        """
        Initialize the ArchiveNoteManager.
        
        Args:
            notes_dir: Optional custom directory for notes
            enable_version_control: Whether to enable version control
        """
        super().__init__(notes_dir, enable_version_control)
        self.archive_manager = ArchiveManager(notes_dir)
    
    def archive_note(self, title: str, reason: Optional[str] = None, 
                   category: Optional[str] = None, output_dir: Optional[str] = None,
                   move_to_archive_dir: bool = False) -> Tuple[bool, str]:
        """
        Archive a note.
        
        Args:
            title: Title of the note to archive
            reason: Optional reason for archiving
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            move_to_archive_dir: Whether to move the note to the archive directory
            
        Returns:
            Tuple of (success, message)
        """
        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found."
            
        try:
            # Check if already archived
            if self.archive_manager.is_note_archived(note_path):
                return False, f"Note '{title}' is already archived."
                
            # Archive the note
            success, message, _ = self.archive_manager.archive_note(
                note_path, 
                reason, 
                move_to_archive_dir
            )
            return success, message
            
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def unarchive_note(self, title: str, category: Optional[str] = None, 
                      output_dir: Optional[str] = None, move_from_archive_dir: bool = False,
                      destination_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Unarchive a note.
        
        Args:
            title: Title of the note to unarchive
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            move_from_archive_dir: Whether to move the note from the archive directory
            destination_dir: Optional destination directory for the unarchived note
            
        Returns:
            Tuple of (success, message)
        """
        # Try to find in regular locations first
        note_path = self.find_note_path(title, category, output_dir)
        
        # If not found, check in archive directory
        if not note_path:
            # Check archive directory
            archive_dir = self.archive_manager.archive_dir
            if category:
                archive_cat_dir = os.path.join(archive_dir, category)
                note_path = self.find_note_path(title, None, archive_cat_dir)
            
            if not note_path:
                note_path = self.find_note_path(title, None, archive_dir)
        
        if not note_path:
            return False, f"Note '{title}' not found."
            
        try:
            # Check if actually archived
            if not self.archive_manager.is_note_archived(note_path):
                return False, f"Note '{title}' is not archived."
                
            # Unarchive the note
            success, message, _ = self.archive_manager.unarchive_note(
                note_path, 
                move_from_archive_dir, 
                destination_dir
            )
            return success, message
            
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def list_archived_notes(self, include_content: bool = False, 
                           category: Optional[str] = None) -> List[Dict]:
        """
        List all archived notes.
        
        Args:
            include_content: Whether to include the note content
            category: Optional category to filter archived notes
            
        Returns:
            List of dictionaries with note information
        """
        return self.archive_manager.list_archived_notes(include_content, category)
    
    def get_archive_stats(self) -> Dict:
        """
        Get statistics about archived notes.
        
        Returns:
            Dictionary with archive statistics
        """
        return self.archive_manager.get_archive_stats()
    
    def batch_archive_notes(self, titles: List[str], reason: Optional[str] = None,
                          category: Optional[str] = None, output_dir: Optional[str] = None,
                          move_to_archive_dir: bool = False) -> Dict[str, str]:
        """
        Archive multiple notes.
        
        Args:
            titles: List of note titles to archive
            reason: Optional reason for archiving
            category: Optional category to help find the notes
            output_dir: Optional specific directory to look for the notes
            move_to_archive_dir: Whether to move notes to the archive directory
            
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
                # Check if already archived
                if self.archive_manager.is_note_archived(note_path):
                    results[title] = "Already archived."
                    continue
                    
                # Archive the note
                success, message, _ = self.archive_manager.archive_note(
                    note_path, 
                    reason, 
                    move_to_archive_dir
                )
                
                results[title] = message if success else f"Failed: {message}"
                
            except Exception as e:
                results[title] = f"Error: {str(e)}"
                
        return results
    
    def auto_archive_by_age(self, days: int, reason: str = "Auto-archived due to age",
                          move_to_archive_dir: bool = True) -> Dict[str, str]:
        """
        Auto-archive notes that haven't been updated in the specified number of days.
        
        Args:
            days: Number of days since last update to trigger archiving
            reason: Reason for archiving
            move_to_archive_dir: Whether to move notes to the archive directory
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        return self.archive_manager.auto_archive_by_age(days, reason, move_to_archive_dir)
    
    def is_note_archived(self, title: str, category: Optional[str] = None, 
                        output_dir: Optional[str] = None) -> bool:
        """
        Check if a note is archived.
        
        Args:
            title: Title of the note
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            
        Returns:
            True if the note is archived, False otherwise
        """
        # Try to find in regular locations first
        note_path = self.find_note_path(title, category, output_dir)
        
        # If not found, check in archive directory
        if not note_path:
            # Check archive directory
            archive_dir = self.archive_manager.archive_dir
            if category:
                archive_cat_dir = os.path.join(archive_dir, category)
                note_path = self.find_note_path(title, None, archive_cat_dir)
            
            if not note_path:
                note_path = self.find_note_path(title, None, archive_dir)
        
        if not note_path:
            return False
            
        return self.archive_manager.is_note_archived(note_path)