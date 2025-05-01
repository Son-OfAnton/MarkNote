"""
PDF export functionality for MarkNote.

This module provides utilities to export Markdown notes to PDF format.
"""
import os
from typing import Dict, Any, Optional
import tempfile
import logging
import markdown
from weasyprint import HTML, CSS
from jinja2 import Template

# Set up logging
logger = logging.getLogger(__name__)

# Default CSS for styling the exported PDF
DEFAULT_CSS = """
body {
    font-family: 'Arial', sans-serif;
    line-height: 1.6;
    margin: 2cm;
    font-size: 11pt;
    color: #333;
}
h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}
h1 {
    font-size: 2em;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.3em;
}
h2 {
    font-size: 1.75em;
}
h3 {
    font-size: 1.5em;
}
h4 {
    font-size: 1.25em;
}
p {
    margin: 1em 0;
}
a {
    color: #3498db;
    text-decoration: none;
}
code {
    background-color: #f8f8f8;
    border-radius: 3px;
    padding: 0.2em 0.4em;
    font-family: 'Courier New', monospace;
}
pre {
    background-color: #f8f8f8;
    border-radius: 3px;
    padding: 1em;
    overflow: auto;
}
blockquote {
    border-left: 4px solid #ddd;
    padding-left: 1em;
    color: #777;
    margin-left: 0;
}
img {
    max-width: 100%;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}
th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}
th {
    background-color: #f8f8f8;
}
ul, ol {
    padding-left: 2em;
}
li {
    margin: 0.5em 0;
}
/* Metadata section styling */
.metadata {
    background-color: #f8f8f8;
    padding: 1em;
    margin-bottom: 2em;
    border-radius: 5px;
    font-size: 0.9em;
}
.metadata-item {
    margin: 0.5em 0;
}
.metadata-label {
    font-weight: bold;
    margin-right: 0.5em;
}
.tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5em;
}
.tag {
    background-color: #e0e0e0;
    padding: 0.2em 0.5em;
    border-radius: 3px;
    font-size: 0.8em;
}
"""

# HTML template for the PDF
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <style>
        {{ css }}
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    
    {% if include_metadata %}
    <div class="metadata">
        {% if created_at %}
        <div class="metadata-item">
            <span class="metadata-label">Created:</span> {{ created_at }}
        </div>
        {% endif %}
        {% if updated_at %}
        <div class="metadata-item">
            <span class="metadata-label">Updated:</span> {{ updated_at }}
        </div>
        {% endif %}
        {% if category %}
        <div class="metadata-item">
            <span class="metadata-label">Category:</span> {{ category }}
        </div>
        {% endif %}
        {% if tags and tags|length > 0 %}
        <div class="metadata-item">
            <span class="metadata-label">Tags:</span>
            <div class="tags">
                {% for tag in tags %}
                <span class="tag">{{ tag }}</span>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    {% endif %}
    
    <div class="content">
        {{ content|safe }}
    </div>
</body>
</html>
"""


def export_note_to_pdf(
    note_content: str, 
    title: str,
    output_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    custom_css: Optional[str] = None,
    include_metadata: bool = True
) -> bool:
    """
    Export a note to PDF format.

    Args:
        note_content: The Markdown content of the note
        title: The title of the note
        output_path: Path where the PDF should be saved
        metadata: Optional dictionary of note metadata
        custom_css: Optional custom CSS for styling
        include_metadata: Whether to include metadata in the PDF

    Returns:
        True if export was successful, False otherwise
    """
    try:
        # Convert the Markdown content to HTML
        html_content = markdown.markdown(
            note_content,
            extensions=[
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.codehilite',
                'markdown.extensions.nl2br',
                'markdown.extensions.toc'
            ]
        )
        
        # Parse metadata if provided
        if metadata is None:
            metadata = {}
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Prepare the template context
        context = {
            'title': title,
            'content': html_content,
            'css': custom_css or DEFAULT_CSS,
            'include_metadata': include_metadata,
            **metadata
        }
        
        # Render the HTML template
        template = Template(HTML_TEMPLATE)
        html_string = template.render(**context)
        
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False) as temp_file:
            temp_html_path = temp_file.name
            temp_file.write(html_string)
        
        try:
            # Convert HTML to PDF
            html = HTML(filename=temp_html_path)
            html.write_pdf(output_path)
            logger.info(f"PDF exported successfully to {output_path}")
            return True
        finally:
            # Clean up temporary file
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)
                
    except Exception as e:
        logger.error(f"Error exporting note to PDF: {str(e)}")
        return False


def convert_markdown_to_pdf(
    markdown_path: str,
    output_path: str,
    title: Optional[str] = None,
    custom_css: Optional[str] = None,
    include_metadata: bool = True
) -> bool:
    """
    Convert an existing Markdown file to PDF.

    Args:
        markdown_path: Path to the Markdown file
        output_path: Path where the PDF should be saved
        title: Optional title (defaults to filename if not provided)
        custom_css: Optional custom CSS for styling
        include_metadata: Whether to include metadata in the PDF

    Returns:
        True if conversion was successful, False otherwise
    """
    try:
        # Read the Markdown file
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter if present
        from app.utils.file_handler import parse_frontmatter
        metadata, markdown_content = parse_frontmatter(content)
        
        # Use provided title or extract from metadata or filename
        note_title = title
        if not note_title:
            note_title = metadata.get('title')
            if not note_title:
                # Use the filename without extension as title
                note_title = os.path.splitext(os.path.basename(markdown_path))[0]
        
        # Export to PDF
        return export_note_to_pdf(
            note_content=markdown_content,
            title=note_title,
            output_path=output_path,
            metadata=metadata,
            custom_css=custom_css,
            include_metadata=include_metadata
        )
    
    except Exception as e:
        logger.error(f"Error converting Markdown to PDF: {str(e)}")
        return False