"""
Unit tests for the 'templates' command functionality in the CLI.

These tests focus on the functionality of the templates command,
which lists available note templates.
"""
import os
import shutil
import tempfile
import pytest
from click.testing import CliRunner
from app.cli.commands import cli


class TestTemplatesCommandFunctionality:
    """Test case for the 'templates' command functionality."""

    @pytest.fixture
    def runner(self):
        """Provide a Click CLI test runner."""
        return CliRunner()

    def test_templates_basic_functionality(self, runner):
        """Test basic functionality of the 'templates' command."""
        # Act
        result = runner.invoke(cli, ["templates"], catch_exceptions=False)
        
        # Assert
        assert result.exit_code == 0
        
        # Should list the default templates
        assert "default" in result.output
        assert "meeting" in result.output
        assert "journal" in result.output
        
        # The output should indicate these are templates
        assert "Available templates" in result.output

    def test_templates_output_format(self, runner):
        """Test that the output format of the templates command is as expected."""
        # Act
        result = runner.invoke(cli, ["templates"], catch_exceptions=False)
        
        # Assert
        assert result.exit_code == 0
        
        # Split the output into lines for detailed checking
        output_lines = result.output.strip().split('\n')
        
        # There should be at least 4 lines:
        # 1. "Available templates" header
        # 2. "- default" template
        # 3. "- meeting" template
        # 4. "- journal" template
        assert len(output_lines) >= 4
        
        # The first line should be the header
        assert "Available templates" in output_lines[0]
        
        # The next lines should each list a template (order may vary)
        template_lines = output_lines[1:]
        template_names = [line.strip().replace('- ', '') for line in template_lines if line.strip().startswith('- ')]
        
        # Check that all expected templates are listed
        assert "default" in template_names
        assert "meeting" in template_names
        assert "journal" in template_names

    def test_templates_with_custom_templates(self, runner):
        """Test templates command with custom templates added."""
        # Create a temporary directory to add custom templates
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy the app into the temp directory
            app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app'))
            temp_app_dir = os.path.join(temp_dir, 'app')
            shutil.copytree(app_dir, temp_app_dir)
            
            # Create a custom template
            custom_template_dir = os.path.join(temp_app_dir, 'templates', 'custom')
            os.makedirs(custom_template_dir, exist_ok=True)
            
            # Create a template.md file in the custom template directory
            with open(os.path.join(custom_template_dir, 'template.md'), 'w', encoding='utf-8') as f:
                f.write("""---
title: {{ title }}
created_at: {{ created_at }}
updated_at: {{ updated_at }}
{% if tags %}tags:
{% for tag in tags %}  - {{ tag }}
{% endfor %}{% endif %}
{% if category %}category: {{ category }}
{% endif %}type: custom
---

# {{ title }}

## Custom Template Section

This is a custom template for testing.
""")
            
            # Adjust the Python path to include our temp directory
            import sys
            sys.path.insert(0, temp_dir)
            
            try:
                # Run the templates command
                # We need to import the CLI from our modified app
                from app.cli.commands import cli as temp_cli
                
                # Act
                result = runner.invoke(temp_cli, ["templates"], catch_exceptions=False)
                
                # Assert
                assert result.exit_code == 0
                
                # Should list the default templates and our custom template
                assert "default" in result.output
                assert "meeting" in result.output
                assert "journal" in result.output
                assert "custom" in result.output
            finally:
                # Restore the Python path
                sys.path.remove(temp_dir)
    
    def test_templates_after_removing_template(self, runner):
        """Test templates command after removing a template."""
        # Create a temporary directory to modify templates
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy the app into the temp directory
            app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app'))
            temp_app_dir = os.path.join(temp_dir, 'app')
            shutil.copytree(app_dir, temp_app_dir)
            
            # Remove a template (journal)
            journal_template_dir = os.path.join(temp_app_dir, 'templates', 'journal')
            shutil.rmtree(journal_template_dir)
            
            # Adjust the Python path to include our temp directory
            import sys
            sys.path.insert(0, temp_dir)
            
            try:
                # Run the templates command
                from app.cli.commands import cli as temp_cli
                
                # Act
                result = runner.invoke(temp_cli, ["templates"], catch_exceptions=False)
                
                # Assert
                assert result.exit_code == 0
                
                # Should list the remaining templates but not journal
                assert "default" in result.output
                assert "meeting" in result.output
                assert "journal" not in result.output
            finally:
                # Restore the Python path
                sys.path.remove(temp_dir)

    def test_templates_with_damaged_template(self, runner):
        """Test templates command when a template directory exists but has no template.md file."""
        # Create a temporary directory to add damaged templates
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy the app into the temp directory
            app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app'))
            temp_app_dir = os.path.join(temp_dir, 'app')
            shutil.copytree(app_dir, temp_app_dir)
            
            # Create a damaged template (directory without template.md)
            broken_template_dir = os.path.join(temp_app_dir, 'templates', 'broken')
            os.makedirs(broken_template_dir, exist_ok=True)
            
            # Create a different file, not template.md
            with open(os.path.join(broken_template_dir, 'not-a-template.txt'), 'w', encoding='utf-8') as f:
                f.write("This is not a template file")
            
            # Adjust the Python path to include our temp directory
            import sys
            sys.path.insert(0, temp_dir)
            
            try:
                # Run the templates command
                from app.cli.commands import cli as temp_cli
                
                # Act
                result = runner.invoke(temp_cli, ["templates"], catch_exceptions=False)
                
                # Assert
                assert result.exit_code == 0
                
                # Should list only the valid templates, not the broken one
                assert "default" in result.output
                assert "meeting" in result.output
                assert "journal" in result.output
                assert "broken" not in result.output
            finally:
                # Restore the Python path
                sys.path.remove(temp_dir)
    
    def test_templates_with_empty_templates_dir(self, runner):
        """Test templates command when the templates directory is empty."""
        # Create a temporary directory with an empty templates dir
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy the app into the temp directory
            app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app'))
            temp_app_dir = os.path.join(temp_dir, 'app')
            shutil.copytree(app_dir, temp_app_dir)
            
            # Remove all template directories
            templates_dir = os.path.join(temp_app_dir, 'templates')
            for item in os.listdir(templates_dir):
                item_path = os.path.join(templates_dir, item)
                if os.path.isdir(item_path) and item != "__pycache__":
                    shutil.rmtree(item_path)
            
            # Adjust the Python path to include our temp directory
            import sys
            sys.path.insert(0, temp_dir)
            
            try:
                # Run the templates command
                from app.cli.commands import cli as temp_cli
                
                # Act
                result = runner.invoke(temp_cli, ["templates"], catch_exceptions=False)
                
                # Assert
                assert result.exit_code == 0
                
                # Should indicate no templates found
                assert "No templates found" in result.output
            finally:
                # Restore the Python path
                sys.path.remove(temp_dir)

    def test_templates_graceful_error_handling(self, runner, monkeypatch):
        """Test the templates command handles errors gracefully."""
        # Mock the TemplateManager.list_templates method to raise an exception
        def mock_list_templates(*args, **kwargs):
            raise Exception("Simulated error in template listing")
        
        # Apply the monkeypatch
        from app.utils.template_manager import TemplateManager
        monkeypatch.setattr(TemplateManager, "list_templates", mock_list_templates)
        
        # Act
        result = runner.invoke(cli, ["templates"], catch_exceptions=False)
        
        # Assert
        assert result.exit_code == 1  # Should exit with error
        assert "Error" in result.output
        assert "Simulated error" in result.output