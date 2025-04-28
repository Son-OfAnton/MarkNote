"""
Unit tests for the DailyNoteService.

These tests focus on testing the service layer functionality for daily notes,
which includes configuration handling and business logic.
"""
import os
import tempfile
import pytest
from datetime import datetime, date, timedelta
import shutil
from unittest.mock import patch, MagicMock

from app.core.daily_note_service import DailyNoteService, get_daily_note_service
from app.config.config_manager import get_daily_note_config


class TestDailyNoteService:
    """Test case for testing the DailyNoteService."""

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for test notes."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return {
            "enabled": True,
            "template": "daily",
            "category": "daily",
            "default_tags": ["daily", "test"],
            "title_format": "Daily Note: {date} ({day})",
            "auto_open": False  # Disable auto-open for tests
        }
    
    @pytest.fixture
    def daily_service(self, temp_notes_dir, mock_config):
        """Create a DailyNoteService instance for testing."""
        with patch('app.services.daily_note_service.get_daily_note_config', return_value=mock_config):
            service = DailyNoteService()
            # Set notes_dir on the underlying note_manager
            service.note_manager.notes_dir = temp_notes_dir
            return service
    
    def test_service_initialization(self, daily_service, mock_config):
        """Test that the service initializes with the correct configuration."""
        assert daily_service.config == mock_config, "Service should initialize with the provided config"
    
    def test_get_or_create_todays_note_new(self, daily_service):
        """Test getting today's note when it doesn't exist (creates a new one)."""
        # Act
        exists, message, note = daily_service.get_or_create_todays_note()
        
        # Assert
        assert not exists, "Should report that note doesn't exist initially"
        assert note is not None, "Should create and return a new note"
        assert "daily" in note.tags, "Note should have 'daily' tag"
        assert note.category == "daily", "Note should have correct category from config"
    
    def test_get_or_create_todays_note_existing(self, daily_service):
        """Test getting today's note when it already exists."""
        # Arrange - create a note first
        daily_service.create_note_for_date()
        
        # Act
        exists, message, note = daily_service.get_or_create_todays_note()
        
        # Assert
        assert exists, "Should report that note exists"
        assert note is not None, "Should return the existing note"
        assert "already exists" in message.lower(), "Message should indicate note already exists"
    
    def test_create_note_for_date_with_custom_category(self, daily_service):
        """Test creating a note with a custom category that overrides config."""
        # Arrange
        custom_category = "custom_category"
        
        # Act
        success, message, note = daily_service.create_note_for_date(category=custom_category)
        
        # Assert
        assert success, "Should successfully create the note"
        assert note.category == custom_category, f"Note should have custom category {custom_category}"
    
    def test_create_note_for_date_with_custom_template(self, daily_service):
        """Test creating a note with a custom template that overrides config."""
        # This test requires mocking the template rendering since we don't have actual template files
        # For simplicity, we'll just check that the template name is passed correctly to create_daily_note
        
        # Arrange
        custom_template = "custom_template"
        
        # Mock the create_daily_note method to capture the template_name parameter
        with patch.object(daily_service.note_manager, 'create_daily_note', 
                          return_value=(True, "Success", MagicMock())) as mock_create:
            
            # Act
            success, message, note = daily_service.create_note_for_date(template_name=custom_template)
            
            # Assert
            mock_create.assert_called_once()
            # Check that the template_name parameter was passed correctly
            args, kwargs = mock_create.call_args
            assert kwargs.get('template_name') == custom_template, \
                f"Expected template_name={custom_template}, got {kwargs.get('template_name')}"
    
    def test_create_note_for_date_specific_date(self, daily_service):
        """Test creating a note for a specific date."""
        # Arrange
        test_date = (date.today() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Act
        success, message, note = daily_service.create_note_for_date(date_str=test_date)
        
        # Assert
        assert success, f"Failed to create note for {test_date}: {message}"
        assert note.metadata.get('date') == test_date, \
            f"Note should have date {test_date}, got {note.metadata.get('date')}"
    
    def test_create_note_for_date_with_force(self, daily_service):
        """Test force-creating a note for a date that already has one."""
        # Arrange - create a note first
        test_date = date.today().strftime("%Y-%m-%d")
        first_result = daily_service.create_note_for_date(date_str=test_date)
        assert first_result[0], f"Failed to create initial note: {first_result[1]}"
        
        # Act - create another note with force=True
        success, message, note = daily_service.create_note_for_date(date_str=test_date, force=True)
        
        # Assert
        assert success, f"Failed to force-create note: {message}"
        assert note is not None, "Should create and return a new note"
        
        # Verify this is actually a new note (would have a different file path)
        assert note.metadata.get('path') != first_result[2].metadata.get('path'), \
            "Forced note creation should create a new note, not return the existing one"
    
    def test_get_daily_note_service_singleton(self):
        """Test that get_daily_note_service returns the same instance each time."""
        # Act
        service1 = get_daily_note_service()
        service2 = get_daily_note_service()
        
        # Assert
        assert service1 is service2, "get_daily_note_service should return the same instance each time"