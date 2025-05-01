"""
Encryption utilities for MarkNote.

This module provides functions to encrypt and decrypt note content
using strong encryption algorithms.
"""
import os
import base64
import logging
import getpass
from typing import Tuple, Union, Optional, Dict, Any
import json

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SALT_SIZE = 16  # Size of salt in bytes
KEY_LENGTH = 32  # 256 bits
ITERATIONS = 100000  # Number of iterations for PBKDF2
NONCE_SIZE = 12  # Size of nonce for AES-GCM
TAG_SIZE = 16  # Size of authentication tag (part of ciphertext in AESGCM)
MARKER = b'MARKNOTE_ENCRYPTED_V1'  # Marker to identify encrypted content

class EncryptionError(Exception):
    """Exception raised for encryption-related errors."""
    pass

class DecryptionError(Exception):
    """Exception raised for decryption-related errors."""
    pass

class AuthenticationError(DecryptionError):
    """Exception raised when authentication fails during decryption."""
    pass

class PasswordError(DecryptionError):
    """Exception raised when password is incorrect or missing."""
    pass

def derive_key(password: str, salt: bytes, iterations: int = ITERATIONS) -> bytes:
    """
    Derive a cryptographic key from a password using PBKDF2.
    
    Args:
        password: The password from which to derive the key
        salt: Random salt for key derivation
        iterations: Number of iterations for PBKDF2
        
    Returns:
        Derived key as bytes
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode('utf-8'))

def encrypt_content(content: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Encrypt note content with a password.
    
    Args:
        content: The note content to encrypt
        password: Password for encryption
        metadata: Optional metadata to include in encrypted file
    
    Returns:
        Base64-encoded encrypted content
        
    Raises:
        EncryptionError: If encryption fails
    """
    try:
        # Generate a random salt
        salt = os.urandom(SALT_SIZE)
        
        # Derive key from password
        key = derive_key(password, salt)
        
        # Create encryption cipher
        cipher = AESGCM(key)
        
        # Generate a random nonce
        nonce = os.urandom(NONCE_SIZE)
        
        # Prepare the data to encrypt
        data = {
            "content": content,
            "metadata": metadata or {}
        }
        plaintext = json.dumps(data).encode('utf-8')
        
        # Encrypt the data
        ciphertext = cipher.encrypt(nonce, plaintext, MARKER)
        
        # Format the output: MARKER + salt + nonce + ciphertext
        encrypted_data = MARKER + salt + nonce + ciphertext
        
        # Base64 encode for storage
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    except Exception as e:
        logger.error(f"Encryption failed: {str(e)}")
        raise EncryptionError(f"Failed to encrypt content: {str(e)}") from e

def decrypt_content(encrypted_content: str, password: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Decrypt encrypted note content.
    
    Args:
        encrypted_content: The encrypted content as a base64 string
        password: Password for decryption
    
    Returns:
        Tuple of (decrypted content, metadata)
        
    Raises:
        DecryptionError: If decryption fails
        AuthenticationError: If the authentication tag is invalid
        PasswordError: If the provided password is incorrect
    """
    try:
        # Decode from base64
        raw_data = base64.b64decode(encrypted_content)
        
        # Check format marker
        if not raw_data.startswith(MARKER):
            raise DecryptionError("Invalid encrypted data format")
        
        # Extract components
        marker_size = len(MARKER)
        salt = raw_data[marker_size:marker_size + SALT_SIZE]
        nonce = raw_data[marker_size + SALT_SIZE:marker_size + SALT_SIZE + NONCE_SIZE]
        ciphertext = raw_data[marker_size + SALT_SIZE + NONCE_SIZE:]
        
        # Derive key from password
        key = derive_key(password, salt)
        
        # Create decryption cipher
        cipher = AESGCM(key)
        
        try:
            # Decrypt the data
            plaintext = cipher.decrypt(nonce, ciphertext, MARKER)
            
            # Parse the JSON data
            data = json.loads(plaintext.decode('utf-8'))
            
            # Extract content and metadata
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            
            return content, metadata
        
        except InvalidTag:
            raise PasswordError("Invalid password or corrupted data")
    
    except json.JSONDecodeError:
        raise DecryptionError("Corrupted data: Could not parse decrypted content")
    except PasswordError:
        raise  # Re-raise password errors
    except Exception as e:
        logger.error(f"Decryption failed: {str(e)}")
        raise DecryptionError(f"Failed to decrypt content: {str(e)}") from e

def is_encrypted(content: str) -> bool:
    """
    Check if the content is encrypted.
    
    Args:
        content: The content to check
        
    Returns:
        True if the content appears to be encrypted, False otherwise
    """
    try:
        # Try to decode as base64
        decoded = base64.b64decode(content)
        
        # Check for the marker
        return decoded.startswith(MARKER)
    except:
        # If it's not valid base64, it's not encrypted
        return False

def prompt_for_password(prompt_text: str = "Enter password: ", confirm: bool = False) -> str:
    """
    Prompt the user for a password with optional confirmation.
    
    Args:
        prompt_text: Text to display for the password prompt
        confirm: Whether to confirm the password with a second prompt
        
    Returns:
        The entered password
    """
    password = getpass.getpass(prompt_text)
    
    if confirm:
        confirm_password = getpass.getpass("Confirm password: ")
        if password != confirm_password:
            raise ValueError("Passwords do not match")
            
    return password

def change_password(encrypted_content: str, current_password: str, new_password: str) -> str:
    """
    Change the password for encrypted content.
    
    Args:
        encrypted_content: The encrypted content
        current_password: The current password
        new_password: The new password
        
    Returns:
        Newly encrypted content with the new password
        
    Raises:
        PasswordError: If the current password is incorrect
        EncryptionError: If re-encryption fails
    """
    # Decrypt with current password
    content, metadata = decrypt_content(encrypted_content, current_password)
    
    # Re-encrypt with new password
    return encrypt_content(content, new_password, metadata)