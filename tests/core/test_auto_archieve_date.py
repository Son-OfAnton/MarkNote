"""
Tests for the auto-archive by date functionality in ArchiveManager.
"""
import os
import shutil
import tempfile
from unittest import TestCase, mock
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.core.archive_manager import ArchiveManager
from app.core.note_manager_archieve_extension import ArchiveNoteManager
from app.utils.file_handler import write_note_file, read_note_file, ensure_notes_dir


class TestAutoArchiveByDate(TestCase):
    """Test cases for auto-archive by date functionality."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary base directory for tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create an ArchiveManager with the test directory
        self.archive_manager = ArchiveManager(notes_dir=self.test_dir)
        
        # Create notes with different dates for testing
        self.create_test_notes()

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def create_test_notes(self):
        """Create test notes with different created_at and updated_at dates."""
        # Dates for testing
        base_date = datetime(2023, 1, 15)  # Base date: January 15, 2023
        
        self.test_notes = [
            {
                "title": "Old Note 1", 
                "created_at": (base_date - timedelta(days=100)).isoformat(),  # ~ Oct 2022
                "updated_at": (base_date - timedelta(days=50)).isoformat(),   # ~ Nov 2022
                "tags": ["old", "test"],
                "content": "This is an old note."
            },
            {
                "title": "Recent Note 1", 
                "created_at": base_date.isoformat(),  # Jan 15, 2023
                "updated_at": (base_date + timedelta(days=10)).isoformat(),  # Jan 25, 2023
                "tags": ["recent", "test"],
                "content": "This is a recent note."
            },
            {
                "title": "Old Updated Note", 
                "created_at": (base_date - timedelta(days=80)).isoformat(),  # ~ Oct 2022
                "updated_at": (base_date + timedelta(days=20)).isoformat(),  # ~ Feb 2023
                "custom_date": (base_date - timedelta(days=30)).isoformat(),  # ~ Dec 2022
                "tags": ["old", "updated"],
                "content": "This is an old note with a recent update."
            },
            {
                "title": "New Note", 
                "created_at": (base_date + timedelta(days=30)).isoformat(),  # ~ Feb 2023
                "updated_at": (base_date + timedelta(days=40)).isoformat(),  # ~ Feb 2023
                "tags": ["new", "test"],
                "content": "This is a new note."
            },
            {
                "title": "Note With Custom Date", 
                "created_at": base_date.isoformat(),  # Jan 15, 2023
                "updated_at": base_date.isoformat(),  # Jan 15, 2023
                "custom_date": (base_date - timedelta(days=60)).isoformat(),  # ~ Nov 2022
                "tags": ["custom", "test"],
                "content": "This note has a custom date field."
            }
        ]
        
        # Create the note files
        for note_data in self.test_notes:
            title = note_data.pop("title")
            content = note_data.pop("content")
            self._create_note_file(title, content, note_data)

    def _create_note_file(self, title: str, content: str, metadata: Dict[str, Any]):
        """Create a note file with the given title, content, and metadata."""
        # Generate filename
        filename = title.lower().replace(" ", "-") + ".md"
        
        # Create the file path
        file_path = os.path.join(self.test_dir, filename)
        
        # Add title to metadata
        metadata["title"] = title
        
        # Write the note file
        write_note_file(file_path, metadata, content)
        
        return file_path

    def _is_note_archived(self, title: str) -> bool:
        """Check if a note is archived (either marked as archived or moved to archive directory)."""
        # Check if the note exists in the main directory (not archived)
        filename = title.lower().replace(" ", "-") + ".md"
        main_path = os.path.join(self.test_dir, filename)
        
        if os.path.exists(main_path):
            # The file exists in the main directory, check if it's marked as archived
            metadata, _ = read_note_file(main_path)
            return metadata.get("is_archived", False)
        
        # Check if the note exists in the archive directory
        archive_path = os.path.join(self.test_dir, "archive", filename)
        return os.path.exists(archive_path)

    def test_auto_archive_by_date_before(self):
        """Test archiving notes created before a specific date."""
        # Archive notes created before January 1, 2023
        archive_date = datetime(2023, 1, 1)
        field = "created_at"
        
        # Call the method
        results = self.archive_manager.auto_archive_by_date(
            archive_date,
            field=field,
            before_date=True,
            move_to_archive_dir=True
        )
        
        # Check the results
        self.assertEqual(len(results), 2)  # Should archive 2 notes
        
        # Verify that the expected notes are archived
        self.assertTrue(self._is_note_archived("Old Note 1"))
        self.assertTrue(self._is_note_archived("Old Updated Note"))
        
        # Verify that the other notes are not archived
        self.assertFalse(self._is_note_archived("Recent Note 1"))
        self.assertFalse(self._is_note_archived("New Note"))
        self.assertFalse(self._is_note_archived("Note With Custom Date"))

    def test_auto_archive_by_date_after(self):
        """Test archiving notes created after a specific date."""
        # Archive notes created after January 20, 2023
        archive_date = datetime(2023, 1, 20)
        field = "created_at"
        
        # Call the method
        results = self.archive_manager.auto_archive_by_date(
            archive_date,
            field=field,
            before_date=False,  # After the date
            move_to_archive_dir=True
        )
        
        # Check the results
        self.assertEqual(len(results), 1)  # Should archive 1 note
        
        # Verify that the expected notes are archived
        self.assertTrue(self._is_note_archived("New Note"))
        
        # Verify that the other notes are not archived
        self.assertFalse(self._is_note_archived("Old Note 1"))
        self.assertFalse(self._is_note_archived("Recent Note 1"))
        self.assertFalse(self._is_note_archived("Old Updated Note"))
        self.assertFalse(self._is_note_archived("Note With Custom Date"))

    def test_auto_archive_by_updated_at_field(self):
        """Test archiving notes using the updated_at field."""
        # Archive notes updated before January 1, 2023
        archive_date = datetime(2023, 1, 1)
        field = "updated_at"
        
        # Call the method
        results = self.archive_manager.auto_archive_by_date(
            archive_date,
            field=field,
            before_date=True,
            move_to_archive_dir=True
        )
        
        # Check the results
        self.assertEqual(len(results), 1)  # Should archive 1 note
        
        # Verify that the expected notes are archived
        self.assertTrue(self._is_note_archived("Old Note 1"))
        
        # Verify that the other notes are not archived
        self.assertFalse(self._is_note_archived("Recent Note 1"))
        self.assertFalse(self._is_note_archived("Old Updated Note"))
        self.assertFalse(self._is_note_archived("New Note"))
        self.assertFalse(self._is_note_archived("Note With Custom Date"))

    def test_auto_archive_by_custom_field(self):
        """Test archiving notes using a custom date field."""
        # Archive notes with custom_date before January 1, 2023
        archive_date = datetime(2023, 1, 1)
        field = "custom_date"
        
        # Call the method
        results = self.archive_manager.auto_archive_by_date(
            archive_date,
            field=field,
            before_date=True,
            move_to_archive_dir=True
        )
        
        # Check the results
        # Should include 2 notes with custom_date, but only archive those with date before Jan 1
        archived_paths = [path for path, msg in results.items() 
                          if "archived successfully" in msg]
        self.assertEqual(len(archived_paths), 2)
        
        # Verify that the expected notes are archived
        self.assertTrue(self._is_note_archived("Old Updated Note"))
        self.assertTrue(self._is_note_archived("Note With Custom Date"))
        
        # Verify that the other notes are not archived
        self.assertFalse(self._is_note_archived("Old Note 1"))
        self.assertFalse(self._is_note_archived("Recent Note 1"))
        self.assertFalse(self._is_note_archived("New Note"))

    def test_auto_archive_with_no_matches(self):
        """Test archiving when no notes match the criteria."""
        # Archive notes created before a very old date
        archive_date = datetime(2000, 1, 1)  # No notes are this old
        field = "created_at"
        
        # Call the method
        results = self.archive_manager.auto_archive_by_date(
            archive_date,
            field=field,
            before_date=True,
            move_to_archive_dir=True
        )
        
        # Check the results
        archived_paths = [path for path, msg in results.items() 
                         if "archived successfully" in msg]
        self.assertEqual(len(archived_paths), 0)
        
        # Verify no notes were archived
        for note_data in self.test_notes:
            title = note_data.get("title", "")
            self.assertFalse(self._is_note_archived(title))

    def test_auto_archive_without_moving(self):
        """Test archiving notes without moving them to archive directory."""
        # Archive notes created before January 1, 2023 but don't move them
        archive_date = datetime(2023, 1, 1)
        field = "created_at"
        
        # Call the method
        results = self.archive_manager.auto_archive_by_date(
            archive_date,
            field=field,
            before_date=True,
            move_to_archive_dir=False  # Don't move to archive dir
        )
        
        # Check results
        archived_paths = [path for path, msg in results.items() 
                         if "archived successfully" in msg]
        self.assertEqual(len(archived_paths), 2)
        
        # Check that the files still exist in the original location
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "old-note-1.md")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "old-updated-note.md")))
        
        # But they should be marked as archived in the metadata
        for filename in ["old-note-1.md", "old-updated-note.md"]:
            metadata, _ = read_note_file(os.path.join(self.test_dir, filename))
            self.assertTrue(metadata.get("is_archived", False))

    def test_archive_note_manager_auto_archive_by_date(self):
        """Test the ArchiveNoteManager wrapper for auto_archive_by_date."""
        # Create an ArchiveNoteManager
        note_manager = ArchiveNoteManager(notes_dir=self.test_dir)
        
        # Archive notes created before January 1, 2023
        date_str = "2023-01-01"  # YYYY-MM-DD format
        
        # Call the method
        results = note_manager.auto_archive_by_date(
            date_str,
            field="created_at",
            before_date=True,
            move_to_archive_dir=True
        )
        
        # Check the results
        archived_paths = [path for path, msg in results.items() 
                         if "archived successfully" in msg]
        self.assertEqual(len(archived_paths), 2)
        
        # Verify that the expected notes are archived
        self.assertTrue(self._is_note_archived("Old Note 1"))
        self.assertTrue(self._is_note_archived("Old Updated Note"))

    def test_archive_note_manager_with_invalid_date(self):
        """Test ArchiveNoteManager with invalid date format."""
        # Create an ArchiveNoteManager
        note_manager = ArchiveNoteManager(notes_dir=self.test_dir)
        
        # Archive with invalid date format
        with self.assertRaises(ValueError):
            note_manager.auto_archive_by_date(
                "2023/01/01",  # Invalid format (should be YYYY-MM-DD)
                field="created_at",
                before_date=True
            )

    def test_archive_note_manager_with_full_iso_date(self):
        """Test ArchiveNoteManager with full ISO date format."""
        # Create an ArchiveNoteManager
        note_manager = ArchiveNoteManager(notes_dir=self.test_dir)
        
        # Archive with full ISO format
        date_str = "2023-01-01T12:00:00"
        
        # Call the method
        results = note_manager.auto_archive_by_date(
            date_str,
            field="created_at",
            before_date=True
        )
        
        # Verify results
        archived_paths = [path for path, msg in results.items() 
                         if "archived successfully" in msg]
        self.assertEqual(len(archived_paths), 2)