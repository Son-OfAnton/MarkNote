"""
Tests for the 'marknote versions diff' command.
"""
import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock, call
from click.testing import CliRunner
from app.cli.commands import cli


class TestVersionsDiffCommand:
    """Tests for the 'marknote versions diff' command."""

    @pytest.fixture
    def runner(self):
        """Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_note_manager(self):
        """Create a mocked NoteManager."""
        with patch('app.cli.commands.create_note_manager') as mock_create_nm:
            # Mock the NoteManager instance
            mock_nm = MagicMock()
            mock_create_nm.return_value = mock_nm
            
            # Default behavior for diff_note_versions
            diff_lines = [
                "  # Title",
                "- Old content line",
                "+ New content line",
                "  Unchanged content"
            ]
            mock_nm.diff_note_versions.return_value = (True, "Successfully compared versions", diff_lines)
            
            yield mock_nm

    def test_diff_command_basic(self, runner, mock_note_manager):
        """Test basic diff command with title and version IDs."""
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v2'])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Assert NoteManager.diff_note_versions was called with correct parameters
        mock_note_manager.diff_note_versions.assert_called_once_with(
            title='Test Note',
            old_version_id='v1',
            new_version_id='v2',
            category=None,
            output_dir=None
        )
        
        # Assert output shows diff lines
        assert "Successfully compared versions" in result.output
        assert "OLD VERS" in result.output  # Looking for the diff table header
        assert "NEW VERS" in result.output
        assert "Old content line" in result.output
        assert "New content line" in result.output

    def test_diff_command_with_category(self, runner, mock_note_manager):
        """Test diff command with category option."""
        result = runner.invoke(cli, [
            'versions', 'diff', 
            'Test Note', 'v1', 'v2', 
            '--category', 'work'
        ])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Assert category param was passed
        mock_note_manager.diff_note_versions.assert_called_once_with(
            title='Test Note',
            old_version_id='v1',
            new_version_id='v2',
            category='work',
            output_dir=None
        )

    def test_diff_command_with_custom_output_dir(self, runner, mock_note_manager, temp_dir):
        """Test diff command with custom output directory."""
        result = runner.invoke(cli, [
            'versions', 'diff', 
            'Test Note', 'v1', 'v2', 
            '--output-dir', temp_dir
        ])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Assert output_dir param was passed
        mock_note_manager.diff_note_versions.assert_called_once_with(
            title='Test Note',
            old_version_id='v1',
            new_version_id='v2',
            category=None,
            output_dir=temp_dir
        )

    def test_diff_command_note_not_found(self, runner, mock_note_manager):
        """Test diff command when note is not found."""
        # Mock note not found
        mock_note_manager.diff_note_versions.return_value = (False, "Note 'Nonexistent Note' not found.", None)
        
        result = runner.invoke(cli, ['versions', 'diff', 'Nonexistent Note', 'v1', 'v2'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "Note 'Nonexistent Note' not found." in result.output

    def test_diff_command_version_not_found(self, runner, mock_note_manager):
        """Test diff command when a version is not found."""
        # Mock version not found
        mock_note_manager.diff_note_versions.return_value = (False, "Version v999 not found", None)
        
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v999'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "Version v999 not found" in result.output

    def test_diff_command_no_versions(self, runner, mock_note_manager):
        """Test diff command when there are no versions."""
        # Mock no versions
        mock_note_manager.diff_note_versions.return_value = (False, "No versions available", None)
        
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v2'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "No versions available" in result.output

    def test_diff_command_same_version(self, runner, mock_note_manager):
        """Test diff command when comparing the same version."""
        # Mock empty diff for identical versions
        mock_note_manager.diff_note_versions.return_value = (True, "Versions are identical", [])
        
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v1'])

        # Command should succeed but indicate no differences
        assert result.exit_code == 0
        assert "Versions are identical" in result.output

    @patch('app.cli.commands.difflib')
    @patch('app.cli.commands.Syntax')
    def test_diff_command_syntax_highlighting(self, mock_syntax, mock_difflib, runner, mock_note_manager):
        """Test diff command with syntax highlighting."""
        # Setup mock for Syntax
        mock_syntax_instance = MagicMock()
        mock_syntax.return_value = mock_syntax_instance
        
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v2'])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Assert Syntax was called with diff text and correct parameters
        mock_syntax.assert_called_once()
        args = mock_syntax.call_args[0]
        assert args[1] == "diff"  # Verify using diff syntax highlighting

    def test_diff_command_version_control_disabled(self, runner, mock_note_manager):
        """Test diff command when version control is disabled."""
        # Mock version control disabled
        mock_note_manager.version_control_enabled = False
        mock_note_manager.diff_note_versions.return_value = (False, "Version control is not enabled.", None)
        
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v2'])

        # Assert command fails with appropriate message
        assert result.exit_code == 1
        assert "Version control is not enabled" in result.output

    def test_diff_command_method_missing(self, runner, mock_note_manager):
        """Test diff command when diff_note_versions method is missing."""
        # Remove the diff_note_versions method
        delattr(mock_note_manager, 'diff_note_versions')
        
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v2'])

        # Assert command fails with appropriate message
        assert result.exit_code == 1
        assert "Version control functionality is not available" in result.output

    def test_diff_command_exception(self, runner, mock_note_manager):
        """Test diff command when an exception occurs."""
        # Mock an exception
        mock_note_manager.diff_note_versions.side_effect = Exception("Unexpected error")
        
        result = runner.invoke(cli, ['versions', 'diff', 'Test Note', 'v1', 'v2'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "Error showing diff" in result.output

    def test_diff_command_complex_diff(self, runner, mock_note_manager):
        """Test diff command with a complex diff including multiple changes."""
        # Mock a complex diff output
        complex_diff = [
            "  # Meeting Notes",
            "- ## Meeting on January 15",
            "+ ## Meeting on January 16",
            "  ",
            "- ### Attendees: Alice, Bob, Charlie",
            "+ ### Attendees: Alice, Charlie, Dave",
            "  ",
            "  ## Agenda",
            "  ",
            "- 1. Review previous meeting notes",
            "- 2. Discuss project timeline",
            "- 3. Assign tasks",
            "+ 1. Welcome Dave to the team",
            "+ 2. Review previous meeting notes",
            "+ 3. Discuss project timeline",
            "+ 4. Assign tasks",
            "  ",
            "  ## Notes",
            "  "
        ]
        mock_note_manager.diff_note_versions.return_value = (True, "Successfully compared versions", complex_diff)
        
        result = runner.invoke(cli, ['versions', 'diff', 'Meeting Notes', 'v1', 'v2'])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Assert output contains the complex diff
        assert "Meeting Notes" in result.output
        assert "Meeting on January 15" in result.output
        assert "Meeting on January 16" in result.output
        assert "Welcome Dave to the team" in result.output


if __name__ == "__main__":
    pytest.main(["-v", "test_versions_diff_command.py"])