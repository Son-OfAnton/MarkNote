"""
Backup and restore functionality for MarkNote.
"""
import os
import shutil
import json
import tempfile
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
import yaml

from app.models.note import Note
from app.utils.file_handler import (
    ensure_notes_dir,
    list_note_files,
    read_note_file,
    parse_frontmatter,
    add_frontmatter,
    validate_path
)

class BackupManager:
    """
    Manages backup and restore operations for notes.
    """
    
    def __init__(self, notes_dir: Optional[str] = None, backup_dir: Optional[str] = None):
        """
        Initialize the BackupManager.
        
        Args:
            notes_dir: Directory containing notes. If None, the default notes directory is used.
            backup_dir: Directory to store backups. If None, a 'backups' directory is created
                       inside the notes directory.
        """
        self.notes_dir = ensure_notes_dir(notes_dir)
        
        if backup_dir:
            self.backup_dir = backup_dir
        else:
            self.backup_dir = os.path.join(self.notes_dir, "backups")
            
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self, 
                      backup_name: Optional[str] = None,
                      category: Optional[str] = None, 
                      tags: Optional[List[str]] = None,
                      include_versions: bool = True,
                      include_archived: bool = False,
                      metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create a backup of notes, optionally filtering by category or tags.
        
        Args:
            backup_name: Optional name for the backup file. If None, a timestamp-based name is used.
            category: If provided, only backup notes in this category.
            tags: If provided, only backup notes with at least one of these tags.
            include_versions: Whether to include version history in the backup.
            include_archived: Whether to include archived notes in the backup.
            metadata: Additional metadata to store in the backup.
            
        Returns:
            A tuple of (success, message, backup_path).
        """
        try:
            # Generate backup name if not provided
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"marknote_backup_{timestamp}"
            
            # Ensure backup has .zip extension
            if not backup_name.endswith(".zip"):
                backup_name += ".zip"
                
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Check if backup already exists
            if os.path.exists(backup_path):
                return False, f"Backup file '{backup_path}' already exists.", None
            
            # Create temporary directory for organizing backup contents
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create notes directory structure in temp directory
                temp_notes_dir = os.path.join(temp_dir, "notes")
                os.makedirs(temp_notes_dir, exist_ok=True)
                
                # Create metadata file
                backup_metadata = {
                    "created_at": datetime.now().isoformat(),
                    "notes_dir": self.notes_dir,
                    "include_versions": include_versions,
                    "include_archived": include_archived,
                    "filter_category": category,
                    "filter_tags": tags
                }
                
                # Add user-provided metadata if any
                if metadata:
                    backup_metadata["user_metadata"] = metadata
                
                # Create versions directory if including versions
                temp_versions_dir = None
                if include_versions:
                    versions_dir = os.path.join(self.notes_dir, ".versions")
                    if os.path.exists(versions_dir):
                        temp_versions_dir = os.path.join(temp_dir, ".versions")
                        os.makedirs(temp_versions_dir, exist_ok=True)
                
                # Create archives directory if including archived notes
                temp_archives_dir = None
                if include_archived:
                    archives_dir = os.path.join(self.notes_dir, "archive")
                    if os.path.exists(archives_dir):
                        temp_archives_dir = os.path.join(temp_dir, "archive")
                        os.makedirs(temp_archives_dir, exist_ok=True)
                
                # Collect note files
                note_files = list_note_files(self.notes_dir)
                backup_metadata["total_notes"] = len(note_files)
                
                # Track notes that meet filter criteria
                included_notes = []
                
                # Process each note file
                for note_file in note_files:
                    note_path = os.path.join(self.notes_dir, note_file)
                    
                    # Skip directories and non-markdown files
                    if os.path.isdir(note_path) or not note_path.lower().endswith(('.md', '.markdown')):
                        continue
                    
                    # Read note metadata
                    try:
                        metadata, _ = read_note_file(note_path)
                        
                        # Apply category filter if specified
                        if category and metadata.get("category") != category:
                            continue
                            
                        # Apply tags filter if specified
                        if tags:
                            note_tags = metadata.get("tags", [])
                            # Check if any tag matches
                            if not any(tag in note_tags for tag in tags):
                                continue
                        
                        # Note passed filters, copy it to temp dir
                        included_notes.append(note_file)
                        
                        # Preserve directory structure relative to notes_dir
                        rel_path = os.path.relpath(note_path, self.notes_dir)
                        dest_path = os.path.join(temp_notes_dir, rel_path)
                        
                        # Create destination directory if needed
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        
                        # Copy the note file
                        shutil.copy2(note_path, dest_path)
                        
                    except Exception as e:
                        # Log the error but continue processing other notes
                        print(f"Warning: Could not process note {note_file}: {str(e)}")
                
                # Update backup metadata with included notes count
                backup_metadata["included_notes"] = len(included_notes)
                backup_metadata["included_note_files"] = included_notes
                
                # Copy version history if requested
                if include_versions and temp_versions_dir and os.path.exists(versions_dir):
                    # Only copy versions of included notes
                    for note_file in included_notes:
                        note_name = os.path.splitext(os.path.basename(note_file))[0]
                        for root, dirs, files in os.walk(versions_dir):
                            for file in files:
                                # Simple heuristic: if filename contains the note name
                                if note_name in file and file.endswith(('.json', '.md')):
                                    src_path = os.path.join(root, file)
                                    # Preserve relative path from versions dir
                                    rel_path = os.path.relpath(src_path, versions_dir)
                                    dest_path = os.path.join(temp_versions_dir, rel_path)
                                    
                                    # Create destination directory if needed
                                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                    
                                    # Copy the version file
                                    shutil.copy2(src_path, dest_path)
                
                # Copy archived notes if requested
                if include_archived and temp_archives_dir and os.path.exists(archives_dir):
                    # Apply same filters to archived notes
                    for root, dirs, files in os.walk(archives_dir):
                        for file in files:
                            if file.lower().endswith(('.md', '.markdown')):
                                src_path = os.path.join(root, file)
                                
                                # Read archived note metadata for filtering
                                try:
                                    metadata, _ = read_note_file(src_path)
                                    
                                    # Apply category filter if specified
                                    if category and metadata.get("category") != category:
                                        continue
                                        
                                    # Apply tags filter if specified
                                    if tags:
                                        note_tags = metadata.get("tags", [])
                                        if not any(tag in note_tags for tag in tags):
                                            continue
                                    
                                    # Preserve relative path from archives dir
                                    rel_path = os.path.relpath(src_path, archives_dir)
                                    dest_path = os.path.join(temp_archives_dir, rel_path)
                                    
                                    # Create destination directory if needed
                                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                    
                                    # Copy the archived note
                                    shutil.copy2(src_path, dest_path)
                                    
                                except Exception as e:
                                    # Log the error but continue
                                    print(f"Warning: Could not process archived note {file}: {str(e)}")
                
                # Write backup metadata to file
                metadata_path = os.path.join(temp_dir, "backup_metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(backup_metadata, f, indent=2)
                
                # Create the zip file
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files from temp directory to the zip
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Make path relative to temp_dir for the archive
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname=arcname)
            
            return True, f"Backup created successfully at '{backup_path}'.", backup_path
            
        except Exception as e:
            return False, f"Error creating backup: {str(e)}", None
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups with their metadata.
        
        Returns:
            A list of dictionaries containing backup information.
        """
        backups = []
        
        try:
            # List all zip files in the backup directory
            for file in os.listdir(self.backup_dir):
                if file.endswith(".zip"):
                    backup_path = os.path.join(self.backup_dir, file)
                    
                    # Extract metadata from the backup
                    try:
                        with zipfile.ZipFile(backup_path, 'r') as zipf:
                            # Check if metadata file exists
                            if "backup_metadata.json" in zipf.namelist():
                                with zipf.open("backup_metadata.json") as f:
                                    metadata = json.load(f)
                                    
                                    # Add file info to metadata
                                    backup_info = {
                                        "filename": file,
                                        "path": backup_path,
                                        "size": os.path.getsize(backup_path),
                                        "created_at": os.path.getctime(backup_path),
                                        "metadata": metadata
                                    }
                                    
                                    backups.append(backup_info)
                            else:
                                # Basic info for backups without metadata
                                backup_info = {
                                    "filename": file,
                                    "path": backup_path,
                                    "size": os.path.getsize(backup_path),
                                    "created_at": os.path.getctime(backup_path),
                                    "metadata": {"note": "Metadata not available"}
                                }
                                backups.append(backup_info)
                    except Exception as e:
                        # Include the backup but note the error
                        backup_info = {
                            "filename": file,
                            "path": backup_path,
                            "size": os.path.getsize(backup_path),
                            "created_at": os.path.getctime(backup_path),
                            "metadata": {"error": f"Error reading metadata: {str(e)}"}
                        }
                        backups.append(backup_info)
        
        except Exception as e:
            print(f"Error listing backups: {str(e)}")
            
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    def get_backup_info(self, backup_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific backup.
        
        Args:
            backup_name: Name of the backup file.
            
        Returns:
            A dictionary with backup information or None if not found.
        """
        # Ensure backup has .zip extension
        if not backup_name.endswith(".zip"):
            backup_name += ".zip"
            
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            return None
            
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # List all files in the backup
                all_files = zipf.namelist()
                
                # Get metadata if available
                metadata = {}
                if "backup_metadata.json" in all_files:
                    with zipf.open("backup_metadata.json") as f:
                        metadata = json.load(f)
                
                # Count notes, versions, etc.
                note_files = [f for f in all_files if f.startswith("notes/") and f.lower().endswith(('.md', '.markdown'))]
                version_files = [f for f in all_files if f.startswith(".versions/")]
                archive_files = [f for f in all_files if f.startswith("archive/")]
                
                # Calculate total size
                total_size = os.path.getsize(backup_path)
                
                return {
                    "filename": backup_name,
                    "path": backup_path,
                    "size": total_size,
                    "created_at": os.path.getctime(backup_path),
                    "note_count": len(note_files),
                    "version_count": len(version_files),
                    "archive_count": len(archive_files),
                    "metadata": metadata,
                    "all_files_count": len(all_files)
                }
        
        except Exception as e:
            # Return basic info with error
            return {
                "filename": backup_name,
                "path": backup_path,
                "size": os.path.getsize(backup_path),
                "created_at": os.path.getctime(backup_path),
                "error": str(e)
            }
    
    def restore_backup(self, 
                       backup_name: str,
                       restore_dir: Optional[str] = None,
                       overwrite: bool = False,
                       restore_versions: bool = True,
                       restore_archives: bool = True) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Restore notes from a backup.
        
        Args:
            backup_name: Name of the backup file to restore.
            restore_dir: Directory to restore to. If None, restores to original notes directory.
            overwrite: Whether to overwrite existing files.
            restore_versions: Whether to restore version history.
            restore_archives: Whether to restore archived notes.
            
        Returns:
            A tuple of (success, message, stats) where stats contains restoration statistics.
        """
        # Ensure backup has .zip extension
        if not backup_name.endswith(".zip"):
            backup_name += ".zip"
            
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            return False, f"Backup file '{backup_path}' not found.", None
        
        # Determine restoration directory
        target_dir = restore_dir if restore_dir else self.notes_dir
        
        # Create restoration stats
        stats = {
            "notes_restored": 0,
            "notes_skipped": 0,
            "versions_restored": 0,
            "versions_skipped": 0,
            "archives_restored": 0,
            "archives_skipped": 0,
            "errors": []
        }
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Get backup metadata if available
                metadata = {}
                if "backup_metadata.json" in zipf.namelist():
                    with zipf.open("backup_metadata.json") as f:
                        metadata = json.load(f)
                
                # Extract notes
                for member in zipf.namelist():
                    try:
                        # Process notes
                        if member.startswith("notes/") and member.lower().endswith(('.md', '.markdown')):
                            # Determine target path
                            rel_path = member[len("notes/"):]  # Remove 'notes/' prefix
                            dest_path = os.path.join(target_dir, rel_path)
                            
                            # Check if file exists and handle overwrite
                            if os.path.exists(dest_path) and not overwrite:
                                stats["notes_skipped"] += 1
                                continue
                            
                            # Create destination directory if needed
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            
                            # Extract file
                            with zipf.open(member) as source, open(dest_path, 'wb') as target:
                                target.write(source.read())
                                
                            stats["notes_restored"] += 1
                            
                        # Process versions if requested
                        elif restore_versions and member.startswith(".versions/"):
                            # Skip if it's a directory entry
                            if member.endswith("/"):
                                continue
                                
                            # Determine target path
                            dest_path = os.path.join(target_dir, member)
                            
                            # Check if file exists and handle overwrite
                            if os.path.exists(dest_path) and not overwrite:
                                stats["versions_skipped"] += 1
                                continue
                            
                            # Create destination directory if needed
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            
                            # Extract file
                            with zipf.open(member) as source, open(dest_path, 'wb') as target:
                                target.write(source.read())
                            
                            stats["versions_restored"] += 1
                            
                        # Process archived notes if requested
                        elif restore_archives and member.startswith("archive/"):
                            # Skip if it's a directory entry
                            if member.endswith("/"):
                                continue
                                
                            # Determine target path
                            dest_path = os.path.join(target_dir, member)
                            
                            # Check if file exists and handle overwrite
                            if os.path.exists(dest_path) and not overwrite:
                                stats["archives_skipped"] += 1
                                continue
                            
                            # Create destination directory if needed
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            
                            # Extract file
                            with zipf.open(member) as source, open(dest_path, 'wb') as target:
                                target.write(source.read())
                            
                            stats["archives_restored"] += 1
                            
                    except Exception as e:
                        # Log the error but continue with other files
                        stats["errors"].append(f"Error restoring {member}: {str(e)}")
            
            # Include the backup metadata in stats
            stats["backup_metadata"] = metadata
            
            return True, f"Backup restored successfully to '{target_dir}'.", stats
            
        except Exception as e:
            return False, f"Error restoring backup: {str(e)}", stats
    
    def delete_backup(self, backup_name: str) -> Tuple[bool, str]:
        """
        Delete a backup file.
        
        Args:
            backup_name: Name of the backup file to delete.
            
        Returns:
            A tuple of (success, message).
        """
        # Ensure backup has .zip extension
        if not backup_name.endswith(".zip"):
            backup_name += ".zip"
            
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            return False, f"Backup file '{backup_path}' not found."
        
        try:
            os.remove(backup_path)
            return True, f"Backup '{backup_name}' deleted."
        except Exception as e:
            return False, f"Error deleting backup: {str(e)}"