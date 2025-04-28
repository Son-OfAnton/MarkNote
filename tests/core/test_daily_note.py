"""
Unit tests for the daily note functionality in the NoteManager.

These tests focus on testing the core functionality of the daily note features
including creation, finding, and retrieving daily notes.
"""
import os
import tempfile
import pytest
from datetime import datetime, date, timedelta
import shutil
import yaml

from app.core.note_manager import NoteManager


class TestDailyNoteFunctionality:
    """Test case for testing the daily note functionality in NoteManager."""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for test notes."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def note_manager(self, temp_notes_dir):
        """Create a NoteManager instance for testing."""
        return NoteManager(notes_dir=temp_notes_dir)
    
    def test_create_daily_note(self, note_manager, temp_notes_dir):
        """Test creating a daily note for today."""
        # Act
        success, message, note = note_manager.create_daily_note()
        
        # Assert
        assert success, f"Failed to create daily note: {message}"
        assert note is not None, "Note should not be None"
        
        # Verify the note has correct title format
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        day_name = today.strftime("%A")
        expected_title = f"Daily Note: {today_str} ({day_name})"
        assert note.title == expected_title, f"Expected title {expected_title}, got {note.title}"
        
        # Verify the note has the daily tag
        assert "daily" in note.tags, "Note should have 'daily' tag"
        
        # Verify the note is in the daily category
        assert note.category == "daily", f"Expected category 'daily', got {note.category}"
        
        # Verify the note was created in the correct location
        expected_path = os.path.join(temp_notes_dir, "daily")
        assert os.path.exists(expected_path), f"Category directory {expected_path} doesn't exist"
        
        # Verify the content uses the daily template
        note_path = note.metadata.get('path')
        assert note_path is not None, "Note path should be in metadata"
        assert os.path.exists(note_path), f"Note file {note_path} doesn't exist"
        
        # Read the file and check its contents
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "## Tasks for Today" in content, "Content should include daily template sections"
        assert "## Daily Journal" in content, "Content should include daily template sections"
    
    def test_create_daily_note_specific_date(self, note_manager):
        """Test creating a daily note for a specific date."""
        # Arrange
        test_date = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        # Act
        success, message, note = note_manager.create_daily_note(date_str=test_date)
        
        # Assert
        assert success, f"Failed to create daily note for {test_date}: {message}"
        assert note is not None, "Note should not be None"
        
        # Verify the note has correct title format
        day_name = datetime.strptime(test_date, "%Y-%m-%d").strftime("%A")
        expected_title = f"Daily Note: {test_date} ({day_name})"
        assert note.title == expected_title, f"Expected title {expected_title}, got {note.title}"
        
        # Verify the date is stored in the metadata
        assert note.metadata.get('date') == test_date, f"Expected date {test_date}, got {note.metadata.get('date')}"
    
    def test_create_daily_note_with_custom_category(self, note_manager, temp_notes_dir):
        """Test creating a daily note with a custom category."""
        # Arrange
        category = "journal"
        
        # Act
        success, message, note = note_manager.create_daily_note(category=category)
        
        # Assert
        assert success, f"Failed to create daily note: {message}"
        assert note.category == category, f"Expected category {category}, got {note.category}"
        
        # Verify the note was created in the correct location
        expected_path = os.path.join(temp_notes_dir, category)
        assert os.path.exists(expected_path), f"Category directory {expected_path} doesn't exist"
    
    def test_create_daily_note_with_custom_tags(self, note_manager):
        """Test creating a daily note with custom tags."""
        # Arrange
        tags = ["daily", "important", "work"]
        
        # Act
        success, message, note = note_manager.create_daily_note(tags=tags)
        
        # Assert
        assert success, f"Failed to create daily note: {message}"
        
        # Verify all tags are present
        for tag in tags:
            assert tag in note.tags, f"Tag {tag} should be in note tags"
    
    def test_find_daily_note(self, note_manager):
        """Test finding a daily note after creation."""
        # Arrange - create a daily note
        success, message, created_note = note_manager.create_daily_note()
        assert success, f"Failed to create daily note: {message}"
        
        # Act - find the daily note
        found_note = note_manager.find_daily_note(date.today())
        
        # Assert
        assert found_note is not None, "Should find the daily note"
        assert found_note.title == created_note.title, "Found note should match created note"
    
    def test_find_daily_note_nonexistent(self, note_manager):
        """Test finding a daily note that doesn't exist."""
        # Arrange - use a date in the past
        test_date = date.today() - timedelta(days=10)
        
        # Act - try to find the note
        found_note = note_manager.find_daily_note(test_date)
        
        # Assert
        assert found_note is None, "Should not find a daily note for a non-existent date"
    
    def test_get_todays_daily_note_existing(self, note_manager):
        """Test getting today's daily note when it already exists."""
        # Arrange - create a daily note for today
        success, message, created_note = note_manager.create_daily_note()
        assert success, f"Failed to create daily note: {message}"
        
        # Act - get today's daily note
        exists, message, note = note_manager.get_todays_daily_note()
        
        # Assert
        assert exists, "Should report that note exists"
        assert note.title == created_note.title, "Retrieved note should match created note"
    
    def test_get_todays_daily_note_nonexistent(self, note_manager):
        """Test getting today's daily note when it doesn't exist."""
        # Act - get today's daily note
        exists, message, note = note_manager.get_todays_daily_note()
        
        # Assert
        assert not exists, "Should report that note doesn't exist"
        assert note is not None, "Should create and return a new note"
        assert "created" in message.lower(), "Message should indicate note was created"
    
    def test_create_daily_note_duplicate(self, note_manager):
        """Test trying to create a daily note for a date that already has one."""
        # Arrange - create a daily note
        success, message, created_note = note_manager.create_daily_note()
        assert success, f"Failed to create daily note: {message}"
        
        # Act - try to create another note for the same date
        success, message, note = note_manager.create_daily_note()
        
        # Assert
        assert not success, "Should report failure when trying to create duplicate"
        assert "already exists" in message.lower(), "Message should indicate note already exists"
        assert note is not None, "Should return the existing note"
        assert note.title == created_note.title, "Returned note should match existing note"
    
    def test_create_daily_note_invalid_date(self, note_manager):
        """Test creating a daily note with an invalid date format."""
        # Arrange
        invalid_date = "not-a-date"
        
        # Act
        success, message, note = note_manager.create_daily_note(date_str=invalid_date)
        
        # Assert
        assert not success, "Should report failure with invalid date"
        assert "invalid date format" in message.lower(), "Message should indicate invalid date format"
        assert note is None, "Note should be None"