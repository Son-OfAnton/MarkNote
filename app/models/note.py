"""
Enhanced Note model for MarkNote with linking capability.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

@dataclass
class Note:
    """
    Represents a Markdown note in the system.
    """
    title: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    filename: Optional[str] = None
    linked_notes: Set[str] = field(default_factory=set)  # Set of titles of linked notes

    def __post_init__(self):
        """
        Set filename if not provided based on title.
        """
        if not self.filename:
            # This is just a placeholder. The actual implementation will use slugify
            self.filename = self.title.lower().replace(" ", "-") + ".md"
        
        # Ensure linked_notes is a set
        if not isinstance(self.linked_notes, set):
            self.linked_notes = set(self.linked_notes)

    def is_modified(self) -> bool:
        """
        Check if the note has been modified since it was created.
        """
        return self.created_at != self.updated_at

    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the note.
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()

    def remove_tag(self, tag: str) -> None:
        """
        Remove a tag from the note.
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()

    def update_content(self, content: str) -> None:
        """
        Update the content of the note.
        """
        self.content = content
        self.updated_at = datetime.now()

    def add_link(self, target_note_title: str) -> None:
        """
        Add a link to another note.
        
        Args:
            target_note_title: The title of the note to link to.
        """
        if target_note_title != self.title:  # Prevent self-linking
            self.linked_notes.add(target_note_title)
            self.updated_at = datetime.now()

    def remove_link(self, target_note_title: str) -> None:
        """
        Remove a link to another note.
        
        Args:
            target_note_title: The title of the note to unlink.
        """
        if target_note_title in self.linked_notes:
            self.linked_notes.remove(target_note_title)
            self.updated_at = datetime.now()

    def get_links(self) -> Set[str]:
        """
        Get all linked note titles.
        
        Returns:
            A set of titles of linked notes.
        """
        return self.linked_notes

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the note to a dictionary for serialization.
        """
        return {
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "category": self.category,
            "linked_notes": list(self.linked_notes),
            "metadata": self.metadata,
            "filename": self.filename,
        }
    
    def get_word_count(self) -> int:
        """
        Count the number of words in the note's content.
        
        Returns:
            The number of words in the note's content.
        """
        # Split the content by whitespace and count the words
        # This is a simple approach that works for most cases
        return len(self.content.split())
        
    def get_statistics(self) -> Dict[str, int]:
        """
        Get various statistics about the note content.
        
        Returns:
            A dictionary with statistics (word count, character count, etc.)
        """
        content = self.content
        return {
            "word_count": len(content.split()),
            "character_count": len(content),
            "character_count_no_spaces": len(content.replace(" ", "")),
            "line_count": len(content.splitlines()),
            "paragraph_count": len([p for p in content.split("\n\n") if p.strip()]),
            "avg_words_per_paragraph": (
                len(content.split()) / 
                len([p for p in content.split("\n\n") if p.strip()])
                if [p for p in content.split("\n\n") if p.strip()] else 0
            )
        }