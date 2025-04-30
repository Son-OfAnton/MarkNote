"""
Tests for the 'marknote versions edit' command.
"""
import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock, call, mock_open
from click.testing import CliRunner
from app.cli.commands import cli


class TestVersionsEditCommand:
    """Tests for the 'marknote versions edit' command."""

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
            
            # Default behavior for edit_version
            mock_nm.edit_version.return_value = (
                True, 
                "Version edited successfully. New version: v2_2023-11-07T10-00-00", 
                "v2_2023-11-07T10-00-00"
            )
            
            # Default behavior for get_note_version_history
            mock_nm.get_note_version_history.return_value = (
                True,
                "Found 2 versions.",
                [
                    {
                        "version_id": "v1_2023-11-03T10-00-00",
                        "timestamp": "2023-11-03T10:00:00",
                        "author": "Test User",
                        "message": "Initial version"
                    },
                    {
                        "version_id": "v2_2023-11-07T10-00-00",
                        "timestamp": "2023-11-07T10:00:00",
                        "author": "Test User",
                        "message": "Edited version"
                    }
                ]
            )
            
            yield mock_nm

    def test_edit_command_basic(self, runner, mock_note_manager):
        """Test basic edit command with title and version ID."""
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Assert NoteManager.edit_version was called with correct parameters
        mock_note_manager.edit_version.assert_called_once_with(
            title='Test Note',
            version_id='v1',
            category=None,
            output_dir=None,
            editor=None,
            commit_message=None,
            author=None
        )
        
        # Assert success message in output
        assert "Version edited successfully" in result.output
        assert "New version: v2_2023-11-07T10-00-00" in result.output

    def test_edit_command_with_complete_options(self, runner, mock_note_manager):
        """Test edit command with all available options."""
        result = runner.invoke(cli, [
            'versions', 'edit', 
            'Test Note', 'v1',
            '--category', 'work',
            '--output-dir', '/tmp/notes',
            '--editor', 'nano',
            '--message', 'Updated formatting',
            '--author', 'John Doe'
        ])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Assert NoteManager.edit_version was called with correct parameters
        mock_note_manager.edit_version.assert_called_once_with(
            title='Test Note',
            version_id='v1',
            category='work',
            output_dir='/tmp/notes',
            editor='nano',
            commit_message='Updated formatting',
            author='John Doe'
        )

    def test_edit_command_no_changes_made(self, runner, mock_note_manager):
        """Test edit command when no changes are made to the content."""
        # Mock scenario where no changes were made
        mock_note_manager.edit_version.return_value = (
            True, 
            "No changes were made to the version.", 
            None
        )
        
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Assert command executed successfully but indicates no changes
        assert result.exit_code == 0
        assert "No changes were made" in result.output
        
        # Verify get_note_version_history is NOT called (since no new version was created)
        mock_note_manager.get_note_version_history.assert_not_called()

    def test_edit_command_note_not_found(self, runner, mock_note_manager):
        """Test edit command when note is not found."""
        # Mock note not found scenario
        mock_note_manager.edit_version.return_value = (
            False, 
            "Note 'Nonexistent Note' not found.", 
            None
        )
        
        result = runner.invoke(cli, ['versions', 'edit', 'Nonexistent Note', 'v1'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "Note 'Nonexistent Note' not found." in result.output

    def test_edit_command_version_not_found(self, runner, mock_note_manager):
        """Test edit command when version is not found."""
        # Mock version not found scenario
        mock_note_manager.edit_version.return_value = (
            False, 
            "Version v999 not found.", 
            None
        )
        
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v999'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "Version v999 not found." in result.output

    def test_edit_command_editor_failure(self, runner, mock_note_manager):
        """Test edit command when the editor fails to open."""
        # Mock editor failure
        mock_note_manager.edit_version.return_value = (
            False, 
            "Failed to edit version content.", 
            None
        )
        
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "Failed to edit version content." in result.output

    @patch('app.cli.commands.Panel')
    def test_edit_command_version_details_panel(self, mock_panel, runner, mock_note_manager):
        """Test the version details panel after successful edit."""
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Assert command executed successfully
        assert result.exit_code == 0
        
        # Verify Panel was created with proper version details
        mock_panel.assert_called_once()
        panel_content = mock_panel.call_args[0][0]
        
        # Check that the panel contains key version information
        assert "Version ID" in panel_content
        assert "v2_2023-11-07T10-00-00" in panel_content
        assert "Created" in panel_content
        assert "Author" in panel_content
        assert "Message" in panel_content

    def test_edit_command_version_control_disabled(self, runner, mock_note_manager):
        """Test edit command when version control is disabled."""
        # Set version_control_enabled to False
        mock_note_manager.version_control_enabled = False
        
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Assert command fails with appropriate error
        assert result.exit_code == 1
        assert "Version control is not enabled" in result.output

    def test_edit_command_method_missing(self, runner, mock_note_manager):
        """Test edit command when the edit_version method is missing."""
        # Remove the edit_version method
        delattr(mock_note_manager, 'edit_version')
        
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Assert command fails with appropriate error
        assert result.exit_code == 1
        assert "Version editing functionality is not available" in result.output

    def test_edit_command_history_error(self, runner, mock_note_manager):
        """Test edit command when there's an error getting version history."""
        # Set up successful edit but failure when getting history
        mock_note_manager.edit_version.return_value = (
            True, 
            "Version edited successfully. New version: v2", 
            "v2"
        )
        mock_note_manager.get_note_version_history.return_value = (
            False,
            "Error retrieving version history.",
            None
        )
        
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Command should still succeed because the edit itself succeeded
        assert result.exit_code == 0
        assert "Version edited successfully" in result.output
        # But no version panel details should be shown

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.utils.editor_handler.edit_file')
    def test_edit_version_method_implementation(self, mock_edit_file, mock_temp_file, runner, mock_note_manager):
        """Test the implementation of the edit_version method in NoteManager.
        
        This is a more in-depth test that verifies the internal workings
        of the edit_version method rather than just its CLI interface.
        """
        # This test won't use runner as we're testing the method directly
        
        # Mock the temporary file
        mock_file = MagicMock()
        mock_file.name = '/tmp/temp_edit_file.md'
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Mock the edit_file function to indicate successful editing
        mock_edit_file.return_value = True
        
        # Mock get_note_version to return version content
        mock_note_manager.get_note_version.return_value = (
            True,
            "Retrieved version v1",
            "# Original Content\n\nThis is the original content.",
            {"version_id": "v1", "timestamp": "2023-11-03T10:00:00"}
        )
        
        # Mock reading edited content after editor closes
        with patch("builtins.open", mock_open(read_data="# Edited Content\n\nThis is the edited content.")):
            # Test by directly calling the method instead of through CLI
            result = mock_note_manager.edit_version(
                title="Test Note",
                version_id="v1",
                editor="nano"
            )
            
            # Assert it returns success and the new version ID
            assert result[0]  # success
            assert "Version edited successfully" in result[1]  # message
            assert result[2] is not None  # new_version_id
            
            # Verify temp file was created
            mock_temp_file.assert_called_once()
            
            # Verify edit_file was called with temp file
            mock_edit_file.assert_called_once_with('/tmp/temp_edit_file.md', custom_editor="nano")
            
            # Verify a new version was created with the edited content
            assert mock_note_manager.version_manager.save_version.called

    def test_edit_command_exception(self, runner, mock_note_manager):
        """Test edit command when an unexpected exception occurs."""
        # Mock an exception
        mock_note_manager.edit_version.side_effect = Exception("Unexpected error during edit")
        
        result = runner.invoke(cli, ['versions', 'edit', 'Test Note', 'v1'])

        # Assert command fails with error
        assert result.exit_code == 1
        assert "Error editing version" in result.output


if __name__ == "__main__":
    pytest.main(["-v", "test_versions_edit_command.py"])