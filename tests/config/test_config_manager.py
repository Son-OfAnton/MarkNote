"""
Unit tests for the daily note CLI commands.

These tests focus on the CLI commands for creating and managing daily notes.
"""
import os
import tempfile
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from app.cli.commands import cli
from app.core.daily_note_service import DailyNoteService


class TestDailyCommandsFunctionality:
    """Test case for testing the daily note CLI commands."""

    @pytest.fixture
    def runner(self):
        """Provide a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for test notes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_daily_command_creates_note(self, runner, temp_notes_dir):
        """Test that 'daily' command creates a new daily note."""
        # Act
        result = runner.invoke(
            cli, ["daily", "--output-dir", temp_notes_dir, "--no-edit"],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Success" in result.output, "Output should indicate success"
        
        # Verify a note was created in the directory
        daily_dir = os.path.join(temp_notes_dir, "daily")
        assert os.path.exists(daily_dir), "Daily category directory should be created"
        
        # There should be at least one markdown file in the daily directory
        files = [f for f in os.listdir(daily_dir) if f.endswith(".md")]
        assert len(files) > 0, "At least one markdown file should be created"

    def test_daily_command_with_specific_date(self, runner, temp_notes_dir):
        """Test 'daily' command with a specific date."""
        # Arrange
        test_date = (date.today() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Act
        result = runner.invoke(
            cli, ["daily", "--date", test_date, "--output-dir", temp_notes_dir, "--no-edit"],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        assert "Success" in result.output, "Output should indicate success"
        assert test_date in result.output, f"Output should mention the date {test_date}"
        
        # Verify the note file exists and contains the date
        daily_dir = os.path.join(temp_notes_dir, "daily")
        files = [f for f in os.listdir(daily_dir) if f.endswith(".md")]
        assert len(files) > 0, "At least one markdown file should be created"
        
        # Check the content of the file
        with open(os.path.join(daily_dir, files[0]), 'r') as f:
            content = f.read()
            assert test_date in content, f"Note content should include the date {test_date}"

    def test_daily_command_with_custom_category(self, runner, temp_notes_dir):
        """Test 'daily' command with a custom category."""
        # Arrange
        category = "journal"
        
        # Act
        result = runner.invoke(
            cli, ["daily", "--category", category, "--output-dir", temp_notes_dir, "--no-edit"],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Verify the note was created in the correct category
        category_dir = os.path.join(temp_notes_dir, category)
        assert os.path.exists(category_dir), f"Category directory {category} should be created"
        
        # There should be at least one markdown file in the category directory
        files = [f for f in os.listdir(category_dir) if f.endswith(".md")]
        assert len(files) > 0, f"At least one markdown file should be created in {category} category"

    def test_daily_command_with_tags(self, runner, temp_notes_dir):
        """Test 'daily' command with custom tags."""
        # Arrange
        tags = "daily,important,work"
        
        # Act
        result = runner.invoke(
            cli, ["daily", "--tags", tags, "--output-dir", temp_notes_dir, "--no-edit"],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Verify the note file exists and contains the tags
        daily_dir = os.path.join(temp_notes_dir, "daily")
        files = [f for f in os.listdir(daily_dir) if f.endswith(".md")]
        
        # Check the content of the file
        with open(os.path.join(daily_dir, files[0]), 'r') as f:
            content = f.read()
            for tag in tags.split(","):
                assert tag in content, f"Note content should include tag {tag}"

    def test_daily_command_with_template(self, runner, temp_notes_dir):
        """Test 'daily' command with custom template."""
        # Arrange - we'll use 'journal' template since it should exist
        template = "journal"
        
        # Act
        result = runner.invoke(
            cli, ["daily", "--template", template, "--output-dir", temp_notes_dir, "--no-edit"],
            catch_exceptions=False
        )
        
        # Assert - if the template doesn't exist, the command will fail
        # This is a basic check that the parameter is accepted
        assert result.exit_code == 0, f"Command failed with output: {result.output}"

    def test_today_command_no_existing_note(self, runner, temp_notes_dir):
        """Test 'today' command when no daily note exists."""
        # Mock the click.confirm to always return False (don't create note)
        with patch('app.cli.commands.click.confirm', return_value=False):
            # Act
            result = runner.invoke(
                cli, ["today", "--output-dir", temp_notes_dir],
                catch_exceptions=False
            )
            
            # Assert
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "No daily note exists" in result.output, "Output should indicate no note exists"
            
            # Verify no note was created
            daily_dir = os.path.join(temp_notes_dir, "daily")
            if os.path.exists(daily_dir):
                files = [f for f in os.listdir(daily_dir) if f.endswith(".md")]
                assert len(files) == 0, "No files should be created when user chooses not to create"

    def test_today_command_with_existing_note(self, runner, temp_notes_dir):
        """Test 'today' command when daily note exists."""
        # First create a daily note
        create_result = runner.invoke(
            cli, ["daily", "--output-dir", temp_notes_dir, "--no-edit"],
            catch_exceptions=False
        )
        assert create_result.exit_code == 0, "Failed to create initial note"
        
        # Mock the click.confirm to always return False (don't open note)
        with patch('app.cli.commands.click.confirm', return_value=False):
            # Act
            result = runner.invoke(
                cli, ["today", "--output-dir", temp_notes_dir],
                catch_exceptions=False
            )
            
            # Assert
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "Today's Daily Note" in result.output, "Output should show note info"
            today_str = date.today().strftime("%Y-%m-%d")
            assert today_str in result.output, f"Output should include today's date {today_str}"

    def test_config_daily_command_display(self, runner):
        """Test 'config daily' command displays current settings."""
        # Mock the configuration
        mock_config = {
            "template": "daily",
            "category": "daily",
            "auto_open": True,
            "default_tags": ["daily"],
            "title_format": "Daily Note: {date} ({day})"
        }
        
        with patch('app.cli.commands.get_config_manager') as mock_get_config:
            # Setup the mock to return our config
            mock_config_instance = MagicMock()
            mock_config_instance.get_daily_note_config.return_value = mock_config
            mock_get_config.return_value = mock_config_instance
            
            # Act
            result = runner.invoke(cli, ["config", "daily"], catch_exceptions=False)
            
            # Assert
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "Current Daily Note Configuration" in result.output, "Output should show config"
            assert "Template: daily" in result.output, "Output should show template setting"
            assert "Category: daily" in result.output, "Output should show category setting"
            assert "Auto-open: True" in result.output, "Output should show auto-open setting"

    def test_config_daily_command_update(self, runner):
        """Test 'config daily' command updates settings."""
        # Mock the configuration
        with patch('app.cli.commands.get_config_manager') as mock_get_config:
            # Setup the mock
            mock_config_instance = MagicMock()
            mock_config_instance.get_daily_note_config.return_value = {
                "template": "daily",
                "category": "daily",
                "auto_open": True
            }
            mock_config_instance.save_config.return_value = True
            mock_get_config.return_value = mock_config_instance
            
            # Act - update template and auto-open
            result = runner.invoke(
                cli, ["config", "daily", "--template", "journal", "--no-auto-open"],
                catch_exceptions=False
            )
            
            # Assert
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            
            # Verify set_config was called with correct parameters
            mock_config_instance.set_config.assert_any_call("daily_notes", "template", "journal")
            mock_config_instance.set_config.assert_any_call("daily_notes", "auto_open", False)
            
            # Verify save_config was called
            mock_config_instance.save_config.assert_called_once()