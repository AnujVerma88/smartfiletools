"""
Security utilities for file upload and processing.
Implements security measures to prevent malicious file uploads and attacks.
"""
import os
import re
import logging
from pathlib import Path

logger = logging.getLogger('apps.tools')


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


def sanitize_filename(filename, max_length=100):
    """
    Sanitize filename to prevent directory traversal and other security issues.
    
    Security measures:
    - Removes path components (prevents directory traversal)
    - Removes special characters that could be exploited
    - Prevents null byte injection
    - Limits filename length
    - Prevents hidden files (starting with .)
    - Removes multiple consecutive dots
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length (default: 100)
        
    Returns:
        str: Sanitized filename
        
    Raises:
        SecurityError: If filename cannot be sanitized safely
    """
    if not filename:
        raise SecurityError("Filename cannot be empty")
    
    # Get just the filename without any path components
    filename = os.path.basename(filename)
    
    # Check for null bytes (security vulnerability)
    if '\x00' in filename:
        logger.warning(f"Null byte detected in filename: {repr(filename)}")
        raise SecurityError("Invalid filename: contains null bytes")
    
    # Remove any non-alphanumeric characters except dots, hyphens, and underscores
    # This prevents special characters that could be exploited
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove multiple consecutive dots (prevents ../ attacks)
    filename = re.sub(r'\.{2,}', '.', filename)
    
    # Remove leading dots (prevents hidden files)
    filename = filename.lstrip('.')
    
    # Split into name and extension
    parts = filename.rsplit('.', 1)
    if len(parts) == 2:
        name, ext = parts
    else:
        name = filename
        ext = ''
    
    # Limit name length
    if len(name) > max_length:
        name = name[:max_length]
    
    # Reconstruct filename
    if ext:
        filename = f"{name}.{ext}"
    else:
        filename = name
    
    # Final validation
    if not filename or filename == '.':
        raise SecurityError("Filename is invalid after sanitization")
    
    # Check for reserved names (Windows)
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    name_without_ext = filename.rsplit('.', 1)[0].upper()
    if name_without_ext in reserved_names:
        filename = f"file_{filename}"
        logger.warning(f"Reserved filename detected, prefixed with 'file_': {filename}")
    
    logger.debug(f"Filename sanitized: {filename}")
    return filename


def validate_file_path(file_path, allowed_base_paths):
    """
    Validate that a file path is within allowed directories.
    Prevents directory traversal attacks.
    
    Args:
        file_path: Path to validate
        allowed_base_paths: List of allowed base directory paths
        
    Returns:
        bool: True if valid
        
    Raises:
        SecurityError: If path is outside allowed directories
    """
    # Resolve to absolute path
    abs_path = Path(file_path).resolve()
    
    # Check if path is within any allowed base path
    for base_path in allowed_base_paths:
        abs_base = Path(base_path).resolve()
        try:
            abs_path.relative_to(abs_base)
            return True
        except ValueError:
            continue
    
    logger.error(
        f"Path traversal attempt detected: {file_path} "
        f"not in allowed paths: {allowed_base_paths}"
    )
    raise SecurityError(
        "Invalid file path: outside allowed directories"
    )


def check_file_content_safety(file_path, max_scan_bytes=10240):
    """
    Perform basic content safety checks on uploaded files.
    Checks for potentially malicious content patterns.
    
    Args:
        file_path: Path to file to check
        max_scan_bytes: Maximum bytes to scan (default: 10KB)
        
    Returns:
        dict: Safety check results
        
    Raises:
        SecurityError: If dangerous content is detected
    """
    dangerous_patterns = [
        # Script tags
        b'<script',
        b'</script>',
        # PHP code
        b'<?php',
        b'<?=',
        # Executable signatures
        b'MZ\x90\x00',  # Windows PE
        b'\x7fELF',     # Linux ELF
        # Shell commands
        b'#!/bin/bash',
        b'#!/bin/sh',
    ]
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read(max_scan_bytes)
            
            for pattern in dangerous_patterns:
                if pattern in content:
                    logger.warning(
                        f"Dangerous content pattern detected in file: {file_path}"
                    )
                    raise SecurityError(
                        "File contains potentially malicious content"
                    )
        
        return {
            'safe': True,
            'scanned_bytes': len(content),
            'message': 'No dangerous patterns detected'
        }
        
    except SecurityError:
        raise
    except Exception as e:
        logger.error(f"Error scanning file content: {str(e)}")
        return {
            'safe': False,
            'error': str(e),
            'message': 'Could not scan file content'
        }


def generate_safe_filename(original_filename, prefix='file'):
    """
    Generate a safe, unique filename based on original filename.
    Useful for storing uploaded files with guaranteed safe names.
    
    Args:
        original_filename: Original uploaded filename
        prefix: Prefix for generated filename (default: 'file')
        
    Returns:
        str: Safe, unique filename
    """
    import uuid
    from datetime import datetime
    
    # Sanitize the original filename
    try:
        safe_name = sanitize_filename(original_filename)
        # Get extension
        ext = Path(safe_name).suffix
    except SecurityError:
        # If sanitization fails, use generic name
        ext = '.bin'
    
    # Generate unique identifier
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    
    # Construct safe filename
    safe_filename = f"{prefix}_{timestamp}_{unique_id}{ext}"
    
    return safe_filename


def validate_upload_directory(directory_path):
    """
    Validate that upload directory exists and has proper permissions.
    
    Args:
        directory_path: Path to upload directory
        
    Returns:
        bool: True if valid
        
    Raises:
        SecurityError: If directory is invalid or has wrong permissions
    """
    dir_path = Path(directory_path)
    
    # Check if directory exists
    if not dir_path.exists():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created upload directory: {directory_path}")
        except Exception as e:
            raise SecurityError(
                f"Cannot create upload directory: {str(e)}"
            )
    
    # Check if it's actually a directory
    if not dir_path.is_dir():
        raise SecurityError(
            f"Upload path is not a directory: {directory_path}"
        )
    
    # Check write permissions
    if not os.access(directory_path, os.W_OK):
        raise SecurityError(
            f"No write permission for upload directory: {directory_path}"
        )
    
    return True


def get_safe_file_path(base_dir, filename):
    """
    Get a safe file path within base directory.
    Ensures no directory traversal and filename is sanitized.
    
    Args:
        base_dir: Base directory path
        filename: Filename to use
        
    Returns:
        str: Safe absolute file path
        
    Raises:
        SecurityError: If path cannot be made safe
    """
    # Sanitize filename
    safe_filename = sanitize_filename(filename)
    
    # Construct path
    file_path = Path(base_dir) / safe_filename
    
    # Validate path is within base directory
    validate_file_path(file_path, [base_dir])
    
    return str(file_path)


def log_security_event(event_type, details, severity='warning'):
    """
    Log security-related events for monitoring and auditing.
    
    Args:
        event_type: Type of security event (e.g., 'file_upload_rejected')
        details: Dictionary with event details
        severity: Log severity ('info', 'warning', 'error', 'critical')
    """
    log_message = f"SECURITY EVENT [{event_type}]: {details}"
    
    if severity == 'critical':
        logger.critical(log_message)
    elif severity == 'error':
        logger.error(log_message)
    elif severity == 'warning':
        logger.warning(log_message)
    else:
        logger.info(log_message)
