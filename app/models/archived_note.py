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