"""
Signature Renderer for E-Sign.
Handles processing of drawn, uploaded, and typed signatures.
"""
import base64
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps
from django.conf import settings
from django.core.files.base import ContentFile
import os
import logging

logger = logging.getLogger('apps.esign')

class SignatureRenderer:
    
    @staticmethod
    def render_drawn_signature(data_url, width=None, height=None):
        """
        Convert base64 data URL (from canvas) to PIL Image.
        """
        try:
            # Remove header if present (e.g., "data:image/png;base64,")
            if ',' in data_url:
                header, encoded = data_url.split(',', 1)
            else:
                encoded = data_url
                
            data = base64.b64decode(encoded)
            image = Image.open(io.BytesIO(data))
            
            # Resize if dimensions provided
            if width and height:
                image = image.resize((width, height), Image.Resampling.LANCZOS)
                
            return image
        except Exception as e:
            logger.error(f"Failed to render drawn signature: {str(e)}")
            raise

    @staticmethod
    def process_uploaded_signature(uploaded_file, width=None, height=None):
        """
        Process uploaded signature image (remove background, resize).
        """
        try:
            image = Image.open(uploaded_file)
            
            # Convert to RGBA
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Simple background removal (make white transparent)
            # This is a basic implementation; for better results, use more advanced techniques
            data = image.getdata()
            new_data = []
            for item in data:
                # If pixel is white (or close to white), make it transparent
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            
            image.putdata(new_data)
            
            # Resize if dimensions provided
            if width and height:
                image.thumbnail((width, height), Image.Resampling.LANCZOS)
                
            return image
        except Exception as e:
            logger.error(f"Failed to process uploaded signature: {str(e)}")
            raise

    @staticmethod
    def render_typed_signature(text, font_name='default', width=400, height=150):
        """
        Render text as a signature image using a cursive font.
        """
        try:
            # Create blank transparent image
            image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(image)
            
            # Load font
            font = SignatureRenderer._get_font(font_name, size=60)
            
            # Calculate text position to center it
            # getbbox returns (left, top, right, bottom)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) / 2
            y = (height - text_height) / 2
            
            # Draw text in black
            draw.text((x, y), text, font=font, fill=(0, 0, 0, 255))
            
            return image
        except Exception as e:
            logger.error(f"Failed to render typed signature: {str(e)}")
            raise

    @staticmethod
    def save_signature_image(pil_image, filename='signature.png', format='PNG'):
        """
        Save PIL image to bytes for Django FileField.
        Returns a ContentFile with proper name attribute.
        """
        output = io.BytesIO()
        pil_image.save(output, format=format)
        output.seek(0)
        return ContentFile(output.getvalue(), name=filename)

    @staticmethod
    def _get_font(font_name, size=40):
        """
        Helper to load fonts. Tries to load from static/fonts, then system fonts.
        """
        # 1. Check static/fonts
        font_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
        
        # Map friendly names to filenames (including Windows system fonts)
        font_map = {
            'Dancing Script': 'DancingScript-Regular.ttf',
            'Pacifico': 'Pacifico-Regular.ttf',
            'Brush Script': 'BrushScript.ttf',
            'Brush Script MT': 'BRUSHSCI.TTF',
            'Segoe Script': 'SEGOESC.TTF',
            'Lucida Handwriting': 'LHANDW.TTF',
        }
        
        filename = font_map.get(font_name)
        if filename:
            # Check static dir
            font_path = os.path.join(font_dir, filename)
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    pass
            
            # Check Windows Fonts
            if os.name == 'nt':
                win_font_path = os.path.join('C:\\Windows\\Fonts', filename)
                if os.path.exists(win_font_path):
                    try:
                        return ImageFont.truetype(win_font_path, size)
                    except:
                        pass
        
        # Fallback to default
        return ImageFont.load_default()
