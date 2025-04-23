"""
Core note management functionality for MarkNote.
"""
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
import yaml

from app.models.note import Note
from app.utils.file_handler import (
    ensure_notes_dir,
    parse_frontmatter,
    add_frontmatter,
    list_note_files,
)

class NoteManager:
    """
    Manages notes in the filesystem.
    """
    def __init__(self, notes_dir: Optional[str] = None):
        self.notes_dir = ensure_notes_dir(notes_dir)

    def create_note(self, title: str, content: str = "", tags: List[str] = None,
                   category: Optional[str] = None) -> Note:
        """
        Create a new note.
        
        Args:
            title: The title of the note.
            content: The initial content of the note.
            tags: Optional list of tags for the note.
            category: Optional category for the note.
            
        Returns:
            The created Note object.
        """
        if tags is None:
            tags = []
            
        # Create a new Note object
        note = Note(
            title=title,
            content=content,
            tags=tags,
            category=category,
        )
        
        # Prepare metadata for frontmatter
        metadata = {
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tags": tags,
        }
        
        if category:
            metadata["category"] = category
        
        # Add frontmatter to content
        content_with_frontmatter = add_frontmatter(content, metadata)
        
        # Ensure the note directory exists (including any category subdirectories)
        note_dir = self.notes_dir
        if category:
            note_dir = os.path.join(note_dir, category)
            os.makedirs(note_dir, exist_ok=True)
        
        # Save the note to a file
        note_path = os.path.join(note_dir, note.filename)
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content_with_frontmatter)
        
        return note

    def get_note(self, title: str, category: Optional[str] = None) -> Optional[Note]:
        """
        Get a note by its title and optional category.
        
        Args:
            title: The title of the note.
            category: Optional category of the note.
            
        Returns:
            The Note object if found, None otherwise.
        """
        # This is a placeholder implementation
        # In a real implementation, we would:
        # 1. Convert title to filename
        # 2. Look for the file in the appropriate directory
        # 3. Return the note if found
        return None

    def list_notes(self, tag: Optional[str] = None, 
                   category: Optional[str] = None) -> List[Note]:
        """
        List notes, optionally filtered by tag or category.
        
        Args:
            tag: Optional tag to filter by.
            category: Optional category to filter by.
            
        Returns:
            A list of Note objects matching the criteria.
        """
        # This is a placeholder implementation
        return []

    def search_notes(self, query: str) -> List[Note]:
        """
        Search for notes containing the query string.
        
        Args:
            query: The query string to search for.
            
        Returns:
            A list of Note objects matching the query.
        """
        # This is a placeholder implementation
        return []