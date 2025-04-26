import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.core.note_manager import NoteManager
from app.utils.file_handler import parse_frontmatter


class TestFileCreation(unittest.TestCase):
    """Test file creation functionality for the NoteManager."""
    
    def setUp(self):
        """Set up a temporary directory for the test notes."""
        # Create a temporary directory for test notes
        self.temp_dir = tempfile.mkdtemp()
        self.note_manager = NoteManager(notes_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up the temporary directory after tests."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def test_create_note_with_title_only(self):
        """Test creating a note with just a title."""
        # Create a note with just a title
        title = "Test Note Title"
        note = self.note_manager.create_note(title=title)
        
        # Check that the note object has the correct title
        self.assertEqual(note.title, title)
        
        # Get the expected file path
        expected_filename = "test-note-title.md"
        expected_path = os.path.join(self.temp_dir, expected_filename)
        
        # Check that the file exists
        self.assertTrue(os.path.exists(expected_path))
        
        # Check that the file path in note metadata matches the actual path
        self.assertEqual(note.metadata['path'], expected_path)
        
        # Read the file content and check frontmatter
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the frontmatter
        frontmatter, content_without_frontmatter = parse_frontmatter(content)
        
        # Check frontmatter contains correct title
        self.assertEqual(frontmatter.get('title'), title)
        
        # Check content includes the title as a header
        self.assertIn(f"# {title}", content_without_frontmatter)
    
    def test_create_duplicate_note(self):
        """Test that creating a duplicate note raises an exception."""
        # Create the first note
        title = "Duplicate Test"
        self.note_manager.create_note(title=title)
        
        # Try to create a second note with the same title
        with self.assertRaises(FileExistsError):
            self.note_manager.create_note(title=title)
    
    def test_file_path_matches_metadata(self):
        """Test that the file path in metadata matches the actual file path."""
        # Create a note
        title = "Path Test"
        note = self.note_manager.create_note(title=title)
        
        # Get the expected file path
        expected_path = os.path.join(self.temp_dir, "path-test.md")
        
        # Check that the file path in metadata matches the expected path
        self.assertEqual(note.metadata['path'], expected_path)
        
        # Verify that the file exists at this path
        self.assertTrue(os.path.isfile(expected_path))


if __name__ == '__main__':
    unittest.main()