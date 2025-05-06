"""
Extended Note model with archiving support.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from app.models.note import Note

@dataclass
class ArchivedNote(Note):
    """
    Extended Note class with archiving capabilities.
    """
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    
    @classmethod
    def from_note(cls, note: Note, reason: Optional[str] = None) -> 'ArchivedNote':
        """
        Create an ArchivedNote from a regular Note.
        
        Args:
            note: The Note to archive
            reason: Optional reason for archiving
            
        Returns:
            An ArchivedNote instance
        """
        return cls(
            title=note.title,
            content=note.content,
            created_at=note.created_at,
            updated_at=note.updated_at,
            tags=note.tags,
            category=note.category,
            metadata=note.metadata,
            filename=note.filename,
            linked_notes=note.linked_notes,
            is_archived=True,
            archived_at=datetime.now(),
            archive_reason=reason
        )
    
    def unarchive(self) -> Note:
        """
        Convert an ArchivedNote back to a regular Note.
        
        Returns:
            A regular Note instance
        """
        return Note(
            title=self.title,
            content=self.content,
            created_at=self.created_at,
            updated_at=self.updated_at,
            tags=self.tags,
            category=self.category,
            metadata=self.metadata,
            filename=self.filename,
            linked_notes=self.linked_notes
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the archived note to a dictionary for serialization.
        Extends the base Note.to_dict() method with archiving fields.
        """
        note_dict = super().to_dict()
        note_dict.update({
            "is_archived": self.is_archived,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "archive_reason": self.archive_reason
        })
        return note_dict
    
    @property
    def archive_age_days(self) -> Optional[int]:
        """
        Calculate how many days ago this note was archived.
        
        Returns:
            Number of days since archiving, or None if not archived
        """
        if not self.archived_at:
            return None
            
        delta = datetime.now() - self.archived_at
        return delta.days
    
    def auto_archive_by_date(self, date_str: str, field: str = "created_at",
                           before_date: bool = True, reason: str = "Auto-archived by date",
                           move_to_archive_dir: bool = True) -> Dict[str, str]:
        """
        Auto-archive notes based on a specific date field.
        
        Args:
            date_str: Date in ISO format (YYYY-MM-DD)
            field: The metadata field to compare ("created_at", "updated_at", or a custom date field)
            before_date: If True, archives notes before the date; if False, archives notes after the date
            reason: Reason for archiving
            move_to_archive_dir: Whether to move notes to the archive directory
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        try:
            # Parse the date string
            if "T" in date_str:
                # Handle full ISO format with time (e.g. 2023-01-01T12:00:00)
                archive_date = datetime.fromisoformat(date_str)
            else:
                # Handle date-only format (e.g. 2023-01-01)
                archive_date = datetime.fromisoformat(f"{date_str}T00:00:00")
                
            return self.archive_manager.auto_archive_by_date(
                archive_date, 
                field=field,
                before_date=before_date,
                reason=reason,
                move_to_archive_dir=move_to_archive_dir
            )
        except ValueError as e:
            raise ValueError(f"Invalid date format: {str(e)}. Use YYYY-MM-DD or ISO format.")