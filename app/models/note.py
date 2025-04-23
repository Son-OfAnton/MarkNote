"""
Note model for MarkNote.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

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

    def __post_init__(self):
        """
        Set filename if not provided based on title.
        """
        if not self.filename:
            # This is just a placeholder. The actual implementation will use slugify
            self.filename = self.title.lower().replace(" ", "-") + ".md"

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
            "metadata": self.metadata,
            "filename": self.filename,
        }