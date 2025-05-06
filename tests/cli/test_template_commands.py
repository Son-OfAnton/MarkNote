"""
Tests for the template management CLI commands.
"""
import os
import tempfile
import shutil
from unittest import TestCase, mock
from click.testing import CliRunner
from typing import Dict, Any, List, Optional

from app.cli.commands import register_template_commands
from app.utils.template_manager import TemplateManager


class TestTemplateCommandsCLI(TestCase):
    """Test cases for template management CLI commands."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create a CLI runner
        self.runner = CliRunner()
        
        # Create a mock click group for testing
        self.mock_group = mock.MagicMock()
        
        # Register template commands to the mock group
        register_template_commands(self.mock_group)
        
        # Extract the template management commands for testing
        self.create_template_func = None
        self.edit_template_func = None
        self.show_template_func = None
        self.delete_template_func = None
        self.copy_template_func = None
        self.list_templates_func = None
        
        for args, kwargs in self.mock_group.group.return_value.command.call_args_list:
            if 'name' in kwargs:
                if kwargs['name'] == 'create':
                    self.create_template_func = kwargs['callback']
                elif kwargs['name'] == 'edit':
                    self.edit_template_func = kwargs['callback']
                elif kwargs['name'] == 'show':
                    self.show_template_func = kwargs['callback']
                elif kwargs['name'] == 'delete':
                    self.delete_template_func = kwargs['callback']
                elif kwargs['name'] == 'copy':
                    self.copy_template_func = kwargs['callback']
                elif kwargs['name'] == 'list':
                    self.list_templates_func = kwargs['callback']
        
        # Create a mock template manager
        self.mock_template_manager = mock.MagicMock(spec=TemplateManager)
        
        # Create a patch for the TemplateManager constructor
        self.template_manager_patch = mock.patch('app.cli.commands.TemplateManager',
                                                return_value=self.mock_template_manager)
        
        # Create a patch for the editor handler
        self.editor_handler_patch = mock.patch('app.cli.commands.get_editor_handlers')
        self.mock_editor_handler = mock.MagicMock()
        self.mock_editor_handler.edit_file = mock.MagicMock(return_value=True)
        self.mock_get_editor_handlers = self.editor_handler_patch.start()
        self.mock_get_editor_handlers.return_value = self.mock_editor_handler

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
        
        # Stop editor handler patch if it was started
        self.editor_handler_patch.stop()

    def test_create_template_basic(self):
        """Test basic template creation."""
        with self.template_manager_patch:
            # Mock template creation
            template_path = os.path.join(self.test_dir, "new_template", "template.md")
            self.mock_template_manager.create_template.return_value = template_path
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function
                result = self.create_template_func(
                    name="new_template",
                    base_template=None,
                    editor=None,
                    open_editor=False,
                    empty=False,
                    yes=False
                )
                
                # Check function returned success
                self.assertEqual(result, 0)
                
                # Check template manager was called correctly
                self.mock_template_manager.create_template.assert_called_once_with(
                    "new_template", None, None
                )
                
                # Editor should not be called
                self.mock_editor_handler.edit_file.assert_not_called()

    def test_create_template_with_base(self):
        """Test creating a template based on an existing one."""
        with self.template_manager_patch:
            # Mock template creation
            template_path = os.path.join(self.test_dir, "new_template", "template.md")
            self.mock_template_manager.create_template.return_value = template_path
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function with base template
                result = self.create_template_func(
                    name="new_template",
                    base_template="meeting",
                    editor=None,
                    open_editor=False,
                    empty=False,
                    yes=False
                )
                
                # Check function returned success
                self.assertEqual(result, 0)
                
                # Check template manager was called with base template
                self.mock_template_manager.create_template.assert_called_once_with(
                    "new_template", None, "meeting"
                )

    def test_create_template_empty(self):
        """Test creating an empty template."""
        with self.template_manager_patch:
            # Mock template creation
            template_path = os.path.join(self.test_dir, "empty_template", "template.md")
            self.mock_template_manager.create_template.return_value = template_path
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function with empty flag
                result = self.create_template_func(
                    name="empty_template",
                    base_template=None,
                    editor=None,
                    open_editor=False,
                    empty=True,
                    yes=False
                )
                
                # Check function returned success
                self.assertEqual(result, 0)
                
                # Check template manager was called with empty content
                self.mock_template_manager.create_template.assert_called_once_with(
                    "empty_template", "", None
                )

    def test_create_template_open_editor(self):
        """Test creating a template and opening it in editor."""
        with self.template_manager_patch:
            # Mock template creation
            template_path = os.path.join(self.test_dir, "edit_template", "template.md")
            self.mock_template_manager.create_template.return_value = template_path
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function with open_editor flag
                result = self.create_template_func(
                    name="edit_template",
                    base_template=None,
                    editor=None,
                    open_editor=True,
                    empty=False,
                    yes=False
                )
                
                # Check function returned success
                self.assertEqual(result, 0)
                
                # Check editor was called
                self.mock_editor_handler.edit_file.assert_called_once_with(
                    template_path, None
                )

    def test_create_template_with_specific_editor(self):
        """Test creating a template and opening it in a specific editor."""
        with self.template_manager_patch:
            # Mock template creation
            template_path = os.path.join(self.test_dir, "edit_template", "template.md")
            self.mock_template_manager.create_template.return_value = template_path
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function with editor specified
                result = self.create_template_func(
                    name="edit_template",
                    base_template=None,
                    editor="vim",
                    open_editor=False,
                    empty=False,
                    yes=False
                )
                
                # Check function returned success
                self.assertEqual(result, 0)
                
                # Check editor was called with the specified editor
                self.mock_editor_handler.edit_file.assert_called_once_with(
                    template_path, "vim"
                )

    def test_create_template_with_invalid_name(self):
        """Test creating a template with an invalid name."""
        with self.template_manager_patch:
            # Mock template creation to raise ValueError
            self.mock_template_manager.create_template.side_effect = ValueError("Invalid template name")
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function with invalid name
                result = self.create_template_func(
                    name="invalid name",
                    base_template=None,
                    editor=None,
                    open_editor=False,
                    empty=False,
                    yes=False
                )
                
                # Should return error code
                self.assertEqual(result, 1)

    def test_edit_template(self):
        """Test editing an existing template."""
        with self.template_manager_patch:
            # Mock that template exists
            template_path = os.path.join(self.test_dir, "existing_template", "template.md")
            self.mock_template_manager.templates_dir = self.test_dir
            
            # Create the directory structure for the test
            os.makedirs(os.path.join(self.test_dir, "existing_template"))
            with open(template_path, "w") as f:
                f.write("Test content")
            
            # Call the function
            result = self.edit_template_func(
                name="existing_template",
                output=None,
                editor=None
            )
            
            # Check function returned success
            self.assertEqual(result, 0)
            
            # Check editor was called
            self.mock_editor_handler.edit_file.assert_called_once_with(
                template_path, None
            )

    def test_edit_template_with_specific_editor(self):
        """Test editing a template with a specific editor."""
        with self.template_manager_patch:
            # Mock that template exists
            template_path = os.path.join(self.test_dir, "existing_template", "template.md")
            self.mock_template_manager.templates_dir = self.test_dir
            
            # Create the directory structure for the test
            os.makedirs(os.path.join(self.test_dir, "existing_template"))
            with open(template_path, "w") as f:
                f.write("Test content")
            
            # Call the function with editor specified
            result = self.edit_template_func(
                name="existing_template",
                output=None,
                editor="nano"
            )
            
            # Check function returned success
            self.assertEqual(result, 0)
            
            # Check editor was called with the specified editor
            self.mock_editor_handler.edit_file.assert_called_once_with(
                template_path, "nano"
            )

    def test_edit_nonexistent_template(self):
        """Test editing a template that doesn't exist."""
        with self.template_manager_patch:
            # Set templates directory
            self.mock_template_manager.templates_dir = self.test_dir
            
            # Call the function with nonexistent template
            result = self.edit_template_func(
                name="nonexistent",
                output=None,
                editor=None
            )
            
            # Should return error code
            self.assertEqual(result, 1)
            
            # Editor should not be called
            self.mock_editor_handler.edit_file.assert_not_called()

    def test_delete_template(self):
        """Test deleting a template."""
        with self.template_manager_patch:
            # Mock successful deletion
            self.mock_template_manager.delete_template.return_value = True
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function
                result = self.delete_template_func(
                    name="custom_template",
                    yes=False
                )
                
                # Check function returned success
                self.assertEqual(result, 0)
                
                # Check template manager was called
                self.mock_template_manager.delete_template.assert_called_once_with(
                    "custom_template"
                )

    def test_delete_template_without_confirmation(self):
        """Test deleting a template when user declines confirmation."""
        with self.template_manager_patch:
            # Mock confirmation as False
            with mock.patch('click.confirm', return_value=False):
                # Call the function
                result = self.delete_template_func(
                    name="custom_template",
                    yes=False
                )
                
                # Check function returned success but no deletion occurred
                self.assertEqual(result, 0)
                
                # Check template manager was not called
                self.mock_template_manager.delete_template.assert_not_called()

    def test_delete_template_with_yes_flag(self):
        """Test deleting a template with --yes flag to skip confirmation."""
        with self.template_manager_patch:
            # Mock successful deletion
            self.mock_template_manager.delete_template.return_value = True
            
            # Call the function with yes flag
            result = self.delete_template_func(
                name="custom_template",
                yes=True
            )
            
            # Check function returned success
            self.assertEqual(result, 0)
            
            # Check template manager was called
            self.mock_template_manager.delete_template.assert_called_once()

    def test_delete_builtin_template(self):
        """Test attempting to delete a built-in template."""
        with self.template_manager_patch:
            # Mock deletion to raise ValueError for built-in template
            self.mock_template_manager.delete_template.side_effect = ValueError("Cannot delete built-in template")
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function
                result = self.delete_template_func(
                    name="default",
                    yes=False
                )
                
                # Should return error code
                self.assertEqual(result, 1)

    def test_copy_template(self):
        """Test copying a template."""
        with self.template_manager_patch:
            # Mock template creation
            template_path = os.path.join(self.test_dir, "new_copy", "template.md")
            self.mock_template_manager.create_template.return_value = template_path
            
            # Mock confirmation
            with mock.patch('click.confirm', return_value=True):
                # Call the function
                result = self.copy_template_func(
                    source="original",
                    destination="new_copy",
                    yes=False
                )
                
                # Check function returned success
                self.assertEqual(result, 0)
                
                # These assertions may need adjustment based on your exact implementation
                self.mock_template_manager.create_template.assert_called_once()

    def test_list_templates(self):
        """Test listing templates."""
        with self.template_manager_patch:
            # Mock template listing
            self.mock_template_manager.list_templates.return_value = ["default", "meeting", "custom"]
            
            # Call the function
            result = self.list_templates_func(
                details=False
            )
            
            # Check function returned success
            self.assertEqual(result, 0)
            
            # Check template manager was called
            self.mock_template_manager.list_templates.assert_called_once()