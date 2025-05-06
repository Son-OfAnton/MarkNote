"""
Tests for the template management functionality in TemplateManager.
"""
import os
import shutil
import tempfile
from unittest import TestCase, mock
from typing import List, Dict, Any, Optional

from app.utils.template_manager import TemplateManager


class TestTemplateManager(TestCase):
    """Test cases for the TemplateManager class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create template directories with sample templates
        self.setup_test_templates()
        
        # Create a TemplateManager with the test directory
        self.template_manager = TemplateManager(templates_dir=self.test_dir)

    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def setup_test_templates(self):
        """Set up test templates in the test directory."""
        # Create default template directory
        default_dir = os.path.join(self.test_dir, "default")
        os.makedirs(default_dir)
        
        # Create default template file
        with open(os.path.join(default_dir, "template.md"), "w") as f:
            f.write("""---
title: {{ title }}
created_at: {{ created_at }}
updated_at: {{ updated_at }}
type: default
---

# {{ title }}

## Default Template Content

This is a default template for testing.
""")
        
        # Create another built-in template
        meeting_dir = os.path.join(self.test_dir, "meeting")
        os.makedirs(meeting_dir)
        with open(os.path.join(meeting_dir, "template.md"), "w") as f:
            f.write("""---
title: {{ title }}
created_at: {{ created_at }}
updated_at: {{ updated_at }}
type: meeting
---

# {{ title }}

## Meeting Notes

Meeting details go here.
""")

    def test_list_templates(self):
        """Test listing available templates."""
        templates = self.template_manager.list_templates()
        
        # Should find the templates we created
        self.assertIn("default", templates)
        self.assertIn("meeting", templates)
        self.assertEqual(len(templates), 2)

    def test_create_template_basic(self):
        """Test creating a new template with default content."""
        template_name = "test_template"
        
        # Create a new template
        template_path = self.template_manager.create_template(template_name)
        
        # Check that the template file was created
        self.assertTrue(os.path.exists(template_path))
        self.assertEqual(os.path.basename(template_path), "template.md")
        self.assertEqual(os.path.dirname(template_path), os.path.join(self.test_dir, template_name))
        
        # Check the template content
        with open(template_path, "r") as f:
            content = f.read()
            
        # Verify the content contains the template name
        self.assertIn(f"type: {template_name}", content)
        self.assertIn("# {{ title }}", content)
        
        # Verify the template is now in the list
        templates = self.template_manager.list_templates()
        self.assertIn(template_name, templates)

    def test_create_template_with_content(self):
        """Test creating a template with custom content."""
        template_name = "custom_content"
        custom_content = """---
title: {{ title }}
created_at: {{ created_at }}
type: custom_content
---

# {{ title }}

## Custom Content

This is custom template content.
"""
        
        # Create a template with custom content
        template_path = self.template_manager.create_template(template_name, content=custom_content)
        
        # Check that the template was created
        self.assertTrue(os.path.exists(template_path))
        
        # Check the content
        with open(template_path, "r") as f:
            content = f.read()
            
        self.assertEqual(content, custom_content)

    def test_create_template_based_on_existing(self):
        """Test creating a template based on an existing template."""
        template_name = "meeting_clone"
        base_template = "meeting"
        
        # Create a template based on an existing one
        template_path = self.template_manager.create_template(template_name, base_template=base_template)
        
        # Check that the template was created
        self.assertTrue(os.path.exists(template_path))
        
        # Check the content
        with open(template_path, "r") as f:
            content = f.read()
            
        # Should be based on meeting template but with updated type
        self.assertIn("## Meeting Notes", content)
        self.assertIn(f"type: {template_name}", content)
        self.assertNotIn("type: meeting", content)

    def test_create_template_with_invalid_name(self):
        """Test creating a template with an invalid name."""
        # Test with invalid names
        invalid_names = ["", "test with spaces", "test/with/slashes", "test!@#$"]
        
        for name in invalid_names:
            with self.assertRaises(ValueError):
                self.template_manager.create_template(name)

    def test_create_template_already_exists(self):
        """Test creating a template that already exists."""
        # Create a template
        template_name = "already_exists"
        self.template_manager.create_template(template_name)
        
        # Try to create it again
        with self.assertRaises(FileExistsError):
            self.template_manager.create_template(template_name)

    def test_update_template(self):
        """Test updating an existing template."""
        # Create a template first
        template_name = "update_test"
        self.template_manager.create_template(template_name)
        
        # New content to update with
        new_content = """---
title: {{ title }}
updated_at: {{ updated_at }}
type: update_test
---

# {{ title }}

## Updated Content

This content has been updated.
"""
        
        # Update the template
        updated_path = self.template_manager.update_template(template_name, new_content)
        
        # Check that the path is correct
        self.assertEqual(os.path.basename(updated_path), "template.md")
        self.assertEqual(os.path.dirname(updated_path), os.path.join(self.test_dir, template_name))
        
        # Check the updated content
        with open(updated_path, "r") as f:
            content = f.read()
            
        self.assertEqual(content, new_content)

    def test_update_nonexistent_template(self):
        """Test updating a template that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.template_manager.update_template("nonexistent", "Some content")

    def test_delete_template(self):
        """Test deleting a template."""
        # Create a template first
        template_name = "delete_test"
        template_path = self.template_manager.create_template(template_name)
        
        # Verify it exists
        self.assertTrue(os.path.exists(template_path))
        
        # Delete the template
        result = self.template_manager.delete_template(template_name)
        
        # Check the result and that the file is gone
        self.assertTrue(result)
        self.assertFalse(os.path.exists(template_path))
        self.assertFalse(os.path.exists(os.path.dirname(template_path)))  # Directory should be gone too
        
        # Should not be in the list anymore
        templates = self.template_manager.list_templates()
        self.assertNotIn(template_name, templates)

    def test_delete_builtin_template(self):
        """Test attempting to delete a built-in template."""
        # Try to delete the default template
        with self.assertRaises(ValueError):
            self.template_manager.delete_template("default")
            
        # Default template should still exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "default", "template.md")))
        
        # Should still be in the list
        templates = self.template_manager.list_templates()
        self.assertIn("default", templates)

    def test_delete_nonexistent_template(self):
        """Test deleting a template that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.template_manager.delete_template("nonexistent")

    def test_render_template(self):
        """Test rendering a template with context variables."""
        # Create a test context
        context = {
            "title": "Test Title",
            "created_at": "2024-05-05T12:00:00",
            "updated_at": "2024-05-05T12:00:00"
        }
        
        # Render the default template
        rendered = self.template_manager.render_template("default", context)
        
        # Check rendered content
        self.assertIn("# Test Title", rendered)
        self.assertIn("created_at: 2024-05-05T12:00:00", rendered)
        self.assertIn("## Default Template Content", rendered)
        
    def test_render_nonexistent_template(self):
        """Test rendering a template that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.template_manager.render_template("nonexistent", {})