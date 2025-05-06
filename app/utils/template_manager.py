"""
Template management utilities for MarkNote.
"""
import os
import jinja2
from datetime import datetime
from typing import Dict, Any, List, Optional

class TemplateManager:
    """
    Manages templates for note creation.
    """
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            # Use the default templates directory in the package
            templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        
        self.templates_dir = templates_dir
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            autoescape=False,  # No need to escape in markdown
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            A list of template names.
        """
        templates = []
        for item in os.listdir(self.templates_dir):
            if os.path.isdir(os.path.join(self.templates_dir, item)):
                if os.path.exists(os.path.join(self.templates_dir, item, "template.md")):
                    templates.append(item)
        return templates
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template to render.
            context: Dictionary of variables to use in the template.
            
        Returns:
            The rendered template as a string.
            
        Raises:
            FileNotFoundError: If the template does not exist.
        """
        # Set default values if not provided
        if 'created_at' not in context:
            context['created_at'] = datetime.now().isoformat()
        if 'updated_at' not in context:
            context['updated_at'] = context.get('created_at')
        
        # Check if template exists
        template_path = os.path.join(template_name, "template.md")
        if not os.path.exists(os.path.join(self.templates_dir, template_path)):
            if template_name != "default":
                # Try default template as fallback
                template_path = os.path.join("default", "template.md")
                if not os.path.exists(os.path.join(self.templates_dir, template_path)):
                    raise FileNotFoundError(f"Template {template_name} not found")
            else:
                raise FileNotFoundError(f"Template {template_name} not found")
                
        # Render the template
        template = self.env.get_template(template_path)
        return template.render(**context)
    

    def create_template(self, template_name: str, content: Optional[str] = None, 
                        base_template: Optional[str] = None) -> str:
        """
        Create a new template with the given name and content.
        
        Args:
            template_name: Name of the template to create.
            content: Content of the template. If None, a starter template will be created.
            base_template: Name of template to use as a base. If provided, will copy from this template.
            
        Returns:
            The path to the new template file.
            
        Raises:
            FileExistsError: If the template already exists.
            ValueError: If the template name is invalid.
        """
        # Validate template name
        if not template_name or not template_name.isalnum() and not template_name.replace('_', '').isalnum():
            raise ValueError("Template name must be alphanumeric (underscores allowed)")
        
        # Check if template already exists
        template_dir = os.path.join(self.templates_dir, template_name)
        template_path = os.path.join(template_dir, "template.md")
        
        if os.path.exists(template_dir):
            raise FileExistsError(f"Template '{template_name}' already exists")
        
        # Create template directory
        os.makedirs(template_dir, exist_ok=True)
        
        # Determine template content
        if content is not None:
            # Use provided content
            template_content = content
        elif base_template is not None:
            # Copy from base template
            try:
                base_template_path = os.path.join(self.templates_dir, base_template, "template.md")
                with open(base_template_path, 'r') as f:
                    template_content = f.read()
                
                # Update the template type
                template_content = template_content.replace(f"type: {base_template}", f"type: {template_name}")
            except FileNotFoundError:
                raise FileNotFoundError(f"Base template '{base_template}' not found")
        else:
            # Use a simple starter template
            template_content = f"""---
                title: {{{{ title }}}}
                created_at: {{{{ created_at }}}}
                updated_at: {{{{ updated_at }}}}
                {{% if tags %}}tags:
                {{% for tag in tags %}}  - {{{{ tag }}}}
                {{% endfor %}}{{% endif %}}
                {{% if category %}}category: {{{{ category }}}}
                {{% endif %}}{{% if linked_notes %}}linked_notes:
                {{% for link in linked_notes %}}  - {{{{ link }}}}
                {{% endfor %}}{{% endif %}}type: {template_name}
                ---

                # {{{{ title }}}}

                ## Section 1

                Content for section 1...

                ## Section 2

                Content for section 2...

                {{% if linked_notes %}}
                ## Related Notes

                {{% for link in linked_notes %}}* [[{{{{ link }}}}]]
                {{% endfor %}}
                {{% endif %}}
                """
        
        # Write template to file
        with open(template_path, 'w') as f:
            f.write(template_content)
            
        return template_path
        
    def update_template(self, template_name: str, content: str) -> str:
        """
        Update an existing template with new content.
        
        Args:
            template_name: Name of the template to update.
            content: New content for the template.
            
        Returns:
            The path to the updated template file.
            
        Raises:
            FileNotFoundError: If the template does not exist.
        """
        template_dir = os.path.join(self.templates_dir, template_name)
        template_path = os.path.join(template_dir, "template.md")
        
        if not os.path.exists(template_dir):
            raise FileNotFoundError(f"Template '{template_name}' not found")
            
        with open(template_path, 'w') as f:
            f.write(content)
            
        return template_path
        
    def delete_template(self, template_name: str) -> bool:
        """
        Delete a template.
        
        Args:
            template_name: Name of the template to delete.
            
        Returns:
            True if the template was deleted, False otherwise.
            
        Raises:
            FileNotFoundError: If the template does not exist.
            ValueError: If attempting to delete a built-in template.
        """
        # Don't allow delete of built-in templates
        if template_name in ["default", "daily", "meeting", "journal"]:
            raise ValueError(f"Cannot delete built-in template '{template_name}'")
        
        template_dir = os.path.join(self.templates_dir, template_name)
        
        if not os.path.exists(template_dir):
            raise FileNotFoundError(f"Template '{template_name}' not found")
            
        template_path = os.path.join(template_dir, "template.md")
        
        if os.path.exists(template_path):
            os.remove(template_path)
            
        # Remove directory if empty
        if not os.listdir(template_dir):
            os.rmdir(template_dir)
            
        return True
    

def get_editor_handlers():
    """Get editor handler for opening files."""
    try:
        from app.utils.editor_handler import EditorHandler
        return EditorHandler()
    except ImportError:
        return None