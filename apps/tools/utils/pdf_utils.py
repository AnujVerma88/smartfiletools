"""
PDF validation and inspection utilities.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger('apps.tools')

# Try to import PyPDF2
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    logger.warning("PyPDF2 not available. PDF validation features will be limited.")


class PDFValidationError(Exception):
    """Custom exception for PDF validation errors."""
    pass


def is_valid_pdf(file_path):
    """
    Verify that a file is a valid PDF that can be opened.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        bool: True if file is a valid PDF
        
    Raises:
        PDFValidationError: If file is not a valid PDF
    """
    if not os.path.exists(file_path):
        raise PDFValidationError(f"PDF file not found: {file_path}")
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise PDFValidationError(f"PDF file is empty: {file_path}")
    
    # Check PDF header
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF'):
                raise PDFValidationError(
                    f"File does not have a valid PDF header: {file_path}"
                )
    except Exception as e:
        raise PDFValidationError(f"Could not read PDF file: {str(e)}")
    
    # Try to open with PyPDF2 if available
    if HAS_PYPDF2:
        try:
            reader = PdfReader(file_path)
            # Try to access pages to verify PDF is readable
            _ = len(reader.pages)
            logger.debug(f"PDF validation passed: {file_path}")
            return True
        except Exception as e:
            raise PDFValidationError(
                f"PDF file appears to be corrupted or invalid: {str(e)}"
            )
    
    # Basic validation passed (header check)
    logger.debug(f"PDF basic validation passed: {file_path}")
    return True


def get_pdf_page_count(file_path):
    """
    Extract the number of pages from a PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        int: Number of pages in the PDF, or None if cannot be determined
        
    Raises:
        PDFValidationError: If file is not a valid PDF
    """
    if not HAS_PYPDF2:
        logger.warning("PyPDF2 not available. Cannot extract page count.")
        return None
    
    try:
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
        logger.debug(f"PDF page count: {page_count} pages in {file_path}")
        return page_count
    except Exception as e:
        raise PDFValidationError(
            f"Could not extract page count from PDF: {str(e)}"
        )


def get_pdf_page_dimensions(file_path, page_index=0):
    """
    Extract page dimensions from a PDF file.
    
    Args:
        file_path: Path to PDF file
        page_index: Index of page to get dimensions for (default: 0 = first page)
        
    Returns:
        dict: Page dimensions with 'width' and 'height' in points, or None if cannot be determined
        
    Raises:
        PDFValidationError: If file is not a valid PDF or page doesn't exist
    """
    if not HAS_PYPDF2:
        logger.warning("PyPDF2 not available. Cannot extract page dimensions.")
        return None
    
    try:
        reader = PdfReader(file_path)
        
        if page_index >= len(reader.pages):
            raise PDFValidationError(
                f"Page index {page_index} out of range. PDF has {len(reader.pages)} pages."
            )
        
        page = reader.pages[page_index]
        
        # Get page dimensions (in points: 1 point = 1/72 inch)
        mediabox = page.mediabox
        width = float(mediabox.width)
        height = float(mediabox.height)
        
        dimensions = {
            'width': width,
            'height': height,
            'width_inches': width / 72,
            'height_inches': height / 72,
            'aspect_ratio': width / height if height > 0 else 0
        }
        
        logger.debug(
            f"PDF page dimensions: {width:.2f}x{height:.2f} points "
            f"({dimensions['width_inches']:.2f}x{dimensions['height_inches']:.2f} inches)"
        )
        
        return dimensions
        
    except PDFValidationError:
        raise
    except Exception as e:
        raise PDFValidationError(
            f"Could not extract page dimensions from PDF: {str(e)}"
        )


def get_pdf_info(file_path):
    """
    Get comprehensive information about a PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        dict: PDF information including page count, dimensions, file size, etc.
        
    Raises:
        PDFValidationError: If file is not a valid PDF
    """
    # Validate PDF first
    is_valid_pdf(file_path)
    
    path = Path(file_path)
    file_size = path.stat().st_size
    
    info = {
        'path': str(path.absolute()),
        'name': path.name,
        'size': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2),
        'valid': True,
    }
    
    # Add page count if PyPDF2 is available
    try:
        page_count = get_pdf_page_count(file_path)
        if page_count is not None:
            info['page_count'] = page_count
    except Exception as e:
        logger.warning(f"Could not get page count: {str(e)}")
        info['page_count'] = None
    
    # Add page dimensions if PyPDF2 is available
    try:
        dimensions = get_pdf_page_dimensions(file_path)
        if dimensions is not None:
            info['dimensions'] = dimensions
    except Exception as e:
        logger.warning(f"Could not get page dimensions: {str(e)}")
        info['dimensions'] = None
    
    return info


def validate_pdf_page_count(file_path, expected_count, tolerance=0):
    """
    Validate that a PDF has the expected number of pages.
    
    Args:
        file_path: Path to PDF file
        expected_count: Expected number of pages
        tolerance: Allowed difference in page count (default: 0 = exact match)
        
    Returns:
        bool: True if page count matches within tolerance
        
    Raises:
        PDFValidationError: If page count doesn't match or cannot be determined
    """
    actual_count = get_pdf_page_count(file_path)
    
    if actual_count is None:
        raise PDFValidationError(
            "Cannot validate page count: PyPDF2 not available"
        )
    
    difference = abs(actual_count - expected_count)
    
    if difference > tolerance:
        raise PDFValidationError(
            f"PDF page count mismatch: expected {expected_count} pages "
            f"(±{tolerance}), but found {actual_count} pages"
        )
    
    logger.info(
        f"PDF page count validation passed: {actual_count} pages "
        f"(expected {expected_count} ±{tolerance})"
    )
    
    return True


def validate_pdf_aspect_ratio(file_path, expected_ratio, tolerance=0.05):
    """
    Validate that a PDF page has the expected aspect ratio.
    
    Args:
        file_path: Path to PDF file
        expected_ratio: Expected aspect ratio (width/height)
        tolerance: Allowed difference in aspect ratio (default: 0.05 = 5%)
        
    Returns:
        bool: True if aspect ratio matches within tolerance
        
    Raises:
        PDFValidationError: If aspect ratio doesn't match or cannot be determined
    """
    dimensions = get_pdf_page_dimensions(file_path)
    
    if dimensions is None:
        raise PDFValidationError(
            "Cannot validate aspect ratio: PyPDF2 not available"
        )
    
    actual_ratio = dimensions['aspect_ratio']
    difference = abs(actual_ratio - expected_ratio)
    
    if difference > tolerance:
        raise PDFValidationError(
            f"PDF aspect ratio mismatch: expected {expected_ratio:.3f} "
            f"(±{tolerance:.3f}), but found {actual_ratio:.3f}"
        )
    
    logger.info(
        f"PDF aspect ratio validation passed: {actual_ratio:.3f} "
        f"(expected {expected_ratio:.3f} ±{tolerance:.3f})"
    )
    
    return True
