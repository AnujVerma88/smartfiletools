"""
PDF manipulation services (merge, split, compress, extract text).
"""
import time
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import pdfplumber

from apps.tools.utils.base_converter import BaseConverter, ConversionError
from apps.tools.utils.converter_factory import register_converter


@register_converter('merge_pdf')
class PDFMerger(BaseConverter):
    """
    PDF merger service using PyPDF2.
    Merges multiple PDF files into a single PDF.
    """
    
    ALLOWED_INPUT_TYPES = ['application/pdf']
    ALLOWED_INPUT_EXTENSIONS = ['pdf']
    MAX_FILE_SIZE_MB = 100
    OUTPUT_EXTENSION = 'pdf'
    
    def convert(self, input_path, output_path, additional_pdfs=None):
        """
        Merge multiple PDF files into one.
        
        Args:
            input_path: Path to first PDF file
            output_path: Path where merged PDF should be saved
            additional_pdfs: List of additional PDF file paths to merge
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Collect all PDF paths
            if additional_pdfs:
                all_pdfs = [input_path] + additional_pdfs
            else:
                all_pdfs = [input_path]
            
            # Validate all PDFs
            for pdf_path in all_pdfs:
                self.validate_file(pdf_path)
            
            # Create merger
            merger = PdfMerger()
            
            # Add all PDFs
            total_pages = 0
            for pdf_path in all_pdfs:
                merger.append(pdf_path)
                reader = PdfReader(pdf_path)
                total_pages += len(reader.pages)
            
            # Write merged PDF
            merger.write(output_path)
            merger.close()
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'pdfs_merged': len(all_pdfs),
                'total_pages': total_pages,
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"PDF merge failed: {str(e)}")


@register_converter('split_pdf')
class PDFSplitter(BaseConverter):
    """
    PDF splitter service using PyPDF2.
    Splits PDF into individual pages or page ranges.
    """
    
    ALLOWED_INPUT_TYPES = ['application/pdf']
    ALLOWED_INPUT_EXTENSIONS = ['pdf']
    MAX_FILE_SIZE_MB = 100
    OUTPUT_EXTENSION = 'pdf'
    
    def convert(self, input_path, output_path, page_ranges=None, split_mode='all'):
        """
        Split PDF file.
        
        Args:
            input_path: Path to input PDF file
            output_path: Base path for output files (will append page numbers)
            page_ranges: List of tuples (start, end) for page ranges (1-indexed)
            split_mode: 'all' (each page), 'ranges' (specified ranges), 'half' (split in half)
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Read PDF
            reader = PdfReader(input_path)
            total_pages = len(reader.pages)
            
            output_files = []
            
            if split_mode == 'all':
                # Split into individual pages
                for page_num in range(total_pages):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_num])
                    
                    # Create output filename
                    output_dir = Path(output_path).parent
                    output_name = Path(output_path).stem
                    output_ext = Path(output_path).suffix
                    page_output = output_dir / f"{output_name}_page_{page_num + 1}{output_ext}"
                    
                    with open(page_output, 'wb') as output_file:
                        writer.write(output_file)
                    
                    output_files.append(str(page_output))
            
            elif split_mode == 'half':
                # Split in half
                mid_point = total_pages // 2
                
                # First half
                writer1 = PdfWriter()
                for page_num in range(mid_point):
                    writer1.add_page(reader.pages[page_num])
                
                output_dir = Path(output_path).parent
                output_name = Path(output_path).stem
                output_ext = Path(output_path).suffix
                output1 = output_dir / f"{output_name}_part_1{output_ext}"
                
                with open(output1, 'wb') as output_file:
                    writer1.write(output_file)
                output_files.append(str(output1))
                
                # Second half
                writer2 = PdfWriter()
                for page_num in range(mid_point, total_pages):
                    writer2.add_page(reader.pages[page_num])
                
                output2 = output_dir / f"{output_name}_part_2{output_ext}"
                with open(output2, 'wb') as output_file:
                    writer2.write(output_file)
                output_files.append(str(output2))
            
            elif split_mode == 'ranges' and page_ranges:
                # Split by specified ranges
                for idx, (start, end) in enumerate(page_ranges, 1):
                    writer = PdfWriter()
                    
                    # Convert to 0-indexed
                    start_idx = start - 1
                    end_idx = min(end, total_pages)
                    
                    for page_num in range(start_idx, end_idx):
                        writer.add_page(reader.pages[page_num])
                    
                    output_dir = Path(output_path).parent
                    output_name = Path(output_path).stem
                    output_ext = Path(output_path).suffix
                    range_output = output_dir / f"{output_name}_pages_{start}-{end_idx}{output_ext}"
                    
                    with open(range_output, 'wb') as output_file:
                        writer.write(output_file)
                    
                    output_files.append(str(range_output))
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'output_files': output_files,
                'duration': duration,
                'total_pages': total_pages,
                'files_created': len(output_files),
                'split_mode': split_mode,
                'input_info': self.get_file_info(input_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"PDF split failed: {str(e)}")


@register_converter('compress_pdf')
class PDFCompressor(BaseConverter):
    """
    PDF compression service using PyPDF2.
    Reduces PDF file size by removing redundant data.
    """
    
    ALLOWED_INPUT_TYPES = ['application/pdf']
    ALLOWED_INPUT_EXTENSIONS = ['pdf']
    MAX_FILE_SIZE_MB = 100
    OUTPUT_EXTENSION = 'pdf'
    
    def convert(self, input_path, output_path):
        """
        Compress PDF file.
        
        Args:
            input_path: Path to input PDF file
            output_path: Path where compressed PDF should be saved
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Get original file size
            original_size = self.get_file_info(input_path)['size']
            
            # Read and write PDF with compression
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Add all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Compress
            writer.compress_identical_objects(remove_identicals=True)
            for page in writer.pages:
                page.compress_content_streams()
            
            # Write compressed PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            # Get compressed file size
            compressed_size = self.get_file_info(output_path)['size']
            compression_ratio = ((original_size - compressed_size) / original_size) * 100
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': round(compression_ratio, 2),
                'bytes_saved': original_size - compressed_size,
                'pages': len(reader.pages),
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"PDF compression failed: {str(e)}")


@register_converter('extract_text')
class PDFTextExtractor(BaseConverter):
    """
    PDF text extraction service using pdfplumber.
    Extracts text content while preserving structure.
    """
    
    ALLOWED_INPUT_TYPES = ['application/pdf']
    ALLOWED_INPUT_EXTENSIONS = ['pdf']
    MAX_FILE_SIZE_MB = 100
    OUTPUT_EXTENSION = 'txt'
    
    def convert(self, input_path, output_path):
        """
        Extract text from PDF file.
        
        Args:
            input_path: Path to input PDF file
            output_path: Path where extracted text should be saved
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Extract text
            extracted_text = []
            page_count = 0
            
            with pdfplumber.open(input_path) as pdf:
                page_count = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        extracted_text.append(f"--- Page {page_num} ---\n")
                        extracted_text.append(text)
                        extracted_text.append("\n\n")
            
            # Write to text file
            full_text = ''.join(extracted_text)
            with open(output_path, 'w', encoding='utf-8') as output_file:
                output_file.write(full_text)
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'pages_processed': page_count,
                'characters_extracted': len(full_text),
                'words_extracted': len(full_text.split()),
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"PDF text extraction failed: {str(e)}")
