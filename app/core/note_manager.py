"""
Core note management functionality for MarkNote.
"""
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import yaml
from slugify import slugify

from app.models.note import Note
from app.utils.file_handler import (
    ensure_notes_dir,
    parse_frontmatter,
    add_frontmatter,
    list_note_files,
    validate_path,
)
from app.utils.template_manager import TemplateManager

class NoteManager:
    """
    Manages notes in the filesystem.
    """
    def __init__(self, notes_dir: Optional[str] = None):
        """
        Initialize the NoteManager with the specified notes directory.
        
        Args:
            notes_dir: Optional custom directory path for storing notes.
                      If not provided, the default directory will be used.
        """
        self.notes_dir = ensure_notes_dir(notes_dir)
        self.template_manager = TemplateManager()

    def create_note(self, title: str, template_name: str = "default", 
                   content: str = "", tags: List[str] = None,
                   category: Optional[str] = None, 
                   additional_metadata: Optional[Dict[str, Any]] = None,
                   output_dir: Optional[str] = None) -> Note:
        """
        Create a new note.
        
        Args:
            title: The title of the note.
            template_name: The name of the template to use.
            content: The initial content of the note (if not using a template).
            tags: Optional list of tags for the note.
            category: Optional category for the note.
            additional_metadata: Optional additional metadata for the frontmatter.
            output_dir: Optional specific directory to save the note to.
                        This overrides the notes_dir for this specific note.
            
        Returns:
            The created Note object.
        """
        if tags is None:
            tags = []
        
        if additional_metadata is None:
            additional_metadata = {}
            
        # Create a filename from the title
        filename = f"{slugify(title)}.md"
        
        # Create the note object
        now = datetime.now()
        note = Note(
            title=title,
            content=content,
            tags=tags,
            category=category,
            created_at=now,
            updated_at=now,
            filename=filename,
            metadata=additional_metadata.copy()
        )
        
        # Prepare the template context
        context = {
            "title": title,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "tags": tags,
            "category": category,
            **additional_metadata
        }
        
        try:
            # If using a template, render it
            content = self.template_manager.render_template(template_name, context)
        except FileNotFoundError:
            # If template doesn't exist, use the provided content or create a basic one
            if not content:
                content = f"# {title}\n\n"
        
        # Determine the directory to save the note
        if output_dir:
            # If output_dir specified, use it instead of the default
            base_dir = os.path.expanduser(output_dir)
            if not os.path.isabs(base_dir):
                base_dir = os.path.abspath(base_dir)
            
            # Create output directory if it doesn't exist
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
                
            note_dir = base_dir
            if category:
                note_dir = os.path.join(base_dir, category)
                os.makedirs(note_dir, exist_ok=True)
        else:
            # Use the default notes directory
            note_dir = self.notes_dir
            if category:
                note_dir = os.path.join(note_dir, category)
                os.makedirs(note_dir, exist_ok=True)
        
        # Determine the full path to the note
        note_path = os.path.join(note_dir, filename)
        
        # Check if the path is valid
        if not validate_path(os.path.dirname(note_path)):
            raise PermissionError(f"Cannot write to the specified path: {note_path}")
        
        # Don't overwrite existing notes unless explicitly handled elsewhere
        if os.path.exists(note_path):
            raise FileExistsError(f"A note with the title '{title}' already exists.")
        
        # Write the note content to the file
        try:
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Note saved to: {note_path}")
        except Exception as e:
            raise IOError(f"Failed to write note file: {str(e)}")
        
        # Set the full path on the note object
        note.metadata['path'] = note_path
        
        return note

    def update_note(self, title: str, new_content: Optional[str] = None, 
                   new_tags: Optional[List[str]] = None,
                   new_category: Optional[str] = None,
                   additional_metadata: Optional[Dict[str, Any]] = None,
                   category: Optional[str] = None,
                   output_dir: Optional[str] = None) -> Tuple[bool, Note, str]:
        """
        Update an existing note.
        
        Args:
            title: The title of the note to update.
            new_content: Optional new content for the note.
            new_tags: Optional new tags for the note.
            new_category: Optional new category for the note.
            additional_metadata: Optional additional metadata to update.
            category: Optional category to help find the note.
            output_dir: Optional directory to look for the note.
            
        Returns:
            A tuple of (success, updated note, error message).
        """
        # Get the existing note
        note = self.get_note(title, category, output_dir)
        if not note:
            return False, None, f"Note '{title}' not found"
        
        # Update the note content if provided
        if new_content is not None:
            note.content = new_content
        
        # Update tags if provided
        if new_tags is not None:
            note.tags = new_tags
        
        # Update category if provided
        if new_category is not None:
            note.category = new_category
        
        # Update additional metadata if provided
        if additional_metadata:
            for key, value in additional_metadata.items():
                note.metadata[key] = value
        
        # Update the updated_at timestamp
        note.updated_at = datetime.now()
        
        # Prepare metadata for saving
        metadata = {
            'title': note.title,
            'created_at': note.created_at.isoformat(),
            'updated_at': note.updated_at.isoformat(),
        }
        
        if note.tags:
            metadata['tags'] = note.tags
        
        if note.category:
            metadata['category'] = note.category
        
        # Add other metadata
        for key, value in note.metadata.items():
            if key not in ['title', 'created_at', 'updated_at', 'tags', 'category', 'path']:
                metadata[key] = value
        
        # If the category changed, we need to move the file
        note_path = note.metadata.get('path')
        if new_category is not None and new_category != note.category:
            # Determine base directory
            if output_dir:
                base_dir = os.path.expanduser(output_dir)
                if not os.path.isabs(base_dir):
                    base_dir = os.path.abspath(base_dir)
            else:
                base_dir = self.notes_dir
                
            # Create new directory if needed
            new_dir = os.path.join(base_dir, new_category) if new_category else base_dir
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
                
            # Determine new path
            new_path = os.path.join(new_dir, note.filename)
            
            # Check if target file already exists
            if os.path.exists(new_path):
                return False, note, f"Cannot move note to category '{new_category}': a note with the same name already exists"
                
            # Delete original file only after we've successfully created the new one
            try:
                # Add frontmatter to content
                full_content = add_frontmatter(note.content, metadata)
                
                # Write to the new location
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                    
                # Update the path in the note
                note.metadata['path'] = new_path
                    
                # Remove the old file
                if os.path.exists(note_path):
                    os.remove(note_path)
                
                # Check if old category directory is empty and remove it if so
                old_dir = os.path.dirname(note_path)
                if os.path.exists(old_dir) and old_dir != base_dir:
                    if not os.listdir(old_dir):
                        os.rmdir(old_dir)
                
                return True, note, ""
            except Exception as e:
                return False, note, f"Error moving note: {str(e)}"
        else:
            # Just update the existing file
            try:
                # Add frontmatter to content
                full_content = add_frontmatter(note.content, metadata)
                
                # Write to the file
                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                
                return True, note, ""
            except Exception as e:
                return False, note, f"Error updating note: {str(e)}"

    def get_note(self, title: str, category: Optional[str] = None,
                output_dir: Optional[str] = None) -> Optional[Note]:
        """
        Get a note by its title and optional category.
        
        Args:
            title: The title of the note.
            category: Optional category of the note.
            output_dir: Optional specific directory to look for the note.
                        This overrides the notes_dir for this specific lookup.
            
        Returns:
            The Note object if found, None otherwise.
        """
        filename = f"{slugify(title)}.md"
        
        # Determine the directory to look for the note
        if output_dir:
            # If output_dir specified, use it instead of the default
            base_dir = os.path.expanduser(output_dir)
            if not os.path.isabs(base_dir):
                base_dir = os.path.abspath(base_dir)
                
            note_dir = base_dir
            if category:
                note_dir = os.path.join(base_dir, category)
        else:
            # Use the default notes directory
            note_dir = self.notes_dir
            if category:
                note_dir = os.path.join(note_dir, category)
        
        note_path = os.path.join(note_dir, filename)
        
        if not os.path.exists(note_path):
            return None
        
        # Read the note content
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter and content
        metadata, content_without_frontmatter = parse_frontmatter(content)
        
        # Extract basic metadata
        try:
            created_at = datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
        except (ValueError, TypeError):
            created_at = datetime.now()
            
        try:
            updated_at = datetime.fromisoformat(metadata.get('updated_at', datetime.now().isoformat()))
        except (ValueError, TypeError):
            updated_at = datetime.now()
            
        tags = metadata.get('tags', [])
        category = metadata.get('category', category)
        
        # Create and return the note object
        note = Note(
            title=title,
            content=content_without_frontmatter,
            created_at=created_at,
            updated_at=updated_at,
            tags=tags,
            category=category,
            filename=filename,
            metadata=metadata
        )
        
        # Set the full path on the note object
        note.metadata['path'] = note_path
        
        return note

    def edit_note_content(self, title: str, new_content: str, 
                          category: Optional[str] = None,
                          output_dir: Optional[str] = None) -> Tuple[bool, Optional[Note], str]:
        """
        Edit the content of an existing note.
        
        Args:
            title: The title of the note to edit.
            new_content: The new content for the note.
            category: Optional category to help find the note.
            output_dir: Optional directory to look for the note.
            
        Returns:
            A tuple of (success, updated note, error message).
        """
        return self.update_note(title, new_content=new_content, 
                               category=category, output_dir=output_dir)

    def list_notes(self, tag: Optional[str] = None, 
                   category: Optional[str] = None,
                   output_dir: Optional[str] = None) -> List[Note]:
        """
        List notes, optionally filtered by tag or category.
        
        Args:
            tag: Optional tag to filter by.
            category: Optional category to filter by.
            output_dir: Optional specific directory to look for the notes.
                        This overrides the notes_dir for this specific listing.
            
        Returns:
            A list of Note objects matching the criteria.
        """
        # Determine the directory to look for notes
        if output_dir:
            base_dir = os.path.expanduser(output_dir)
            if not os.path.isabs(base_dir):
                base_dir = os.path.abspath(base_dir)
        else:
            base_dir = self.notes_dir
        
        # List of directories to search
        dirs_to_search = []
        
        if category:
            # If category is specified, only search in that category
            category_dir = os.path.join(base_dir, category)
            if os.path.isdir(category_dir):
                dirs_to_search.append(category_dir)
        else:
            # Otherwise, search in the main notes directory
            dirs_to_search.append(base_dir)
            
            # And all category subdirectories
            if os.path.exists(base_dir):
                for item in os.listdir(base_dir):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isdir(item_path):
                        dirs_to_search.append(item_path)
        
        # Find all markdown files
        markdown_files = []
        for directory in dirs_to_search:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    if file.endswith('.md'):
                        markdown_files.append(os.path.join(directory, file))
        
        # Load each note and filter by tag if needed
        notes = []
        for file_path in markdown_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata, content_without_frontmatter = parse_frontmatter(content)
            
            # Skip if tag filter is specified and note doesn't have the tag
            if tag and tag not in metadata.get('tags', []):
                continue
            
            # Extract necessary data
            title = metadata.get('title', os.path.basename(file_path)[:-3])  # Remove .md
            
            # Handle date parsing with error handling
            try:
                created_at = datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
            except (ValueError, TypeError):
                created_at = datetime.now()
                
            try:
                updated_at = datetime.fromisoformat(metadata.get('updated_at', datetime.now().isoformat()))
            except (ValueError, TypeError):
                updated_at = datetime.now()
                
            tags = metadata.get('tags', [])
            note_category = metadata.get('category', None)
            
            # Determine category from directory structure if not in metadata
            if not note_category:
                dir_name = os.path.basename(os.path.dirname(file_path))
                if dir_name != os.path.basename(base_dir):
                    note_category = dir_name
            
            # Create note object
            note = Note(
                title=title,
                content=content_without_frontmatter,
                created_at=created_at,
                updated_at=updated_at,
                tags=tags,
                category=note_category,
                filename=os.path.basename(file_path),
                metadata=metadata
            )
            
            # Set the full path on the note object
            note.metadata['path'] = file_path
            
            notes.append(note)
        
        # Sort by updated_at, most recent first
        notes.sort(key=lambda x: x.updated_at, reverse=True)
        
        return notes

    def search_notes(self, query: str, output_dir: Optional[str] = None) -> List[Note]:
        """
        Search for notes containing the query string.
        
        Args:
            query: The query string to search for.
            output_dir: Optional specific directory to look for the notes.
                        This overrides the notes_dir for this specific search.
            
        Returns:
            A list of Note objects matching the query.
        """
        # Get all notes
        all_notes = self.list_notes(output_dir=output_dir)
        
        # Filter notes by query string (case insensitive)
        matching_notes = []
        query = query.lower()
        
        for note in all_notes:
            # Check title
            if query in note.title.lower():
                matching_notes.append(note)
                continue
            
            # Check content
            if query in note.content.lower():
                matching_notes.append(note)
                continue
            
            # Check tags
            if any(query in tag.lower() for tag in note.tags):
                matching_notes.append(note)
                continue
        
        return matching_notes