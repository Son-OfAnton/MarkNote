"""
Unit tests for the 'new' command options in the CLI.

These tests focus on how the different options of the 'new' command 
affect the note creation process.
"""
import os
import shutil
import tempfile
import pytest
from click.testing import CliRunner
from app.cli.commands import new
import yaml


class TestNewCommandOptions:
    """Test case for the 'new' command options."""

    @pytest.fixture
    def runner(self):
        """Provide a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for output files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)

    def test_new_with_template_option(self, runner, temp_output_dir):
        """Test the 'new' command with the --template option."""
        # Arrange
        title = "Template Option Test"
        template = "meeting"  # Use meeting template
        
        # Act
        result = runner.invoke(new, 
            [title, "--template", template, "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check if file was created
        expected_filename = "template-option-test.md"
        expected_path = os.path.join(temp_output_dir, expected_filename)
        assert os.path.exists(expected_path)
        
        # Read the file content and check for meeting template sections
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # The meeting template should include specific sections
        assert '## Meeting Details' in content
        assert '## Agenda' in content
        assert '## Discussion' in content
        assert '## Action Items' in content

    def test_new_with_tags_option(self, runner, temp_output_dir):
        """Test the 'new' command with the --tags option."""
        # Arrange
        title = "Tags Option Test"
        tags = "test,example,unit-test"
        
        # Act
        result = runner.invoke(new, 
            [title, "--tags", tags, "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check if file was created
        expected_filename = "tags-option-test.md"
        expected_path = os.path.join(temp_output_dir, expected_filename)
        assert os.path.exists(expected_path)
        
        # Read the file content and verify the frontmatter
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter
        frontmatter_end_index = content.find('---', 3)
        frontmatter = content[3:frontmatter_end_index].strip()
        metadata = yaml.safe_load(frontmatter)
        
        # Check that the tags were properly included
        assert 'tags' in metadata
        assert len(metadata['tags']) == 3
        assert 'test' in metadata['tags']
        assert 'example' in metadata['tags']
        assert 'unit-test' in metadata['tags']

    def test_new_with_category_option(self, runner, temp_output_dir):
        """Test the 'new' command with the --category option."""
        # Arrange
        title = "Category Option Test"
        category = "test-category"
        
        # Act
        result = runner.invoke(new, 
            [title, "--category", category, "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check if file was created in the category subdirectory
        expected_filename = "category-option-test.md"
        expected_category_dir = os.path.join(temp_output_dir, category)
        expected_path = os.path.join(expected_category_dir, expected_filename)
        
        assert os.path.exists(expected_category_dir)
        assert os.path.exists(expected_path)
        
        # Read the file content and verify the frontmatter includes the category
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter
        frontmatter_end_index = content.find('---', 3)
        frontmatter = content[3:frontmatter_end_index].strip()
        metadata = yaml.safe_load(frontmatter)
        
        # Check that the category was properly included
        assert 'category' in metadata
        assert metadata['category'] == category

    def test_new_with_force_option(self, runner, temp_output_dir):
        """Test the 'new' command with the --force option to overwrite existing notes."""
        # Arrange
        title = "Force Option Test"
        
        # Act - Create the note first time
        initial_result = runner.invoke(new, 
            [title, "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        assert initial_result.exit_code == 0
        
        # Try to create it again without --force (should fail)
        repeat_result = runner.invoke(new, 
            [title, "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        # This should have an error code
        assert repeat_result.exit_code == 1
        
        # Try with --force (should succeed)
        force_result = runner.invoke(new, 
            [title, "--force", "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert force_result.exit_code == 0
        assert "Note created successfully" in force_result.output

    def test_new_with_output_dir_option(self, runner):
        """Test the 'new' command with the --output-dir option to specify a custom location."""
        # Arrange
        title = "Output Dir Test"
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_output = os.path.join(temp_dir, "custom-notes")
            
            # Act
            result = runner.invoke(new, 
                [title, "--output-dir", custom_output],
                catch_exceptions=False
            )
            
            # Assert
            assert result.exit_code == 0
            
            # Check that the custom directory was created
            assert os.path.exists(custom_output)
            
            # Check if file was created in the custom directory
            expected_filename = "output-dir-test.md"
            expected_path = os.path.join(custom_output, expected_filename)
            assert os.path.exists(expected_path)

    def test_new_with_editor_option(self, runner, temp_output_dir, monkeypatch):
        """Test the 'new' command with the --editor option."""
        # Skip this test if in CI environment or no editor available
        import os
        if os.environ.get("CI") == "true":
            pytest.skip("Skipping editor test in CI environment")
        
        # Use a mock for the edit function to avoid actually opening an editor
        def mock_edit_file(path, custom_editor=None):
            # Just record that this was called with the right editor
            mock_edit_file.called = True
            mock_edit_file.path = path
            mock_edit_file.editor = custom_editor
            return True, ""
            
        mock_edit_file.called = False
        mock_edit_file.path = None
        mock_edit_file.editor = None
        
        # Monkeypatch the edit_file function
        from app.utils.editor_handler import edit_file
        monkeypatch.setattr("app.cli.commands.edit_file", mock_edit_file)
        
        # Also monkeypatch the Confirm.ask function to return True for editing
        from rich.prompt import Confirm
        monkeypatch.setattr(Confirm, "ask", lambda *args, **kwargs: True)
        
        # Arrange
        title = "Editor Option Test"
        editor = "nano"  # Choose a common editor
        
        # Act
        result = runner.invoke(new, 
            [title, "--editor", editor, "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check if file was created
        expected_filename = "editor-option-test.md"
        expected_path = os.path.join(temp_output_dir, expected_filename)
        assert os.path.exists(expected_path)
        
        # Check that edit_file was called with the right editor
        assert mock_edit_file.called
        assert mock_edit_file.path == expected_path
        assert mock_edit_file.editor == editor

    def test_new_with_multiple_options(self, runner, temp_output_dir):
        """Test the 'new' command with multiple options combined."""
        # Arrange
        title = "Multiple Options Test"
        template = "journal"
        category = "journal-entries"
        tags = "test,combined,options"
        
        # Act
        result = runner.invoke(new, 
            [
                title, 
                "--template", template,
                "--category", category,
                "--tags", tags,
                "--output-dir", temp_output_dir
            ],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 0
        
        # Check if file was created in the right location
        expected_filename = "multiple-options-test.md"
        expected_category_dir = os.path.join(temp_output_dir, category)
        expected_path = os.path.join(expected_category_dir, expected_filename)
        
        assert os.path.exists(expected_path)
        
        # Read the file and verify all options were applied
        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter
        frontmatter_end_index = content.find('---', 3)
        frontmatter = content[3:frontmatter_end_index].strip()
        metadata = yaml.safe_load(frontmatter)
        
        # Verify all options
        assert metadata['title'] == title
        assert 'tags' in metadata and len(metadata['tags']) == 3
        assert metadata['category'] == category
        assert metadata['type'] == 'journal'  # Type from the journal template
        
        # Verify journal template content
        assert "Today's Highlights" in content
        assert "Thoughts and Reflections" in content
        assert "Gratitude" in content

    def test_new_with_nonexistent_template(self, runner, temp_output_dir):
        """Test the 'new' command with a nonexistent template."""
        # Arrange
        title = "Bad Template Test"
        template = "nonexistent_template"
        
        # Act
        result = runner.invoke(new, 
            [title, "--template", template, "--output-dir", temp_output_dir],
            catch_exceptions=False
        )
        
        # Assert
        assert result.exit_code == 1  # Should exit with error
        assert "Error" in result.output
        assert f"Template '{template}' not found" in result.output
        
        # Check that file was not created
        expected_filename = "bad-template-test.md"
        expected_path = os.path.join(temp_output_dir, expected_filename)
        assert not os.path.exists(expected_path)