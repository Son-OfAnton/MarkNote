"""
Version control utilities for MarkNote.

This module provides functionality for tracking and managing versions of notes.
"""
import os
import json
import shutil
import difflib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


class VersionControlManager:
    """
    Manages version history for notes.
    
    This class provides version control functionality by:
    - Tracking changes to notes
    - Storing version history
    - Providing methods to view and compare versions
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the VersionControlManager.
        
        Args:
            base_dir: Base directory for storing version history.
                     If None, uses default location.
        """
        if base_dir is None:
            # Default location: ~/.marknote/versions
            home = os.path.expanduser("~")
            base_dir = os.path.join(home, ".marknote", "versions")
        
        self.base_dir = base_dir
        self._ensure_version_dir()
    
    def _ensure_version_dir(self) -> None:
        """Ensure the version directory exists."""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
    
    def _get_note_version_dir(self, note_id: str) -> str:
        """
        Get the directory for storing versions of a specific note.
        
        Args:
            note_id: Unique identifier for the note (typically a hash of title/path)
            
        Returns:
            The path to the version directory for this note
        """
        note_version_dir = os.path.join(self.base_dir, note_id)
        os.makedirs(note_version_dir, exist_ok=True)
        return note_version_dir
    
    def _get_version_info_path(self, note_id: str) -> str:
        """Get path to version info file for a note."""
        return os.path.join(self._get_note_version_dir(note_id), "version_info.json")
    
    def generate_note_id(self, note_path: str, title: str) -> str:
        """
        Generate a unique identifier for a note.
        
        Args:
            note_path: Path to the note file
            title: Title of the note
            
        Returns:
            A unique string ID for the note
        """
        # Use a combination of simplified title and path hash for identification
        import hashlib
        # Create a unique identifier based on path and title
        unique_str = f"{note_path}:{title}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def save_version(self, note_id: str, content: str, title: str, 
                     author: Optional[str] = None, message: Optional[str] = None) -> str:
        """
        Save a new version of a note.
        
        Args:
            note_id: Unique identifier for the note
            content: Current content of the note
            title: Title of the note
            author: Optional author of the change
            message: Optional message describing the change
            
        Returns:
            The version ID of the new version
        """
        self._ensure_version_dir()
        note_version_dir = self._get_note_version_dir(note_id)
        
        # Get existing version info or create new
        version_info_path = self._get_version_info_path(note_id)
        if os.path.exists(version_info_path):
            with open(version_info_path, 'r', encoding='utf-8') as f:
                version_info = json.load(f)
        else:
            version_info = {
                "note_id": note_id,
                "title": title,
                "versions": []
            }
        
        # Generate a new version ID
        timestamp = datetime.now().isoformat()
        version_id = f"v{len(version_info['versions']) + 1}_{timestamp.replace(':', '-')}"
        
        # Save the content to a version file
        version_path = os.path.join(note_version_dir, f"{version_id}.md")
        with open(version_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update version info
        version_info["versions"].append({
            "version_id": version_id,
            "timestamp": timestamp,
            "author": author or "Unknown",
            "message": message or "Update note",
            "path": version_path
        })
        
        # Save updated version info
        with open(version_info_path, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, indent=2)
        
        return version_id
    
    def get_version_history(self, note_id: str) -> List[Dict[str, Any]]:
        """
        Get the version history for a note.
        
        Args:
            note_id: Unique identifier for the note
            
        Returns:
            A list of version information dictionaries, in chronological order (oldest first)
        """
        version_info_path = self._get_version_info_path(note_id)
        if not os.path.exists(version_info_path):
            return []
        
        with open(version_info_path, 'r', encoding='utf-8') as f:
            version_info = json.load(f)
        
        # Return versions in chronological order
        return version_info.get("versions", [])
    
    def get_version_content(self, note_id: str, version_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Get the content of a specific version.
        
        Args:
            note_id: Unique identifier for the note
            version_id: ID of the version to retrieve
            
        Returns:
            A tuple of (content, version_info)
            
        Raises:
            FileNotFoundError: If the version doesn't exist
        """
        history = self.get_version_history(note_id)
        version = next((v for v in history if v["version_id"] == version_id), None)
        
        if not version or not os.path.exists(version["path"]):
            raise FileNotFoundError(f"Version {version_id} not found")
        
        with open(version["path"], 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content, version
    
    def get_latest_version(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest version info for a note.
        
        Args:
            note_id: Unique identifier for the note
            
        Returns:
            The latest version info, or None if no versions exist
        """
        history = self.get_version_history(note_id)
        if not history:
            return None
        return history[-1]
    
    def compare_versions(self, note_id: str, old_version_id: str, 
                         new_version_id: Optional[str] = None) -> List[str]:
        """
        Compare two versions of a note and generate a diff.
        
        Args:
            note_id: Unique identifier for the note
            old_version_id: ID of the older version to compare
            new_version_id: ID of the newer version to compare. If None, uses the latest version.
            
        Returns:
            A list of lines showing the differences
        """
        # Get old version content
        old_content, _ = self.get_version_content(note_id, old_version_id)
        
        # Get new version content
        if new_version_id:
            new_content, _ = self.get_version_content(note_id, new_version_id)
        else:
            # Use the latest version
            latest = self.get_latest_version(note_id)
            if not latest:
                raise ValueError("No versions available")
                
            new_content, _ = self.get_version_content(note_id, latest["version_id"])
        
        # Generate diff
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        differ = difflib.Differ()
        return list(differ.compare(old_lines, new_lines))
    
    def restore_version(self, note_id: str, version_id: str, note_path: str) -> bool:
        """
        Restore a note to a specific version.
        
        Args:
            note_id: Unique identifier for the note
            version_id: ID of the version to restore
            note_path: Path to the note file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get version content
            content, _ = self.get_version_content(note_id, version_id)
            
            # Backup current file
            if os.path.exists(note_path):
                backup_path = f"{note_path}.backup"
                shutil.copy2(note_path, backup_path)
            
            # Write content to note file
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True
        except Exception:
            # Restore from backup if anything goes wrong
            if os.path.exists(f"{note_path}.backup"):
                shutil.copy2(f"{note_path}.backup", note_path)
            return False
        finally:
            # Clean up backup
            if os.path.exists(f"{note_path}.backup"):
                os.remove(f"{note_path}.backup")