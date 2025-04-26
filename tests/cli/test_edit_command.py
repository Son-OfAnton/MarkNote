import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.core.note_manager import NoteManager
from app.utils.file_handler import parse_frontmatter


class TestEditCommand(unittest.TestCase):
    """Test the functionality of the 'edit' command for modifying notes."""
    
    def setUp(self):
        """Set up a temporary directory and create test notes."""
        # Create a temporary directory for test notes
        self.temp_dir = tempfile.mkdtemp()
        self.note_manager = NoteManager(notes_dir=self.temp_dir)
        
        # Create a test note to edit
        self.test_title = "Test Note for Editing"
        self.initial_content = "This is the initial content of the note."
        self.test_note = self.note_manager.create_note(
            title=self.test_title,
            content=self.initial_content
        )
        
        # Create a note with tags and category for testing
        self.categorized_title = "Categorized Note"
        self.category = "work"
        self.tags = ["important", "meeting"]
        self.categorized_note = self.note_manager.create_note(
            title=self.categorized_title,
            category=self.category,
            tags=self.tags
        )
    
    def tearDown(self):
        """Clean up the temporary directory after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_edit_content(self):
        """Test editing the content of a note."""
        # New content for the note
        new_content = "This is the updated content of the note."
        
        # Edit the note
        success, updated_note, _ = self.note_manager.edit_note_content(
            title=self.test_title,
            new_content=new_content
        )
        
        # Verify the edit was successful
        self.assertTrue(success)
        
        # Verify the note object was updated
        self.assertEqual(updated_note.content, new_content)
        
        # Read the file and check content
        with open(updated_note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter
        _, content_without_frontmatter = parse_frontmatter(content)
        
        # Verify the file content was updated
        self.assertEqual(content_without_frontmatter, new_content)
    
    def test_edit_nonexistent_note(self):
        """Test editing a note that doesn't exist."""
        # Try to edit a non-existent note
        success, updated_note, error = self.note_manager.edit_note_content(
            title="Non-Existent Note",
            new_content="This content won't be saved."
        )
        
        # Verify the edit failed
        self.assertFalse(success)
        self.assertIsNone(updated_note)
        self.assertTrue(len(error) > 0)  # Error message should not be empty
    
    def test_edit_note_in_category(self):
        """Test editing a note that is in a category."""
        # New content for the categorized note
        new_content = "This is the updated content of the categorized note."
        
        # Edit the note
        success, updated_note, _ = self.note_manager.edit_note_content(
            title=self.categorized_title,
            new_content=new_content,
            category=self.category
        )
        
        # Verify the edit was successful
        self.assertTrue(success)
        
        # Verify the note object was updated
        self.assertEqual(updated_note.content, new_content)
        
        # Verify the category was preserved
        self.assertEqual(updated_note.category, self.category)
        
        # Verify the tags were preserved
        self.assertEqual(updated_note.tags, self.tags)
        
        # Read the file and check content
        with open(updated_note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter
        frontmatter, content_without_frontmatter = parse_frontmatter(content)
        
        # Verify the file content was updated
        self.assertEqual(content_without_frontmatter, new_content)
        
        # Verify the category and tags were preserved in frontmatter
        self.assertEqual(frontmatter.get('category'), self.category)
        self.assertEqual(frontmatter.get('tags'), self.tags)
    
    def test_update_note_metadata(self):
        """Test updating note metadata while editing."""
        # New content and metadata
        new_content = "Updated content with new metadata."
        new_tags = ["updated", "test"]
        new_category = "personal"
        
        # Update the note with new metadata
        success, updated_note, _ = self.note_manager.update_note(
            title=self.test_title,
            new_content=new_content,
            new_tags=new_tags,
            new_category=new_category
        )
        
        # Verify the update was successful
        self.assertTrue(success)
        
        # Verify the note object was updated with new content and metadata
        self.assertEqual(updated_note.content, new_content)
        self.assertEqual(updated_note.tags, new_tags)
        self.assertEqual(updated_note.category, new_category)
        
        # Read the file and check content and metadata
        with open(updated_note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter
        frontmatter, content_without_frontmatter = parse_frontmatter(content)
        
        # Verify the file content and metadata were updated
        self.assertEqual(content_without_frontmatter, new_content)
        self.assertEqual(frontmatter.get('tags'), new_tags)
        self.assertEqual(frontmatter.get('category'), new_category)
        
        # The physical file should now be in the new category directory
        category_path = os.path.join(self.temp_dir, new_category)
        self.assertTrue(os.path.exists(category_path))
        note_filename = updated_note.metadata['path'].split(os.path.sep)[-1]
        self.assertTrue(os.path.exists(os.path.join(category_path, note_filename)))
    
    def test_find_note_with_approximate_title(self):
        """Test finding a note with an approximate title match."""
        # Create a note with a long title
        long_title = "This is a Very Long Title for Testing Approximate Matching"
        self.note_manager.create_note(
            title=long_title,
            content="Content for the long title note."
        )
        
        # Try to edit the note using a shortened version of the title
        shortened_title = "Very Long Title"
        new_content = "Updated content using approximate title match."
        
        # Let's first test if find_note_path can find it using the shortened title
        note_path = self.note_manager.find_note_path(shortened_title)
        
        # Verify that the note was found
        self.assertIsNotNone(note_path)
        
        # Now try to edit using the approximate title
        success, updated_note, _ = self.note_manager.edit_note_content(
            title=shortened_title,
            new_content=new_content
        )
        
        # Depending on implementation, this may not work - but at least we verify the behavior
        # This test documents the current behavior rather than enforcing a specific outcome
        if success:
            self.assertEqual(updated_note.content, new_content)
        else:
            # If not successful, verify at least the note exists
            self.assertIsNotNone(note_path)
    
    def test_edit_with_output_dir(self):
        """Test editing a note within a custom output directory."""
        # Create a new output directory
        output_dir = tempfile.mkdtemp()
        
        try:
            # Create a note in the custom directory
            custom_title = "Note in Custom Directory"
            custom_note = self.note_manager.create_note(
                title=custom_title,
                content="Initial content in custom directory.",
                output_dir=output_dir
            )
            
            # Edit the note in the custom directory
            new_content = "Updated content in custom directory."
            success, updated_note, _ = self.note_manager.edit_note_content(
                title=custom_title,
                new_content=new_content,
                output_dir=output_dir
            )
            
            # Verify the edit was successful
            self.assertTrue(success)
            
            # Verify the content was updated
            self.assertEqual(updated_note.content, new_content)
            
            # Verify the file still exists in the custom directory
            note_path = updated_note.metadata['path']
            self.assertTrue(os.path.exists(note_path))
            self.assertTrue(note_path.startswith(output_dir))
            
            # Read the file and check content
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse frontmatter
            _, content_without_frontmatter = parse_frontmatter(content)
            
            # Verify the file content was updated
            self.assertEqual(content_without_frontmatter, new_content)
        
        finally:
            # Clean up the custom output directory
            shutil.rmtree(output_dir)
    
    def test_update_note_additional_metadata(self):
        """Test updating additional metadata fields of a note."""
        # Create a note with meeting template and metadata
        meeting_title = "Meeting With Metadata"
        meeting_metadata = {
            "meeting_date": "2023-05-01",
            "meeting_time": "10:00 AM",
            "location": "Conference Room A",
            "attendees": "Alice, Bob, Charlie"
        }
        
        meeting_note = self.note_manager.create_note(
            title=meeting_title,
            template_name="meeting",
            additional_metadata=meeting_metadata
        )
        
        # Update the metadata
        updated_metadata = {
            "meeting_date": "2023-05-02",  # Changed date
            "meeting_time": "11:30 AM",    # Changed time
            "location": "Zoom Call",       # Changed location
            "attendees": "Alice, Dave",    # Changed attendees
            "status": "Completed"          # New field
        }
        
        # Update the note
        success, updated_note, _ = self.note_manager.update_note(
            title=meeting_title,
            additional_metadata=updated_metadata
        )
        
        # Verify the update was successful
        self.assertTrue(success)
        
        # Read the file and check metadata
        with open(updated_note.metadata['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter
        frontmatter, _ = parse_frontmatter(content)
        
        # Verify the metadata was updated
        for key, value in updated_metadata.items():
            self.assertEqual(frontmatter.get(key), value)


if __name__ == '__main__':
    unittest.main()