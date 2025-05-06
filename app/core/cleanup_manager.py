"""
CleanupManager for identifying and removing empty and duplicate notes.
"""
import os
import difflib
from typing import List, Dict, Tuple, Set, Optional, Any
from dataclasses import dataclass
import re

from app.models.note import Note
from app.core.note_manager import NoteManager


@dataclass
class EmptyNoteInfo:
    """Information about an empty note."""
    title: str
    category: Optional[str]
    path: str
    size_bytes: int
    has_metadata: bool
    has_tags: bool
    link_count: int


@dataclass
class DuplicateGroup:
    """Group of duplicate notes."""
    notes: List[Note]
    similarity: float  # 0.0-1.0, where 1.0 is 100% similar
    content_hash: str  # Hash of content for comparison


class CleanupManager:
    """
    Manager for finding and cleaning up empty and duplicate notes.
    """
    
    def __init__(self, note_manager: Optional[NoteManager] = None, notes_dir: Optional[str] = None):
        """
        Initialize the CleanupManager.
        
        Args:
            note_manager: Optional NoteManager. If None, a new one is created.
            notes_dir: Directory containing notes. If None, the default notes directory is used.
        """
        self.note_manager = note_manager if note_manager else NoteManager(notes_dir)
        self.notes_dir = self.note_manager.notes_dir
    
    def find_empty_notes(self, 
                         min_content_length: int = 10,
                         include_whitespace_only: bool = True) -> List[EmptyNoteInfo]:
        """
        Find notes that have no content or minimal content.
        
        Args:
            min_content_length: Minimum number of characters to consider a note non-empty.
            include_whitespace_only: Whether to include notes that have only whitespace.
            
        Returns:
            List of empty note information.
        """
        empty_notes = []
        
        # Get all notes
        note_files = self.note_manager.list_notes()
        
        for note_info in note_files:
            # Get note title and category
            title = note_info.get("title")
            category = note_info.get("category")
            
            try:
                # Load the note
                note = self.note_manager.get_note(title, category)
                
                if not note:
                    continue
                
                # Get note path
                note_path = self.note_manager.find_note_path(title, category)
                
                # Get file size
                size_bytes = os.path.getsize(note_path) if note_path else 0
                
                # Clean content (remove whitespace if configured)
                cleaned_content = note.content
                if include_whitespace_only:
                    cleaned_content = cleaned_content.strip()
                
                # Check if content is empty or under the minimum length
                if not cleaned_content or len(cleaned_content) < min_content_length:
                    # Create empty note info
                    empty_note = EmptyNoteInfo(
                        title=title,
                        category=category,
                        path=note_path or "",
                        size_bytes=size_bytes,
                        has_metadata=bool(note.metadata),
                        has_tags=bool(note.tags),
                        link_count=len(note.get_links())
                    )
                    
                    empty_notes.append(empty_note)
                    
            except Exception as e:
                # Skip notes that can't be processed
                print(f"Error processing note {title}: {str(e)}")
        
        return empty_notes
    
    def _get_content_hash(self, content: str) -> str:
        """
        Generate a simple hash of content for comparison.
        
        Args:
            content: The content to hash.
            
        Returns:
            A string representing the content hash.
        """
        # Normalize content: convert to lowercase, remove whitespace
        normalized = re.sub(r'\s+', '', content.lower())
        
        # Use a simple hash function
        import hashlib
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate the similarity ratio between two texts.
        
        Args:
            text1: First text.
            text2: Second text.
        
        Returns:
            Similarity ratio between 0.0 and 1.0.
        """
        # Convert to lowercase and strip whitespace for more accurate comparison
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Use difflib's SequenceMatcher for comparing text similarity
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    def find_duplicate_notes(self, 
                             similarity_threshold: float = 0.9,
                             compare_content_only: bool = False,
                             ignore_case: bool = True) -> List[DuplicateGroup]:
        """
        Find notes that have duplicate or highly similar content.
        
        Args:
            similarity_threshold: Minimum similarity ratio (0.0-1.0) to consider notes as duplicates.
            compare_content_only: Whether to compare only the content (True) or content and metadata (False).
            ignore_case: Whether to ignore case during comparison.
            
        Returns:
            List of duplicate note groups.
        """
        duplicate_groups = []
        
        # Get all notes
        note_files = self.note_manager.list_notes()
        
        # Dictionary to store notes by content hash for quick duplicate detection
        notes_by_hash = {}
        
        # First pass: group by hash (exact duplicates)
        for note_info in note_files:
            # Get note title and category
            # title = note_info.get("title")
            # category = note_info.get("category")
            title = note_info.title
            category = note_info.category
            
            try:
                # Load the note
                note = self.note_manager.get_note(title, category)
                
                if not note:
                    continue
                
                # Get the content to compare
                compare_text = note.content
                if not compare_content_only:
                    # Include metadata in comparison (tags, category)
                    tags_text = ",".join(note.tags) if note.tags else ""
                    category_text = note.category if note.category else ""
                    compare_text = f"{compare_text}\n{tags_text}\n{category_text}"
                
                # Apply case normalization if requested
                if ignore_case:
                    compare_text = compare_text.lower()
                
                # Generate content hash
                content_hash = self._get_content_hash(compare_text)
                
                # Add to hash-based dictionary
                if content_hash in notes_by_hash:
                    notes_by_hash[content_hash].append(note)
                else:
                    notes_by_hash[content_hash] = [note]
                    
            except Exception as e:
                # Skip notes that can't be processed
                print(f"Error processing note {title}: {str(e)}")
        
        # Convert exact duplicates (same hash) to duplicate groups
        for content_hash, notes in notes_by_hash.items():
            if len(notes) > 1:  # Only include if there are multiple notes with the same hash
                duplicate_groups.append(DuplicateGroup(
                    notes=notes,
                    similarity=1.0,  # Exact duplicates
                    content_hash=content_hash
                ))
        
        # Second pass: check for similar but not identical content
        # Only if similarity threshold is less than 1.0
        if similarity_threshold < 1.0:
            # Get list of all notes that aren't exact duplicates
            unique_hashes = [h for h, notes in notes_by_hash.items() if len(notes) == 1]
            unique_notes = [notes[0] for h, notes in notes_by_hash.items() if len(notes) == 1]
            
            # Compare each unique note with others
            for i in range(len(unique_notes)):
                for j in range(i + 1, len(unique_notes)):
                    note1 = unique_notes[i]
                    note2 = unique_notes[j]
                    
                    # Get comparison text using same rules as above
                    text1 = note1.content
                    text2 = note2.content
                    
                    if not compare_content_only:
                        # Include metadata
                        tags1 = ",".join(note1.tags) if note1.tags else ""
                        category1 = note1.category if note1.category else ""
                        text1 = f"{text1}\n{tags1}\n{category1}"
                        
                        tags2 = ",".join(note2.tags) if note2.tags else ""
                        category2 = note2.category if note2.category else ""
                        text2 = f"{text2}\n{tags2}\n{category2}"
                    
                    # Apply case normalization if requested
                    if ignore_case:
                        text1 = text1.lower()
                        text2 = text2.lower()
                    
                    # Calculate similarity
                    similarity = self._calculate_similarity(text1, text2)
                    
                    # If similar enough, create a new duplicate group
                    if similarity >= similarity_threshold:
                        duplicate_groups.append(DuplicateGroup(
                            notes=[note1, note2],
                            similarity=similarity,
                            content_hash=f"{unique_hashes[i]}_{unique_hashes[j]}"
                        ))
        
        return duplicate_groups
    
    def delete_empty_notes(self, 
                           empty_notes: List[EmptyNoteInfo],
                           dry_run: bool = False) -> Tuple[int, List[str], List[str]]:
        """
        Delete empty notes.
        
        Args:
            empty_notes: List of empty notes to delete.
            dry_run: If True, only simulate deletion without actually deleting.
            
        Returns:
            Tuple of (number of notes deleted, titles of deleted notes, error messages).
        """
        deleted_count = 0
        deleted_titles = []
        errors = []
        
        for empty_note in empty_notes:
            title = empty_note.title
            category = empty_note.category
            
            try:
                if not dry_run:
                    # Delete the note
                    success = self.note_manager.delete_note(title, category)
                    
                    if success:
                        deleted_count += 1
                        deleted_titles.append(title)
                    else:
                        errors.append(f"Failed to delete note: {title}")
                else:
                    # In dry run mode, just count
                    deleted_count += 1
                    deleted_titles.append(title)
                    
            except Exception as e:
                errors.append(f"Error deleting note {title}: {str(e)}")
        
        return deleted_count, deleted_titles, errors
    
    def delete_duplicate_notes(self, 
                               duplicate_groups: List[DuplicateGroup],
                               keep_strategy: str = "newest",
                               dry_run: bool = False) -> Tuple[int, List[str], List[str]]:
        """
        Delete duplicate notes, keeping one note from each group.
        
        Args:
            duplicate_groups: List of duplicate note groups.
            keep_strategy: Strategy for which note to keep. Options:
                - "newest": Keep the most recently updated note
                - "oldest": Keep the oldest note
                - "longest": Keep the note with the most content
                - "shortest": Keep the note with the least content
            dry_run: If True, only simulate deletion without actually deleting.
            
        Returns:
            Tuple of (number of notes deleted, titles of deleted notes, error messages).
        """
        deleted_count = 0
        deleted_titles = []
        errors = []
        
        for group in duplicate_groups:
            notes = group.notes
            
            # Skip if there's only one note
            if len(notes) <= 1:
                continue
                
            # Determine which note to keep based on strategy
            if keep_strategy == "newest":
                # Sort by updated_at, most recent first
                sorted_notes = sorted(notes, key=lambda n: n.updated_at, reverse=True)
                keep_note = sorted_notes[0]
            elif keep_strategy == "oldest":
                # Sort by created_at, oldest first
                sorted_notes = sorted(notes, key=lambda n: n.created_at)
                keep_note = sorted_notes[0]
            elif keep_strategy == "longest":
                # Sort by content length, longest first
                sorted_notes = sorted(notes, key=lambda n: len(n.content), reverse=True)
                keep_note = sorted_notes[0]
            elif keep_strategy == "shortest":
                # Sort by content length, shortest first
                sorted_notes = sorted(notes, key=lambda n: len(n.content))
                keep_note = sorted_notes[0]
            else:
                # Default to newest
                sorted_notes = sorted(notes, key=lambda n: n.updated_at, reverse=True)
                keep_note = sorted_notes[0]
            
            # Delete all notes except the one to keep
            for note in notes:
                if note.title != keep_note.title or note.category != keep_note.category:
                    try:
                        if not dry_run:
                            # Delete the note
                            success = self.note_manager.delete_note(note.title, note.category)
                            
                            if success:
                                deleted_count += 1
                                deleted_titles.append(note.title)
                            else:
                                errors.append(f"Failed to delete note: {note.title}")
                        else:
                            # In dry run mode, just count
                            deleted_count += 1
                            deleted_titles.append(note.title)
                            
                    except Exception as e:
                        errors.append(f"Error deleting note {note.title}: {str(e)}")
        
        return deleted_count, deleted_titles, errors