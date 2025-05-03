"""
Tests for the get_most_frequent_tags functionality in NoteManager.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import List, Optional, Tuple

from app.core.note_manager import NoteManager
from app.models.note import Note

def create_test_notes_with_tags(note_manager, notes_data: List[Tuple[str, List[str], Optional[str]]], output_dir: Optional[str] = None):
    """
    Helper function to create test notes with specific tags and categories.
    
    Args:
        note_manager: The NoteManager instance to use
        notes_data: List of tuples (title, tags, category)
        output_dir: Optional output directory
    """
    for index, (title, tags, category) in enumerate(notes_data):
        content = f"This is test note {index+1} content."
        note_manager.create_note(
            title=title,
            content=content,
            tags=tags,
            category=category,
            output_dir=output_dir
        )

def test_empty_notes_returns_empty_list(note_manager, temp_dir):
    """Test that when there are no notes, an empty list is returned."""
    # With no notes, there should be no frequent tags
    top_tags = note_manager.get_most_frequent_tags(output_dir=temp_dir)
    assert len(top_tags) == 0, "Empty directory should return empty list"

def test_notes_with_no_tags_returns_empty_list(note_manager, temp_dir):
    """Test that when there are notes but no tags, an empty list is returned."""
    # Create notes without tags
    for i in range(5):
        note_manager.create_note(
            title=f"Untagged Note {i+1}",
            content=f"This is an untagged note {i+1}.",
            output_dir=temp_dir
        )
    
    top_tags = note_manager.get_most_frequent_tags(output_dir=temp_dir)
    assert len(top_tags) == 0, "Notes without tags should return empty list"

def test_most_frequent_tag_single(note_manager, temp_dir):
    """Test identifying a single most frequent tag."""
    # Create notes with various tags
    notes_data = [
        ("Note 1", ["important"], None),
        ("Note 2", ["important"], None),
        ("Note 3", ["important", "work"], None),
        ("Note 4", ["work"], None),
        ("Note 5", ["personal"], None)
    ]
    create_test_notes_with_tags(note_manager, notes_data, temp_dir)
    
    # Get the single most frequent tag
    top_tag = note_manager.get_most_frequent_tags(output_dir=temp_dir)
    
    # Should have one result
    assert len(top_tag) == 1, "Should return exactly one tag"
    
    # Most frequent tag should be "important" with count 3
    assert top_tag[0][0] == "important", "Most frequent tag should be 'important'"
    assert top_tag[0][1] == 3, "Count for 'important' should be 3"

def test_most_frequent_tags_multiple(note_manager, temp_dir):
    """Test retrieving multiple top tags ordered by frequency."""
    # Create notes with various tags
    notes_data = [
        ("Note 1", ["important", "work"], None),
        ("Note 2", ["important", "work"], None),
        ("Note 3", ["important", "urgent"], None),
        ("Note 4", ["work", "project"], None),
        ("Note 5", ["personal", "urgent"], None),
        ("Note 6", ["project", "personal"], None)
    ]
    create_test_notes_with_tags(note_manager, notes_data, temp_dir)
    
    # Get top 3 tags
    top_tags = note_manager.get_most_frequent_tags(output_dir=temp_dir, limit=3)
    
    # Should have three results
    assert len(top_tags) == 3, "Should return 3 tags"
    
    # Verify the order and counts
    # Expected: important (3), work (3), personal (2) or project (2) or urgent (2)
    assert top_tags[0][0] in ["important", "work"], "First tag should be either 'important' or 'work'"
    assert top_tags[0][1] == 3, "Count for top tag should be 3"
    
    # Second tag should also have frequency 3 (tie with first)
    assert top_tags[1][0] in ["important", "work"], "Second tag should be either 'important' or 'work'"
    assert top_tags[1][1] == 3, "Count for second tag should be 3"
    
    # Third tag should have frequency 2
    assert top_tags[2][0] in ["personal", "project", "urgent"], "Third tag should be 'personal', 'project', or 'urgent'"
    assert top_tags[2][1] == 2, "Count for third tag should be 2"

def test_most_frequent_tags_limit(note_manager, temp_dir):
    """Test that the limit parameter works as expected."""
    # Create notes with many tags
    notes_data = [
        ("Note 1", ["tag1", "tag2", "tag3"], None),
        ("Note 2", ["tag1", "tag2", "tag4"], None),
        ("Note 3", ["tag1", "tag5"], None),
        ("Note 4", ["tag2", "tag6"], None),
        ("Note 5", ["tag3", "tag7"], None)
    ]
    create_test_notes_with_tags(note_manager, notes_data, temp_dir)
    
    # Get top 2 tags
    top_tags = note_manager.get_most_frequent_tags(output_dir=temp_dir, limit=2)
    
    # Should have exactly 2 results, regardless of how many tags exist
    assert len(top_tags) == 2, "Should return exactly 2 tags"
    
    # Verify the order
    assert top_tags[0][0] == "tag1", "Most frequent tag should be 'tag1'"
    assert top_tags[0][1] == 3, "Count for 'tag1' should be 3"
    
    assert top_tags[1][0] == "tag2", "Second most frequent tag should be 'tag2'"
    assert top_tags[1][1] == 3, "Count for 'tag2' should be 3"

def test_most_frequent_tags_with_category_filter(note_manager, temp_dir):
    """Test that category filtering works with tag frequency calculation."""
    # Create notes with categories
    notes_data = [
        ("Work Note 1", ["important", "urgent"], "work"),
        ("Work Note 2", ["important", "project"], "work"),
        ("Personal Note 1", ["important", "family"], "personal"),
        ("Personal Note 2", ["family", "health"], "personal"),
        ("Personal Note 3", ["family", "finance"], "personal")
    ]
    create_test_notes_with_tags(note_manager, notes_data, temp_dir)
    
    # Get top tag for work category only
    work_tags = note_manager.get_most_frequent_tags(category="work", output_dir=temp_dir)
    
    # Should be "important" with count 2
    assert work_tags[0][0] == "important", "Most frequent work tag should be 'important'"
    assert work_tags[0][1] == 2, "Count for 'important' in work category should be 2"
    
    # Get top tag for personal category
    personal_tags = note_manager.get_most_frequent_tags(category="personal", output_dir=temp_dir)
    
    # Should be "family" with count 3
    assert personal_tags[0][0] == "family", "Most frequent personal tag should be 'family'"
    assert personal_tags[0][1] == 3, "Count for 'family' in personal category should be 3"

def test_most_frequent_tags_with_large_limit(note_manager, temp_dir):
    """Test that requesting more tags than exist returns all available tags."""
    # Create notes with a few tags
    notes_data = [
        ("Note 1", ["tag1", "tag2"], None),
        ("Note 2", ["tag1", "tag3"], None)
    ]
    create_test_notes_with_tags(note_manager, notes_data, temp_dir)
    
    # Get top 10 tags (more than exist)
    all_tags = note_manager.get_most_frequent_tags(output_dir=temp_dir, limit=10)
    
    # Should only return 3 tags total
    assert len(all_tags) == 3, "Should return all 3 available tags"
    
    # Verify all tags are present with correct counts
    tag_dict = dict(all_tags)
    assert tag_dict.get("tag1") == 2, "tag1 should appear twice"
    assert tag_dict.get("tag2") == 1, "tag2 should appear once"
    assert tag_dict.get("tag3") == 1, "tag3 should appear once"

@patch('app.core.note_manager.NoteManager.list_notes')
def test_get_most_frequent_tags_calls_list_notes(mock_list_notes, note_manager):
    """Test that get_most_frequent_tags calls list_notes with correct parameters."""
    # Create mock notes with tags
    mock_note1 = MagicMock()
    mock_note1.tags = ["tag1", "tag2"]
    
    mock_note2 = MagicMock()
    mock_note2.tags = ["tag1", "tag3"]
    
    # Set up mock to return our test notes
    mock_list_notes.return_value = [mock_note1, mock_note2]
    
    # Call function with specific parameters
    tags = note_manager.get_most_frequent_tags(
        category="test-category",
        output_dir="/test/dir",
        limit=5
    )
    
    # Verify list_notes was called with correct parameters
    mock_list_notes.assert_called_once_with(
        category="test-category",
        output_dir="/test/dir"
    )
    
    # Verify result
    assert len(tags) == 3, "Should return 3 unique tags"
    assert tags[0][0] == "tag1", "Most frequent tag should be tag1"
    assert tags[0][1] == 2, "tag1 should appear twice"