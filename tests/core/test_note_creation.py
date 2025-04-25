"""
Unit test for the note creation functionality.
Tests the basic file creation functionality of NoteManager.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from app.core.note_manager import NoteManager
from app.models.note import Note


class TestNoteCreation:
    """Test case for the note creation functionality."""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for test notes."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)

    def test_create_note_with_title_only(self, temp_notes_dir):
        """Test creating a note with just a title."""
        # Arrange
        note_manager = NoteManager(notes_dir=temp_notes_dir)
        title = "Test Note Title"
        expected_filename = "test-note-title.md"
        
        # Act
        note = note_manager.create_note(title=title)
        
        # Assert
        # Check that a Note object was returned
        assert isinstance(note, Note)
        assert note.title == title
        
        # Check that file was created with the expected name
        expected_path = os.path.join(temp_notes_dir, expected_filename)
        assert os.path.exists(expected_path)
        
        # Check that the file contains the title
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert title in content
        
        # Check note path in metadata
        assert 'path' in note.metadata
        assert note.metadata['path'] == expected_path
    
    def test_create_note_file_exists(self, temp_notes_dir):
        """Test that an exception is raised when trying to create a note with a title that already exists."""
        # Arrange
        note_manager = NoteManager(notes_dir=temp_notes_dir)
        title = "Duplicate Note"
        
        # Create the note first time
        note_manager.create_note(title=title)
        
        # Act & Assert
        # Attempt to create the same note again should raise an exception
        with pytest.raises(FileExistsError):
            note_manager.create_note(title=title)

    def test_note_content_has_frontmatter(self, temp_notes_dir):
        """Test that the created note file includes YAML frontmatter."""
        # Arrange
        note_manager = NoteManager(notes_dir=temp_notes_dir)
        title = "Frontmatter Test"
        
        # Act
        note = note_manager.create_note(title=title)
        
        # Assert
        # Get the path to the created file
        note_path = note.metadata['path']
        assert os.path.exists(note_path)
        
        # Read the file content
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for frontmatter delimiters
        assert content.startswith('---')
        assert '---\n\n' in content
        
        # Check for basic frontmatter fields
        assert f'title: {title}' in content
        assert 'created_at:' in content
        assert 'updated_at:' in content

    def test_create_note_template_applied(self, temp_notes_dir):
        """Test that the default template is applied when creating a note."""
        # Arrange
        note_manager = NoteManager(notes_dir=temp_notes_dir)
        title = "Template Test"
        
        # Act
        note = note_manager.create_note(title=title)
        
        # Assert
        # Get the path to the created file
        note_path = note.metadata['path']
        
        # Read the file content
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for template components (assuming default template)
        # This may need adjustment based on your actual default template
        assert '# Template Test' in content
        assert '## Overview' in content
        assert '## Details' in content
        assert '## Conclusion' in content