"""
File validation and utility functions.
"""
import os
import re
import mimetypes
from pathlib import Path
import logging

logger = logging.getLogger('apps.tools')

# Optional import for python-magic
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


# MIME type mappings for common file types
MIME_TYPE_MAPPINGS = {
    # PDF
    'pdf': ['application/pdf'],
    
    # Microsoft Office
    'docx': [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'application/zip',  # DOCX files are ZIP archives
        'application/x-zip-compressed'
    ],
    'xlsx': [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'application/zip',  # XLSX files are ZIP archives
        'application/x-zip-compressed'
    ],
    'pptx': [
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.ms-powerpoint',
        'application/zip',  # PPTX files are ZIP archives
        'application/x-zip-compressed'
    ],
    'doc': ['application/msword'],
    'xls': ['application/vnd.ms-excel'],
    'ppt': ['application/vnd.ms-powerpoint'],
    
    # Images
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'png': ['image/png'],
    'gif': ['image/gif'],
    'bmp': ['image/bmp', 'image/x-ms-bmp'],
    'webp': ['image/webp'],
    'tiff': ['image/tiff'],
    'tif': ['image/tiff'],
    
    # Video
    'mp4': ['video/mp4'],
    'mov': ['video/quicktime'],
    'avi': ['video/x-msvideo'],
    'mkv': ['video/x-matroska'],
    'webm': ['video/webm'],
    
    # Text
    'txt': ['text/plain'],
    'csv': ['text/csv', 'application/csv'],
    'json': ['application/json'],
    'xml': ['application/xml', 'text/xml'],
}


def validate_file_size(file, max_size_mb):
    """
    Validate that file size is within the allowed limit.
    
    Args:
        file: File object or file path
        max_size_mb: Maximum allowed size in megabytes
        
    Returns:
        bool: True if valid
        
    Raises:
        FileValidationError: If file exceeds size limit
    """
    if hasattr(file, 'size'):
        file_size = file.size
    else:
        file_size = os.path.getsize(file)
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        raise FileValidationError(
            f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds "
            f"maximum allowed size ({max_size_mb} MB)"
        )
    
    return True


def validate_mime_type(file, allowed_types):
    """
    Validate file MIME type against allowed types.
    Uses multiple methods for robust validation:
    1. python-magic (if available) - reads file content
    2. Django's content_type attribute
    3. Extension-based fallback
    
    Args:
        file: File object or file path
        allowed_types: List of allowed MIME types (e.g., ['application/pdf'])
        
    Returns:
        bool: True if valid
        
    Raises:
        FileValidationError: If MIME type is not allowed
    """
    mime = None
    detected_mime = None
    
    # Method 1: Try to get MIME type using python-magic if available (most reliable)
    if HAS_MAGIC:
        try:
            if hasattr(file, 'read'):
                # File object - read first 2KB for magic detection
                file.seek(0)
                file_content = file.read(2048)
                detected_mime = magic.from_buffer(file_content, mime=True)
                file.seek(0)
                logger.debug(f"Magic detected MIME type: {detected_mime}")
                
                # Special handling for .doc files that might be detected as text/plain
                if detected_mime == 'text/plain' and hasattr(file, 'name'):
                    filename = file.name.lower()
                    if filename.endswith('.doc'):
                        detected_mime = 'application/msword'
                        logger.info(f"Corrected MIME type for .doc file: {detected_mime}")
            else:
                # File path
                detected_mime = magic.from_file(file, mime=True)
                logger.debug(f"Magic detected MIME type from file: {detected_mime}")
                
                # Special handling for .doc files
                if detected_mime == 'text/plain' and str(file).lower().endswith('.doc'):
                    detected_mime = 'application/msword'
                    logger.info(f"Corrected MIME type for .doc file: {detected_mime}")
        except Exception as e:
            logger.warning(f"Failed to detect MIME type with magic: {str(e)}")
    
    # Method 2: Check Django's content_type attribute (from upload)
    if hasattr(file, 'content_type'):
        mime = file.content_type
        logger.debug(f"Django content_type: {mime}")
    
    # Method 3: Fallback to extension-based validation
    if not mime and not detected_mime:
        if hasattr(file, 'name'):
            filename = file.name
        else:
            filename = str(file)
        
        mime, _ = mimetypes.guess_type(filename)
        logger.debug(f"Extension-based MIME type: {mime}")
    
    # Use detected_mime if available, otherwise use mime
    final_mime = detected_mime or mime
    
    if not final_mime:
        raise FileValidationError(
            "Could not determine file type. Please ensure the file is valid."
        )
    
    # Check if MIME type is in allowed list
    if final_mime not in allowed_types:
        # Log security warning
        logger.warning(
            f"File upload rejected - MIME type mismatch. "
            f"Detected: {final_mime}, Allowed: {', '.join(allowed_types)}"
        )
        raise FileValidationError(
            f"File type '{final_mime}' is not allowed. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
    
    logger.info(f"File MIME type validated successfully: {final_mime}")
    return True


def validate_file_extension(filename, allowed_extensions):
    """
    Validate file extension against allowed extensions.
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (e.g., ['pdf', 'docx'])
        
    Returns:
        bool: True if valid
        
    Raises:
        FileValidationError: If extension is not allowed
    """
    file_ext = get_file_extension(filename)
    
    if not file_ext:
        raise FileValidationError("File has no extension")
    
    if file_ext not in allowed_extensions:
        raise FileValidationError(
            f"File extension '.{file_ext}' is not allowed. "
            f"Allowed extensions: {', '.join('.' + ext for ext in allowed_extensions)}"
        )
    
    return True


def get_allowed_mime_types(extensions):
    """
    Get list of allowed MIME types for given file extensions.
    
    Args:
        extensions: List of file extensions (e.g., ['pdf', 'docx'])
        
    Returns:
        list: List of allowed MIME types
    """
    mime_types = []
    
    for ext in extensions:
        ext_lower = ext.lower()
        if ext_lower in MIME_TYPE_MAPPINGS:
            mime_types.extend(MIME_TYPE_MAPPINGS[ext_lower])
        else:
            # Fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(f'file.{ext_lower}')
            if mime_type:
                mime_types.append(mime_type)
    
    return list(set(mime_types))  # Remove duplicates


def validate_file_comprehensive(file, max_size_mb, allowed_extensions):
    """
    Comprehensive file validation combining size, extension, and MIME type checks.
    
    Args:
        file: Uploaded file object
        max_size_mb: Maximum file size in MB
        allowed_extensions: List of allowed file extensions
        
    Returns:
        dict: Validation result with file info
        
    Raises:
        FileValidationError: If any validation fails
    """
    # Validate file size
    validate_file_size(file, max_size_mb)
    
    # Validate file extension
    validate_file_extension(file.name, allowed_extensions)
    
    # Get allowed MIME types for the extensions
    allowed_mime_types = get_allowed_mime_types(allowed_extensions)
    
    # Validate MIME type
    validate_mime_type(file, allowed_mime_types)
    
    # Return file info
    return {
        'name': file.name,
        'size': file.size,
        'size_mb': round(file.size / (1024 * 1024), 2),
        'extension': get_file_extension(file.name),
        'content_type': getattr(file, 'content_type', None),
        'validated': True
    }


def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal and other security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Get just the filename without path
    filename = os.path.basename(filename)
    
    # Remove any non-alphanumeric characters except dots, hyphens, and underscores
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove multiple consecutive dots (prevent ../ attacks)
    filename = re.sub(r'\.+', '.', filename)
    
    # Limit filename length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    filename = name + ext
    
    # Ensure filename is not empty
    if not filename or filename == '.':
        filename = 'file'
    
    return filename


def get_file_info(file_path):
    """
    Get detailed information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        dict: File information including size, type, extension
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = path.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(path))
    
    return {
        'name': path.name,
        'size': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2),
        'extension': path.suffix.lower(),
        'mime_type': mime_type,
        'path': str(path.absolute()),
    }


def get_file_extension(filename):
    """
    Get file extension from filename.
    
    Args:
        filename: Filename or path
        
    Returns:
        str: File extension without dot (e.g., 'pdf', 'docx')
    """
    return Path(filename).suffix.lower().lstrip('.')
