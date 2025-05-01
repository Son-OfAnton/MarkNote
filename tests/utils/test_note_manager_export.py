"""
Tests for the export functionality in NoteManager.
"""
import os
import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, Any, List, Tuple, Optional

from app.core.note_manager import NoteManager
from app.models.note import Note

# Sample note metadata
SAMPLE_METADATA = {
    "title": "Test Note",
    "created_at": "2024-06-26T10:00:00",
    "updated_at": "2024-06-26T11:00:00",
    "tags": ["test", "example", "pdf"],
    "category": "Tests",
    "path": "/path/to/note.md"
}

# Sample note content
SAMPLE_CONTENT = """
# Test Note

This is a sample note content.

## Section 1

Some content here.

## Section 2

More content here.
"""


class TestNoteManagerPdfExport:
    """Tests for the PDF export methods in NoteManager."""

    @pytest.fixture
    def note_manager(self):
        """Create a NoteManager instance for testing."""
        # Don't enable version control for these tests
        return NoteManager(enable_version_control=False)

    def test_export_note_to_pdf(self, note_manager, monkeypatch):
        """Test exporting a single note to PDF."""
        # Mock find_note_path to return a path
        mock_find_path = MagicMock(return_value="/path/to/note.md")
        monkeypatch.setattr(note_manager, "find_note_path", mock_find_path)
        
        # Mock read_note_file to return metadata and content
        mock_read_file = MagicMock(return_value=(SAMPLE_METADATA, SAMPLE_CONTENT))
        monkeypatch.setattr("app.core.note_manager.read_note_file", mock_read_file)
        
        # Mock export_note_to_pdf function from pdf_exporter
        mock_export = MagicMock(return_value=True)
        monkeypatch.setattr("app.core.note_manager.export_note_to_pdf", mock_export)
        
        # Mock os.path functions
        monkeypatch.setattr("os.path.isabs", lambda path: False)
        monkeypatch.setattr("os.path.abspath", lambda path: f"/absolute{path}")
        monkeypatch.setattr("os.path.dirname", lambda path: os.path.split(path)[0])
        monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
        
        # Test export with minimal parameters
        success, message = note_manager.export_note_to_pdf(
            title="Test Note", 
            category="Tests"
        )
        
        # Check result
        assert success is True
        assert "exported successfully" in message
        
        # Verify that the correct functions were called
        mock_find_path.assert_called_once_with("Test Note", "Tests", None)
        mock_read_file.assert_called_once_with("/path/to/note.md")
        mock_export.assert_called_once()

    def test_export_note_to_pdf_not_found(self, note_manager, monkeypatch):
        """Test exporting a note that doesn't exist."""
        # Mock find_note_path to return None (note not found)
        mock_find_path = MagicMock(return_value=None)
        monkeypatch.setattr(note_manager, "find_note_path", mock_find_path)
        
        # Test export with a note that doesn't exist
        success, message = note_manager.export_note_to_pdf(
            title="Nonexistent Note", 
            category="Tests"
        )
        
        # Check result
        assert success is False
        assert "not found" in message
        
        # Verify that only find_note_path was called
        mock_find_path.assert_called_once_with("Nonexistent Note", "Tests", None)

    def test_export_note_to_pdf_with_custom_path(self, note_manager, monkeypatch):
        """Test exporting a note with a custom output path."""
        # Mock find_note_path to return a path
        mock_find_path = MagicMock(return_value="/path/to/note.md")
        monkeypatch.setattr(note_manager, "find_note_path", mock_find_path)
        
        # Mock read_note_file to return metadata and content
        mock_read_file = MagicMock(return_value=(SAMPLE_METADATA, SAMPLE_CONTENT))
        monkeypatch.setattr("app.core.note_manager.read_note_file", mock_read_file)
        
        # Mock export_note_to_pdf function from pdf_exporter
        mock_export = MagicMock(return_value=True)
        monkeypatch.setattr("app.core.note_manager.export_note_to_pdf", mock_export)
        
        # Mock os.path functions
        monkeypatch.setattr("os.path.isabs", lambda path: path.startswith("/"))
        monkeypatch.setattr("os.path.dirname", lambda path: os.path.split(path)[0])
        monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
        
        # Custom output path
        output_path = "/custom/output/test_note.pdf"
        
        # Test export with custom output path
        success, message = note_manager.export_note_to_pdf(
            title="Test Note", 
            output_path=output_path
        )
        
        # Check result
        assert success is True
        assert output_path in message
        
        # Verify that export_note_to_pdf was called with the custom path
        mock_export.assert_called_once()
        args, kwargs = mock_export.call_args
        assert kwargs["output_path"] == output_path

    def test_export_note_to_pdf_with_custom_css(self, note_manager, monkeypatch):
        """Test exporting a note with custom CSS."""
        # Mock find_note_path to return a path
        mock_find_path = MagicMock(return_value="/path/to/note.md")
        monkeypatch.setattr(note_manager, "find_note_path", mock_find_path)
        
        # Mock read_note_file to return metadata and content
        mock_read_file = MagicMock(return_value=(SAMPLE_METADATA, SAMPLE_CONTENT))
        monkeypatch.setattr("app.core.note_manager.read_note_file", mock_read_file)
        
        # Mock export_note_to_pdf function from pdf_exporter
        mock_export = MagicMock(return_value=True)
        monkeypatch.setattr("app.core.note_manager.export_note_to_pdf", mock_export)
        
        # Mock os.path functions
        monkeypatch.setattr("os.path.isabs", lambda path: False)
        monkeypatch.setattr("os.path.abspath", lambda path: f"/absolute{path}")
        monkeypatch.setattr("os.path.dirname", lambda path: os.path.split(path)[0])
        monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
        
        # Custom CSS
        custom_css = "body { font-family: Arial; }"
        
        # Test export with custom CSS
        success, message = note_manager.export_note_to_pdf(
            title="Test Note",
            custom_css=custom_css
        )
        
        # Check result
        assert success is True
        
        # Verify that export_note_to_pdf was called with the custom CSS
        mock_export.assert_called_once()
        args, kwargs = mock_export.call_args
        assert kwargs["custom_css"] == custom_css

    def test_export_note_to_pdf_without_metadata(self, note_manager, monkeypatch):
        """Test exporting a note without metadata."""
        # Mock find_note_path to return a path
        mock_find_path = MagicMock(return_value="/path/to/note.md")
        monkeypatch.setattr(note_manager, "find_note_path", mock_find_path)
        
        # Mock read_note_file to return metadata and content
        mock_read_file = MagicMock(return_value=(SAMPLE_METADATA, SAMPLE_CONTENT))
        monkeypatch.setattr("app.core.note_manager.read_note_file", mock_read_file)
        
        # Mock export_note_to_pdf function from pdf_exporter
        mock_export = MagicMock(return_value=True)
        monkeypatch.setattr("app.core.note_manager.export_note_to_pdf", mock_export)
        
        # Mock os.path functions
        monkeypatch.setattr("os.path.isabs", lambda path: False)
        monkeypatch.setattr("os.path.abspath", lambda path: f"/absolute{path}")
        monkeypatch.setattr("os.path.dirname", lambda path: os.path.split(path)[0])
        monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
        
        # Test export without metadata
        success, message = note_manager.export_note_to_pdf(
            title="Test Note",
            include_metadata=False
        )
        
        # Check result
        assert success is True
        
        # Verify that export_note_to_pdf was called without metadata
        mock_export.assert_called_once()
        args, kwargs = mock_export.call_args
        assert kwargs["include_metadata"] is False

    def test_export_note_to_pdf_error(self, note_manager, monkeypatch):
        """Test handling errors during PDF export."""
        # Mock find_note_path to return a path
        mock_find_path = MagicMock(return_value="/path/to/note.md")
        monkeypatch.setattr(note_manager, "find_note_path", mock_find_path)
        
        # Mock read_note_file to return metadata and content
        mock_read_file = MagicMock(return_value=(SAMPLE_METADATA, SAMPLE_CONTENT))
        monkeypatch.setattr("app.core.note_manager.read_note_file", mock_read_file)
        
        # Mock export_note_to_pdf function from pdf_exporter to raise an exception
        mock_export = MagicMock(side_effect=Exception("Test error"))
        monkeypatch.setattr("app.core.note_manager.export_note_to_pdf", mock_export)
        
        # Mock os.path functions
        monkeypatch.setattr("os.path.isabs", lambda path: False)
        monkeypatch.setattr("os.path.abspath", lambda path: f"/absolute{path}")
        monkeypatch.setattr("os.path.dirname", lambda path: os.path.split(path)[0])
        monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
        
        # Test export with an error
        success, message = note_manager.export_note_to_pdf(title="Test Note")
        
        # Check result
        assert success is False
        assert "Error" in message
        assert "Test error" in message

    def test_export_notes_to_pdf(self, note_manager, monkeypatch):
        """Test exporting multiple notes to PDF."""
        # Mock export_note_to_pdf to return different results for different notes
        def mock_export_note(title, **kwargs):
            if title == "Note1":
                return True, f"Note exported successfully to {title}.pdf"
            elif title == "Note2":
                return True, f"Note exported successfully to {title}.pdf"
            else:
                return False, f"Failed to export {title}"
        
        monkeypatch.setattr(note_manager, "export_note_to_pdf", mock_export_note)
        
        # Mock os.path functions
        monkeypatch.setattr("os.path.expanduser", lambda path: path)
        monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
        
        # Test exporting multiple notes
        note_titles = ["Note1", "Note2", "Note3"]
        results = note_manager.export_notes_to_pdf(
            notes=note_titles,
            output_dir="/output/dir",
            category="Tests"
        )
        
        # Check results
        assert "Note1" in results
        assert "Note2" in results
        assert "Note3" in results
        assert "successfully" in results["Note1"]
        assert "successfully" in results["Note2"]
        assert "Failed" in results["Note3"]

    def test_export_all_notes_to_pdf(self, note_manager, monkeypatch):
        """Test exporting all notes to PDF."""
        # Mock list_note_files to return a list of note files
        mock_list_files = MagicMock(return_value=[
            "/path/to/note1.md",
            "/path/to/note2.md",
            "/path/to/note3.md"
        ])
        monkeypatch.setattr("app.core.note_manager.list_note_files", mock_list_files)
        
        # Mock read_note_file to return different metadata for different notes
        def mock_read_note_file(path):
            if "note1" in path:
                metadata = {**SAMPLE_METADATA, "title": "Note1"}
                return metadata, SAMPLE_CONTENT
            elif "note2" in path:
                metadata = {**SAMPLE_METADATA, "title": "Note2"}
                return metadata, SAMPLE_CONTENT
            else:
                # Simulate an error for the third note
                raise Exception("Error reading note")
        
        monkeypatch.setattr("app.core.note_manager.read_note_file", mock_read_note_file)
        
        # Mock convert_markdown_to_pdf to succeed for note1 but fail for note2
        def mock_convert(markdown_path, output_path, **kwargs):
            return "note1" in markdown_path
        
        monkeypatch.setattr("app.core.note_manager.convert_markdown_to_pdf", mock_convert)
        
        # Mock os.path functions
        monkeypatch.setattr("os.path.expanduser", lambda path: path)
        monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
        monkeypatch.setattr("os.path.splitext", lambda path: os.path.split(path))
        monkeypatch.setattr("os.path.basename", lambda path: os.path.split(path)[1])
        
        # Test exporting all notes
        successful, total, failed = note_manager.export_all_notes_to_pdf(
            output_dir="/output/dir",
            category="Tests"
        )
        
        # Check results
        assert successful == 1  # Only note1 succeeded
        assert total == 3  # All three notes were processed
        assert len(failed) == 2  # note2 and note3 failed
        assert "Note2" in failed  # note2 should be in failed list by title
        assert "note3.md" in failed  # note3 should be in failed list by filename