"""
Unit tests for the 'list' command functionality in the CLI.

These tests focus on the functionality of the list command,
including note listing and filtering by tags and categories.
"""
import os
import shutil
import tempfile
import pytest
from click.testing import CliRunner
from app.cli.commands import new, cli
import yaml
from datetime import datetime, timedelta


class TestListCommandFunctionality:
    """Test case for the 'list' command functionality."""

    @pytest.fixture
    def runner(self):
        """Provide a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_notes_dir(self):
        """Create a temporary directory for test notes."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_notes(self, runner, temp_notes_dir):
        """Create several sample notes with different tags and categories."""
        # Create notes with various attributes for testing
        notes = [
            {
                "title": "Work Meeting",
                "tags": "work,meeting,important",
                "category": "work"
            },
            {
                "title": "Personal Task",
                "tags": "personal,task",
                "category": "personal"
            },
            {
                "title": "Project Ideas",
                "tags": "work,project,ideas",
                "category": "work"
            },
            {
                "title": "Shopping List",
                "tags": "personal,shopping",
                "category": "personal"
            },
            {
                "title": "Research Notes",
                "tags": "work,research",
                "category": "work"
            },
            {
                "title": "Journal Entry",
                "tags": "personal,journal",
                "category": "journal"
            },
        ]
        
        created_notes = []
        for note in notes:
            result = runner.invoke(new, 
                [
                    note["title"],
                    "--tags", note["tags"],
                    "--category", note["category"],
                    "--output-dir", temp_notes_dir
                ],
                catch_exceptions=False
            )
            assert result.exit_code == 0
            
            # Create the note path
            filename = note["title"].lower().replace(" ", "-") + ".md"
            path = os.path.join(temp_notes_dir, note["category"], filename)
            created_notes.append({**note, "path": path})
            
        return created_notes

    def test_list_basic_functionality(self, runner, temp_notes_dir, sample_notes):
        """Test basic functionality of the 'list' command."""
        # Act
        result = runner.invoke(cli, ["list", "--output-dir", temp_notes_dir], catch_exceptions=False)
        
        # Assert
        assert result.exit_code == 0
        
        # Check that all notes are listed
        for note in sample_notes:
            assert note["title"] in result.output

    def test_list_with_tag_filter(self, runner, temp_notes_dir, sample_notes):
        """Test 'list' command with tag filtering."""
        # Act - filter by 'work' tag
        result = runner.invoke(cli, 
            ["list", "--tag", "work", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check that only notes with 'work' tag are listed
        work_notes = [note for note in sample_notes if "work" in note["tags"].split(",")]
        non_work_notes = [note for note in sample_notes if "work" not in note["tags"].split(",")]
        
        for note in work_notes:
            assert note["title"] in result.output
            
        for note in non_work_notes:
            assert note["title"] not in result.output

    def test_list_with_category_filter(self, runner, temp_notes_dir, sample_notes):
        """Test 'list' command with category filtering."""
        # Act - filter by 'personal' category
        result = runner.invoke(cli, 
            ["list", "--category", "personal", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check that only notes in the 'personal' category are listed
        personal_notes = [note for note in sample_notes if note["category"] == "personal"]
        non_personal_notes = [note for note in sample_notes if note["category"] != "personal"]
        
        for note in personal_notes:
            assert note["title"] in result.output
            
        for note in non_personal_notes:
            assert note["title"] not in result.output

    def test_list_with_multiple_filters(self, runner, temp_notes_dir, sample_notes):
        """Test 'list' command with multiple filters applied simultaneously."""
        # Act - filter by 'work' tag AND 'work' category
        result = runner.invoke(cli, 
            ["list", "--tag", "work", "--category", "work", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check that only notes with 'work' tag in 'work' category are listed
        matching_notes = [
            note for note in sample_notes 
            if "work" in note["tags"].split(",") and note["category"] == "work"
        ]
        non_matching_notes = [
            note for note in sample_notes 
            if "work" not in note["tags"].split(",") or note["category"] != "work"
        ]
        
        for note in matching_notes:
            assert note["title"] in result.output
            
        for note in non_matching_notes:
            assert note["title"] not in result.output

    def test_list_sort_order(self, runner, temp_notes_dir):
        """Test that notes are sorted by updated_at date (most recent first)."""
        # Create notes with different timestamps
        now = datetime.now()
        note_data = [
            {
                "title": "Old Note",
                "created_at": (now - timedelta(days=5)).isoformat(),
                "updated_at": (now - timedelta(days=5)).isoformat(),
            },
            {
                "title": "Recent Note",
                "created_at": (now - timedelta(days=2)).isoformat(),
                "updated_at": (now - timedelta(days=2)).isoformat(),
            },
            {
                "title": "Newest Note",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]
        
        # Create the notes in a way to ensure the timestamps are set
        for note in note_data:
            # Create the file directly rather than using the CLI
            # to have precise control over timestamps
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
                
        # Act - list notes
        result = runner.invoke(cli, ["list", "--output-dir", temp_notes_dir], catch_exceptions=False)
        
        # Assert
        assert result.exit_code == 0
        
        # Check that notes are listed in reverse chronological order (newest first)
        # The titles should appear in this order in the output
        expected_order = ["Newest Note", "Recent Note", "Old Note"]
        title_indices = [result.output.find(title) for title in expected_order]
        
        # Verify each title is found
        for idx in title_indices:
            assert idx != -1
            
        # Check order: each subsequent index should be greater than the previous one
        for i in range(1, len(title_indices)):
            assert title_indices[i] > title_indices[i-1]

    def test_list_empty_directory(self, runner):
        """Test 'list' command with an empty directory."""
        with tempfile.TemporaryDirectory() as empty_dir:
            # Act
            result = runner.invoke(cli, ["list", "--output-dir", empty_dir], catch_exceptions=False)
            
            # Assert
            assert result.exit_code == 0
            assert "No notes found" in result.output

    def test_list_nonexistent_directory(self, runner, temp_notes_dir):
        """Test 'list' command with a nonexistent directory."""
        # Create a path to a directory that doesn't exist
        nonexistent_dir = os.path.join(temp_notes_dir, "does_not_exist")
        
        # Act
        result = runner.invoke(cli, ["list", "--output-dir", nonexistent_dir], catch_exceptions=False)
        
        # Assert
        assert result.exit_code == 0
        assert "No notes found" in result.output

    def test_list_with_complex_tag_filter(self, runner, temp_notes_dir, sample_notes):
        """Test filtering by a specific tag that's only on some notes."""
        # Act - filter by the 'important' tag, which should be on only one note
        result = runner.invoke(cli, 
            ["list", "--tag", "important", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Only the 'Work Meeting' note should have the 'important' tag
        important_notes = [note for note in sample_notes if "important" in note["tags"].split(",")]
        non_important_notes = [note for note in sample_notes if "important" not in note["tags"].split(",")]
        
        assert len(important_notes) == 1  # Sanity check
        assert important_notes[0]["title"] == "Work Meeting"
        
        assert "Work Meeting" in result.output
        
        for note in non_important_notes:
            assert note["title"] not in result.output

    def test_list_with_column_formatting(self, runner, temp_notes_dir, sample_notes):
        """Test that the output has proper column formatting."""
        # Act
        result = runner.invoke(cli, ["list", "--output-dir", temp_notes_dir], catch_exceptions=False)
        
        # Assert
        assert result.exit_code == 0
        
        # Check output structure for column headers
        # We should see column headers like "Title", "Category", "Tags"
        output_lines = result.output.split('\n')
        headers_line = next((line for line in output_lines if "Title" in line), None)
        
        assert headers_line is not None
        assert "Title" in headers_line
        assert "Category" in headers_line
        assert "Tags" in headers_line
        
        # Verify all notes have their details included
        for note in sample_notes:
            # For each note, find the line that contains its title
            title_line = next((line for line in output_lines if note["title"] in line), None)
            assert title_line is not None
            
            # That line should also include the category and at least one tag
            assert note["category"] in title_line
            
            # At least one tag from the note should be in the line
            tags = note["tags"].split(",")
            assert any(tag in title_line for tag in tags)

    def test_list_custom_output_dir(self, runner):
        """Test 'list' command with a custom output directory that contains notes."""
        with tempfile.TemporaryDirectory() as main_dir:
            # Create a custom output directory
            custom_dir = os.path.join(main_dir, "custom-notes")
            os.makedirs(custom_dir)
            
            # Create a note in the custom directory
            title = "Custom Dir Note"
            result = runner.invoke(new, 
                [title, "--output-dir", custom_dir],
                catch_exceptions=False
            )
            assert result.exit_code == 0
            
            # Act - list notes specifying the custom directory
            list_result = runner.invoke(cli, 
                ["list", "--output-dir", custom_dir],
                catch_exceptions=False
            )
            
            # Assert
            assert list_result.exit_code == 0
            assert title in list_result.output
            
            # Also verify that listing from a different directory doesn't show the note
            different_dir = os.path.join(main_dir, "different-dir")
            os.makedirs(different_dir)
            
            different_result = runner.invoke(cli, 
                ["list", "--output-dir", different_dir],
                catch_exceptions=False
            )
            
            assert different_result.exit_code == 0
            assert "No notes found" in different_result.output
            assert title not in different_result.output