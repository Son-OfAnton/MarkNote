"""
Tests for the Note model.
"""
import pytest
from datetime import datetime
from app.models.note import Note

def test_note_initialization():
    """Test that a Note can be initialized with basic properties."""
    title = "Test Note"
    content = "This is a test note."
    note = Note(title=title, content=content)
    
    assert note.title == title
    assert note.content == content
    assert note.tags == []
    assert note.category is None
    assert note.filename == "test-note.md"
    assert isinstance(note.created_at, datetime)
    assert isinstance(note.updated_at, datetime)

def test_note_with_tags_and_category():
    """Test that a Note can be initialized with tags and category."""
    title = "Test Note"
    content = "This is a test note."
    tags = ["test", "example"]
    category = "work"
    note = Note(title=title, content=content, tags=tags, category=category)
    
    assert note.title == title
    assert note.content == content
    assert note.tags == tags
    assert note.category == category

def test_is_modified():
    """Test that is_modified returns the correct value."""
    note = Note(title="Test", content="Content")
    assert not note.is_modified()
    
    # Simulate a modification
    note.created_at = datetime(2025, 1, 1, 12, 0, 0)
    note.updated_at = datetime(2025, 1, 1, 12, 30, 0)
    assert note.is_modified()

def test_add_tag():
    """Test adding a tag to a note."""
    note = Note(title="Test", content="Content")
    assert note.tags == []
    
    note.add_tag("test")
    assert note.tags == ["test"]
    
    # Adding the same tag again should not duplicate it
    note.add_tag("test")
    assert note.tags == ["test"]
    
    note.add_tag("example")
    assert set(note.tags) == {"test", "example"}

def test_remove_tag():
    """Test removing a tag from a note."""
    note = Note(title="Test", content="Content", tags=["test", "example"])
    
    note.remove_tag("test")
    assert note.tags == ["example"]
    
    # Removing a non-existent tag should not raise an error
    note.remove_tag("nonexistent")
    assert note.tags == ["example"]

def test_update_content():
    """Test updating the content of a note."""
    note = Note(title="Test", content="Original content")
    original_updated_at = note.updated_at
    
    # Wait a moment to ensure the timestamp will be different
    import time
    time.sleep(0.001)
    
    note.update_content("New content")
    assert note.content == "New content"
    assert note.updated_at > original_updated_at

def test_to_dict():
    """Test converting a note to a dictionary."""
    title = "Test Note"
    content = "This is a test note."
    tags = ["test", "example"]
    category = "work"
    created_at = datetime(2025, 1, 1, 12, 0, 0)
    updated_at = datetime(2025, 1, 1, 12, 30, 0)
    
    note = Note(
        title=title,
        content=content,
        tags=tags,
        category=category,
        created_at=created_at,
        updated_at=updated_at
    )
    
    note_dict = note.to_dict()
    
    assert note_dict["title"] == title
    assert note_dict["content"] == content
    assert note_dict["tags"] == tags
    assert note_dict["category"] == category
    assert note_dict["created_at"] == created_at.isoformat()
    assert note_dict["updated_at"] == updated_at.isoformat()