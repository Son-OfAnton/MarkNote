"""
Unit tests for the 'list' command with sort by creation date functionality.

These tests focus on verifying that notes can be sorted by creation date.
"""
import os
import tempfile
import pytest
from click.testing import CliRunner
from app.cli.commands import cli
from datetime import datetime, timedelta


class TestListSortByCreatedFunctionality:
    """Test case for the 'list' command with sort by creation date functionality."""

    @pytest.fixture
    def runner(self):
        """Provide a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for test notes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_list_sort_by_creation_date(self, runner, temp_notes_dir):
        """Test that notes are sorted by creation date when using --sort created."""
        # Create notes with different creation and update timestamps
        now = datetime.now()
        
        # Note 1: Created first, updated last
        # This note was created a long time ago but recently updated
        note1_created = now - timedelta(days=10)
        note1_updated = now - timedelta(days=1)
        
        # Note 2: Created last, updated first
        # This note was created recently but hasn't been updated
        note2_created = now - timedelta(days=3)
        note2_updated = now - timedelta(days=7)
        
        # Note 3: In the middle for both dates
        note3_created = now - timedelta(days=5)
        note3_updated = now - timedelta(days=5)
        
        note_data = [
            {
                "title": "Old Creation, Recent Update",
                "created_at": note1_created.isoformat(),
                "updated_at": note1_updated.isoformat(),
            },
            {
                "title": "Recent Creation, Old Update",
                "created_at": note2_created.isoformat(),
                "updated_at": note2_updated.isoformat(),
            },
            {
                "title": "Middle Creation and Update",
                "created_at": note3_created.isoformat(),
                "updated_at": note3_updated.isoformat(),
            }
        ]
        
        # Create the notes with precise timestamps
        for note in note_data:
            filename = note["title"].lower().replace(" ", "-") + ".md"
            note_path = os.path.join(temp_notes_dir, filename)
            
            # Create note content with frontmatter
            content = "---\n"
            content += f"title: {note['title']}\n"
            content += f"created_at: {note['created_at']}\n"
            content += f"updated_at: {note['updated_at']}\n"
            content += "---\n\n"
            content += f"# {note['title']}\n\nTest content for {note['title']}\n"
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Act - list notes with default sort (by updated date)
        default_result = runner.invoke(
            cli, 
            ["list", "--output-dir", temp_notes_dir], 
            catch_exceptions=False
        )
        
        # Assert default sort is by updated date
        assert default_result.exit_code == 0
        
        # Expected order for default sort (by updated date, newest first)
        # "Old Creation, Recent Update" should be first as it was updated most recently
        default_expected_order = [
            "Old Creation, Recent Update",  # Most recently updated
            "Middle Creation and Update",
            "Recent Creation, Old Update"   # Least recently updated
        ]
        
        # Verify default sort order
        default_indices = [default_result.output.find(title) for title in default_expected_order]
        # Check indices are in descending order (smaller index means earlier in output)
        assert default_indices[0] < default_indices[1] < default_indices[2], \
            "Notes not sorted by updated date by default"
        
        # Act - list notes with sort by creation date
        created_result = runner.invoke(
            cli, 
            ["list", "--output-dir", temp_notes_dir, "--sort", "created"],
            catch_exceptions=False
        )
        
        # Assert
        assert created_result.exit_code == 0
        
        # Expected order for sort by creation date (newest first)
        created_expected_order = [
            "Recent Creation, Old Update",  # Most recently created
            "Middle Creation and Update",
            "Old Creation, Recent Update"   # Least recently created
        ]
        
        # Verify creation date sort order
        created_indices = [created_result.output.find(title) for title in created_expected_order]
        assert created_indices[0] < created_indices[1] < created_indices[2], \
            "Notes not sorted by creation date when --sort created is used"
        
        # The order should be different between the two sorts
        assert default_expected_order != created_expected_order, \
            "Sort orders should differ between updated and created date sorts"

    def test_list_sort_by_creation_date_display(self, runner, temp_notes_dir):
        """Test that when sorting by creation date, the creation date is displayed."""
        # Create a single note with different creation and update dates
        now = datetime.now()
        created_at = now - timedelta(days=5)
        updated_at = now - timedelta(days=1)
        
        # Format these dates for string comparison in the output
        created_str = created_at.strftime("%Y-%m-%d")
        updated_str = updated_at.strftime("%Y-%m-%d")
        
        note = {
            "title": "Test Note",
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }
        
        # Create the note
        filename = note["title"].lower().replace(" ", "-") + ".md"
        note_path = os.path.join(temp_notes_dir, filename)
        
        content = "---\n"
        content += f"title: {note['title']}\n"
        content += f"created_at: {note['created_at']}\n"
        content += f"updated_at: {note['updated_at']}\n"
        content += "---\n\n"
        content += f"# {note['title']}\n\nTest content\n"
        
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Act - list notes with default sort (should show updated date)
        default_result = runner.invoke(
            cli, 
            ["list", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert - default sort should show Updated date
        assert default_result.exit_code == 0
        assert "Updated" in default_result.output
        assert updated_str in default_result.output
        
        # Act - list notes with sort by created date
        created_result = runner.invoke(
            cli, 
            ["list", "--output-dir", temp_notes_dir, "--sort", "created"],
            catch_exceptions=False
        )
        
        # Assert - sort by created should show Created date
        assert created_result.exit_code == 0
        assert "Created" in created_result.output
        assert created_str in created_result.output