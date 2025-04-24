"""
Editor handling utilities for MarkNote.
"""
import os
import sys
import tempfile
import subprocess
from typing import Optional, Tuple
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

def edit_file(file_path: str) -> Tuple[bool, str]:
    """
    Open a file in the user's preferred editor.
    
    Args:
        file_path: Path to the file to edit.
        
    Returns:
        A tuple of (success, error_message).
    """
    editor = get_editor()
    
    try:
        # Ensure file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        # Launch editor and wait for it to close
        result = subprocess.run([editor, file_path], check=True)
        return result.returncode == 0, ""
    except FileNotFoundError:
        return False, f"Editor not found: {editor}"
    except subprocess.CalledProcessError as e:
        return False, f"Editor exited with an error: {e}"
    except Exception as e:
        return False, f"Error opening editor: {str(e)}"

def edit_content(content: str) -> Tuple[bool, str, str]:
    """
    Edit content in the user's preferred editor using a temporary file.
    
    Args:
        content: The initial content to edit.
        
    Returns:
        A tuple of (success, edited_content, error_message).
    """
    editor = get_editor()
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w+', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(content)
        
        try:
            # Launch editor and wait for it to close
            result = subprocess.run([editor, tmp_path], check=True)
            
            if result.returncode == 0:
                # Read the edited content
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    edited_content = f.read()
                return True, edited_content, ""
            else:
                return False, content, f"Editor exited with code: {result.returncode}"
                
        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    except FileNotFoundError:
        return False, content, f"Editor not found: {editor}"
    except subprocess.CalledProcessError as e:
        return False, content, f"Editor exited with an error: {e}"
    except Exception as e:
        return False, content, f"Error opening editor: {str(e)}"