"""
Tests for the export commands in the CLI.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from app.cli.commands import export_to_pdf, batch_export_to_pdf


class TestPdfExportCommand:
    """Tests for the 'export pdf' command."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI runner for testing."""
        return CliRunner()

    @patch('app.cli.export_commands.NoteManager')
    def test_export_single_note(self, mock_note_manager_class, runner):
        """Test exporting a single note to PDF."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        mock_note_manager.export_note_to_pdf.return_value = (True, "Note exported successfully to /path/to/output.pdf")

        # Run the command
        result = runner.invoke(export_to_pdf, ["Test Note"])

        # Check the result
        assert result.exit_code == 0
        assert "Success" in result.output
        assert "exported successfully" in result.output

        # Verify that the NoteManager method was called correctly
        mock_note_manager.export_note_to_pdf.assert_called_once_with(
            title="Test Note",
            output_path=None,
            category=None,
            output_dir=None,
            custom_css=None,
            include_metadata=True
        )

    @patch('app.cli.export_commands.NoteManager')
    def test_export_single_note_with_options(self, mock_note_manager_class, runner):
        """Test exporting a single note with all options specified."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        mock_note_manager.export_note_to_pdf.return_value = (True, "Note exported successfully to /custom/path/test.pdf")

        # Create a temporary CSS file
        with runner.isolated_filesystem():
            with open("custom.css", "w") as f:
                f.write("body { font-family: Arial; }")

            # Run the command with options
            result = runner.invoke(export_to_pdf, [
                "Test Note",
                "--output-path", "/custom/path/test.pdf",
                "--category", "Tests",
                "--source-dir", "~/notes",
                "--custom-css", "custom.css",
                "--no-metadata"
            ])

        # Check the result
        assert result.exit_code == 0
        assert "Success" in result.output

        # Verify that the correct CSS was loaded
        args, kwargs = mock_note_manager.export_note_to_pdf.call_args
        assert "body { font-family: Arial; }" == kwargs["custom_css"]

        # Verify other parameters
        assert kwargs["title"] == "Test Note"
        assert kwargs["output_path"] == "/custom/path/test.pdf"
        assert kwargs["category"] == "Tests"
        assert kwargs["output_dir"] == "~/notes"
        assert kwargs["include_metadata"] is False

    @patch('app.cli.export_commands.NoteManager')
    def test_export_single_note_failure(self, mock_note_manager_class, runner):
        """Test handling failure when exporting a single note."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        mock_note_manager.export_note_to_pdf.return_value = (False, "Note 'Test Note' not found.")

        # Run the command
        result = runner.invoke(export_to_pdf, ["Test Note"])

        # Check the result
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "not found" in result.output

    @patch('app.cli.export_commands.NoteManager')
    def test_export_all_notes(self, mock_note_manager_class, runner):
        """Test exporting all notes to PDF."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        mock_note_manager.export_all_notes_to_pdf.return_value = (5, 7, ["Note6", "Note7"])

        # Mock os.getcwd and os.makedirs
        with patch('os.getcwd', return_value="/current/dir"), \
             patch('os.makedirs', return_value=None):

            # Run the command without a title (to export all notes)
            result = runner.invoke(export_to_pdf, [])

        # Check the result
        assert result.exit_code == 1  # Some notes failed
        assert "Export Results" in result.output
        assert "Total Notes: 7" in result.output
        assert "Successfully Exported: 5" in result.output
        assert "Failed: 2" in result.output
        assert "Failed to export the following notes:" in result.output
        assert "Note6" in result.output
        assert "Note7" in result.output

    @patch('app.cli.export_commands.NoteManager')
    def test_export_all_notes_success(self, mock_note_manager_class, runner):
        """Test successfully exporting all notes to PDF."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        # All notes exported successfully
        mock_note_manager.export_all_notes_to_pdf.return_value = (7, 7, [])

        # Mock os.getcwd and os.makedirs
        with patch('os.getcwd', return_value="/current/dir"), \
             patch('os.makedirs', return_value=None):

            # Run the command without a title (to export all notes)
            result = runner.invoke(export_to_pdf, [])

        # Check the result
        assert result.exit_code == 0  # All succeeded
        assert "Export Results" in result.output
        assert "Total Notes: 7" in result.output
        assert "Successfully Exported: 7" in result.output
        assert "Failed: 0" in result.output
        assert "Failed to export the following notes:" not in result.output

    @patch('app.cli.export_commands.NoteManager')
    def test_export_all_notes_with_custom_output(self, mock_note_manager_class, runner):
        """Test exporting all notes to a custom output directory."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        mock_note_manager.export_all_notes_to_pdf.return_value = (3, 3, [])

        # Mock os.makedirs
        with patch('os.makedirs', return_value=None):
            # Run the command with custom output path
            result = runner.invoke(export_to_pdf, [
                "--output-path", "/custom/output",
                "--category", "Tests"
            ])

        # Check the result
        assert result.exit_code == 0
        
        # Verify that export_all_notes_to_pdf was called with the correct arguments
        mock_note_manager.export_all_notes_to_pdf.assert_called_once_with(
            output_dir="/custom/output",
            category="Tests",
            source_dir=None,
            custom_css=None,
            include_metadata=True
        )

    @patch('app.cli.export_commands.NoteManager')
    def test_export_all_notes_no_notes_found(self, mock_note_manager_class, runner):
        """Test exporting when no notes are found."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        mock_note_manager.export_all_notes_to_pdf.return_value = (0, 0, [])

        # Mock os.getcwd and os.makedirs
        with patch('os.getcwd', return_value="/current/dir"), \
             patch('os.makedirs', return_value=None):

            # Run the command without a title (to export all notes)
            result = runner.invoke(export_to_pdf, [])

        # Check the result
        assert result.exit_code == 0
        assert "No notes found to export" in result.output


class TestBatchPdfExportCommand:
    """Tests for the 'export batch-pdf' command."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI runner for testing."""
        return CliRunner()

    @patch('app.cli.export_commands.NoteManager')
    def test_batch_export(self, mock_note_manager_class, runner):
        """Test batch exporting notes to PDF."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        
        # Setup mock results for export_notes_to_pdf
        mock_results = {
            "Note1": "Note exported successfully to /output/dir/note1.pdf",
            "Note2": "Note exported successfully to /output/dir/note2.pdf",
            "Note3": "Failed to export Note3: Note not found."
        }
        mock_note_manager.export_notes_to_pdf.return_value = mock_results

        # Mock os.makedirs and os.path.expanduser
        with patch('os.makedirs', return_value=None), \
             patch('os.path.expanduser', lambda path: path):

            # Run the command
            result = runner.invoke(batch_export_to_pdf, [
                "Note1", "Note2", "Note3",
                "--output-dir", "/output/dir"
            ])

        # Check the result
        assert result.exit_code == 1  # One note failed
        assert "Export Results" in result.output
        assert "Note1" in result.output
        assert "Note2" in result.output
        assert "Note3" in result.output
        assert "Success" in result.output
        assert "Failed" in result.output
        assert "Successfully exported 2 of 3 notes" in result.output

        # Verify that export_notes_to_pdf was called with the correct arguments
        mock_note_manager.export_notes_to_pdf.assert_called_once_with(
            notes=["Note1", "Note2", "Note3"],
            output_dir="/output/dir",
            category=None,
            source_dir=None,
            custom_css=None,
            include_metadata=True
        )

    @patch('app.cli.export_commands.NoteManager')
    def test_batch_export_with_options(self, mock_note_manager_class, runner):
        """Test batch exporting with all options."""
        # Setup mock
        mock_note_manager = MagicMock()
        mock_note_manager_class.return_value = mock_note_manager
        
        # Setup mock results for export_notes_to_pdf
        mock_results = {
            "Note1": "Note exported successfully to /output/dir/note1.pdf",
            "Note2": "Note exported successfully to /output/dir/note2.pdf"
        }
        mock_note_manager.export_notes_to_pdf.return_value = mock_results

        # Create a temporary CSS file
        with runner.isolated_filesystem():
            with open("custom.css", "w") as f:
                f.write("body { font-family: Arial; }")

            # Mock os.makedirs and os.path.expanduser
            with patch('os.makedirs', return_value=None), \
                 patch('os.path.expanduser', lambda path: path):

                # Run the command with all options
                result = runner.invoke(batch_export_to_pdf, [
                    "Note1", "Note2",
                    "--output-dir", "/output/dir",
                    "--category", "Tests",
                    "--source-dir", "~/notes",
                    "--custom-css", "custom.css",
                    "--no-metadata"
                ])

        # Check the result
        assert result.exit_code == 0  # All succeeded
        assert "Export Results" in result.output
        assert "Successfully exported 2 of 2 notes" in result.output

        # Verify that the correct CSS was loaded
        args, kwargs = mock_note_manager.export_notes_to_pdf.call_args
        assert "body { font-family: Arial; }" == kwargs["custom_css"]
        
        # Verify other parameters
        assert kwargs["notes"] == ["Note1", "Note2"]
        assert kwargs["output_dir"] == "/output/dir"
        assert kwargs["category"] == "Tests"
        assert kwargs["source_dir"] == "~/notes"
        assert kwargs["include_metadata"] is False

    @patch('app.cli.export_commands.NoteManager')
    def test_batch_export_css_loading_error(self, mock_note_manager_class, runner):
        """Test handling error when loading custom CSS."""
        # Run the command with non-existent CSS file
        result = runner.invoke(batch_export_to_pdf, [
            "Note1", "Note2",
            "--output-dir", "/output/dir",
            "--custom-css", "nonexistent.css"
        ])

        # Check the result
        assert result.exit_code == 1
        assert "Error loading custom CSS" in result.output
        
        # The note_manager should not be created or used
        mock_note_manager_class.assert_not_called()