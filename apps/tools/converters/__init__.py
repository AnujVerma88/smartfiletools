"""
File conversion implementations.
"""
import logging

logger = logging.getLogger('apps.tools')

from .pdf_converters import (
    PDFToDocxConverter,
    DocxToPDFConverter,
    XLSXToPDFConverter,
    PPTXToPDFConverter,
)
from .image_converters import (
    ImageToPDFConverter,
    ImageCompressor,
    ImageConverter,
)
from .pdf_manipulation import (
    PDFMerger,
    PDFSplitter,
    PDFCompressor,
    PDFTextExtractor,
)

# Try to import video converters, but don't fail if moviepy is not available
try:
    from .video_converters import (
        VideoCompressor,
    )
    VIDEO_CONVERTERS_AVAILABLE = True
    logger.info("[OK] VideoCompressor imported successfully")
except ImportError as e:
    VIDEO_CONVERTERS_AVAILABLE = False
    logger.error(f"[FAIL] VideoCompressor import failed: {e}")
    logger.error("  Video compression will be unavailable.")
    logger.error("  To enable video compression, install MoviePy:")
    logger.error("    pip install moviepy")
    logger.error("  MoviePy also requires ffmpeg to be installed on your system:")
    logger.error("    - Windows: Download from https://ffmpeg.org/")
    logger.error("    - Linux: sudo apt-get install ffmpeg")
    logger.error("    - Mac: brew install ffmpeg")
except Exception as e:
    VIDEO_CONVERTERS_AVAILABLE = False
    logger.error(f"[FAIL] Unexpected error importing VideoCompressor: {e}", exc_info=True)
    logger.error("  Video compression will be unavailable.")

__all__ = [
    'PDFToDocxConverter',
    'DocxToPDFConverter',
    'XLSXToPDFConverter',
    'PPTXToPDFConverter',
    'ImageToPDFConverter',
    'ImageCompressor',
    'ImageConverter',
    'PDFMerger',
    'PDFSplitter',
    'PDFCompressor',
    'PDFTextExtractor',
]

if VIDEO_CONVERTERS_AVAILABLE:
    __all__.append('VideoCompressor')
