"""
Archive management functionality for MarkNote.
"""
import os
import shutil
from typing import Optional, Dict, Any, Tuple, List, Set, Union
from datetime import datetime, timedelta
import yaml
import json

from app.models.note import Note
from app.models.archived_note import ArchivedNote
from app.utils.file_handler import (
    ensure_notes_dir,
    parse_frontmatter,
    read_note_file,
    write_note_file,
    list_note_files
)


class ArchiveManager:
    """
    Manages the archiving and unarchiving of notes.
    """
    
    def __init__(self, notes_dir: Optional[str] = None):
        """
        Initialize the ArchiveManager.
        
        Args:
            notes_dir: Optional custom directory path for storing notes.
                      If not provided, the default directory will be used.
        """
        self.notes_dir = ensure_notes_dir(notes_dir)
        self.archive_dir = os.path.join(self.notes_dir, "archive")
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def archive_note(self, note_path: str, reason: Optional[str] = None, 
                   move_to_archive_dir: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        Archive a note.
        
        Args:
            note_path: Path to the note file
            reason: Optional reason for archiving
            move_to_archive_dir: Whether to move the note to the archive directory
            
        Returns:
            Tuple of (success, message, new_path)
            
        Raises:
            FileNotFoundError: If the note doesn't exist
            PermissionError: If the note can't be read or written
        """
        # Check if the note exists
        if not os.path.exists(note_path):
            return False, f"Note not found: {note_path}", None
        
        try:
            # Read the note
            metadata, content = read_note_file(note_path)
            
            # Check if already archived
            if metadata.get('is_archived', False):
                return False, f"Note is already archived: {note_path}", None
            
            # Add archive metadata
            now = datetime.now()
            metadata.update({
                'is_archived': True,
                'archived_at': now.isoformat(),
                'archive_reason': reason
            })
            
            # Add 'Archived' tag if not already present
            if 'tags' not in metadata or metadata['tags'] is None:
                metadata['tags'] = []
            if 'Archived' not in metadata['tags']:
                metadata['tags'].append('Archived')
            
            # Prepare new path if moving
            new_path = note_path
            if move_to_archive_dir:
                filename = os.path.basename(note_path)
                category_dir = os.path.basename(os.path.dirname(note_path))
                
                # Check if the note is in a category directory
                if category_dir and category_dir != os.path.basename(self.notes_dir):
                    # Preserve the category structure
                    archive_category_dir = os.path.join(self.archive_dir, category_dir)
                    os.makedirs(archive_category_dir, exist_ok=True)
                    new_path = os.path.join(archive_category_dir, filename)
                else:
                    new_path = os.path.join(self.archive_dir, filename)
            
            # Write the updated note
            if move_to_archive_dir and new_path != note_path:
                # Write to new location and delete old file
                write_note_file(new_path, metadata, content)
                os.remove(note_path)
                return True, f"Note archived and moved to archive directory", new_path
            else:
                # Update in place
                write_note_file(note_path, metadata, content)
                return True, f"Note archived successfully", note_path
                
        except Exception as e:
            return False, f"Error archiving note: {str(e)}", None
    
    def unarchive_note(self, note_path: str, move_from_archive_dir: bool = False, 
                      destination_dir: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Unarchive a note.
        
        Args:
            note_path: Path to the archived note file
            move_from_archive_dir: Whether to move the note from the archive directory
            destination_dir: Optional destination directory for the unarchived note
            
        Returns:
            Tuple of (success, message, new_path)
            
        Raises:
            FileNotFoundError: If the note doesn't exist
            PermissionError: If the note can't be read or written
        """
        # Check if the note exists
        if not os.path.exists(note_path):
            return False, f"Note not found: {note_path}", None
        
        try:
            # Read the note
            metadata, content = read_note_file(note_path)
            
            # Check if actually archived
            if not metadata.get('is_archived', False):
                return False, f"Note is not archived: {note_path}", None
            
            # Update metadata to remove archive info
            metadata.update({
                'is_archived': False,
                'archived_at': None,
                'archive_reason': None
            })
            
            # Remove 'Archived' tag if present
            if 'tags' in metadata and metadata['tags'] and 'Archived' in metadata['tags']:
                metadata['tags'].remove('Archived')
            
            # Prepare new path if moving
            new_path = note_path
            if move_from_archive_dir:
                filename = os.path.basename(note_path)
                category_dir = os.path.basename(os.path.dirname(note_path))
                
                if destination_dir:
                    # Use specified destination
                    dest_path = os.path.expanduser(destination_dir)
                else:
                    # Default to notes_dir
                    dest_path = self.notes_dir
                
                # Check if the note is in a category directory within the archive
                if category_dir and category_dir != os.path.basename(self.archive_dir):
                    # Preserve the category structure
                    dest_category_dir = os.path.join(dest_path, category_dir)
                    os.makedirs(dest_category_dir, exist_ok=True)
                    new_path = os.path.join(dest_category_dir, filename)
                else:
                    new_path = os.path.join(dest_path, filename)
            
            # Write the updated note
            if move_from_archive_dir and new_path != note_path:
                # Write to new location and delete old file
                write_note_file(new_path, metadata, content)
                os.remove(note_path)
                return True, f"Note unarchived and moved from archive directory", new_path
            else:
                # Update in place
                write_note_file(note_path, metadata, content)
                return True, f"Note unarchived successfully", note_path
                
        except Exception as e:
            return False, f"Error unarchiving note: {str(e)}", None
    
    def list_archived_notes(self, include_content: bool = False,
                           category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all archived notes.
        
        Args:
            include_content: Whether to include the note content
            category: Optional category to filter archived notes
            
        Returns:
            List of dictionaries with note information
        """
        archived_notes = []
        
        # Check the main archive directory
        archive_path = self.archive_dir
        archive_notes = list_note_files(archive_path, category)
        
        # Also check the notes_dir for notes archived in-place
        main_notes = list_note_files(self.notes_dir, category)
        
        # Combine the lists
        all_notes = archive_notes + main_notes
        
        # Filter for archived notes
        for note_path in all_notes:
            try:
                metadata, content = read_note_file(note_path)
                if metadata.get('is_archived', False):
                    note_info = {
                        'path': note_path,
                        'filename': os.path.basename(note_path),
                        'title': metadata.get('title', os.path.splitext(os.path.basename(note_path))[0]),
                        'category': metadata.get('category', None) or os.path.basename(os.path.dirname(note_path)),
                        'tags': metadata.get('tags', []),
                        'archived_at': metadata.get('archived_at', None),
                        'archive_reason': metadata.get('archive_reason', None),
                        'size_bytes': os.path.getsize(note_path)
                    }
                    
                    # Add other metadata fields
                    for key, value in metadata.items():
                        if key not in note_info and key != 'content':
                            note_info[key] = value
                    
                    # Optionally include content
                    if include_content:
                        note_info['content'] = content
                        
                    archived_notes.append(note_info)
            except Exception:
                # Skip files that can't be read
                pass
                
        return archived_notes
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """
        Get statistics about archived notes.
        
        Returns:
            Dictionary with archive statistics
        """
        archived_notes = self.list_archived_notes()
        
        # Initialize stats
        stats = {
            'total_archived': len(archived_notes),
            'storage_bytes': sum(note.get('size_bytes', 0) for note in archived_notes),
            'categories': {},
            'tags': {},
            'archived_by_date': {},
            'oldest_archive': None,
            'newest_archive': None,
            'archive_reasons': {}
        }
        
        # Process each note
        for note in archived_notes:
            # Categories
            category = note.get('category', 'Uncategorized')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # Tags
            for tag in note.get('tags', []):
                stats['tags'][tag] = stats['tags'].get(tag, 0) + 1
            
            # Archive date
            if note.get('archived_at'):
                try:
                    archive_date = datetime.fromisoformat(note['archived_at'])
                    date_str = archive_date.strftime('%Y-%m-%d')
                    stats['archived_by_date'][date_str] = stats['archived_by_date'].get(date_str, 0) + 1
                    
                    # Track oldest/newest
                    if stats['oldest_archive'] is None or archive_date < stats['oldest_archive']:
                        stats['oldest_archive'] = archive_date
                    
                    if stats['newest_archive'] is None or archive_date > stats['newest_archive']:
                        stats['newest_archive'] = archive_date
                except (ValueError, TypeError):
                    pass
            
            # Archive reason
            reason = note.get('archive_reason', 'No reason specified')
            stats['archive_reasons'][reason] = stats['archive_reasons'].get(reason, 0) + 1
        
        # Convert datetime objects to strings
        if stats['oldest_archive']:
            stats['oldest_archive'] = stats['oldest_archive'].isoformat()
        
        if stats['newest_archive']:
            stats['newest_archive'] = stats['newest_archive'].isoformat()
        
        return stats
    
    def batch_archive_notes(self, note_paths: List[str], reason: Optional[str] = None,
                          move_to_archive_dir: bool = False) -> Dict[str, str]:
        """
        Archive multiple notes.
        
        Args:
            note_paths: List of paths to notes to archive
            reason: Optional reason for archiving
            move_to_archive_dir: Whether to move notes to the archive directory
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        results = {}
        
        for path in note_paths:
            try:
                success, message, _ = self.archive_note(path, reason, move_to_archive_dir)
                results[path] = message
            except Exception as e:
                results[path] = f"Error: {str(e)}"
                
        return results
    
    def batch_unarchive_notes(self, note_paths: List[str], move_from_archive_dir: bool = False,
                            destination_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Unarchive multiple notes.
        
        Args:
            note_paths: List of paths to archived notes
            move_from_archive_dir: Whether to move notes from the archive directory
            destination_dir: Optional destination directory
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        results = {}
        
        for path in note_paths:
            try:
                success, message, _ = self.unarchive_note(path, move_from_archive_dir, destination_dir)
                results[path] = message
            except Exception as e:
                results[path] = f"Error: {str(e)}"
                
        return results
    
    def auto_archive_by_age(self, days: int, reason: str = "Auto-archived due to age", 
                          move_to_archive_dir: bool = True) -> Dict[str, str]:
        """
        Auto-archive notes that haven't been updated in the specified number of days.
        
        Args:
            days: Number of days since last update to trigger archiving
            reason: Reason for archiving
            move_to_archive_dir: Whether to move notes to the archive directory
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        results = {}
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all note files
        all_notes = list_note_files(self.notes_dir)
        
        for note_path in all_notes:
            try:
                # Skip notes that are already in the archive directory
                if self.archive_dir in note_path:
                    continue
                    
                # Read the note
                metadata, _ = read_note_file(note_path)
                
                # Skip notes that are already archived
                if metadata.get('is_archived', False):
                    continue
                
                # Check the last update date
                updated_at = None
                if 'updated_at' in metadata:
                    try:
                        updated_at = datetime.fromisoformat(metadata['updated_at'])
                    except (ValueError, TypeError):
                        # If parsing fails, use file modification time
                        updated_at = datetime.fromtimestamp(os.path.getmtime(note_path))
                else:
                    # Use file modification time if metadata doesn't include update time
                    updated_at = datetime.fromtimestamp(os.path.getmtime(note_path))
                
                # Archive if older than cutoff date
                if updated_at < cutoff_date:
                    success, message, _ = self.archive_note(
                        note_path, 
                        reason=f"{reason} (Last updated: {updated_at.strftime('%Y-%m-%d')})", 
                        move_to_archive_dir=move_to_archive_dir
                    )
                    results[note_path] = message
            except Exception as e:
                results[note_path] = f"Error: {str(e)}"
                
        return results
    
    def is_note_archived(self, note_path: str) -> bool:
        """
        Check if a note is archived.
        
        Args:
            note_path: Path to the note
            
        Returns:
            True if the note is archived, False otherwise
        """
        try:
            metadata, _ = read_note_file(note_path)
            return metadata.get('is_archived', False)
        except Exception:
            return False
        

    def auto_archive_by_date(self, archive_date: datetime, field: str = "created_at", 
                           before_date: bool = True, reason: str = "Auto-archived by date",
                           move_to_archive_dir: bool = True) -> Dict[str, str]:
        """
        Auto-archive notes based on a specific date field.
        
        Args:
            archive_date: The date to compare against
            field: The metadata field to compare ("created_at", "updated_at", or a custom date field)
            before_date: If True, archives notes before the date; if False, archives notes after the date
            reason: Reason for archiving
            move_to_archive_dir: Whether to move notes to the archive directory
            
        Returns:
            Dictionary mapping note paths to success/error messages
        """
        results = {}
        
        # Get all note files
        all_notes = list_note_files(self.notes_dir)
        
        for note_path in all_notes:
            try:
                # Skip notes that are already in the archive directory
                if self.archive_dir in note_path:
                    continue
                    
                # Read the note
                metadata, _ = read_note_file(note_path)
                
                # Skip notes that are already archived
                if metadata.get('is_archived', False):
                    continue
                
                # Get the date value from metadata
                date_value = None
                if field in metadata:
                    try:
                        # Handle both ISO format strings and date objects
                        if isinstance(metadata[field], str):
                            date_value = datetime.fromisoformat(metadata[field])
                        elif isinstance(metadata[field], datetime):
                            date_value = metadata[field]
                        else:
                            # Try to parse as string, otherwise skip
                            date_value = datetime.fromisoformat(str(metadata[field]))
                    except (ValueError, TypeError):
                        # If parsing fails, skip this note
                        results[note_path] = f"Error: Could not parse date field '{field}'"
                        continue
                
                # Skip notes that don't have the specified date field
                if date_value is None:
                    results[note_path] = f"Skipped: Note does not have '{field}' field"
                    continue
                
                # Determine if the note should be archived based on date comparison
                should_archive = False
                if before_date and date_value < archive_date:
                    should_archive = True
                elif not before_date and date_value > archive_date:
                    should_archive = True
                    
                if should_archive:
                    date_str = date_value.strftime('%Y-%m-%d')
                    comparison = "before" if before_date else "after"
                    archive_reason = f"{reason} ({field}: {date_str} is {comparison} {archive_date.strftime('%Y-%m-%d')})"
                    
                    success, message, _ = self.archive_note(
                        note_path,
                        reason=archive_reason,
                        move_to_archive_dir=move_to_archive_dir
                    )
                    results[note_path] = message
            except Exception as e:
                results[note_path] = f"Error: {str(e)}"
                
        return results