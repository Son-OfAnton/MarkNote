"""
Tests for the auto-archive by date CLI command.
"""
import os
import tempfile
import shutil
from unittest import TestCase, mock
from click.testing import CliRunner
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.cli.commands import auto_archive_by_date
from app.core.note_manager_archieve_extension import ArchiveNoteManager
from app.models.note import Note


class TestAutoArchiveDateCLI(TestCase):
    """Test cases for auto-archive by date CLI command."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create a CLI runner
        self.runner = CliRunner()
        
        # Create a mock ArchiveNoteManager
        self.mock_note_manager = mock.MagicMock(spec=ArchiveNoteManager)
        
        # Create a patch for the ArchiveNoteManager constructor
        self.note_manager_patch = mock.patch('app.cli.commands.ArchiveNoteManager',
                                             return_value=self.mock_note_manager)

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_auto_archive_by_date_basic(self):
        """Test basic auto-archive by date command."""
        with self.note_manager_patch:
            # Mock successful archiving
            self.mock_note_manager.auto_archive_by_date.return_value = {
                "/path/to/note1.md": "Note 'Note 1' was archived successfully",
                "/path/to/note2.md": "Note 'Note 2' was archived successfully"
            }
            
            # Call the command
            result = self.runner.invoke(auto_archive_by_date, ["2023-01-01"])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # Check the note manager was called correctly
            self.mock_note_manager.auto_archive_by_date.assert_called_once_with(
                "2023-01-01",
                field="created_at",
                before_date=True,
                reason="Auto-archived by date",
                move_to_archive_dir=True
            )

    def test_auto_archive_by_date_with_field_option(self):
        """Test auto-archive by date with field option."""
        with self.note_manager_patch:
            # Mock successful archiving
            self.mock_note_manager.auto_archive_by_date.return_value = {
                "/path/to/note1.md": "Note 'Note 1' was archived successfully"
            }
            
            # Call the command with field option
            result = self.runner.invoke(auto_archive_by_date, [
                "2023-01-01",
                "--field", "updated_at"
            ])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # Check the note manager was called with the correct field
            self.mock_note_manager.auto_archive_by_date.assert_called_once_with(
                "2023-01-01",
                field="updated_at",
                before_date=True,
                reason="Auto-archived by date",
                move_to_archive_dir=True
            )

    def test_auto_archive_by_date_after_option(self):
        """Test auto-archive by date with after option."""
        with self.note_manager_patch:
            # Mock successful archiving
            self.mock_note_manager.auto_archive_by_date.return_value = {
                "/path/to/note1.md": "Note 'Note 1' was archived successfully"
            }
            
            # Call the command with after option
            result = self.runner.invoke(auto_archive_by_date, [
                "2023-01-01",
                "--after"
            ])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # Check the note manager was called with before_date=False
            self.mock_note_manager.auto_archive_by_date.assert_called_once_with(
                "2023-01-01",
                field="created_at",
                before_date=False,  # After the date
                reason="Auto-archived by date",
                move_to_archive_dir=True
            )

    def test_auto_archive_by_date_with_reason(self):
        """Test auto-archive by date with custom reason."""
        with self.note_manager_patch:
            # Mock successful archiving
            self.mock_note_manager.auto_archive_by_date.return_value = {
                "/path/to/note1.md": "Note 'Note 1' was archived successfully"
            }
            
            # Call the command with reason option
            result = self.runner.invoke(auto_archive_by_date, [
                "2023-01-01",
                "--reason", "Custom archive reason"
            ])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # Check the note manager was called with the custom reason
            self.mock_note_manager.auto_archive_by_date.assert_called_once_with(
                "2023-01-01",
                field="created_at",
                before_date=True,
                reason="Custom archive reason",
                move_to_archive_dir=True
            )

    def test_auto_archive_by_date_no_move(self):
        """Test auto-archive by date without moving files."""
        with self.note_manager_patch:
            # Mock successful archiving
            self.mock_note_manager.auto_archive_by_date.return_value = {
                "/path/to/note1.md": "Note 'Note 1' was archived successfully"
            }
            
            # Call the command with no-move option
            result = self.runner.invoke(auto_archive_by_date, [
                "2023-01-01",
                "--no-move"
            ])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # Check the note manager was called with move_to_archive_dir=False
            self.mock_note_manager.auto_archive_by_date.assert_called_once_with(
                "2023-01-01",
                field="created_at",
                before_date=True,
                reason="Auto-archived by date",
                move_to_archive_dir=False
            )

    def test_auto_archive_by_date_invalid_date(self):
        """Test auto-archive by date with invalid date format."""
        with self.note_manager_patch:
            # Call the command with invalid date
            result = self.runner.invoke(auto_archive_by_date, ["2023/01/01"])
            
            # Check the command failed
            self.assertEqual(result.exit_code, 1)
            
            # Note manager should not be called
            self.mock_note_manager.auto_archive_by_date.assert_not_called()

    def test_auto_archive_by_date_dry_run_with_matches(self):
        """Test auto-archive by date with dry run when notes match criteria."""
        with self.note_manager_patch:
            # Mock notes list
            mock_notes = [
                mock.MagicMock(
                    title="Note 1",
                    metadata={"created_at": "2022-12-15T12:00:00"}
                ),
                mock.MagicMock(
                    title="Note 2",
                    metadata={"created_at": "2022-11-10T12:00:00"}
                )
            ]
            self.mock_note_manager.list_notes.return_value = mock_notes
            
            # Call the command with dry run
            result = self.runner.invoke(auto_archive_by_date, [
                "2023-01-01",
                "--dry-run"
            ])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # The auto_archive_by_date should not be called in dry-run mode
            self.mock_note_manager.auto_archive_by_date.assert_not_called()
            
            # list_notes should be called
            self.mock_note_manager.list_notes.assert_called_once()

    def test_auto_archive_by_date_dry_run_no_matches(self):
        """Test auto-archive by date with dry run when no notes match criteria."""
        with self.note_manager_patch:
            # Mock notes list with dates after archive date
            mock_notes = [
                mock.MagicMock(
                    title="Note 1",
                    metadata={"created_at": "2023-02-15T12:00:00"}
                ),
                mock.MagicMock(
                    title="Note 2",
                    metadata={"created_at": "2023-03-10T12:00:00"}
                )
            ]
            self.mock_note_manager.list_notes.return_value = mock_notes
            
            # Call the command with dry run
            result = self.runner.invoke(auto_archive_by_date, [
                "2023-01-01",
                "--dry-run"
            ])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # The auto_archive_by_date should not be called in dry-run mode
            self.mock_note_manager.auto_archive_by_date.assert_not_called()
            
            # list_notes should be called
            self.mock_note_manager.list_notes.assert_called_once()

    def test_auto_archive_by_date_exception_handling(self):
        """Test exception handling in auto-archive by date command."""
        with self.note_manager_patch:
            # Make auto_archive_by_date raise an exception
            self.mock_note_manager.auto_archive_by_date.side_effect = ValueError("Test error")
            
            # Call the command
            result = self.runner.invoke(auto_archive_by_date, ["2023-01-01"])
            
            # Check the command failed
            self.assertEqual(result.exit_code, 1)

    def test_auto_archive_by_date_no_notes_archived(self):
        """Test auto-archive by date when no notes match criteria."""
        with self.note_manager_patch:
            # Mock empty results
            self.mock_note_manager.auto_archive_by_date.return_value = {}
            
            # Call the command
            result = self.runner.invoke(auto_archive_by_date, ["2023-01-01"])
            
            # Check the command succeeded
            self.assertEqual(result.exit_code, 0)
            
            # Note manager should be called
            self.mock_note_manager.auto_archive_by_date.assert_called_once()