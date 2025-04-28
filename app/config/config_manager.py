"""
Configuration management for MarkNote.
"""
import os
import yaml
from typing import Dict, Any, Optional, List

class ConfigManager:
    """
    Manages configuration settings for MarkNote.
    """
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_default_config()
        
        # If a config file is specified, load it
        if config_file:
            self.config_file = config_file
        else:
            # Use default config location
            home_dir = os.path.expanduser("~")
            self.config_file = os.path.join(home_dir, ".marknote", "config.yaml")
        
        # Load config from file if it exists
        if os.path.exists(self.config_file):
            self._load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """
        Load the default configuration settings.
        
        Returns:
            A dictionary containing default configuration.
        """
        return {
            "notes_dir": os.path.join(os.path.expanduser("~"), "marknote"),
            "default_template": "default",
            "daily_notes": {
                "enabled": True,
                "template": "daily",
                "category": "daily",
                "default_tags": ["daily"],
                "title_format": "Daily Note: {date} ({day})",
                "auto_open": True
            },
            "editor": None,  # Use system default
            "default_values": {
                "tags": [],
                "category": None
            }
        }
    
    def _load_config(self) -> None:
        """
        Load configuration from the config file.
        """
        try:
            with open(self.config_file, 'r') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # Merge with defaults, preserving user settings
                    self._merge_config(self.config, user_config)
        except Exception as e:
            print(f"Warning: Could not load config file: {str(e)}")
    
    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]) -> None:
        """
        Merge user configuration with default configuration.
        
        Args:
            default: The default configuration dictionary.
            user: The user configuration dictionary.
        """
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def save_config(self) -> bool:
        """
        Save the current configuration to the config file.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Ensure directory exists
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Save config
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False
    
    def get_config(self, section: Optional[str] = None) -> Any:
        """
        Get configuration settings.
        
        Args:
            section: Optional section name to get. If None, returns the entire config.
            
        Returns:
            The requested configuration section or the entire config.
        """
        if section:
            return self.config.get(section, {})
        return self.config
    
    def set_config(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            section: The section of the config to modify.
            key: The key to set.
            value: The value to set.
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def get_daily_note_config(self) -> Dict[str, Any]:
        """
        Get the configuration for daily notes.
        
        Returns:
            A dictionary containing daily note configuration.
        """
        daily_notes_config = self.config.get("daily_notes", {})
        if not daily_notes_config:
            # If daily_notes section is missing completely, use defaults
            daily_notes_config = self._load_default_config().get("daily_notes", {})
            self.config["daily_notes"] = daily_notes_config
        
        # Ensure all required keys are present
        defaults = self._load_default_config().get("daily_notes", {})
        for key, value in defaults.items():
            if key not in daily_notes_config:
                daily_notes_config[key] = value
        
        return daily_notes_config

# Create a global instance for easy access
_config_manager = None

def get_config_manager() -> ConfigManager:
    """
    Get the global ConfigManager instance.
    
    Returns:
        The ConfigManager instance.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_daily_note_config() -> Dict[str, Any]:
    """
    Get the configuration for daily notes.
    
    Returns:
        A dictionary containing daily note configuration.
    """
    config_manager = get_config_manager()
    return config_manager.get_daily_note_config()