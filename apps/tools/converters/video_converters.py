"""
Video processing services.
"""
import time
from pathlib import Path
from moviepy.editor import VideoFileClip

from apps.tools.utils.base_converter import BaseConverter, ConversionError
from apps.tools.utils.converter_factory import register_converter


@register_converter('compress_video')
class VideoCompressor(BaseConverter):
    """
    Video compression service using moviepy.
    Reduces video file size by adjusting bitrate and resolution.
    """
    
    ALLOWED_INPUT_TYPES = [
        'video/mp4',
        'video/mpeg',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-matroska',
    ]
    ALLOWED_INPUT_EXTENSIONS = ['mp4', 'mpeg', 'mpg', 'mov', 'avi', 'mkv']
    MAX_FILE_SIZE_MB = 500
    OUTPUT_EXTENSION = 'mp4'
    
    def convert(self, input_path, output_path, target_resolution=None, bitrate='2000k', fps=None):
        """
        Compress video file.
        
        Args:
            input_path: Path to input video file
            output_path: Path where compressed video should be saved
            target_resolution: Tuple (width, height) or None to keep original
            bitrate: Target bitrate (e.g., '2000k', '1000k')
            fps: Target frames per second or None to keep original
            
        Returns:
            dict: Conversion result with status and metadata
        """
        start_time = time.time()
        self.log_conversion_start(input_path, output_path)
        
        clip = None
        try:
            # Validate input file
            self.validate_file(input_path)
            
            # Get original file size
            original_size = self.get_file_info(input_path)['size']
            
            # Load video
            clip = VideoFileClip(input_path)
            
            # Get original properties
            original_duration = clip.duration
            original_fps = clip.fps
            original_size_tuple = clip.size
            
            # Apply resolution change if specified
            if target_resolution:
                clip = clip.resize(target_resolution)
            
            # Apply FPS change if specified
            if fps and fps != original_fps:
                clip = clip.set_fps(fps)
            
            # Write compressed video
            clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                bitrate=bitrate,
                preset='medium',
                threads=4,
                logger=None  # Suppress moviepy progress output
            )
            
            # Close clip
            clip.close()
            clip = None
            
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
                'video_duration': original_duration,
                'original_resolution': original_size_tuple,
                'target_resolution': target_resolution or original_size_tuple,
                'original_fps': original_fps,
                'target_fps': fps or original_fps,
                'bitrate': bitrate,
                'input_info': self.get_file_info(input_path),
                'output_info': self.get_file_info(output_path),
            }
            
        except Exception as e:
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"Video compression failed: {str(e)}")
        
        finally:
            # Ensure clip is closed even if error occurs
            if clip is not None:
                try:
                    clip.close()
                except:
                    pass
