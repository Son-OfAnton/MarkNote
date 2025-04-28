"""
Core note management functionality for MarkNote.
"""
import os
from typing import List, Optional, Dict, Any, Set, Tuple
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
            content = self.template_manager.render_template(
                template_name, context)
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
            raise PermissionError(
                f"Cannot write to the specified path: {note_path}")

        # Don't overwrite existing notes unless explicitly handled elsewhere
        if os.path.exists(note_path):
            raise FileExistsError(
                f"A note with the title '{title}' already exists.")

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

    def find_note_path(self, title: str, category: Optional[str] = None,
                       output_dir: Optional[str] = None) -> Optional[str]:
        """
        Find a note's file path based on title, category, and optional output directory.
        This is a more thorough search method that will try multiple combinations.

        Args:
            title: The title of the note.
            category: Optional category of the note.
            output_dir: Optional specific directory to look for the note.

        Returns:
            The path to the note file if found, None otherwise.
        """
        # Generate filename from title
        filename = f"{slugify(title)}.md"

        # Determine the base directory
        if output_dir:
            base_dir = os.path.expanduser(output_dir)
            if not os.path.isabs(base_dir):
                base_dir = os.path.abspath(base_dir)
        else:
            base_dir = self.notes_dir

        # Try various combinations to find the note
        possible_paths = []

        # If category is provided, prioritize that path
        if category:
            possible_paths.append(os.path.join(base_dir, category, filename))

        # Also try without category (in case the note is directly in the base directory)
        possible_paths.append(os.path.join(base_dir, filename))

        # If category is not provided, also check in all subdirectories
        if not category:
            try:
                for item in os.listdir(base_dir):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isdir(item_path):
                        possible_paths.append(
                            os.path.join(item_path, filename))
            except (FileNotFoundError, PermissionError):
                # If we can't access the directory, just continue with other checks
                pass

        # Check each path in order
        for path in possible_paths:
            if os.path.isfile(path):
                return path

        return None

    def update_note(self, title: str, new_content: Optional[str] = None,
                    new_tags: Optional[List[str]] = None,
                    new_category: Optional[str] = None,
                    additional_metadata: Optional[Dict[str, Any]] = None,
                    category: Optional[str] = None,
                    output_dir: Optional[str] = None) -> Tuple[bool, Optional[Note], str]:
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
            # Try a more thorough search
            note_path = self.find_note_path(title, category, output_dir)
            if note_path:
                # Try to read the note content
                try:
                    with open(note_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Parse frontmatter and content
                    metadata, content_without_frontmatter = parse_frontmatter(
                        content)

                    # Extract category from path if it doesn't match the filename directly
                    path_parts = os.path.normpath(note_path).split(os.path.sep)
                    if len(path_parts) >= 2:
                        # Check if second-to-last part is a directory (category)
                        possible_category = path_parts[-2]
                        # Verify this is not the base directory name
                        base_name = os.path.basename(
                            output_dir if output_dir else self.notes_dir)
                        detected_category = possible_category if possible_category != base_name else category
                    else:
                        detected_category = category

                    # Create a note object
                    created_at = metadata.get('created_at')
                    if isinstance(created_at, str):
                        try:
                            created_at = datetime.fromisoformat(created_at)
                        except ValueError:
                            created_at = datetime.now()
                    else:
                        created_at = datetime.now()

                    updated_at = metadata.get('updated_at')
                    if isinstance(updated_at, str):
                        try:
                            updated_at = datetime.fromisoformat(updated_at)
                        except ValueError:
                            updated_at = datetime.now()
                    else:
                        updated_at = datetime.now()

                    note = Note(
                        title=title,
                        content=content_without_frontmatter,
                        created_at=created_at,
                        updated_at=updated_at,
                        tags=metadata.get('tags', []),
                        category=metadata.get('category', detected_category),
                        filename=os.path.basename(note_path),
                        metadata=metadata
                    )
                    note.metadata['path'] = note_path

                except Exception as e:
                    return False, None, f"Found note at {note_path} but failed to read it: {str(e)}"
            else:
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
            new_dir = os.path.join(
                base_dir, new_category) if new_category else base_dir
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
        # Try to find the note path
        note_path = self.find_note_path(title, category, output_dir)

        if not note_path:
            return None

        # Read the note content
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter and content
        metadata, content_without_frontmatter = parse_frontmatter(content)

        # Extract basic metadata
        try:
            created_at = datetime.fromisoformat(
                metadata.get('created_at', datetime.now().isoformat()))
        except (ValueError, TypeError):
            created_at = datetime.now()

        try:
            updated_at = datetime.fromisoformat(
                metadata.get('updated_at', datetime.now().isoformat()))
        except (ValueError, TypeError):
            updated_at = datetime.now()

        tags = metadata.get('tags', [])
        detected_category = metadata.get('category', category)

        # If no category is provided in metadata, try to determine it from the path
        if not detected_category:
            path_parts = os.path.normpath(note_path).split(os.path.sep)
            if len(path_parts) >= 2:
                # Check if second-to-last part might be a category directory
                possible_category = path_parts[-2]
                # Get the base directory name to avoid confusing it with a category
                base_dir = output_dir if output_dir else self.notes_dir
                base_name = os.path.basename(os.path.normpath(base_dir))
                if possible_category != base_name:
                    detected_category = possible_category

        # Create and return the note object
        note = Note(
            title=title,
            content=content_without_frontmatter,
            created_at=created_at,
            updated_at=updated_at,
            tags=tags,
            category=detected_category,
            filename=os.path.basename(note_path),
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


    def add_link_between_notes(self, source_title: str, target_title: str,
                               bidirectional: bool = False,
                               category: Optional[str] = None,
                               target_category: Optional[str] = None,
                               output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Add a link from source note to target note.

        Args:
            source_title: Title of the source note.
            target_title: Title of the target note.
            bidirectional: If True, also create a link from target to source.
            category: Optional category of the source note.
            target_category: Optional category of the target note.
            output_dir: Optional specific directory to look for notes.
                       This overrides the notes_dir for this specific operation.

        Returns:
            A tuple of (success, error_message).
        """
        # Verify that source note exists
        try:
            source_note = self.get_note(source_title, category, output_dir)
            if not source_note:
                return False, f"Source note '{source_title}' not found."
        except Exception as e:
            return False, f"Error accessing source note: {str(e)}"

        # Verify that target note exists
        try:
            target_note = self.get_note(
                target_title, target_category, output_dir)
            if not target_note:
                return False, f"Target note '{target_title}' not found."
        except Exception as e:
            return False, f"Error accessing target note: {str(e)}"

        # Prevent self-linking
        if source_title == target_title:
            return False, "Cannot link a note to itself."

        # Add link from source to target
        source_note.add_link(target_title)

        # If bidirectional, add link from target to source
        if bidirectional:
            target_note.add_link(source_title)

        # Save both notes
        try:
            # Update source note
            success, _, error = self.update_note(
                title=source_title,
                category=category,
                output_dir=output_dir,
                additional_metadata={
                    "linked_notes": list(source_note.get_links())}
            )
            if not success:
                return False, f"Failed to update source note: {error}"

            # Update target note if bidirectional
            if bidirectional:
                success, _, error = self.update_note(
                    title=target_title,
                    category=target_category,
                    output_dir=output_dir,
                    additional_metadata={
                        "linked_notes": list(target_note.get_links())}
                )
                if not success:
                    return False, f"Failed to update target note: {error}"

            return True, ""
        except Exception as e:
            return False, f"Error saving notes: {str(e)}"

    def remove_link_between_notes(self, source_title: str, target_title: str,
                                  bidirectional: bool = False,
                                  category: Optional[str] = None,
                                  target_category: Optional[str] = None,
                                  output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Remove a link from source note to target note.

        Args:
            source_title: Title of the source note.
            target_title: Title of the target note.
            bidirectional: If True, also remove the link from target to source.
            category: Optional category of the source note.
            target_category: Optional category of the target note.
            output_dir: Optional specific directory to look for notes.

        Returns:
            A tuple of (success, error_message).
        """
        # Verify that source note exists
        try:
            source_note = self.get_note(source_title, category, output_dir)
            if not source_note:
                return False, f"Source note '{source_title}' not found."
        except Exception as e:
            return False, f"Error accessing source note: {str(e)}"

        # Verify that target note exists (only needed if bidirectional)
        target_note = None
        if bidirectional:
            try:
                target_note = self.get_note(
                    target_title, target_category, output_dir)
                if not target_note:
                    return False, f"Target note '{target_title}' not found."
            except Exception as e:
                return False, f"Error accessing target note: {str(e)}"

        # Remove link from source to target
        if target_title in source_note.get_links():
            source_note.remove_link(target_title)
        else:
            return False, f"No link exists from '{source_title}' to '{target_title}'."

        # If bidirectional, remove link from target to source
        if bidirectional and target_note:
            if source_title in target_note.get_links():
                target_note.remove_link(source_title)

        # Save both notes
        try:
            # Update source note
            success, _, error = self.update_note(
                title=source_title,
                category=category,
                output_dir=output_dir,
                additional_metadata={
                    "linked_notes": list(source_note.get_links())}
            )
            if not success:
                return False, f"Failed to update source note: {error}"

            # Update target note if bidirectional
            if bidirectional and target_note:
                success, _, error = self.update_note(
                    title=target_title,
                    category=target_category,
                    output_dir=output_dir,
                    additional_metadata={
                        "linked_notes": list(target_note.get_links())}
                )
                if not success:
                    return False, f"Failed to update target note: {error}"

            return True, ""
        except Exception as e:
            return False, f"Error saving notes: {str(e)}"

    def get_linked_notes(self, title: str, category: Optional[str] = None,
                         output_dir: Optional[str] = None) -> Tuple[bool, List[Note], str]:
        """
        Get all notes linked from the specified note.

        Args:
            title: The title of the note.
            category: Optional category to help find the note.
            output_dir: Optional directory to look for the note.

        Returns:
            A tuple of (success, list of linked notes, error message).
        """
        # Get the source note
        source_note = self.get_note(title, category, output_dir)
        if not source_note:
            return False, [], f"Note '{title}' not found."

        # Get the linked note titles
        linked_titles = source_note.get_links()
        if not linked_titles:
            return True, [], ""

        # Retrieve all linked notes
        linked_notes = []
        missing_notes = []

        for linked_title in linked_titles:
            # Try to find the linked note
            linked_note = self.get_note(linked_title, output_dir=output_dir)
            if linked_note:
                linked_notes.append(linked_note)
            else:
                missing_notes.append(linked_title)

        # If there are missing notes, include a warning in the error message
        error = ""
        if missing_notes:
            error = f"Could not find the following linked notes: {', '.join(missing_notes)}"

        return True, linked_notes, error

    def get_backlinks(self, title: str, category: Optional[str] = None,
                      output_dir: Optional[str] = None) -> Tuple[bool, List[Note], str]:
        """
        Get all notes that link to the specified note.

        Args:
            title: The title of the note to find backlinks for.
            category: Optional category to help find the note.
            output_dir: Optional directory to look for notes.

        Returns:
            A tuple of (success, list of notes linking to the specified note, error message).
        """
        # First check if the note exists
        target_note = self.get_note(title, category, output_dir)
        if not target_note:
            return False, [], f"Note '{title}' not found."

        # Get all notes
        all_notes = self.list_notes(output_dir=output_dir)

        # Find notes that link to the specified note
        backlinks = []
        for note in all_notes:
            if title in note.get_links():
                backlinks.append(note)

        return True, backlinks, ""

    def find_orphaned_links(self, output_dir: Optional[str] = None) -> List[Tuple[Note, Set[str]]]:
        """
        Find all orphaned links (links to notes that don't exist).

        Args:
            output_dir: Optional directory to look for notes.

        Returns:
            A list of tuples (note, set of orphaned link titles).
        """
        # Get all notes
        all_notes = self.list_notes(output_dir=output_dir)

        # Create a set of all note titles
        all_titles = {note.title for note in all_notes}

        # Find orphaned links
        orphaned_links = []

        for note in all_notes:
            linked_titles = note.get_links()
            if linked_titles:
                # Find links to non-existent notes
                missing_links = linked_titles - all_titles
                if missing_links:
                    orphaned_links.append((note, missing_links))

        return orphaned_links

    def get_note_with_links(self, title: str, category: Optional[str] = None,
                            output_dir: Optional[str] = None) -> Tuple[Optional[Note], List[Note], List[Note]]:
        """
        Get a note along with its linked notes and backlinks.

        Args:
            title: The title of the note.
            category: Optional category to help find the note.
            output_dir: Optional directory to look for the note.

        Returns:
            A tuple of (note, linked notes, backlinks).
        """
        # Get the main note
        note = self.get_note(title, category, output_dir)
        if not note:
            return None, [], []

        # Get linked notes
        _, linked_notes, _ = self.get_linked_notes(title, category, output_dir)

        # Get backlinks
        _, backlinks, _ = self.get_backlinks(title, category, output_dir)

        return note, linked_notes, backlinks


    def generate_link_graph(self, output_dir: Optional[str] = None) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        """
        Generate a graph of all links between notes.
        
        Args:
            output_dir: Optional directory to look for notes.
            
        Returns:
            A tuple of (outgoing_links, incoming_links) dictionaries.
            - outgoing_links maps note titles to sets of linked note titles
            - incoming_links maps note titles to sets of notes that link to them
        """
        # Get all notes
        all_notes = self.list_notes(output_dir=output_dir)
        
        # Create the link graphs
        outgoing_links: Dict[str, Set[str]] = {}
        incoming_links: Dict[str, Set[str]] = {}
        
        # Initialize graph with all notes (even those without links)
        for note in all_notes:
            outgoing_links[note.title] = set()
            incoming_links[note.title] = set()
        
        # Populate outgoing and incoming links
        for note in all_notes:
            if hasattr(note, 'linked_notes') and note.linked_notes:
                outgoing_links[note.title] = set(note.linked_notes)
                
                # Update the incoming links for each linked note
                for linked_title in note.linked_notes:
                    if linked_title in incoming_links:
                        incoming_links[linked_title].add(note.title)
                    else:
                        # If it's a link to a note we haven't seen yet
                        incoming_links[linked_title] = {note.title}
        
        return outgoing_links, incoming_links

    def get_linked_notes_stats(self, output_dir: Optional[str] = None) -> Dict[str, Tuple[int, int, List[str], List[str]]]:
        """
        Get statistics about links between notes.
        
        Args:
            output_dir: Optional directory to look for notes.
            
        Returns:
            A dictionary mapping note titles to tuples of:
            (outgoing link count, incoming link count, outgoing link titles, incoming link titles)
        """
        outgoing_links, incoming_links = self.generate_link_graph(output_dir=output_dir)
        
        link_stats = {}
        
        # For each note, compile its statistics
        for title in outgoing_links:
            out_links = list(outgoing_links[title])
            in_links = list(incoming_links.get(title, set()))
            
            link_stats[title] = (
                len(out_links),  # Outgoing link count
                len(in_links),   # Incoming link count
                out_links,       # List of outgoing link titles
                in_links         # List of incoming link titles
            )
        
        # Also include notes that only have incoming links
        for title in incoming_links:
            if title not in link_stats:
                in_links = list(incoming_links[title])
                link_stats[title] = (0, len(in_links), [], in_links)
        
        return link_stats

    def find_most_linked_notes(self, output_dir: Optional[str] = None, limit: int = 10) -> List[Tuple[str, int, int]]:
        """
        Find the most connected notes in the network.
        
        Args:
            output_dir: Optional directory to look for notes.
            limit: Maximum number of notes to return.
            
        Returns:
            A list of tuples (note_title, outgoing_links, incoming_links) sorted by total links.
        """
        link_stats = self.get_linked_notes_stats(output_dir=output_dir)
        
        # Sort by total links (outgoing + incoming)
        sorted_stats = sorted(
            [(title, stats[0], stats[1]) for title, stats in link_stats.items()],
            key=lambda x: x[1] + x[2],  # Sort by sum of outgoing and incoming
            reverse=True  # Most linked first
        )
        
        return sorted_stats[:limit]

    def find_orphaned_links(self, output_dir: Optional[str] = None) -> List[Tuple[Note, Set[str]]]:
        """
        Find all orphaned links (links to notes that don't exist).
        
        Args:
            output_dir: Optional directory to look for notes.
                
        Returns:
            A list of tuples (note, set of orphaned link titles).
        """
        # Get all notes
        all_notes = self.list_notes(output_dir=output_dir)
        
        # Create a set of all note titles
        all_titles = {note.title for note in all_notes}
        
        # Find orphaned links
        orphaned_links = []
        
        for note in all_notes:
            linked_titles = note.get_links()
            if linked_titles:
                # Find links to non-existent notes
                missing_links = linked_titles - all_titles
                if missing_links:
                    orphaned_links.append((note, missing_links))
        
        return orphaned_links

    def find_standalone_notes(self, output_dir: Optional[str] = None) -> List[Note]:
        """
        Find notes that have no links to or from other notes.
        
        Args:
            output_dir: Optional directory to look for notes.
            
        Returns:
            A list of standalone notes.
        """
        outgoing_links, incoming_links = self.generate_link_graph(output_dir=output_dir)
        all_notes = self.list_notes(output_dir=output_dir)
        
        standalone_notes = []
        
        for note in all_notes:
            # Check if the note has any outgoing or incoming links
            if (not outgoing_links.get(note.title) and 
                not incoming_links.get(note.title)):
                standalone_notes.append(note)
        
        return standalone_notes
    
    
    def list_notes(self, tag: Optional[str] = None,
                   category: Optional[str] = None,
                   output_dir: Optional[str] = None,
                   sort_by: str = "updated") -> List[Note]:
        """
        List notes, optionally filtered by tag or category.

        Args:
            tag: Optional tag to filter by.
            category: Optional category to filter by.
            output_dir: Optional specific directory to look for the notes.
                        This overrides the notes_dir for this specific listing.
            sort_by: Sorting method - "updated" (default), "created", or "title"

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
            title = metadata.get('title', os.path.basename(
                file_path)[:-3])  # Remove .md

            # Handle date parsing with error handling
            try:
                created_at = datetime.fromisoformat(
                    metadata.get('created_at', datetime.now().isoformat()))
            except (ValueError, TypeError):
                created_at = datetime.now()

            try:
                updated_at = datetime.fromisoformat(
                    metadata.get('updated_at', datetime.now().isoformat()))
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

        # Sort notes based on the specified sort_by parameter
        if sort_by == "updated":
            notes.sort(key=lambda x: x.updated_at, reverse=True)
        elif sort_by == "created":
            notes.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "title":
            notes.sort(key=lambda x: x.title.lower())
        # Add other sorting options here if needed

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

            # Check tags
            if any(query in tag.lower() for tag in note.tags):
                matching_notes.append(note)
                continue

            # Check content
            if query in note.content.lower():
                matching_notes.append(note)
                continue

        return matching_notes