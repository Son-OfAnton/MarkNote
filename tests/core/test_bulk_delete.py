"""
Tests for the bulk delete functionality in NoteManager.
"""
import os
import shutil
import tempfile
from unittest import TestCase, mock
from datetime import datetime
from typing import List, Optional

from app.core.note_manager import NoteManager
from app.models.note import Note
from app.utils.file_handler import write_note_file


class TestBulkDelete(TestCase):
    """Test cases for bulk delete functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create a NoteManager with the test directory
        self.note_manager = NoteManager(notes_dir=self.test_dir, enable_version_control=False)
        
        # Create some test notes
        self.test_notes = [
            {"title": "Test Note 1", "tags": ["test", "important", "work"]},
            {"title": "Test Note 2", "tags": ["test", "personal"]},
            {"title": "Test Note 3", "tags": ["work", "project"]},
            {"title": "Test Note 4", "tags": ["personal", "important"]},
            {"title": "Test Note 5", "tags": ["test", "work", "project"]},
        ]
        
        # Add notes to the test directory
        for note_data in self.test_notes:
            self._create_test_note(note_data["title"], note_data["tags"])

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def _create_test_note(self, title: str, tags: List[str], 
                         category: Optional[str] = None, content: str = "Test content"):
        """Create a test note file in the test directory."""
        if category:
            # Ensure category directory exists
            category_dir = os.path.join(self.test_dir, category)
            os.makedirs(category_dir, exist_ok=True)
        
        # Create note metadata
        metadata = {
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tags": tags,
        }
        
        if category:
            metadata["category"] = category
            
        # Generate note filename
        filename = title.lower().replace(" ", "-") + ".md"
        
        # Determine the correct path
        file_path = os.path.join(self.test_dir, category or "", filename)
        
        # Write the note file
        write_note_file(file_path, metadata, content)
        
        return file_path

    def test_delete_single_note(self):
        """Test deleting a single note."""
        # Delete a note
        success, message = self.note_manager.delete_note("Test Note 1")
        
        # Check that the function returned success
        self.assertTrue(success)
        self.assertIn("deleted successfully", message)
        
        # Verify the note file was actually deleted
        expected_path = os.path.join(self.test_dir, "test-note-1.md")
        self.assertFalse(os.path.exists(expected_path))
        
        # Other notes should still exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "test-note-2.md")))

    def test_delete_nonexistent_note(self):
        """Test attempting to delete a note that doesn't exist."""
        success, message = self.note_manager.delete_note("Nonexistent Note")
        
        # Should return failure
        self.assertFalse(success)
        self.assertIn("not found", message)
        
        # All original notes should still exist
        for note_data in self.test_notes:
            filename = note_data["title"].lower().replace(" ", "-") + ".md"
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, filename)))

    def test_bulk_delete_by_titles(self):
        """Test deleting multiple notes by their titles."""
        titles_to_delete = ["Test Note 1", "Test Note 3", "Test Note 5"]
        
        # Delete multiple notes
        results = self.note_manager.bulk_delete_notes(titles_to_delete)
        
        # Check results
        self.assertEqual(len(results), 3)
        
        # Verify all specified notes were deleted
        for title in titles_to_delete:
            filename = title.lower().replace(" ", "-") + ".md"
            file_path = os.path.join(self.test_dir, filename)
            self.assertFalse(os.path.exists(file_path))
            
            # Check result message
            self.assertTrue(results[title].startswith("✓"))
            self.assertIn("deleted successfully", results[title])
        
        # Verify other notes still exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "test-note-2.md")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "test-note-4.md")))

    def test_bulk_delete_with_nonexistent_notes(self):
        """Test bulk deleting with a mix of existing and nonexistent notes."""
        titles_to_delete = ["Test Note 1", "Nonexistent Note", "Test Note 4"]
        
        # Delete notes
        results = self.note_manager.bulk_delete_notes(titles_to_delete)
        
        # Check results
        self.assertEqual(len(results), 3)
        
        # Verify existing notes were deleted
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test-note-1.md")))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test-note-4.md")))
        
        # Check result messages
        self.assertTrue(results["Test Note 1"].startswith("✓"))
        self.assertTrue(results["Test Note 4"].startswith("✓"))
        self.assertTrue(results["Nonexistent Note"].startswith("✗"))
        self.assertIn("not found", results["Nonexistent Note"])

    def test_delete_note_with_versioning(self):
        """Test that version control is respected when deleting a note."""
        # Create a NoteManager with version control enabled
        note_manager_with_versioning = NoteManager(notes_dir=self.test_dir, enable_version_control=True)
        
        # Mock the version_manager to check if version is created
        note_manager_with_versioning.version_manager.save_version = mock.MagicMock(return_value="v1_test")
        
        # Delete a note
        success, message = note_manager_with_versioning.delete_note("Test Note 1")
        
        # Verify success
        self.assertTrue(success)
        
        # Check that version_manager.save_version was called
        note_manager_with_versioning.version_manager.save_version.assert_called_once()
        
        # Verify the note was actually deleted
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test-note-1.md")))

    def test_delete_note_in_category(self):
        """Test deleting a note in a category."""
        # Create a note in a category
        category = "work"
        title = "Categorized Note"
        self._create_test_note(title, ["work", "test"], category)
        
        # Delete the note
        success, message = self.note_manager.delete_note(title, category=category)
        
        # Verify success
        self.assertTrue(success)
        
        # Verify the note was deleted
        filename = title.lower().replace(" ", "-") + ".md"
        file_path = os.path.join(self.test_dir, category, filename)
        self.assertFalse(os.path.exists(file_path))