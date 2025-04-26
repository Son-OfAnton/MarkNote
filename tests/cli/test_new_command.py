import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.core.note_manager import NoteManager
from app.utils.file_handler import parse_frontmatter


class TestNewCommandOptions(unittest.TestCase):
    """Test the options of the 'new' command for creating notes."""
    
    def setUp(self):
        """Set up a temporary directory for the test notes."""
        # Create a temporary directory for test notes
        self.temp_dir = tempfile.mkdtemp()
        self.note_manager = NoteManager(notes_dir=self.temp_dir)
        
        # Create a custom output directory for testing
        self.custom_output_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up the temporary directories after tests."""
        # Remove the temporary directories and their contents
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.custom_output_dir)
    
    def test_new_with_template(self):
        """Test creating a note with a specific template."""
        # Create a note with the meeting template
        title = "Team Meeting"
        note = self.note_manager.create_note(
            title=title,
            template_name="meeting"
        )
        
        # Check the note has the correct title
        self.assertEqual(note.title, title)
        
        # Read the file content and check it contains meeting template elements
        with open(note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that the content includes meeting-specific elements
        self.assertIn("Meeting Details", content)
        self.assertIn("Agenda", content)
        self.assertIn("Action Items", content)
        
        # Parse the frontmatter and check type is meeting
        frontmatter, _ = parse_frontmatter(content)
        self.assertEqual(frontmatter.get('type'), "meeting")
    
    def test_new_with_journal_template(self):
        """Test creating a note with the journal template."""
        # Create a note with the journal template
        title = "Today's Journal Entry"
        note = self.note_manager.create_note(
            title=title,
            template_name="journal"
        )
        
        # Read the file content
        with open(note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check journal-specific elements
        self.assertIn("Today's Highlights", content)
        self.assertIn("Thoughts and Reflections", content)
        self.assertIn("Gratitude", content)
        
        # Parse the frontmatter and check type is journal
        frontmatter, _ = parse_frontmatter(content)
        self.assertEqual(frontmatter.get('type'), "journal")
    
    def test_new_with_tags(self):
        """Test creating a note with tags."""
        # Create a note with tags
        title = "Tagged Note"
        tags = ["work", "important", "meeting"]
        note = self.note_manager.create_note(
            title=title,
            tags=tags
        )
        
        # Check the note object has the correct tags
        self.assertEqual(note.tags, tags)
        
        # Read the file content
        with open(note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the frontmatter
        frontmatter, _ = parse_frontmatter(content)
        
        # Check that the tags in frontmatter match
        self.assertEqual(frontmatter.get('tags'), tags)
    
    def test_new_with_category(self):
        """Test creating a note with a category."""
        # Create a note with a category
        title = "Categorized Note"
        category = "work"
        note = self.note_manager.create_note(
            title=title,
            category=category
        )
        
        # Check the note object has the correct category
        self.assertEqual(note.category, category)
        
        # Check that the file is created in the category directory
        category_dir = os.path.join(self.temp_dir, category)
        self.assertTrue(os.path.exists(category_dir))
        
        # Check that the note file is in the category directory
        expected_path = os.path.join(category_dir, "categorized-note.md")
        self.assertTrue(os.path.exists(expected_path))
        
        # Check that the path in metadata matches
        self.assertEqual(note.metadata['path'], expected_path)
        
        # Read the file content
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the frontmatter
        frontmatter, _ = parse_frontmatter(content)
        
        # Check that the category in frontmatter matches
        self.assertEqual(frontmatter.get('category'), category)
    
    def test_new_with_output_dir(self):
        """Test creating a note with a custom output directory."""
        # Create a note with custom output directory
        title = "Custom Location Note"
        note = self.note_manager.create_note(
            title=title,
            output_dir=self.custom_output_dir
        )
        
        # Check that the file is created in the custom directory
        expected_path = os.path.join(self.custom_output_dir, "custom-location-note.md")
        self.assertTrue(os.path.exists(expected_path))
        
        # Check that the path in metadata matches
        self.assertEqual(note.metadata['path'], expected_path)
    
    def test_new_with_category_and_output_dir(self):
        """Test creating a note with both category and custom output directory."""
        # Create a note with both category and output directory
        title = "Specific Location Note"
        category = "projects"
        note = self.note_manager.create_note(
            title=title,
            category=category,
            output_dir=self.custom_output_dir
        )
        
        # Check that the category directory is created in the custom output directory
        category_dir = os.path.join(self.custom_output_dir, category)
        self.assertTrue(os.path.exists(category_dir))
        
        # Check that the note file is in the custom category directory
        expected_path = os.path.join(category_dir, "specific-location-note.md")
        self.assertTrue(os.path.exists(expected_path))
        
        # Check that the path in metadata matches
        self.assertEqual(note.metadata['path'], expected_path)
    
    def test_new_with_additional_metadata(self):
        """Test creating a note with additional metadata."""
        # Create a meeting note with additional metadata
        title = "Meeting with Additional Metadata"
        additional_metadata = {
            "meeting_date": "2023-05-01",
            "meeting_time": "10:00 AM",
            "location": "Conference Room A",
            "attendees": "Alice, Bob, Charlie"
        }
        
        note = self.note_manager.create_note(
            title=title,
            template_name="meeting",
            additional_metadata=additional_metadata
        )
        
        # Read the file content
        with open(note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the frontmatter
        frontmatter, content_without_frontmatter = parse_frontmatter(content)
        
        # Check that the frontmatter contains the additional metadata
        for key, value in additional_metadata.items():
            self.assertEqual(frontmatter.get(key), value)
        
        # Check that the additional metadata is inserted into the template
        self.assertIn(additional_metadata["meeting_date"], content_without_frontmatter)
        self.assertIn(additional_metadata["meeting_time"], content_without_frontmatter)
        self.assertIn(additional_metadata["location"], content_without_frontmatter)
        self.assertIn(additional_metadata["attendees"], content_without_frontmatter)
    
    def test_new_with_custom_content(self):
        """Test creating a note with custom content instead of using a template."""
        # Create a note with custom content
        title = "Custom Content Note"
        custom_content = "# My Custom Note\n\nThis is a custom note with my own content.\n\n## Section 1\n\nSome section content."
        
        note = self.note_manager.create_note(
            title=title,
            content=custom_content
        )
        
        # Read the file content
        with open(note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the frontmatter
        _, content_without_frontmatter = parse_frontmatter(content)
        
        # Check that the content matches the custom content
        self.assertEqual(content_without_frontmatter, custom_content)
    
    def test_new_with_all_options(self):
        """Test creating a note using all available options together."""
        # Create a note with all available options
        title = "Complete Test Note"
        tags = ["test", "comprehensive"]
        category = "tests"
        additional_metadata = {"priority": "high", "status": "draft"}
        custom_content = "This is a fully customized note for testing purposes."
        
        note = self.note_manager.create_note(
            title=title,
            template_name="default",
            content=custom_content,
            tags=tags,
            category=category,
            additional_metadata=additional_metadata,
            output_dir=self.custom_output_dir
        )
        
        # Check that all properties are set correctly on the note object
        self.assertEqual(note.title, title)
        self.assertEqual(note.tags, tags)
        self.assertEqual(note.category, category)
        self.assertEqual(note.content, custom_content)
        
        # Check that the file is in the correct location
        expected_path = os.path.join(self.custom_output_dir, category, "complete-test-note.md")
        self.assertTrue(os.path.exists(expected_path))
        
        # Read the file content
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the frontmatter
        frontmatter, content_without_frontmatter = parse_frontmatter(content)
        
        # Check that all metadata is present in the frontmatter
        self.assertEqual(frontmatter.get('title'), title)
        self.assertEqual(frontmatter.get('tags'), tags)
        self.assertEqual(frontmatter.get('category'), category)
        self.assertEqual(frontmatter.get('priority'), additional_metadata["priority"])
        self.assertEqual(frontmatter.get('status'), additional_metadata["status"])
        
        # Check that the content includes the custom content
        self.assertEqual(content_without_frontmatter, custom_content)


if __name__ == '__main__':
    unittest.main()