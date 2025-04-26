"""
Enhanced file handling utilities for MarkNote with link support.
"""
import os
import sys
import yaml
from typing import Dict, Any, Tuple, Optional, List, Set

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
    else:
        # Expand user directory if path contains ~
        notes_dir = os.path.expanduser(notes_dir)
        
        # If relative path, make it absolute from current directory
        if not os.path.isabs(notes_dir):
            notes_dir = os.path.abspath(notes_dir)
    
    try:
        if not os.path.exists(notes_dir):
            os.makedirs(notes_dir)
            print(f"Created notes directory: {notes_dir}")
    except PermissionError:
        print(f"Error: Permission denied when creating directory: {notes_dir}")
        sys.exit(1)
    except OSError as e:
        print(f"Error creating directory: {notes_dir}")
        print(f"Details: {str(e)}")
        sys.exit(1)
        
    return notes_dir

def validate_path(path: str) -> bool:
    """
    Validate if a path is usable for saving files.
    
    Args:
        path: The path to validate.
        
    Returns:
        True if the path is valid, False otherwise.
    """
    # Check if the directory exists or can be created
    directory = os.path.dirname(path)
    
    # Handle case where directory is empty (current directory)
    if not directory:
        directory = os.getcwd()
        
    if os.path.exists(directory):
        # Check if directory is writable
        return os.access(directory, os.W_OK)
    
    # Check if parent directory exists and is writable
    parent_dir = os.path.dirname(directory)
    if not parent_dir:
        parent_dir = os.getcwd()
        
    return os.path.exists(parent_dir) and os.access(parent_dir, os.W_OK)

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
                
                # Convert linked_notes to set if present
                if 'linked_notes' in metadata and isinstance(metadata['linked_notes'], list):
                    metadata['linked_notes'] = set(metadata['linked_notes'])
                
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
    
    # Handle linked_notes conversion from set to list for YAML
    metadata_copy = metadata.copy()
    if 'linked_notes' in metadata_copy and isinstance(metadata_copy['linked_notes'], set):
        metadata_copy['linked_notes'] = list(metadata_copy['linked_notes'])
    
    # Convert metadata to YAML
    frontmatter = yaml.dump(metadata_copy, default_flow_style=False)
    
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

def read_note_file(file_path: str) -> Tuple[Dict[str, Any], str]:
    """
    Read a note file and parse its frontmatter and content.
    
    Args:
        file_path: Path to the note file.
        
    Returns:
        A tuple of (metadata, content)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Note file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return parse_frontmatter(content)

def write_note_file(file_path: str, metadata: Dict[str, Any], content: str) -> None:
    """
    Write a note file with the given metadata and content.
    
    Args:
        file_path: Path to the note file.
        metadata: Dictionary of metadata for the frontmatter.
        content: Content of the note.
    """
    # Add frontmatter to content
    full_content = add_frontmatter(content, metadata)
    
    # Ensure the directory exists
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except PermissionError:
            raise PermissionError(f"Permission denied when creating directory: {directory}")
        except OSError as e:
            raise OSError(f"Error creating directory: {directory}: {str(e)}")
    
    # Write the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
    except PermissionError:
        raise PermissionError(f"Permission denied when writing to file: {file_path}")
    except OSError as e:
        raise OSError(f"Error writing to file: {file_path}: {str(e)}")