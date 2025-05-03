"""
Tests for the get_notes_per_category functionality in NoteManager.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, List, Optional, Tuple

from app.core.note_manager import NoteManager
from app.models.note import Note

def create_test_notes_by_category(note_manager, category_data: Dict[str, int], output_dir: Optional[str] = None):
    """
    Helper function to create test notes with specific categories.
    
    Args:
        note_manager: The NoteManager instance to use
        category_data: Dictionary mapping category names to note counts
        output_dir: Optional output directory
    """
    note_index = 1
    for category, count in category_data.items():
        # Handle uncategorized notes
        actual_category = None if category == "(uncategorized)" else category
        
        for i in range(count):
            title = f"Note {note_index}"
            content = f"This is test note {note_index} in category {category}."
            note_manager.create_note(
                title=title,
                content=content,
                category=actual_category,
                output_dir=output_dir
            )
            note_index += 1

def test_empty_directory_returns_empty_dict(note_manager, temp_dir):
    """Test that an empty directory returns an empty dictionary."""
    category_counts = note_manager.get_notes_per_category(output_dir=temp_dir)
    assert len(category_counts) == 0, "Empty directory should return empty dictionary"
    
def test_single_category(note_manager, temp_dir):
    """Test counting notes in a single category."""
    # Create 3 notes in "work" category
    create_test_notes_by_category(note_manager, {"work": 3}, temp_dir)
    
    category_counts = note_manager.get_notes_per_category(output_dir=temp_dir)
    
    assert len(category_counts) == 1, "Should have 1 category"
    assert "work" in category_counts, "Category should be 'work'"
    assert category_counts["work"] == 3, "Should have 3 notes in 'work' category"

def test_multiple_categories(note_manager, temp_dir):
    """Test counting notes across multiple categories."""
    # Create notes in different categories
    category_data = {
        "work": 3,
        "personal": 2,
        "project": 4
    }
    create_test_notes_by_category(note_manager, category_data, temp_dir)
    
    category_counts = note_manager.get_notes_per_category(output_dir=temp_dir)
    
    # Check result
    assert len(category_counts) == 3, "Should have 3 categories"
    
    for category, expected_count in category_data.items():
        assert category in category_counts, f"Category '{category}' should be in results"
        assert category_counts[category] == expected_count, f"Category '{category}' should have {expected_count} notes"

def test_uncategorized_notes(note_manager, temp_dir):
    """Test counting notes without a category."""
    # Create notes with and without categories
    category_data = {
        "work": 2,
        "(uncategorized)": 3
    }
    create_test_notes_by_category(note_manager, category_data, temp_dir)
    
    category_counts = note_manager.get_notes_per_category(output_dir=temp_dir)
    
    # Check result
    assert len(category_counts) == 2, "Should have 2 categories (work and uncategorized)"
    assert "work" in category_counts, "Should have 'work' category"
    assert category_counts["work"] == 2, "Should have 2 notes in 'work' category"
    assert "(uncategorized)" in category_counts, "Should have '(uncategorized)' category"
    assert category_counts["(uncategorized)"] == 3, "Should have 3 notes without category"

def test_mixed_categories_and_uncategorized(note_manager, temp_dir):
    """Test a mix of categorized and uncategorized notes."""
    # Create a mix of notes
    category_data = {
        "work": 2,
        "personal": 1,
        "(uncategorized)": 4
    }
    create_test_notes_by_category(note_manager, category_data, temp_dir)
    
    category_counts = note_manager.get_notes_per_category(output_dir=temp_dir)
    
    # Verify results
    assert len(category_counts) == 3, "Should have 3 categories"
    assert category_counts["work"] == 2, "Should have 2 work notes"
    assert category_counts["personal"] == 1, "Should have 1 personal note"
    assert category_counts["(uncategorized)"] == 4, "Should have 4 uncategorized notes"

def test_custom_output_directory(note_manager):
    """Test that specifying a custom output directory works."""
    # Create two temporary directories within the main temp dir
    test_dir1 = os.path.join(note_manager.notes_dir, "dir1")
    test_dir2 = os.path.join(note_manager.notes_dir, "dir2")
    
    if not os.path.exists(test_dir1):
        os.makedirs(test_dir1)
    if not os.path.exists(test_dir2):
        os.makedirs(test_dir2)
    
    # Create different notes in each directory
    # Dir1: 2 work, 1 personal
    create_test_notes_by_category(note_manager, {"work": 2, "personal": 1}, test_dir1)
    
    # Dir2: 3 project, 2 uncategorized
    create_test_notes_by_category(note_manager, {"project": 3, "(uncategorized)": 2}, test_dir2)
    
    # Verify counts for first directory
    dir1_counts = note_manager.get_notes_per_category(output_dir=test_dir1)
    assert len(dir1_counts) == 2, "Dir1 should have 2 categories"
    assert dir1_counts["work"] == 2, "Dir1 should have 2 work notes"
    assert dir1_counts["personal"] == 1, "Dir1 should have 1 personal note"
    assert "(uncategorized)" not in dir1_counts, "Dir1 should have no uncategorized notes"
    
    # Verify counts for second directory
    dir2_counts = note_manager.get_notes_per_category(output_dir=test_dir2)
    assert len(dir2_counts) == 2, "Dir2 should have 2 categories"
    assert "project" in dir2_counts, "Dir2 should have project category"
    assert dir2_counts["project"] == 3, "Dir2 should have 3 project notes"
    assert "(uncategorized)" in dir2_counts, "Dir2 should have uncategorized category"
    assert dir2_counts["(uncategorized)"] == 2, "Dir2 should have 2 uncategorized notes"

@patch('app.core.note_manager.NoteManager.list_notes')
def test_get_notes_per_category_calls_list_notes(mock_list_notes, note_manager):
    """Test that get_notes_per_category calls list_notes with correct parameters."""
    # Create mock notes with different categories
    mock_notes = []
    
    note1 = MagicMock()
    note1.category = "work"
    mock_notes.append(note1)
    
    note2 = MagicMock()
    note2.category = "work"
    mock_notes.append(note2)
    
    note3 = MagicMock()
    note3.category = "personal"
    mock_notes.append(note3)
    
    note4 = MagicMock()
    note4.category = None
    mock_notes.append(note4)
    
    # Set up mock to return our test notes
    mock_list_notes.return_value = mock_notes
    
    # Call function with output_dir parameter
    category_counts = note_manager.get_notes_per_category(output_dir="/test/dir")
    
    # Verify list_notes was called with correct parameters
    mock_list_notes.assert_called_once_with(output_dir="/test/dir")
    
    # Verify result
    assert len(category_counts) == 3, "Should have 3 categories"
    assert category_counts["work"] == 2, "Should have 2 work notes"
    assert category_counts["personal"] == 1, "Should have 1 personal note"
    assert category_counts["(uncategorized)"] == 1, "Should have 1 uncategorized note"