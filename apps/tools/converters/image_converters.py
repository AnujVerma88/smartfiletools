"""
Image conversion and processing services.
"""
import time
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas

from apps.tools.utils.base_converter import BaseConverter, ConversionError
from apps.tools.utils.converter_factory import register_converter


@register_converter('image_to_pdf')
class ImageToPDFConverter(BaseConverter):
    """
    Converter for images to PDF format using Pillow and ReportLab.
    Supports multiple images to single PDF.
    """
    
    ALLOWED_INPUT_TYPES = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/tiff',
    ]
    ALLOWED_INPUT_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif']
    MAX_FILE_SIZE_MB = 50
    OUTPUT_EXTENSION = 'pdf'
    
    def convert(self, input_path, output_path, image_paths=None):
        """
        Convert image(s) to PDF format.
        
        Args:
            input_path: Path to input image file (or first image if multiple)
            output_path: Path where output PDF file should be saved
            image_paths: Optional list of additional image paths for multi-image PDF
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Collect all image paths
            if image_paths:
                all_images = [input_path] + image_paths
            else:
                all_images = [input_path]
            
            # Validate all images
            for img_path in all_images:
                self.validate_file(img_path)
            
            # Create PDF
            c = canvas.Canvas(output_path, pagesize=letter)
            page_width, page_height = letter
            
            for img_path in all_images:
                # Open image
                img = Image.open(img_path)
                
                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate dimensions to fit page while maintaining aspect ratio
                img_width, img_height = img.size
                aspect = img_height / float(img_width)
                
                if aspect > 1:
                    # Portrait
                    display_height = page_height - 100
                    display_width = display_height / aspect
                else:
                    # Landscape
                    display_width = page_width - 100
                    display_height = display_width * aspect
                
                # Center image on page
                x = (page_width - display_width) / 2
                y = (page_height - display_height) / 2
                
                # Draw image on canvas
                c.drawImage(img_path, x, y, width=display_width, height=display_height)
                c.showPage()
            
            # Save PDF
            c.save()
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'images_processed': len(all_images),
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"Image to PDF conversion failed: {str(e)}")


@register_converter('compress_image')
class ImageCompressor(BaseConverter):
    """
    Image compression service using Pillow optimization.
    Reduces file size while maintaining acceptable quality.
    """
    
    ALLOWED_INPUT_TYPES = [
        'image/jpeg',
        'image/jpg',
        'image/png',
    ]
    ALLOWED_INPUT_EXTENSIONS = ['jpg', 'jpeg', 'png']
    MAX_FILE_SIZE_MB = 50
    OUTPUT_EXTENSION = 'jpg'  # Default output format
    
    def convert(self, input_path, output_path, quality=85, max_width=None, max_height=None):
        """
        Compress image file.
        
        Args:
            input_path: Path to input image file
            output_path: Path where output image should be saved
            quality: JPEG quality (1-100, default 85)
            max_width: Optional maximum width for resizing
            max_height: Optional maximum height for resizing
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Open image
            img = Image.open(input_path)
            
            # Convert RGBA to RGB if saving as JPEG
            if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
            
            # Resize if dimensions specified
            if max_width or max_height:
                img.thumbnail((max_width or img.width, max_height or img.height), Image.Resampling.LANCZOS)
            
            # Get original file size
            original_size = self.get_file_info(input_path)['size']
            
            # Save with optimization
            save_kwargs = {'optimize': True}
            if output_path.lower().endswith(('.jpg', '.jpeg')):
                save_kwargs['quality'] = quality
                save_kwargs['progressive'] = True
            elif output_path.lower().endswith('.png'):
                save_kwargs['compress_level'] = 9
            
            img.save(output_path, **save_kwargs)
            
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
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"Image compression failed: {str(e)}")


@register_converter('convert_image')
class ImageConverter(BaseConverter):
    """
    Image format converter using Pillow.
    Converts between JPG, PNG, GIF, BMP, etc.
    """
    
    ALLOWED_INPUT_TYPES = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/tiff',
        'image/webp',
    ]
    ALLOWED_INPUT_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp']
    MAX_FILE_SIZE_MB = 50
    OUTPUT_EXTENSION = 'png'  # Default output format
    
    def convert(self, input_path, output_path, output_format=None):
        """
        Convert image to different format.
        
        Args:
            input_path: Path to input image file
            output_path: Path where output image should be saved
            output_format: Target format (jpg, png, gif, bmp, etc.)
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Determine output format
            if output_format:
                fmt = output_format.upper()
            else:
                fmt = Path(output_path).suffix.upper().lstrip('.')
            
            # Handle JPEG format name
            if fmt == 'JPG':
                fmt = 'JPEG'
            
            # Open image
            img = Image.open(input_path)
            
            # Handle transparency for formats that don't support it
            if fmt in ('JPEG', 'BMP') and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            # Save in new format
            save_kwargs = {}
            if fmt == 'JPEG':
                save_kwargs['quality'] = 95
                save_kwargs['optimize'] = True
            elif fmt == 'PNG':
                save_kwargs['optimize'] = True
            
            img.save(output_path, format=fmt, **save_kwargs)
            
            duration = time.time() - start_time
            self.log_conversion_success(input_path, output_path, duration)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'duration': duration,
                'input_format': img.format,
                'output_format': fmt,
                'dimensions': img.size,
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"Image format conversion failed: {str(e)}")
