"""
Service for managing daily notes.
"""
import os
from datetime import datetime, date as dt
from typing import Dict, Any, Optional, Tuple, List

from app.core.note_manager import NoteManager
from app.config.config_manager import get_daily_note_config
from app.utils.editor_handler import edit_file


class DailyNoteService:
    """
    Service for managing daily notes.
    """

    def __init__(self):
        self.note_manager = NoteManager()
        self.config = get_daily_note_config()

    def get_or_create_todays_note(self,
                                  category: Optional[str] = None,
                                  output_dir: Optional[str] = None,
                                  editor: Optional[str] = None,
                                  auto_open: Optional[bool] = None) -> Tuple[bool, str, Any]:
        """
        Get today's daily note if it exists, or create it if it doesn't.

        Args:
            category: Optional category override.
            output_dir: Optional output directory override.
            editor: Optional editor to use.
            auto_open: Whether to automatically open the note.

        Returns:
            A tuple containing (exists, message, note) where exists is True if the note
            already existed, message is a descriptive string, and note is the Note object.
        """
        # Use config values if not overridden
        if category is None:
            category = self.config.get("category", "daily")

        # Check if today's note exists
        exists, message, note = self.note_manager.get_todays_daily_note(
            category, output_dir)

        # Determine if we should open the note
        should_open = auto_open if auto_open is not None else self.config.get(
            "auto_open", True)

        if exists and should_open:
            # Open the existing note if auto_open is enabled
            note_path = note.metadata.get('path', '')
            if note_path and os.path.exists(note_path):
                edit_file(note_path, custom_editor=editor)
        elif not exists and should_open and note:
            # Open the newly created note if auto_open is enabled
            note_path = note.metadata.get('path', '')
            if note_path and os.path.exists(note_path):
                edit_file(note_path, custom_editor=editor)

        return exists, message, note

    def create_note_for_date(self,
                             date_str: Optional[str] = None,
                             tags: Optional[List[str]] = None,
                             category: Optional[str] = None,
                             template_name: Optional[str] = None,
                             output_dir: Optional[str] = None,
                             force: bool = False,
                             editor: Optional[str] = None,
                             auto_open: Optional[bool] = None) -> Tuple[bool, str, Any]:
        """
        Create a daily note for a specific date.

        Args:
            date_str: Date string in format YYYY-MM-DD.
            tags: Optional tags list.
            category: Optional category override.
            template_name: Optional template override.
            output_dir: Optional output directory override.
            force: Whether to force creation even if a note already exists.
            editor: Optional editor to use.
            auto_open: Whether to automatically open the note.

        Returns:
            A tuple containing (success, message, note) where success is a boolean,
            message is a descriptive string, and note is the Note object.
        """
        # Use config values if not overridden
        if category is None:
            category = self.config.get("category", "daily")

        if template_name is None:
            template_name = self.config.get("template", "daily")

        if tags is None:
            tags = self.config.get("default_tags", ["daily"])

        # Determine if we should open the note
        should_open = auto_open if auto_open is not None else self.config.get(
            "auto_open", True)

        # If date is not provided, use today
        if not date_str:
            date_str = dt.today().strftime("%Y-%m-%d")

        # Parse the date
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return False, f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD", None

        # Check if a note already exists for this date
        existing_note = None
        if not force:
            existing_note = self.note_manager.find_daily_note(
                parsed_date, category, output_dir)

        if existing_note:
            # If a note already exists and force is False, return it
            if should_open:
                note_path = existing_note.metadata.get('path', '')
                if note_path and os.path.exists(note_path):
                    edit_file(note_path, custom_editor=editor)

            return True, f"Daily note for {date_str} already exists.", existing_note

        # Create a new note
        success, message, note = self.note_manager.create_daily_note(
            date_str=date_str,
            tags=tags,
            category=category,
            template_name=template_name,
            output_dir=output_dir
        )

        # Open the note if auto_open is enabled
        if success and should_open and note:
            note_path = note.metadata.get('path', '')
            if note_path and os.path.exists(note_path):
                edit_file(note_path, custom_editor=editor)

        return success, message, note


# Create a global instance for easy access
_daily_note_service = None


def get_daily_note_service() -> DailyNoteService:
    """
    Get the global DailyNoteService instance.

    Returns:
        The DailyNoteService instance.
    """
    global _daily_note_service
    if _daily_note_service is None:
        _daily_note_service = DailyNoteService()
    return _daily_note_service
