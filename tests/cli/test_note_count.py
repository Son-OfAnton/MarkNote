"""
Tests for the get_notes_count functionality.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from typing import List

from app.core.note_manager import NoteManager
from app.models.note import Note

class TestNoteCount(unittest.TestCase):
    """Test cases for counting notes in the system."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for test notes
        self.temp_dir = tempfile.TemporaryDirectory()
        self.notes_dir = self.temp_dir.name
        
        # Create a NoteManager instance with the test directory
        self.note_manager = NoteManager(notes_dir=self.notes_dir)
        
    def tearDown(self):
        """Clean up after the test."""
        self.temp_dir.cleanup()

    def _create_test_notes(self, count: int, category: str = None, tags: List[str] = None) -> None:
        """
        Helper method to create a specified number of test notes.
        
        Args:
            count: Number of notes to create
            category: Optional category for the notes
            tags: Optional tags for the notes
        """
        for i in range(count):
            title = f"Test Note {i+1}"
            content = f"This is test note {i+1} content."
            self.note_manager.create_note(
                title=title,
                content=content,
                category=category,
                tags=tags,
                output_dir=self.notes_dir
            )

    def test_empty_directory_returns_zero(self):
        """Test that an empty directory returns a count of zero."""
        count = self.note_manager.get_notes_count(output_dir=self.notes_dir)
        self.assertEqual(count, 0, "Empty directory should return 0 notes")

    def test_count_all_notes(self):
        """Test counting all notes in a directory."""
        # Create 5 test notes
        self._create_test_notes(5)
        
        # Count should be 5
        count = self.note_manager.get_notes_count(output_dir=self.notes_dir)
        self.assertEqual(count, 5, "Should count 5 notes in total")

    def test_count_notes_with_category_filter(self):
        """Test counting notes filtered by category."""
        # Create notes in different categories
        self._create_test_notes(3, category="work")
        self._create_test_notes(2, category="personal")
        
        # Count notes in "work" category
        work_count = self.note_manager.get_notes_count(
            category="work",
            output_dir=self.notes_dir
        )
        self.assertEqual(work_count, 3, "Should count 3 notes in work category")
        
        # Count notes in "personal" category
        personal_count = self.note_manager.get_notes_count(
            category="personal",
            output_dir=self.notes_dir
        )
        self.assertEqual(personal_count, 2, "Should count 2 notes in personal category")

    def test_count_notes_with_tag_filter(self):
        """Test counting notes filtered by tag."""
        # Create notes with different tags
        self._create_test_notes(2, tags=["important"])
        self._create_test_notes(3, tags=["draft", "important"])
        self._create_test_notes(1, tags=["draft"])
        
        # Count notes with "important" tag
        important_count = self.note_manager.get_notes_count(
            tag="important",
            output_dir=self.notes_dir
        )
        self.assertEqual(important_count, 5, "Should count 5 notes with important tag")
        
        # Count notes with "draft" tag
        draft_count = self.note_manager.get_notes_count(
            tag="draft",
            output_dir=self.notes_dir
        )
        self.assertEqual(draft_count, 4, "Should count 4 notes with draft tag")

    def test_count_notes_with_combined_filters(self):
        """Test counting notes with both category and tag filters."""
        # Create notes with various combinations of categories and tags
        self._create_test_notes(2, category="work", tags=["urgent"])
        self._create_test_notes(1, category="work", tags=["completed"])
        self._create_test_notes(3, category="personal", tags=["urgent"])
        
        # Count work notes with urgent tag
        count = self.note_manager.get_notes_count(
            category="work",
            tag="urgent",
            output_dir=self.notes_dir
        )
        self.assertEqual(count, 2, "Should count 2 work notes with urgent tag")

    def test_nonexistent_category_returns_zero(self):
        """Test that a non-existent category returns zero."""
        # Create some notes
        self._create_test_notes(5, category="existing")
        
        # Count notes in non-existent category
        count = self.note_manager.get_notes_count(
            category="nonexistent",
            output_dir=self.notes_dir
        )
        self.assertEqual(count, 0, "Non-existent category should return 0 notes")

    def test_nonexistent_tag_returns_zero(self):
        """Test that a non-existent tag returns zero."""
        # Create some notes
        self._create_test_notes(5, tags=["existing"])
        
        # Count notes with non-existent tag
        count = self.note_manager.get_notes_count(
            tag="nonexistent",
            output_dir=self.notes_dir
        )
        self.assertEqual(count, 0, "Non-existent tag should return 0 notes")
        
    def test_custom_output_directory(self):
        """Test that specifying a custom output directory works."""
        # Create a second temporary directory
        with tempfile.TemporaryDirectory() as second_dir:
            # Create notes in both directories
            self._create_test_notes(3)  # In self.notes_dir
            
            # Create a second NoteManager for the other directory
            second_manager = NoteManager(notes_dir=second_dir)
            for i in range(5):
                title = f"Second Dir Note {i+1}"
                content = f"This is a note in the second directory."
                second_manager.create_note(
                    title=title,
                    content=content,
                    output_dir=second_dir
                )
            
            # Count notes in first directory
            first_count = self.note_manager.get_notes_count(output_dir=self.notes_dir)
            self.assertEqual(first_count, 3, "Should count 3 notes in first directory")
            
            # Count notes in second directory
            second_count = self.note_manager.get_notes_count(output_dir=second_dir)
            self.assertEqual(second_count, 5, "Should count 5 notes in second directory")

    @patch('app.core.note_manager.NoteManager.list_notes')
    def test_get_notes_count_calls_list_notes(self, mock_list_notes):
        """Test that get_notes_count calls list_notes with the right parameters."""
        # Set up the mock to return a list of 3 notes
        mock_notes = [MagicMock() for _ in range(3)]
        mock_list_notes.return_value = mock_notes
        
        # Call get_notes_count
        count = self.note_manager.get_notes_count(
            tag="test-tag",
            category="test-category",
            output_dir="/test/dir"
        )
        
        # Verify list_notes was called with the right parameters
        mock_list_notes.assert_called_once_with(
            tag="test-tag",
            category="test-category",
            output_dir="/test/dir"
        )
        
        # Verify the count matches the length of the mocked return value
        self.assertEqual(count, 3)

if __name__ == '__main__':
    unittest.main()