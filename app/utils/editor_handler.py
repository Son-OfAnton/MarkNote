"""
Editor handling utilities for MarkNote.
"""
import os
import sys
import tempfile
import subprocess
import shutil
from typing import Optional, Tuple, List
from datetime import datetime

def get_editor() -> str:
    """
    Get the user's preferred editor from environment variables.
    
    Returns:
        The path to the editor executable.
    """
    # Check environment variables in order of precedence
    for env_var in ['VISUAL', 'EDITOR']:
        editor = os.environ.get(env_var)
        if editor:
            return editor
    
    # Default fallbacks based on platform
    if sys.platform.startswith('win'):
        # Windows fallbacks
        return 'notepad.exe'
    else:
        # Unix-like fallbacks
        for editor in ['nano', 'vim', 'vi', 'emacs']:
            try:
                if subprocess.run(['which', editor], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE).returncode == 0:
                    return editor
            except Exception:
                continue
    
    # Final fallback
    return 'nano'  # Most Unix-like systems have nano

def is_valid_editor(editor: str) -> bool:
    """
    Check if the specified editor is valid and available.
    
    Args:
        editor: Path or name of the editor.
        
    Returns:
        True if the editor is valid, False otherwise.
    """
    # If editor contains a path separator, check if it exists as a file
    if os.path.sep in editor:
        return os.path.isfile(editor) and os.access(editor, os.X_OK)
        
    # Otherwise check if it's in PATH
    try:
        if sys.platform.startswith('win'):
            # On Windows, use where command
            result = subprocess.run(['where', editor], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
        else:
            # On Unix-like systems, use which command
            result = subprocess.run(['which', editor], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
                                   
        return result.returncode == 0
    except Exception:
        return False

def get_available_editors() -> List[str]:
    """
    Get a list of common editors available on the system.
    
    Returns:
        List of editor names that are available.
    """
    common_editors = [
        'vim', 'nano', 'emacs', 'vi', 'code', 'atom', 'sublime', 
        'notepad++', 'notepad', 'gedit', 'kate'
    ]
    
    available = []
    for editor in common_editors:
        if is_valid_editor(editor):
            available.append(editor)
            
    return available

def edit_file(file_path: str, custom_editor: Optional[str] = None) -> Tuple[bool, str]:
    """
    Open a file in an editor.
    
    Args:
        file_path: Path to the file to edit.
        custom_editor: Optional specific editor to use instead of the default.
        
    Returns:
        A tuple of (success, error_message).
    """
    # Determine which editor to use
    editor = custom_editor if custom_editor else get_editor()
    
    # Validate the editor
    if custom_editor and not is_valid_editor(editor):
        return False, f"Specified editor '{editor}' not found or not executable"
    
    try:
        # Ensure file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        # Launch editor and wait for it to close
        cmd = [editor, file_path]
        
        # Special case for some GUI editors that don't wait
        gui_editors = {'code', 'atom', 'sublime', 'subl', 'vscode', 'notepad++', 'notepad', 'gedit', 'kate'}
        editor_base = os.path.basename(editor).lower().split()[0]
        
        if editor_base in gui_editors:
            # For GUI editors, we'll launch and wait a bit
            process = subprocess.Popen(cmd)
            print(f"Launched {editor_base}. Please close the editor when finished to continue.")
            process.wait()
        else:
            # For terminal editors, just run normally
            result = subprocess.run(cmd, check=True)
            if result.returncode != 0:
                return False, f"Editor exited with code: {result.returncode}"
        
        return True, ""
    except FileNotFoundError:
        return False, f"Editor not found: {editor}"
    except subprocess.CalledProcessError as e:
        return False, f"Editor exited with an error: {e}"
    except Exception as e:
        return False, f"Error opening editor: {str(e)}"

def edit_content(content: str, custom_editor: Optional[str] = None) -> Tuple[bool, str, str]:
    """
    Edit content in an editor using a temporary file.
    
    Args:
        content: The initial content to edit.
        custom_editor: Optional specific editor to use instead of the default.
        
    Returns:
        A tuple of (success, edited_content, error_message).
    """
    # Determine which editor to use
    editor = custom_editor if custom_editor else get_editor()
    
    # Validate the editor
    if custom_editor and not is_valid_editor(editor):
        return False, content, f"Specified editor '{editor}' not found or not executable"
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w+', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(content)
        
        try:
            # Edit the file
            success, error = edit_file(tmp_path, custom_editor)
            
            if success:
                # Read the edited content
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    edited_content = f.read()
                return True, edited_content, ""
            else:
                return False, content, error
                
        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    except Exception as e:
        return False, content, f"Error opening editor: {str(e)}"
    

class EditorHandler:
    """
    Handler for editing files with various editors.
    """
    def __init__(self, default_editor: Optional[str] = None):
        self.default_editor = default_editor
        
    def edit_file(self, file_path: str, custom_editor: Optional[str] = None) -> Tuple[bool, str]:
        """
        Open a file in an editor.
        
        Args:
            file_path: Path to the file to edit.
            custom_editor: Optional specific editor to use instead of the default.
            
        Returns:
            A tuple of (success, error_message).
        """
        # Use the function from the module
        return edit_file(file_path, custom_editor or self.default_editor)