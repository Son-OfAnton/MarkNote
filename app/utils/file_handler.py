"""
File handling utilities for MarkNote.
"""
import os
import yaml
from typing import Dict, Any, Tuple, Optional, List

def get_default_notes_dir() -> str:
    """
    Get the default directory for storing notes.
    """
    home = os.path.expanduser("~")
    notes_dir = os.path.join(home, "marknote")
    return notes_dir

def ensure_notes_dir(notes_dir: Optional[str] = None) -> str:
    """
    Ensure the notes directory exists.
    
    Args:
        notes_dir: Optional directory path. If not provided, the default will be used.
        
    Returns:
        The path to the notes directory.
    """
    if notes_dir is None:
        notes_dir = get_default_notes_dir()
        
    if not os.path.exists(notes_dir):
        os.makedirs(notes_dir)
        
    return notes_dir

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.
    
    Args:
        content: Markdown content with optional frontmatter.
        
    Returns:
        A tuple of (metadata, content_without_frontmatter)
    """
    metadata = {}
    content_without_frontmatter = content
    
    # Check if the content starts with '---'
    if content.startswith('---'):
        # Find the end of the frontmatter
        end_index = content.find('---', 3)
        if end_index != -1:
            frontmatter = content[3:end_index].strip()
            # Parse the YAML frontmatter
            try:
                metadata = yaml.safe_load(frontmatter) or {}
                content_without_frontmatter = content[end_index + 3:].strip()
            except yaml.YAMLError:
                # If parsing fails, return empty metadata
                pass
    
    return metadata, content_without_frontmatter

def add_frontmatter(content: str, metadata: Dict[str, Any]) -> str:
    """
    Add YAML frontmatter to markdown content.
    
    Args:
        content: Original markdown content.
        metadata: Dictionary of metadata to add as frontmatter.
        
    Returns:
        Content with frontmatter added.
    """
    # Remove any existing frontmatter
    _, clean_content = parse_frontmatter(content)
    
    # Convert metadata to YAML
    frontmatter = yaml.dump(metadata, default_flow_style=False)
    
    # Add frontmatter to content
    return f"---\n{frontmatter}---\n\n{clean_content}"

def list_note_files(notes_dir: Optional[str] = None) -> List[str]:
    """
    List all markdown files in the notes directory.
    
    Args:
        notes_dir: Optional directory path. If not provided, the default will be used.
        
    Returns:
        List of file paths to markdown files.
    """
    if notes_dir is None:
        notes_dir = get_default_notes_dir()
        
    if not os.path.exists(notes_dir):
        return []
    
    markdown_files = []
    for root, _, files in os.walk(notes_dir):
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(os.path.join(root, file))
                
    return markdown_files