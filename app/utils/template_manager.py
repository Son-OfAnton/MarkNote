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