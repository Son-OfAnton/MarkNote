"""
Tests for the bulk tag rename functionality in NoteManager.
"""
import os
import shutil
import tempfile
from unittest import TestCase, mock
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.note_manager import NoteManager
from app.models.note import Note
from app.utils.file_handler import write_note_file, read_note_file


class TestBulkRenameTags(TestCase):
    """Test cases for bulk tag rename functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create a NoteManager with the test directory
        self.note_manager = NoteManager(notes_dir=self.test_dir, enable_version_control=False)
        
        # Create some test notes
        self.test_notes = [
            {"title": "Test Note 1", "tags": ["development", "python", "project"]},
            {"title": "Test Note 2", "tags": ["development", "javascript"]},
            {"title": "Test Note 3", "tags": ["meeting", "project"]},
            {"title": "Test Note 4", "tags": ["personal", "python"]},
            {"title": "Test Note 5", "tags": ["development", "python", "meeting"]},
        ]
        
        # Add notes to the test directory
        for note_data in self.test_notes:
            self._create_test_note(note_data["title"], note_data["tags"])

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def _create_test_note(self, title: str, tags: List[str], 
                         category: Optional[str] = None, content: str = "Test content") -> str:
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

    def _read_note_tags(self, title: str, category: Optional[str] = None) -> List[str]:
        """Read the tags from a note file."""
        # Generate note filename
        filename = title.lower().replace(" ", "-") + ".md"
        
        # Determine the correct path
        file_path = os.path.join(self.test_dir, category or "", filename)
        
        # Read the note file
        metadata, _ = read_note_file(file_path)
        
        return metadata.get("tags", [])

    def test_bulk_rename_tag_basic(self):
        """Test renaming a tag across multiple notes."""
        old_tag = "python"
        new_tag = "python3"
        
        # Call the method to rename tags
        results = self.note_manager.bulk_rename_tag(old_tag, new_tag)
        
        # Check the results
        self.assertEqual(len(results), 3)  # Should affect 3 notes that have "python" tag
        
        # Verify each affected note's tags were updated
        for title in ["Test Note 1", "Test Note 4", "Test Note 5"]:
            tags = self._read_note_tags(title)
            self.assertIn(new_tag, tags)
            self.assertNotIn(old_tag, tags)
            self.assertTrue(results[title].startswith("✓"))
            
        # Verify unaffected notes weren't changed
        for title in ["Test Note 2", "Test Note 3"]:
            tags = self._read_note_tags(title)
            self.assertNotIn(new_tag, tags)
            self.assertEqual(title not in results, True)

    def test_rename_tag_with_filter_tags_OR_logic(self):
        """Test renaming tags only in notes that have specific filter tags (OR logic)."""
        old_tag = "python"
        new_tag = "python3"
        filter_tags = ["meeting"]  # Only rename python to python3 in notes with "meeting" tag
        
        # Call the method with filter tags
        results = self.note_manager.bulk_rename_tag(old_tag, new_tag, filter_tags=filter_tags)
        
        # Check results
        self.assertEqual(len(results), 1)  # Only Note 5 has both "python" AND "meeting" tags
        
        # Verify affected note was updated
        tags = self._read_note_tags("Test Note 5")
        self.assertIn(new_tag, tags)
        self.assertNotIn(old_tag, tags)
        self.assertTrue(results["Test Note 5"].startswith("✓"))
        
        # Verify other notes with python tag weren't changed
        for title in ["Test Note 1", "Test Note 4"]:
            tags = self._read_note_tags(title)
            self.assertIn(old_tag, tags)
            self.assertNotIn(new_tag, tags)
            self.assertEqual(title not in results, True)

    def test_rename_tag_with_filter_tags_AND_logic(self):
        """Test renaming tags only in notes that have ALL specified filter tags (AND logic)."""
        old_tag = "development"
        new_tag = "dev"
        filter_tags = ["python", "project"]  # Only in notes with BOTH python AND project tags
        
        # Call the method with filter tags and AND logic
        results = self.note_manager.bulk_rename_tag(old_tag, new_tag, 
                                                  filter_tags=filter_tags, 
                                                  all_filter_tags=True)
        
        # Check results
        self.assertEqual(len(results), 1)  # Only Note 1 has all three tags
        
        # Verify affected note was updated
        tags = self._read_note_tags("Test Note 1")
        self.assertIn(new_tag, tags)
        self.assertNotIn(old_tag, tags)
        self.assertTrue(results["Test Note 1"].startswith("✓"))
        
        # Verify other notes with development tag weren't changed
        for title in ["Test Note 2", "Test Note 5"]:
            tags = self._read_note_tags(title)
            self.assertIn(old_tag, tags)
            self.assertNotIn(new_tag, tags)
            self.assertEqual(title not in results, True)

    def test_rename_nonexistent_tag(self):
        """Test renaming a tag that doesn't exist in any notes."""
        old_tag = "nonexistent"
        new_tag = "something"
        
        # Call the method
        results = self.note_manager.bulk_rename_tag(old_tag, new_tag)
        
        # Check results
        self.assertEqual(len(results), 0)  # No notes should be affected
        
        # Verify no notes were changed
        for note_data in self.test_notes:
            tags = self._read_note_tags(note_data["title"])
            self.assertEqual(set(tags), set(note_data["tags"]))

    def test_rename_tag_with_category_filter(self):
        """Test renaming tags only in notes of a specific category."""
        # Create notes in a category
        category = "work"
        self._create_test_note("Work Note 1", ["python", "work"], category)
        self._create_test_note("Work Note 2", ["javascript", "work"], category)
        
        old_tag = "python"
        new_tag = "python3"
        
        # Call the method with category filter
        results = self.note_manager.bulk_rename_tag(old_tag, new_tag, category=category)
        
        # Check results
        self.assertEqual(len(results), 1)  # Only "Work Note 1" has the python tag in work category
        
        # Verify affected note was updated
        tags = self._read_note_tags("Work Note 1", category)
        self.assertIn(new_tag, tags)
        self.assertNotIn(old_tag, tags)
        self.assertTrue(results["Work Note 1"].startswith("✓"))
        
        # Verify notes outside the category weren't changed
        for title in ["Test Note 1", "Test Note 4", "Test Note 5"]:
            tags = self._read_note_tags(title)
            self.assertIn(old_tag, tags)
            self.assertNotIn(new_tag, tags)

    def test_rename_tag_with_versioning(self):
        """Test that version control is respected when renaming tags."""
        # Create a NoteManager with version control enabled
        note_manager_with_versioning = NoteManager(notes_dir=self.test_dir, enable_version_control=True)
        
        # Mock the version_manager to check if version is created
        note_manager_with_versioning.version_manager.save_version = mock.MagicMock(return_value="v1_test")
        note_manager_with_versioning.version_manager.generate_note_id = mock.MagicMock(return_value="note_id")
        
        old_tag = "python"
        new_tag = "python3"
        
        # Call the method to rename tags
        results = note_manager_with_versioning.bulk_rename_tag(old_tag, new_tag)
        
        # Check that version_manager.save_version was called for each affected note
        self.assertEqual(note_manager_with_versioning.version_manager.save_version.call_count, 3)
        
        # Verify each affected note's tags were updated
        for title in ["Test Note 1", "Test Note 4", "Test Note 5"]:
            tags = self._read_note_tags(title)
            self.assertIn(new_tag, tags)
            self.assertNotIn(old_tag, tags)

    def test_rename_tag_to_existing_tag(self):
        """Test renaming a tag to another tag that already exists in the note."""
        # Create a note with both tags already
        title = "Duplicate Tags Note"
        tags = ["python", "py", "code"]
        self._create_test_note(title, tags)
        
        old_tag = "python"
        new_tag = "py"  # Already exists in the note
        
        # Call the method
        results = self.note_manager.bulk_rename_tag(old_tag, new_tag)
        
        # Check that the note was processed
        self.assertIn(title, results)
        
        # Verify tags were updated correctly (python removed, py still exists)
        updated_tags = self._read_note_tags(title)
        self.assertNotIn(old_tag, updated_tags)
        self.assertIn(new_tag, updated_tags)
        self.assertEqual(len(updated_tags), 2)  # python removed, py remains (no duplicate)