"""
Core note management functionality for MarkNote.
"""
from collections import Counter
import os
from typing import List, Optional, Dict, Any, Set, Tuple
from datetime import date as dt, datetime
import yaml
from slugify import slugify

from app.models.note import Note
from app.utils.file_handler import (
    ensure_notes_dir,
    parse_frontmatter,
    add_frontmatter,
    list_note_files,
    read_note_file,
    validate_path,
    write_note_file,
)
from app.utils.template_manager import TemplateManager
from app.utils.version_control import VersionControlManager


class NoteManager:
    """
    Manages notes in the filesystem.
    """

    def __init__(self, notes_dir: Optional[str] = None, enable_version_control: bool = True):
        """
        Initialize the NoteManager with the specified notes directory.

        Args:
            notes_dir: Optional custom directory path for storing notes.
                      If not provided, the default directory will be used.
            enable_version_control: Whether to enable version control.
        """
        self.notes_dir = ensure_notes_dir(notes_dir)
        self.template_manager = TemplateManager()

        # Initialize version control
        self.version_control_enabled = enable_version_control
        if self.version_control_enabled:
            self.version_manager = VersionControlManager()

    # Copy your create_version method here - you'll add the rest of the class below
    def create_version(self, title: str, category: Optional[str] = None,
                       output_dir: Optional[str] = None,
                       message: Optional[str] = None,
                       author: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Manually create a new version of an existing note.

        Args:
            title: The title of the note.
            category: Optional category to help find the note.
            output_dir: Optional specific directory to look for the note.
            message: Optional message describing this version.
            author: Optional author of the version.

        Returns:
            A tuple of (success, message, version_id).
        """
        if not self.version_control_enabled:
            return False, "Version control is not enabled.", None

        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found.", None

        try:
            # Read the current note content
            metadata, content = read_note_file(note_path)

            # Create a version ID
            note_id = self.version_manager.generate_note_id(note_path, title)
            full_content = self._get_full_note_content(metadata, content)

            # Save the version
            version_id = self.version_manager.save_version(
                note_id,
                full_content,
                title,
                author,
                message or f"Manual version created for: {title}"
            )

            return True, f"Version {version_id} created successfully.", version_id

        except Exception as e:
            return False, f"Error creating version: {str(e)}", None

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
                    output_dir: Optional[str] = None,
                    commit_message: Optional[str] = None,
                    author: Optional[str] = None) -> Tuple[bool, str, Optional[Note]]:
        """
        Update an existing note and save the change in version history.

        Args:
            All existing parameters, plus:
            commit_message: Optional message describing the change
            author: Optional author of the change
        """
        # Call the original update_note method
        # For this example, we'll simulate the result

        # Find the note
        note_path = self.find_note_path(title, new_category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found.", None

        # Get existing content
        try:
            metadata, content = read_note_file(note_path)
        except Exception as e:
            return False, f"Error reading note: {str(e)}", None

        # Update content
        if new_content is not None:
            content = new_content

        # Update metadata
        if new_tags is not None:
            metadata['tags'] = new_tags
        if new_category is not None:
            metadata['category'] = new_category
        if additional_metadata is not None:
            for key, value in additional_metadata.items():
                metadata[key] = value

        # Update the updated_at timestamp
        metadata['updated_at'] = datetime.now().isoformat()

        # Create a Note object
        note = Note(
            title=metadata.get('title', title),
            content=content,
            created_at=datetime.fromisoformat(metadata.get(
                'created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(metadata.get('updated_at')),
            tags=metadata.get('tags', []),
            category=metadata.get('category', None),
            filename=os.path.basename(note_path),
            metadata=metadata
        )

        # Save the updated note
        try:
            write_note_file(note_path, metadata, content)

            # Save to version control if enabled
            if self.version_control_enabled:
                note_id = self.version_manager.generate_note_id(
                    note_path, title)
                full_content = self._get_full_note_content(metadata, content)
                self.version_manager.save_version(
                    note_id,
                    full_content,
                    title,
                    author,
                    commit_message or f"Update note: {title}"
                )

            return True, "Note updated successfully.", note

        except Exception as e:
            return False, f"Error updating note: {str(e)}", None

    def _get_full_note_content(self, metadata: Dict[str, Any], content: str) -> str:
        """
        Get the full note content including frontmatter.

        Args:
            metadata: The note metadata
            content: The note content

        Returns:
            The full note content
        """
        # Rebuild the full file content with frontmatter
        frontmatter = "---\n"
        for key, value in metadata.items():
            if isinstance(value, list):
                frontmatter += f"{key}:\n"
                for item in value:
                    frontmatter += f"  - {item}\n"
            else:
                frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"

        return frontmatter + content

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
        outgoing_links, incoming_links = self.generate_link_graph(
            output_dir=output_dir)

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
            [(title, stats[0], stats[1])
             for title, stats in link_stats.items()],
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
        outgoing_links, incoming_links = self.generate_link_graph(
            output_dir=output_dir)
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

    def create_daily_note(self, date_str: Optional[str] = None,
                          tags: List[str] = None,
                          category: str = "daily",
                          template_name: str = "daily",
                          additional_metadata: Optional[Dict[str, Any]] = None,
                          output_dir: Optional[str] = None) -> Tuple[bool, str, Any]:
        """
        Create a daily note for a specific date. If no date is provided, today's date is used.

        Args:
            date_str: Optional date string in format 'YYYY-MM-DD'. If None, today's date is used.
            tags: Optional list of tags for the note.
            category: Category for the daily note. Defaults to "daily".
            template_name: Template to use for the daily note. Defaults to "daily".
            additional_metadata: Optional additional metadata for the frontmatter.
            output_dir: Optional specific directory to save the note to.
                        This overrides the notes_dir for this specific note.

        Returns:
            A tuple of (success, message, note_object) where success is a boolean,
            message is a descriptive string, and note_object is the created Note
            object or None if creation failed.
        """
        if tags is None:
            tags = ["daily"]
        elif "daily" not in tags:
            tags.append("daily")

        if additional_metadata is None:
            additional_metadata = {}

        # Determine the date to use
        if date_str:
            try:
                # Parse the provided date string
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return False, f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD", None
        else:
            # Use today's date - using dt.today() instead of date.today() to avoid name collision
            parsed_date = dt.today()

        # Format date for title and filename
        formatted_date = parsed_date.strftime("%Y-%m-%d")
        day_name = parsed_date.strftime("%A")

        # Create title in format "Daily Note: 2023-01-01 (Monday)"
        title = f"Daily Note: {formatted_date} ({day_name})"

        # Check if a daily note for this date already exists
        existing_note = self.find_daily_note(parsed_date, category, output_dir)
        if existing_note:
            return False, f"A daily note for {formatted_date} already exists.", existing_note

        # Add additional metadata for the daily note
        additional_metadata["date"] = formatted_date
        additional_metadata["day_of_week"] = day_name

        try:
            # Create the note using the existing create_note method
            note = self.create_note(
                title=title,
                template_name=template_name,
                tags=tags,
                category=category,
                additional_metadata=additional_metadata,
                output_dir=output_dir
            )
            return True, f"Daily note created for {formatted_date} ({day_name}).", note
        except Exception as e:
            return False, f"Error creating daily note: {str(e)}", None

    def find_daily_note(self, for_date: dt,
                        category: Optional[str] = "daily",
                        output_dir: Optional[str] = None) -> Any:
        """
        Find a daily note for the specified date, if it exists.

        Args:
            for_date: The date to find a daily note for.
            category: Category to look in. Defaults to "daily".
            output_dir: Optional specific directory to look for the note.

        Returns:
            The Note object if found, None otherwise.
        """
        formatted_date = for_date.strftime("%Y-%m-%d")
        day_name = for_date.strftime("%A")
        title = f"Daily Note: {formatted_date} ({day_name})"

        # Get filtered notes
        notes = self.list_notes(
            tag="daily", category=category, output_dir=output_dir)

        # Look for a note matching the title
        for note in notes:
            if note.title == title:
                return note

        # Also check with format variants (simpler matching)
        alt_title_patterns = [
            f"Daily Note: {formatted_date}",
            f"{formatted_date} - Daily Note",
            f"Daily - {formatted_date}"
        ]

        for note in notes:
            for pattern in alt_title_patterns:
                if pattern in note.title:
                    return note

        # Check metadata 'date' field directly as a last resort
        for note in notes:
            if note.metadata.get('date') == formatted_date:
                return note

        return None

    def get_todays_daily_note(self,
                              category: Optional[str] = "daily",
                              output_dir: Optional[str] = None) -> Tuple[bool, str, Any]:
        """
        Get today's daily note if it exists, or create it if it doesn't.

        Args:
            category: Category for the daily note. Defaults to "daily".
            output_dir: Optional specific directory.

        Returns:
            A tuple containing (exists, message, note) where exists is True if the note
            already existed, message is a descriptive string, and note is the Note object.
        """
        # Use dt.today() instead of date.today() to avoid name collision
        today = dt.today()

        # Check if today's daily note already exists
        existing_note = self.find_daily_note(today, category, output_dir)

        if existing_note:
            return True, "Today's daily note already exists.", existing_note

        # If not, create a new daily note
        success, message, note = self.create_daily_note(
            date_str=None,  # Today by default
            category=category,
            output_dir=output_dir
        )

        return False, message, note

    def get_note_version_history(self, title: str, category: Optional[str] = None,
                                 output_dir: Optional[str] = None) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Get the version history for a note.

        Args:
            title: The title of the note.
            category: Optional category to help find the note.
            output_dir: Optional specific directory to look for the note.

        Returns:
            A tuple of (success, message, versions)
        """
        if not self.version_control_enabled:
            return False, "Version control is not enabled.", []

        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found.", []

        # Generate note ID
        note_id = self.version_manager.generate_note_id(note_path, title)

        # Get version history
        versions = self.version_manager.get_version_history(note_id)

        if not versions:
            return True, "No version history found for this note.", []

        return True, f"Found {len(versions)} versions.", versions

    def get_note_version(self, title: str, version_id: str,
                         category: Optional[str] = None,
                         output_dir: Optional[str] = None) -> Tuple[bool, str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Get a specific version of a note.

        Args:
            title: The title of the note.
            version_id: The ID of the version to retrieve.
            category: Optional category to help find the note.
            output_dir: Optional specific directory to look for the note.

        Returns:
            A tuple of (success, message, content, version_info)
        """
        if not self.version_control_enabled:
            return False, "Version control is not enabled.", None, None

        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found.", None, None

        # Generate note ID
        note_id = self.version_manager.generate_note_id(note_path, title)

        try:
            # Get version content
            content, version_info = self.version_manager.get_version_content(
                note_id, version_id)
            return True, f"Retrieved version {version_id} from {version_info['timestamp']}.", content, version_info
        except FileNotFoundError:
            return False, f"Version {version_id} not found.", None, None
        except Exception as e:
            return False, f"Error retrieving version: {str(e)}", None, None

    def compare_note_versions(self, title: str, old_version_id: str,
                              new_version_id: Optional[str] = None,
                              category: Optional[str] = None,
                              output_dir: Optional[str] = None) -> Tuple[bool, str, Optional[List[str]]]:
        """
        Compare two versions of a note.

        Args:
            title: The title of the note.
            old_version_id: The ID of the older version to compare.
            new_version_id: The ID of the newer version to compare. If None, uses latest version.
            category: Optional category to help find the note.
            output_dir: Optional specific directory to look for the note.

        Returns:
            A tuple of (success, message, diff_lines)
        """
        if not self.version_control_enabled:
            return False, "Version control is not enabled.", None

        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found.", None

        # Generate note ID
        note_id = self.version_manager.generate_note_id(note_path, title)

        try:
            # Compare versions
            diff_lines = self.version_manager.compare_versions(
                note_id, old_version_id, new_version_id)
            version_desc = f"{old_version_id} to {new_version_id or 'latest'}"
            return True, f"Compared versions {version_desc}.", diff_lines
        except FileNotFoundError as e:
            return False, str(e), None
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            return False, f"Error comparing versions: {str(e)}", None

    def restore_note_version(self, title: str, version_id: str,
                             category: Optional[str] = None,
                             output_dir: Optional[str] = None) -> Tuple[bool, str, Optional[Note]]:
        """
        Restore a note to a specific version.

        Args:
            title: The title of the note.
            version_id: The ID of the version to restore.
            category: Optional category to help find the note.
            output_dir: Optional specific directory to look for the note.

        Returns:
            A tuple of (success, message, restored_note)
        """
        if not self.version_control_enabled:
            return False, "Version control is not enabled.", None

        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found.", None

        # Generate note ID
        note_id = self.version_manager.generate_note_id(note_path, title)

        try:
            # Get the version content first to ensure it exists
            content, version_info = self.version_manager.get_version_content(
                note_id, version_id)

            # Restore the version
            success = self.version_manager.restore_version(
                note_id, version_id, note_path)
            if not success:
                return False, f"Failed to restore version {version_id}.", None

            # Read the updated note to return it
            metadata, content = read_note_file(note_path)

            # Create a Note object for the restored version
            restored_note = Note(
                title=metadata.get('title', title),
                content=content,
                created_at=datetime.fromisoformat(metadata.get(
                    'created_at', datetime.now().isoformat())),
                updated_at=datetime.now(),  # Set updated_at to now since we're restoring
                tags=metadata.get('tags', []),
                category=metadata.get('category', None),
                filename=os.path.basename(note_path),
                metadata=metadata
            )

            # Save the restored version as a new version in history
            if self.version_control_enabled:
                full_content = self._get_full_note_content(metadata, content)
                self.version_manager.save_version(
                    note_id,
                    full_content,
                    title,
                    "System",
                    f"Restored from version {version_id}"
                )

            return True, f"Note restored to version {version_id}.", restored_note

        except FileNotFoundError:
            return False, f"Version {version_id} not found.", None
        except Exception as e:
            return False, f"Error restoring version: {str(e)}", None

    def edit_version(self, title: str, version_id: str,
                     category: Optional[str] = None,
                     output_dir: Optional[str] = None,
                     editor: Optional[str] = None,
                     commit_message: Optional[str] = None,
                     author: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Edit a specific version of a note.

        This method:
        1. Gets the content of a specific version
        2. Opens it in an editor
        3. Saves the edits as a new version

        Args:
            title: The title of the note
            version_id: The ID of the version to edit
            category: Optional category to help find the note
            output_dir: Optional specific directory to look for the note
            editor: Optional editor to use for editing
            commit_message: Optional message for the new version
            author: Optional author of the edit

        Returns:
            Tuple of (success, message, new_version_id)
        """
        if not self.version_control_enabled:
            return False, "Version control is not enabled.", None

        # Find the note path
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found.", None

        # Generate note ID
        note_id = self.version_manager.generate_note_id(note_path, title)

        try:
            # Get the version content
            success, message, content = self.get_note_version(
                title=title,
                version_id=version_id,
                category=category,
                output_dir=output_dir
            )

            if not success:
                return False, message, None

            # Create a temporary file for editing
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(content)

            # Open the temp file in an editor
            from app.utils.editor_handler import edit_file
            edit_successful = edit_file(temp_path, custom_editor=editor)

            if not edit_successful:
                # Clean up temp file
                import os
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False, "Failed to edit version content.", None

            # Read the edited content
            with open(temp_path, "r", encoding="utf-8") as f:
                edited_content = f.read()

            # Clean up temp file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)

            # If content hasn't changed, no need to create a new version
            if edited_content == content:
                return True, "No changes were made to the version.", None

            # Save the edited content as a new version
            if not commit_message:
                commit_message = f"Edited version {version_id}"

            new_version_id = self.version_manager.save_version(
                note_id,
                edited_content,
                title,
                author or "Unknown",
                commit_message
            )

            return True, f"Version edited successfully. New version: {new_version_id}", new_version_id

        except Exception as e:
            return False, f"Error editing version: {str(e)}", None

    def purge_note_history(self, title: str, category: Optional[str] = None,
                          output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Delete all version history for a note.
        
        Args:
            title: The title of the note.
            category: Optional category to help find the note.
            output_dir: Optional specific directory to look for the note.
            
        Returns:
            A tuple of (success, message)
        """
        if not self.version_control_enabled:
            return False, "Version control is not enabled."
            
        # Find the note
        note_path = self.find_note_path(title, category, output_dir)
        if not note_path:
            return False, f"Note '{title}' not found."
            
        # Generate note ID
        note_id = self.version_manager.generate_note_id(note_path, title)
        
        # Get version history to check if there are any versions
        versions = self.version_manager.get_version_history(note_id)
        if not versions:
            return True, "No version history found for this note. Nothing to purge."
        
        # Purge the history
        success = self.version_manager.purge_history(note_id)
        
        if success:
            return True, f"Successfully purged version history for '{title}'. {len(versions)} versions deleted."
        else:
            return False, f"Failed to purge version history for '{title}'."

    def _format_dates_for_display(self, metadata: Dict[str, Any]) -> None:
        """Helper method to format ISO dates for human-readable display."""
        if 'created_at' in metadata and isinstance(metadata['created_at'], str):
            try:
                # Try to parse with different ISO formats
                try:
                    created_at = datetime.fromisoformat(metadata['created_at'])
                    metadata['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Keep as is if parsing fails
                    pass
            except Exception:
                # Ignore any errors in date parsing
                pass
                
        if 'updated_at' in metadata and isinstance(metadata['updated_at'], str):
            try:
                try:
                    updated_at = datetime.fromisoformat(metadata['updated_at'])
                    metadata['updated_at'] = updated_at.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Keep as is if parsing fails
                    pass
            except Exception:
                # Ignore any errors in date parsing
                pass

    def create_static_site(self, output_dir: str, category: Optional[str] = None, 
                           source_dir: Optional[str] = None, custom_css: Optional[str] = None,
                           include_metadata: bool = True) -> Tuple[int, int, List[str], Optional[str]]:
        """
        Create a static website from notes.
        
        Args:
            output_dir: Directory to save the static site.
            category: Optional category to filter notes.
            source_dir: Optional specific directory to look for the notes.
            custom_css: Optional custom CSS for styling.
            include_metadata: Whether to include note metadata in the HTMLs.
            
        Returns:
            Tuple of (number of successful exports, total number of notes, list of failed notes, path to index file)
        """
        # This is essentially the same as export_all_notes_to_html but named more intuitively for the user
        return self.export_all_notes_to_html(
            output_dir=output_dir,
            create_index=True,
            category=category,
            source_dir=source_dir,
            custom_css=custom_css,
            include_metadata=include_metadata
        )

    def _get_full_note_content(self, metadata: Dict[str, Any], content: str) -> str:
        """Get the full note content, including frontmatter."""
        return add_frontmatter(content, metadata)
        
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

        # Check various possible locations for the note
        possible_paths = []
        
        # Path in base directory
        possible_paths.append(os.path.join(base_dir, filename))
        
        # Path in specified category
        if category:
            possible_paths.append(os.path.join(base_dir, category, filename))
        
        # Check all categories if none specified
        if not category:
            for dir_entry in os.scandir(base_dir):
                if dir_entry.is_dir() and not dir_entry.name.startswith('.'):
                    possible_paths.append(os.path.join(dir_entry.path, filename))
        
        # Check each possible path
        for path in possible_paths:
            if os.path.isfile(path):
                return path
        
        return None
    
    def get_notes_count(self, 
                   tag: Optional[str] = None,
                   category: Optional[str] = None,
                   output_dir: Optional[str] = None) -> int:
        """
        Get the total number of notes in the system, optionally filtered by tag or category.
        
        Args:
            tag: Optional tag to filter by.
            category: Optional category to filter by.
            output_dir: Optional specific directory to look for the notes.
                        This overrides the notes_dir for this specific count.
        
        Returns:
            The total number of notes matching the criteria.
        """
        # Reuse the existing list_notes method to get filtered notes
        notes = self.list_notes(
            tag=tag,
            category=category,
            output_dir=output_dir
        )
        
        # Return the count of notes
        return len(notes)
    
    def get_most_frequent_tag(self, 
                          category: Optional[str] = None,
                          output_dir: Optional[str] = None) -> Tuple[Optional[str], int, Dict[str, int]]:
        """
        Get the most frequently used tag across all notes.
        
        Args:
            category: Optional category to filter notes by.
            output_dir: Optional specific directory to look for the notes.
                        This overrides the notes_dir for this specific operation.
        
        Returns:
            A tuple containing:
            - The most frequent tag (or None if no tags found)
            - The count of notes with this tag
            - A dictionary of all tags with their counts
        """
        # Get all notes using existing method
        notes = self.list_notes(category=category, output_dir=output_dir)
        
        # If no notes found, return None
        if not notes:
            return None, 0, {}
        
        # Create a counter for all tags
        tag_counter = Counter()
        
        # Count occurrences of each tag
        for note in notes:
            for tag in note.tags:
                tag_counter[tag] += 1
        
        # If no tags found, return None
        if not tag_counter:
            return None, 0, {}
        
        # Get the most common tag
        most_common_tag, count = tag_counter.most_common(1)[0]
        
        # Return the most common tag, its count, and the full counter dict
        return most_common_tag, count, dict(tag_counter)
    
    def get_notes_per_category(self, 
                         tag: Optional[str] = None,
                         output_dir: Optional[str] = None) -> Dict[str, int]:
        """
        Get the count of notes per category, optionally filtered by tag.
        
        Args:
            tag: Optional tag to filter by.
            output_dir: Optional specific directory to look for the notes.
                        This overrides the notes_dir for this specific count.
        
        Returns:
            A dictionary with category names as keys and note counts as values.
            Notes without a category are counted under the key "(uncategorized)".
        """
        # Get all notes with the tag filter if provided
        all_notes = self.list_notes(tag=tag, output_dir=output_dir)
        
        # Initialize results dictionary
        category_counts = {}
        
        # Count notes by category
        for note in all_notes:
            category = note.category if note.category else "(uncategorized)"
            if category in category_counts:
                category_counts[category] += 1
            else:
                category_counts[category] = 1
        
        return category_counts
    
    def get_note_word_count(self, title: str, category: Optional[str] = None,
                       output_dir: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, int]]]:
        """
        Get word count statistics for a note.
        
        Args:
            title: The title of the note.
            category: Optional category of the note.
            output_dir: Optional specific directory to look for the note.
                        This overrides the notes_dir for this specific lookup.
                        
        Returns:
            A tuple of (success, message, statistics)
            - success: True if the note was found, False otherwise
            - message: Success or error message
            - statistics: Dictionary of statistics if success is True, None otherwise
        """
        note = self.get_note(title, category, output_dir)
        
        if not note:
            return False, f"Note '{title}' not found.", None
            
        # Get statistics
        stats = note.get_statistics()
        
        return True, f"Statistics for note '{title}'", stats