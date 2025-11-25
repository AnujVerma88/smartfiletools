"""
Base converter class for all file conversion operations.
"""
import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from .file_utils import (
    validate_file_size,
    validate_mime_type,
    sanitize_filename,
    get_file_info,
    FileValidationError,
)

logger = logging.getLogger('apps.tools')


class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass


class BaseConverter(ABC):
    """
    Abstract base class for all file converters.
    Provides common validation and utility methods.
    """
    
    # Subclasses should override these
    ALLOWED_INPUT_TYPES = []  # List of allowed MIME types
    ALLOWED_INPUT_EXTENSIONS = []  # List of allowed file extensions
    MAX_FILE_SIZE_MB = 50  # Default max file size
    OUTPUT_EXTENSION = ''  # Output file extension
    
    def __init__(self):
        """Initialize the converter."""
        self.logger = logger
    
    def validate_file(self, file_path, max_size_mb=None):
        """
        Validate input file before conversion.
        
        Args:
            file_path: Path to the file to validate
            max_size_mb: Maximum file size in MB (uses class default if None)
            
        Returns:
            bool: True if validation passes
            
        Raises:
            FileValidationError: If validation fails
        """
        if not os.path.exists(file_path):
            raise FileValidationError(f"File not found: {file_path}")
        
        # Validate file size
        max_size = max_size_mb or self.MAX_FILE_SIZE_MB
        validate_file_size(file_path, max_size)
        
        # Validate MIME type if specified
        if self.ALLOWED_INPUT_TYPES:
            validate_mime_type(file_path, self.ALLOWED_INPUT_TYPES)
        
        # Validate file extension
        if self.ALLOWED_INPUT_EXTENSIONS:
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            if file_ext not in self.ALLOWED_INPUT_EXTENSIONS:
                raise FileValidationError(
                    f"File extension '.{file_ext}' is not allowed. "
                    f"Allowed extensions: {', '.join(self.ALLOWED_INPUT_EXTENSIONS)}"
                )
        
        self.logger.info(f"File validation passed: {file_path}")
        return True
    
    @abstractmethod
    def convert(self, input_path, output_path):
        """
        Perform the actual file conversion.
        Must be implemented by subclasses.
        
        Args:
            input_path: Path to input file
            output_path: Path where output file should be saved
            
        Returns:
            dict: Conversion result with status, output_path, and metadata
            
        Raises:
            ConversionError: If conversion fails
        """
        pass
    
    def get_file_info(self, file_path):
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            dict: File information
        """
        return get_file_info(file_path)
    
    def prepare_output_path(self, input_path, output_dir, output_extension=None):
        """
        Prepare output file path based on input file.
        
        Args:
            input_path: Path to input file
            output_dir: Directory where output should be saved
            output_extension: Output file extension (uses class default if None)
            
        Returns:
            str: Full path to output file
        """
        input_file = Path(input_path)
        output_ext = output_extension or self.OUTPUT_EXTENSION
        
        # Sanitize filename
        safe_name = sanitize_filename(input_file.stem)
        output_filename = f"{safe_name}.{output_ext}"
        
        # Ensure output directory exists
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / output_filename
        
        # Handle duplicate filenames
        counter = 1
        while output_path.exists():
            output_filename = f"{safe_name}_{counter}.{output_ext}"
            output_path = output_dir / output_filename
            counter += 1
        
        return str(output_path)
    
    def cleanup_temp_files(self, *file_paths):
        """
        Clean up temporary files.
        
        Args:
            *file_paths: Variable number of file paths to delete
        """
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                self.logger.error(f"Error cleaning up {file_path}: {str(e)}")
    
    def log_conversion_start(self, input_path, output_path):
        """Log conversion start."""
        self.logger.info(
            f"Starting conversion: {input_path} -> {output_path} "
            f"(Converter: {self.__class__.__name__})"
        )
    
    def log_conversion_success(self, input_path, output_path, duration):
        """Log successful conversion."""
        self.logger.info(
            f"Conversion successful: {input_path} -> {output_path} "
            f"(Duration: {duration:.2f}s)"
        )
    
    def log_conversion_error(self, input_path, error):
        """Log conversion error."""
        self.logger.error(
            f"Conversion failed: {input_path} "
            f"(Error: {str(error)})"
        )
