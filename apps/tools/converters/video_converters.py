"""
Video processing services.
"""
import time
from pathlib import Path

# MoviePy 2.x has a different import structure
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    # For MoviePy 2.x
    from moviepy import VideoFileClip

from apps.tools.utils.base_converter import BaseConverter, ConversionError
from apps.tools.utils.converter_factory import register_converter
from apps.tools.utils.file_utils import FileValidationError


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
    MAX_FILE_SIZE_MB = 100  # 100MB maximum for video files
    OUTPUT_EXTENSION = 'mp4'
    
    def validate_video_file(self, file_path):
        """
        Validate that the video file can be opened and processed by MoviePy.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            bool: True if validation passes
            
        Raises:
            FileValidationError: If the video file is corrupted or cannot be opened
        """
        try:
            # Try to open the video file with MoviePy
            test_clip = VideoFileClip(file_path)
            
            # Check if we can read basic properties
            if test_clip.duration is None or test_clip.duration <= 0:
                test_clip.close()
                raise FileValidationError(
                    "Video file appears to be corrupted or has invalid duration"
                )
            
            # Close the test clip
            test_clip.close()
            
            self.logger.info(f"Video file validation passed: {file_path}")
            return True
            
        except (IOError, OSError) as e:
            raise FileValidationError(
                f"Cannot open video file. The file may be corrupted or in an unsupported format: {str(e)}"
            )
        except Exception as e:
            raise FileValidationError(
                f"Video file validation failed: {str(e)}"
            )
    
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
            # Validate input file (size, extension, MIME type)
            self.validate_file(input_path)
            
            # Validate that video can be opened by MoviePy
            self.validate_video_file(input_path)
            
            # Get original file size
            original_size = self.get_file_info(input_path)['size']
            
            # Load video
            self.logger.info(f"Loading video file: {input_path}")
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
            
        except FileValidationError as e:
            # File validation errors - pass through with clear message
            self.log_conversion_error(input_path, e)
            raise ConversionError(f"Video file validation failed: {str(e)}")
            
        except (IOError, OSError) as e:
            # File system errors (permissions, disk space, etc.)
            self.log_conversion_error(input_path, e)
            error_msg = "File system error during video compression. "
            if "Permission denied" in str(e):
                error_msg += "Check that the output directory is writable."
            elif "No space left" in str(e):
                error_msg += "Insufficient disk space for output file."
            else:
                error_msg += f"Details: {str(e)}"
            raise ConversionError(error_msg)
            
        except Exception as e:
            # Catch-all for other errors (codec issues, MoviePy errors, etc.)
            self.log_conversion_error(input_path, e)
            error_type = type(e).__name__
            
            # Provide user-friendly messages for common MoviePy errors
            if "codec" in str(e).lower():
                error_msg = (
                    "Video codec error. The video format may not be supported or "
                    "ffmpeg may not be properly installed on your system."
                )
            elif "audio" in str(e).lower():
                error_msg = (
                    "Audio processing error. The video's audio format may not be supported. "
                    "Try converting the video to a standard format first."
                )
            else:
                error_msg = f"Video compression failed: {str(e)}"
            
            self.logger.error(f"Technical error details - Type: {error_type}, Message: {str(e)}")
            raise ConversionError(error_msg)
        
        finally:
            # Ensure clip is closed even if error occurs
            if clip is not None:
                try:
                    self.logger.debug(f"Cleaning up video clip resources for: {input_path}")
                    clip.close()
                    self.logger.debug("Video clip resources cleaned up successfully")
                except Exception as cleanup_error:
                    # Log cleanup errors but don't raise them
                    self.logger.warning(
                        f"Error during video clip cleanup: {str(cleanup_error)}"
                    )
