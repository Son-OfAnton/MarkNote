import os
import time
from datetime import datetime, timedelta
import logging
from typing import Optional, List, Dict, Any

from app.core.note_manager import NoteManager

class DailyNoteService:
    """
    Service for automatically generating daily notes.
    """
    
    def __init__(self, output_dir: Optional[str] = None, 
                 template: str = "daily",
                 category: str = "daily",
                 tags: List[str] = None,
                 enabled: bool = True):
        """
        Initialize the daily note service.
        
        Args:
            output_dir: Directory where to save the daily notes.
            template: Template to use for daily notes.
            category: Category for daily notes.
            tags: Default tags for daily notes.
            enabled: Whether the service is enabled.
        """
        self.note_manager = NoteManager()
        self.output_dir = output_dir
        self.template = template
        self.category = category
        self.tags = tags if tags is not None else ["daily"]
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)
    
    def create_today_note(self) -> bool:
        """
        Create a daily note for today if it doesn't exist.
        
        Returns:
            True if a new note was created, False otherwise.
        """
        if not self.enabled:
            self.logger.info("Daily note service is disabled")
            return False
            
        today = datetime.now()
        
        # Check if today's note already exists
        title = today.strftime("Daily Note: %Y-%m-%d")
        existing_note = self.note_manager.get_note(title, self.category, self.output_dir)
        
        if existing_note:
            self.logger.info(f"Daily note for {today.strftime('%Y-%m-%d')} already exists")
            return False
            
        # Create a new daily note
        try:
            success, message, note = self.note_manager.create_daily_note(
                date=today,
                template_name=self.template,
                tags=self.tags,
                category=self.category,
                output_dir=self.output_dir,
                force=False
            )
            
            if success:
                self.logger.info(f"Created daily note for {today.strftime('%Y-%m-%d')}")
                return True
            else:
                self.logger.warning(f"Failed to create daily note: {message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating daily note: {str(e)}")
            return False
    
    def run_daemon(self, check_interval_seconds: int = 3600) -> None:
        """
        Run as a daemon process, creating daily notes as needed.
        
        Args:
            check_interval_seconds: How often to check if a new daily note needs to be created.
        """
        self.logger.info("Starting daily note daemon")
        
        last_date = datetime.now().date()
        
        while True:
            # Check if it's a new day
            current_date = datetime.now().date()
            
            if current_date > last_date:
                # It's a new day, create a new daily note
                self.create_today_note()
                last_date = current_date
                
            # Sleep for the specified interval
            time.sleep(check_interval_seconds)


def get_configured_daily_note_service():
    """
    Get a DailyNoteService configured from the user's settings.
    
    Returns:
        A configured DailyNoteService instance.
    """
    config = get_daily_note_config()
    
    return DailyNoteService(
        output_dir=None,  # Use default
        template=config.get("template", "daily"),
        category=config.get("category", "daily"),
        tags=config.get("tags", ["daily"]),
        enabled=config.get("enabled", True)
    )

def run_auto_daily_note_service():
    """
    Run the daily note service if auto-create is enabled in the config.
    This can be called at application startup.
    """
    config = get_daily_note_config()
    
    if config.get("auto_create", False) and config.get("enabled", True):
        service = get_configured_daily_note_service()
        service.create_today_note()
