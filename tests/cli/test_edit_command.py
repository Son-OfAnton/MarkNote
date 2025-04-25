"""
Unit tests for the 'edit' command functionality in the CLI.

These tests focus on the functionality of the edit command,
including note finding, note editing, and different command options.
"""
import os
import shutil
import tempfile
import pytest
from click.testing import CliRunner
from app.cli.commands import new, edit
import yaml
from app.core.note_manager import NoteManager
from app.utils.file_handler import parse_frontmatter


class TestEditCommandFunctionality:
    """Test case for the 'edit' command functionality."""

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
    def sample_note(self, runner, temp_notes_dir):
        """Create a sample note for testing edit functionality."""
        title = "Sample Edit Test Note"
        result = runner.invoke(new, 
            [title, "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        assert result.exit_code == 0
        
        # Return both the title and the file path
        note_path = os.path.join(temp_notes_dir, "sample-edit-test-note.md")
        return {"title": title, "path": note_path}

    @pytest.fixture
    def categorized_note(self, runner, temp_notes_dir):
        """Create a sample note with a category for testing edit functionality."""
        title = "Categorized Note"
        category = "test-category"
        result = runner.invoke(new, 
            [title, "--category", category, "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        assert result.exit_code == 0
        
        # Return the details
        note_path = os.path.join(temp_notes_dir, category, "categorized-note.md")
        return {"title": title, "category": category, "path": note_path}

    def test_edit_basic_functionality(self, runner, temp_notes_dir, sample_note, monkeypatch):
        """Test basic functionality of the 'edit' command."""
        # Mock the editor to modify the file
        def mock_edit_file(path, custom_editor=None):
            # Read the current content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract the frontmatter and content
            metadata, content_without_frontmatter = parse_frontmatter(content)
            
            # Modify the content
            modified_content = content_without_frontmatter.replace(
                "Add more detailed information here...",
                "This content was modified by the edit test."
            )
            
            # Rebuild the content with frontmatter
            new_content = "---\n"
            new_content += yaml.dump(metadata, default_flow_style=False)
            new_content += "---\n\n"
            new_content += modified_content
            
            # Write back to the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return True, ""
        
        # Monkeypatch the edit_file function
        monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
        
        # Act
        result = runner.invoke(edit, 
            [sample_note["title"], "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        assert "Note updated successfully" in result.output
        
        # Verify the file was actually modified
        with open(sample_note["path"], 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "This content was modified by the edit test." in content

    def test_edit_note_not_found(self, runner, temp_notes_dir):
        """Test the 'edit' command when the specified note doesn't exist."""
        # Act
        result = runner.invoke(edit, 
            ["Nonexistent Note", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_edit_with_category(self, runner, temp_notes_dir, categorized_note, monkeypatch):
        """Test editing a note within a specific category."""
        # Mock the editor to modify the file
        def mock_edit_file(path, custom_editor=None):
            # Read the current content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract the frontmatter and content
            metadata, content_without_frontmatter = parse_frontmatter(content)
            
            # Modify the content
            modified_content = content_without_frontmatter.replace(
                "Add more detailed information here...",
                "This categorized note was edited."
            )
            
            # Rebuild the content with frontmatter
            new_content = "---\n"
            new_content += yaml.dump(metadata, default_flow_style=False)
            new_content += "---\n\n"
            new_content += modified_content
            
            # Write back to the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return True, ""
        
        # Monkeypatch the edit_file function
        monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
        
        # Act - use category option to find the note
        result = runner.invoke(edit, 
            [
                categorized_note["title"],
                "--category", categorized_note["category"],
                "--output-dir", temp_notes_dir
            ],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        assert "Note updated successfully" in result.output
        
        # Verify the file was actually modified
        with open(categorized_note["path"], 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "This categorized note was edited." in content

    def test_edit_multiple_notes(self, runner, temp_notes_dir, monkeypatch):
        """Test editing multiple notes at once."""
        # Create multiple notes
        titles = ["Multiple Edit Test 1", "Multiple Edit Test 2", "Multiple Edit Test 3"]
        paths = []
        
        for title in titles:
            result = runner.invoke(new, 
                [title, "--output-dir", temp_notes_dir],
                catch_exceptions=False
            )
            assert result.exit_code == 0
            paths.append(os.path.join(temp_notes_dir, title.lower().replace(" ", "-") + ".md"))
        
        # Mock the editor to modify files
        def mock_edit_file(path, custom_editor=None):
            # Read the current content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract the frontmatter and content
            metadata, content_without_frontmatter = parse_frontmatter(content)
            
            # Modify the content
            modified_content = content_without_frontmatter.replace(
                "Add more detailed information here...",
                "This note was batch edited."
            )
            
            # Rebuild the content with frontmatter
            new_content = "---\n"
            new_content += yaml.dump(metadata, default_flow_style=False)
            new_content += "---\n\n"
            new_content += modified_content
            
            # Write back to the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return True, ""
        
        # Monkeypatch the edit_file function
        monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
        
        # Act - edit all notes at once
        result = runner.invoke(edit, 
            titles + ["--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        assert "Note updated successfully" in result.output
        
        # Verify all files were correctly modified
        for path in paths:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "This note was batch edited." in content

    def test_edit_with_custom_editor(self, runner, temp_notes_dir, sample_note, monkeypatch):
        """Test the 'edit' command with a custom editor specified."""
        edit_called_with = {}
        
        # Mock the edit_file function to record what it was called with
        def mock_edit_file(path, custom_editor=None):
            edit_called_with['path'] = path
            edit_called_with['editor'] = custom_editor
            
            # Perform a simple modification to simulate editing
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified_content = content.replace(
                "Add more detailed information here...",
                "Edited with custom editor."
            )
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
                
            return True, ""
        
        # Monkeypatch the edit_file function
        monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
        
        # Act
        custom_editor = "custom-editor"
        result = runner.invoke(edit, 
            [sample_note["title"], "--editor", custom_editor, "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check that edit_file was called with the right editor
        assert edit_called_with['path'] == sample_note["path"]
        assert edit_called_with['editor'] == custom_editor

    def test_edit_with_invalid_editor(self, runner, temp_notes_dir, sample_note, monkeypatch):
        """Test the 'edit' command with an invalid editor specified."""
        # Mock the is_valid_editor function to reject our editor
        def mock_is_valid_editor(editor):
            return editor != "invalid-editor"
        
        # Monkeypatch the is_valid_editor function
        monkeypatch.setattr("app.cli.commands.is_valid_editor", mock_is_valid_editor)
        
        # Act
        result = runner.invoke(edit, 
            [sample_note["title"], "--editor", "invalid-editor", "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Specified editor 'invalid-editor' not found" in result.output

    def test_edit_with_output_dir(self, runner, sample_note, monkeypatch):
        """Test specifying a custom output directory for editing."""
        # Create a different temporary directory
        with tempfile.TemporaryDirectory() as other_temp_dir:
            # Copy the sample note to this directory to simulate it being there
            other_note_path = os.path.join(other_temp_dir, os.path.basename(sample_note["path"]))
            shutil.copy(sample_note["path"], other_note_path)
            
            # Mock the edit_file function
            def mock_edit_file(path, custom_editor=None):
                # Verify this is the path we expect (in the other directory)
                assert path == other_note_path
                
                # Perform a simple modification
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                modified_content = content.replace(
                    "Add more detailed information here...",
                    "Edited in custom directory."
                )
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                    
                return True, ""
            
            # Monkeypatch the edit_file function
            monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
            
            # Act - specify the other directory
            result = runner.invoke(edit, 
                [sample_note["title"], "--output-dir", other_temp_dir],
                catch_exceptions=False
            )
            
            # Assert
            assert result.exit_code == 0
            
            # Verify the file in the other directory was modified
            with open(other_note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "Edited in custom directory." in content

    def test_edit_maintains_metadata(self, runner, temp_notes_dir, monkeypatch):
        """Test that editing a note preserves its metadata."""
        # Create a note with specific metadata
        title = "Metadata Test Note"
        tags = "tag1,tag2,important"
        category = "meta-tests"
        
        create_result = runner.invoke(new, 
            [
                title, 
                "--tags", tags, 
                "--category", category,
                "--output-dir", temp_notes_dir
            ],
            catch_exceptions=False
        )
        assert create_result.exit_code == 0
        
        note_path = os.path.join(temp_notes_dir, category, "metadata-test-note.md")
        
        # Mock the edit_file function
        def mock_edit_file(path, custom_editor=None):
            # Read the current content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract the frontmatter and content
            metadata, content_without_frontmatter = parse_frontmatter(content)
            
            # Modify only the content, not the frontmatter
            modified_content = content_without_frontmatter.replace(
                "Add more detailed information here...",
                "This content was modified but metadata should be preserved."
            )
            
            # Rebuild the content with the same frontmatter
            new_content = "---\n"
            new_content += yaml.dump(metadata, default_flow_style=False)
            new_content += "---\n\n"
            new_content += modified_content
            
            # Write back to the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return True, ""
        
        # Monkeypatch the edit_file function
        monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
        
        # Act - edit the note
        edit_result = runner.invoke(edit, 
            [title, "--category", category, "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert edit_result.exit_code == 0
        
        # Read the file and verify metadata was preserved
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract and check the frontmatter
        metadata, _ = parse_frontmatter(content)
        
        # Verify metadata is preserved
        assert metadata['title'] == title
        assert len(metadata['tags']) == 3
        assert 'tag1' in metadata['tags']
        assert 'tag2' in metadata['tags']
        assert 'important' in metadata['tags']
        assert metadata['category'] == category
        
        # Also verify the content was actually modified
        assert "This content was modified but metadata should be preserved." in content

    def test_edit_error_handling(self, runner, temp_notes_dir, sample_note, monkeypatch):
        """Test error handling during note editing."""
        # Mock the edit_file function to return an error
        def mock_edit_file(path, custom_editor=None):
            return False, "Simulated editor error for testing"
        
        # Monkeypatch the edit_file function
        monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
        
        # Act
        result = runner.invoke(edit, 
            [sample_note["title"], "--output-dir", temp_notes_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Simulated editor error for testing" in result.output