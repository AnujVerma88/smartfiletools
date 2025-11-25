"""
File conversion implementations.
"""
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
except ImportError as e:
    print(f"⚠ Video converters not available: {e}")
    VIDEO_CONVERTERS_AVAILABLE = False

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
