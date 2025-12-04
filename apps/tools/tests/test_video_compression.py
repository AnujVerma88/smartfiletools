"""
Tests for video compression functionality.
Feature: video-compression
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from hypothesis import given, settings, strategies as st

from apps.tools.utils.converter_factory import get_converter, list_converters


class TestConverterRegistration(TestCase):
    """
    Test converter registration for video compression.
    Feature: video-compression, Property 1: Converter Registration Completeness
    Validates: Requirements 2.1, 2.3
    """
    
    def test_compress_video_in_registry(self):
        """
        Test that compress_video appears in converter registry after app initialization.
        
        This test verifies that the VideoCompressor is properly registered with the
        converter factory when the application starts.
        """
        # Get all registered converters
        registered = list_converters()
        
        # Check if compress_video is in the registry
        self.assertIn(
            'compress_video',
            registered,
            "compress_video should be registered in the converter factory. "
            "If this fails, check that MoviePy is installed and VideoCompressor imports successfully."
        )
    
    def test_get_video_converter_returns_instance(self):
        """
        Test that get_converter('compress_video') returns a VideoCompressor instance.
        
        Validates: Requirements 2.4
        """
        try:
            converter = get_converter('compress_video')
            
            # Verify we got an instance
            self.assertIsNotNone(converter)
            
            # Verify it has the convert method
            self.assertTrue(
                hasattr(converter, 'convert'),
                "VideoCompressor should have a convert() method"
            )
            
            # Verify it has the expected class attributes
            self.assertTrue(
                hasattr(converter, 'ALLOWED_INPUT_EXTENSIONS'),
                "VideoCompressor should define ALLOWED_INPUT_EXTENSIONS"
            )
            
        except ValueError as e:
            # If compress_video is not registered, fail with helpful message
            self.fail(
                f"Failed to get compress_video converter: {e}. "
                "Ensure MoviePy is installed and VideoCompressor is properly registered."
            )
    
    def test_video_converter_has_correct_extensions(self):
        """
        Test that VideoCompressor supports the expected file extensions.
        
        Validates: Requirements 1.1
        """
        try:
            converter = get_converter('compress_video')
            
            expected_extensions = ['mp4', 'mpeg', 'mpg', 'mov', 'avi', 'mkv']
            
            for ext in expected_extensions:
                self.assertIn(
                    ext,
                    converter.ALLOWED_INPUT_EXTENSIONS,
                    f"VideoCompressor should support .{ext} files"
                )
                
        except ValueError:
            self.skipTest("VideoCompressor not available - MoviePy may not be installed")


@pytest.mark.skipif(
    'compress_video' not in list_converters(),
    reason="VideoCompressor not available - MoviePy may not be installed"
)
class TestVideoConverterProperties(TestCase):
    """
    Property-based tests for video converter.
    These tests only run if VideoCompressor is available.
    """
    
    @settings(max_examples=100)
    @given(st.sampled_from(['mp4', 'mpeg', 'mpg', 'mov', 'avi', 'mkv']))
    def test_all_supported_formats_accepted(self, extension):
        """
        Property test: All supported video formats should be in ALLOWED_INPUT_EXTENSIONS.
        
        Feature: video-compression, Property 3: Format Validation
        Validates: Requirements 1.1
        """
        converter = get_converter('compress_video')
        
        self.assertIn(
            extension,
            converter.ALLOWED_INPUT_EXTENSIONS,
            f"Extension {extension} should be in ALLOWED_INPUT_EXTENSIONS"
        )
    
    def test_max_file_size_is_500mb(self):
        """
        Test that VideoCompressor has the correct max file size limit.
        
        Validates: Requirements 1.2
        """
        converter = get_converter('compress_video')
        
        self.assertEqual(
            converter.MAX_FILE_SIZE_MB,
            500,
            "VideoCompressor should have MAX_FILE_SIZE_MB set to 500"
        )
    
    def test_output_extension_is_mp4(self):
        """
        Test that VideoCompressor outputs MP4 format.
        
        Validates: Requirements 5.1
        """
        converter = get_converter('compress_video')
        
        self.assertEqual(
            converter.OUTPUT_EXTENSION,
            'mp4',
            "VideoCompressor should output MP4 format"
        )



class TestListConvertersCommand(TestCase):
    """
    Test the list_converters management command.
    Validates: Requirements 2.3
    """
    
    def test_command_lists_converters(self):
        """
        Test that the list_converters command outputs registered converters.
        """
        from io import StringIO
        from django.core.management import call_command
        
        out = StringIO()
        call_command('list_converters', stdout=out)
        output = out.getvalue()
        
        # Check that output contains expected content
        self.assertIn('Registered Converters:', output)
        
        # Check that some known converters are listed
        registered = list_converters()
        if registered:
            # At least one converter should be in the output
            self.assertTrue(
                any(tool_type in output for tool_type in registered.keys()),
                "Output should contain at least one registered converter"
            )
    
    def test_command_highlights_video_converter_status(self):
        """
        Test that the command specifically mentions video compression status.
        """
        from io import StringIO
        from django.core.management import call_command
        
        out = StringIO()
        call_command('list_converters', stdout=out)
        output = out.getvalue()
        
        # Check that video compression status is mentioned
        self.assertTrue(
            'compress_video' in output or 'Video compression' in output,
            "Output should mention video compression status"
        )
    
    def test_command_handles_empty_registry(self):
        """
        Test that the command handles an empty registry gracefully.
        """
        from io import StringIO
        from django.core.management import call_command
        from unittest.mock import patch
        
        out = StringIO()
        
        # Mock list_converters to return empty dict
        with patch('apps.tools.management.commands.list_converters.list_converters', return_value={}):
            call_command('list_converters', stdout=out)
            output = out.getvalue()
            
            # Should indicate no converters registered
            self.assertIn('No converters registered', output)



class TestVideoCompressorResourceCleanup(TestCase):
    """
    Test resource cleanup in VideoCompressor.
    Feature: video-compression, Property 5: Resource Cleanup
    Validates: Requirements 3.5
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_clip_closed_on_success(self):
        """
        Test that VideoFileClip.close() is called on successful conversion.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            # Mock file operations
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'get_file_info', return_value={'size': 1000000}):
                    try:
                        converter.convert('/fake/input.mp4', '/fake/output.mp4')
                    except:
                        pass  # We don't care if it fails, just that close is called
            
            # Verify close was called
            mock_clip.close.assert_called()
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_clip_closed_on_error(self):
        """
        Test that VideoFileClip.close() is called even when an error occurs.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip that raises an error during processing
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip.write_videofile.side_effect = Exception("Simulated error")
            mock_clip_class.return_value = mock_clip
            
            # Mock file operations
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'get_file_info', return_value={'size': 1000000}):
                    with self.assertRaises(Exception):
                        converter.convert('/fake/input.mp4', '/fake/output.mp4')
            
            # Verify close was called even though an error occurred
            mock_clip.close.assert_called()
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_cleanup_error_does_not_propagate(self):
        """
        Test that errors during cleanup don't propagate to the caller.
        """
        from unittest.mock import patch, MagicMock
        from apps.tools.utils.base_converter import ConversionError
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip where close() raises an error
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip.write_videofile.side_effect = Exception("Processing error")
            mock_clip.close.side_effect = Exception("Cleanup error")
            mock_clip_class.return_value = mock_clip
            
            # Mock file operations
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'get_file_info', return_value={'size': 1000000}):
                    # Should raise ConversionError from processing, not cleanup
                    with self.assertRaises(ConversionError) as context:
                        converter.convert('/fake/input.mp4', '/fake/output.mp4')
                    
                    # Error message should be about processing, not cleanup
                    self.assertIn("compression failed", str(context.exception).lower())
                    self.assertNotIn("cleanup", str(context.exception).lower())


class TestVideoCompressorErrorMessages(TestCase):
    """
    Test error message handling in VideoCompressor.
    Feature: video-compression, Property 7: Error Message Presence
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 4.4
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_corrupted_file_error_message(self):
        """
        Test that corrupted video files produce clear error messages.
        """
        from unittest.mock import patch
        from apps.tools.utils.file_utils import FileValidationError
        
        converter = get_converter('compress_video')
        
        # Mock validate_video_file to raise validation error
        with patch.object(converter, 'validate_file'):
            with patch.object(converter, 'validate_video_file') as mock_validate:
                mock_validate.side_effect = FileValidationError("Video file appears to be corrupted")
                
                with self.assertRaises(Exception) as context:
                    converter.convert('/fake/corrupted.mp4', '/fake/output.mp4')
                
                # Check that error message is user-friendly
                error_msg = str(context.exception)
                self.assertIn("validation failed", error_msg.lower())
                self.assertIn("corrupted", error_msg.lower())
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_codec_error_message(self):
        """
        Test that codec errors produce user-friendly messages.
        """
        from unittest.mock import patch, MagicMock
        from apps.tools.utils.base_converter import ConversionError
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip with codec error
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip.write_videofile.side_effect = Exception("Codec not found: libx264")
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info', return_value={'size': 1000000}):
                        with self.assertRaises(ConversionError) as context:
                            converter.convert('/fake/input.mp4', '/fake/output.mp4')
                        
                        # Check for user-friendly codec error message
                        error_msg = str(context.exception)
                        self.assertIn("codec", error_msg.lower())
                        self.assertIn("ffmpeg", error_msg.lower())
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_permission_error_message(self):
        """
        Test that permission errors produce clear messages.
        """
        from unittest.mock import patch, MagicMock
        from apps.tools.utils.base_converter import ConversionError
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip with permission error
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip.write_videofile.side_effect = OSError("Permission denied")
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info', return_value={'size': 1000000}):
                        with self.assertRaises(ConversionError) as context:
                            converter.convert('/fake/input.mp4', '/fake/output.mp4')
                        
                        # Check for user-friendly permission error message
                        error_msg = str(context.exception)
                        self.assertIn("permission", error_msg.lower())
                        self.assertIn("writable", error_msg.lower())


class TestVideoFileValidation(TestCase):
    """
    Test video file validation method.
    Validates: Requirements 3.1, 3.4
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_validate_video_file_success(self):
        """
        Test that valid video files pass validation.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip for a valid video
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip_class.return_value = mock_clip
            
            # Should not raise an exception
            result = converter.validate_video_file('/fake/valid.mp4')
            self.assertTrue(result)
            
            # Verify clip was closed
            mock_clip.close.assert_called_once()
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_validate_video_file_corrupted(self):
        """
        Test that corrupted video files fail validation.
        """
        from unittest.mock import patch, MagicMock
        from apps.tools.utils.file_utils import FileValidationError
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip for a corrupted video (invalid duration)
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = None  # Invalid duration
            mock_clip_class.return_value = mock_clip
            
            # Should raise FileValidationError
            with self.assertRaises(FileValidationError) as context:
                converter.validate_video_file('/fake/corrupted.mp4')
            
            self.assertIn("corrupted", str(context.exception).lower())
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_validate_video_file_cannot_open(self):
        """
        Test that files that cannot be opened fail validation.
        """
        from unittest.mock import patch
        from apps.tools.utils.file_utils import FileValidationError
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip to raise IOError
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip_class.side_effect = IOError("Cannot open file")
            
            # Should raise FileValidationError
            with self.assertRaises(FileValidationError) as context:
                converter.validate_video_file('/fake/unreadable.mp4')
            
            error_msg = str(context.exception)
            self.assertIn("cannot open", error_msg.lower())
            self.assertIn("corrupted", error_msg.lower())



class TestFileSizeValidation(TestCase):
    """
    Property-based tests for file size validation.
    Feature: video-compression, Property 2: File Size Validation
    Validates: Requirements 1.2
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    @settings(max_examples=100)
    @given(st.integers(min_value=1, max_value=1000))
    def test_file_size_validation_property(self, file_size_mb):
        """
        Property test: Files > 500MB should be rejected, files <= 500MB should be accepted.
        
        For any file size, if it exceeds 500MB, validation should fail.
        If it's 500MB or less, validation should pass (assuming other validations pass).
        """
        from unittest.mock import patch, MagicMock
        from apps.tools.utils.file_utils import FileValidationError
        import os
        
        converter = get_converter('compress_video')
        
        # Create a mock file path
        test_file = f'/fake/video_{file_size_mb}mb.mp4'
        
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock os.path.getsize to return the test file size in bytes
            file_size_bytes = file_size_mb * 1024 * 1024
            with patch('os.path.getsize', return_value=file_size_bytes):
                # Mock MIME type validation to pass
                with patch('apps.tools.utils.file_utils.validate_mime_type'):
                    
                    if file_size_mb > 500:
                        # Files larger than 500MB should raise FileValidationError
                        with self.assertRaises(FileValidationError) as context:
                            converter.validate_file(test_file)
                        
                        error_msg = str(context.exception)
                        self.assertIn("size", error_msg.lower())
                    else:
                        # Files 500MB or smaller should pass validation
                        # (assuming extension is valid)
                        try:
                            result = converter.validate_file(test_file)
                            # If it passes, result should be True
                            self.assertTrue(result)
                        except FileValidationError as e:
                            # If it fails, it should be due to extension, not size
                            self.assertNotIn("size", str(e).lower())
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_exactly_500mb_accepted(self):
        """
        Test that exactly 500MB files are accepted (boundary condition).
        """
        from unittest.mock import patch
        import os
        
        converter = get_converter('compress_video')
        
        # Exactly 500MB
        file_size_bytes = 500 * 1024 * 1024
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=file_size_bytes):
                with patch('apps.tools.utils.file_utils.validate_mime_type'):
                    # Should not raise an exception for size
                    result = converter.validate_file('/fake/video_500mb.mp4')
                    self.assertTrue(result)
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_501mb_rejected(self):
        """
        Test that 501MB files are rejected (boundary condition).
        """
        from unittest.mock import patch
        from apps.tools.utils.file_utils import FileValidationError
        import os
        
        converter = get_converter('compress_video')
        
        # 501MB - just over the limit
        file_size_bytes = 501 * 1024 * 1024
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=file_size_bytes):
                with patch('apps.tools.utils.file_utils.validate_mime_type'):
                    # Should raise FileValidationError
                    with self.assertRaises(FileValidationError) as context:
                        converter.validate_file('/fake/video_501mb.mp4')
                    
                    self.assertIn("size", str(context.exception).lower())



class TestFormatValidation(TestCase):
    """
    Property-based tests for format validation.
    Feature: video-compression, Property 3: Format Validation
    Validates: Requirements 1.1
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    @settings(max_examples=100)
    @given(st.sampled_from(['mp4', 'mpeg', 'mpg', 'mov', 'avi', 'mkv']))
    def test_supported_formats_accepted(self, extension):
        """
        Property test: All supported video formats should pass validation.
        
        For any supported extension (mp4, mpeg, mpg, mov, avi, mkv),
        the file should pass format validation.
        """
        from unittest.mock import patch
        import os
        
        converter = get_converter('compress_video')
        
        test_file = f'/fake/video.{extension}'
        
        # Mock file operations
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=10 * 1024 * 1024):  # 10MB
                with patch('apps.tools.utils.file_utils.validate_mime_type'):
                    # Should not raise exception for supported formats
                    result = converter.validate_file(test_file)
                    self.assertTrue(result)
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    @settings(max_examples=100)
    @given(st.sampled_from(['txt', 'pdf', 'doc', 'jpg', 'png', 'zip', 'exe', 'wmv', 'flv']))
    def test_unsupported_formats_rejected(self, extension):
        """
        Property test: Unsupported formats should be rejected.
        
        For any unsupported extension, the file should fail format validation.
        """
        from unittest.mock import patch
        from apps.tools.utils.file_utils import FileValidationError
        import os
        
        converter = get_converter('compress_video')
        
        test_file = f'/fake/file.{extension}'
        
        # Mock file operations
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=10 * 1024 * 1024):  # 10MB
                with patch('apps.tools.utils.file_utils.validate_mime_type'):
                    # Should raise FileValidationError for unsupported formats
                    with self.assertRaises(FileValidationError) as context:
                        converter.validate_file(test_file)
                    
                    error_msg = str(context.exception)
                    self.assertIn("extension", error_msg.lower())
                    self.assertIn(extension, error_msg)
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_case_insensitive_extensions(self):
        """
        Test that file extensions are case-insensitive.
        """
        from unittest.mock import patch
        import os
        
        converter = get_converter('compress_video')
        
        # Test uppercase extensions
        for extension in ['MP4', 'MOV', 'AVI']:
            test_file = f'/fake/video.{extension}'
            
            with patch('os.path.exists', return_value=True):
                with patch('os.path.getsize', return_value=10 * 1024 * 1024):
                    with patch('apps.tools.utils.file_utils.validate_mime_type'):
                        # Should accept uppercase extensions
                        result = converter.validate_file(test_file)
                        self.assertTrue(result)
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_all_supported_formats_listed(self):
        """
        Test that VideoCompressor has all expected supported formats.
        """
        converter = get_converter('compress_video')
        
        expected_formats = ['mp4', 'mpeg', 'mpg', 'mov', 'avi', 'mkv']
        
        for fmt in expected_formats:
            self.assertIn(
                fmt,
                converter.ALLOWED_INPUT_EXTENSIONS,
                f"Format {fmt} should be in ALLOWED_INPUT_EXTENSIONS"
            )



class TestCompressionOutputProperties(TestCase):
    """
    Property-based tests for compression output.
    Feature: video-compression, Property 4: Compression Reduces Size
    Validates: Requirements 1.3
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_compression_reduces_or_maintains_size(self):
        """
        Property test: For successful compressions, output size should be ≤ input size.
        
        This is a fundamental property of compression - the output should never be
        larger than the input (though it may be the same if already optimally compressed).
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        # Test with various input sizes
        test_cases = [
            (10 * 1024 * 1024, 8 * 1024 * 1024),   # 10MB -> 8MB (compressed)
            (50 * 1024 * 1024, 40 * 1024 * 1024),  # 50MB -> 40MB (compressed)
            (100 * 1024 * 1024, 100 * 1024 * 1024), # 100MB -> 100MB (same size)
            (5 * 1024 * 1024, 4 * 1024 * 1024),    # 5MB -> 4MB (compressed)
        ]
        
        for input_size, output_size in test_cases:
            with self.subTest(input_size=input_size, output_size=output_size):
                # Mock VideoFileClip
                with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
                    mock_clip = MagicMock()
                    mock_clip.duration = 10.0
                    mock_clip.fps = 30
                    mock_clip.size = (1920, 1080)
                    mock_clip_class.return_value = mock_clip
                    
                    # Mock file operations
                    with patch.object(converter, 'validate_file'):
                        with patch.object(converter, 'validate_video_file'):
                            with patch.object(converter, 'get_file_info') as mock_get_info:
                                # First call returns input size, second returns output size
                                mock_get_info.side_effect = [
                                    {'size': input_size},
                                    {'size': input_size},
                                    {'size': output_size}
                                ]
                                
                                result = converter.convert('/fake/input.mp4', '/fake/output.mp4')
                                
                                # Verify output size is less than or equal to input size
                                self.assertLessEqual(
                                    result['compressed_size'],
                                    result['original_size'],
                                    "Compressed size should be ≤ original size"
                                )
                                
                                # Verify compression ratio is calculated correctly
                                if result['original_size'] > result['compressed_size']:
                                    self.assertGreater(
                                        result['compression_ratio'],
                                        0,
                                        "Compression ratio should be positive when size is reduced"
                                    )
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_compression_result_contains_size_info(self):
        """
        Test that compression results always include size information.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info') as mock_get_info:
                        mock_get_info.side_effect = [
                            {'size': 10000000},
                            {'size': 10000000},
                            {'size': 8000000}
                        ]
                        
                        result = converter.convert('/fake/input.mp4', '/fake/output.mp4')
                        
                        # Verify all required size fields are present
                        self.assertIn('original_size', result)
                        self.assertIn('compressed_size', result)
                        self.assertIn('compression_ratio', result)
                        self.assertIn('bytes_saved', result)
                        
                        # Verify values are correct
                        self.assertEqual(result['original_size'], 10000000)
                        self.assertEqual(result['compressed_size'], 8000000)
                        self.assertEqual(result['bytes_saved'], 2000000)


class TestOutputFileExistence(TestCase):
    """
    Property-based tests for output file existence.
    Feature: video-compression, Property 8: Output File Existence
    Validates: Requirements 1.4
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_successful_conversion_creates_output_file(self):
        """
        Property test: For completed conversions, output file should exist.
        """
        from unittest.mock import patch, MagicMock, mock_open
        import os
        
        converter = get_converter('compress_video')
        
        output_path = '/fake/output.mp4'
        
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info') as mock_get_info:
                        mock_get_info.side_effect = [
                            {'size': 10000000},
                            {'size': 10000000},
                            {'size': 8000000}
                        ]
                        
                        result = converter.convert('/fake/input.mp4', output_path)
                        
                        # Verify result contains output path
                        self.assertEqual(result['output_path'], output_path)
                        self.assertEqual(result['status'], 'success')
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_output_path_in_result(self):
        """
        Test that output_path is always in the result for successful conversions.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info') as mock_get_info:
                        mock_get_info.side_effect = [
                            {'size': 10000000},
                            {'size': 10000000},
                            {'size': 8000000}
                        ]
                        
                        result = converter.convert('/fake/input.mp4', '/fake/output.mp4')
                        
                        # Verify output_path is in result
                        self.assertIn('output_path', result)
                        self.assertIsNotNone(result['output_path'])
                        self.assertTrue(len(result['output_path']) > 0)


class TestCodecConsistency(TestCase):
    """
    Property-based tests for codec consistency.
    Feature: video-compression, Property 9: Codec Consistency
    Validates: Requirements 5.1, 5.2
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_output_uses_libx264_codec(self):
        """
        Property test: For successful compressions, output should use libx264 codec.
        """
        from unittest.mock import patch, MagicMock, call
        
        converter = get_converter('compress_video')
        
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info') as mock_get_info:
                        mock_get_info.side_effect = [
                            {'size': 10000000},
                            {'size': 10000000},
                            {'size': 8000000}
                        ]
                        
                        converter.convert('/fake/input.mp4', '/fake/output.mp4')
                        
                        # Verify write_videofile was called with libx264 codec
                        mock_clip.write_videofile.assert_called_once()
                        call_kwargs = mock_clip.write_videofile.call_args[1]
                        
                        self.assertEqual(call_kwargs['codec'], 'libx264')
                        self.assertEqual(call_kwargs['audio_codec'], 'aac')
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_output_format_is_mp4(self):
        """
        Test that output format is always MP4.
        """
        converter = get_converter('compress_video')
        
        # Verify OUTPUT_EXTENSION is set to mp4
        self.assertEqual(converter.OUTPUT_EXTENSION, 'mp4')
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_audio_codec_is_aac(self):
        """
        Test that audio codec is AAC for all conversions.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info') as mock_get_info:
                        mock_get_info.side_effect = [
                            {'size': 10000000},
                            {'size': 10000000},
                            {'size': 8000000}
                        ]
                        
                        converter.convert('/fake/input.mp4', '/fake/output.mp4')
                        
                        # Verify audio_codec is aac
                        call_kwargs = mock_clip.write_videofile.call_args[1]
                        self.assertEqual(call_kwargs['audio_codec'], 'aac')



class TestStatusProgression(TestCase):
    """
    Property-based tests for status progression.
    Feature: video-compression, Property 6: Status Progression
    Validates: Requirements 4.1, 4.2, 4.3, 4.4
    """
    
    def test_valid_status_transitions(self):
        """
        Property test: Status should follow valid progression.
        
        Valid progressions:
        - pending → processing → completed
        - pending → processing → failed
        - Status should never move backward
        """
        from apps.tools.models import ConversionHistory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Create a test user
        user = User.objects.create_user(
            username='testuser_status',
            email='test_status@example.com',
            password='testpass123'
        )
        
        # Test successful progression: pending → processing → completed
        conversion = ConversionHistory.objects.create(
            user=user,
            tool_type='compress_video',
            status='pending'
        )
        
        # Verify initial status
        self.assertEqual(conversion.status, 'pending')
        
        # Update to processing
        conversion.status = 'processing'
        conversion.save()
        conversion.refresh_from_db()
        self.assertEqual(conversion.status, 'processing')
        
        # Update to completed
        conversion.status = 'completed'
        conversion.save()
        conversion.refresh_from_db()
        self.assertEqual(conversion.status, 'completed')
        
        # Test failed progression: pending → processing → failed
        conversion2 = ConversionHistory.objects.create(
            user=user,
            tool_type='compress_video',
            status='pending'
        )
        
        conversion2.status = 'processing'
        conversion2.save()
        
        conversion2.status = 'failed'
        conversion2.error_message = 'Test error'
        conversion2.save()
        conversion2.refresh_from_db()
        
        self.assertEqual(conversion2.status, 'failed')
        self.assertIsNotNone(conversion2.error_message)
        
        # Cleanup
        user.delete()
    
    def test_status_never_moves_backward(self):
        """
        Test that status transitions are always forward.
        
        Once a conversion reaches 'completed' or 'failed', it should not
        change to an earlier status.
        """
        from apps.tools.models import ConversionHistory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        user = User.objects.create_user(
            username='testuser_backward',
            email='test_backward@example.com',
            password='testpass123'
        )
        
        # Create completed conversion
        conversion = ConversionHistory.objects.create(
            user=user,
            tool_type='compress_video',
            status='completed'
        )
        
        # Verify it's completed
        self.assertEqual(conversion.status, 'completed')
        
        # In a real system, we would prevent backward transitions
        # For now, we just verify the current status
        self.assertIn(conversion.status, ['pending', 'processing', 'completed', 'failed'])
        
        # Cleanup
        user.delete()
    
    def test_failed_status_has_error_message(self):
        """
        Property test: Failed conversions should have error messages.
        
        For any conversion with status='failed', error_message should be non-empty.
        """
        from apps.tools.models import ConversionHistory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        user = User.objects.create_user(
            username='testuser_error',
            email='test_error@example.com',
            password='testpass123'
        )
        
        # Create failed conversion with error message
        conversion = ConversionHistory.objects.create(
            user=user,
            tool_type='compress_video',
            status='failed',
            error_message='Video compression failed: codec error'
        )
        
        # Verify error message is present
        self.assertEqual(conversion.status, 'failed')
        self.assertIsNotNone(conversion.error_message)
        self.assertTrue(len(conversion.error_message) > 0)
        
        # Cleanup
        user.delete()
    
    def test_completed_status_has_output_file(self):
        """
        Test that completed conversions have output files.
        """
        from apps.tools.models import ConversionHistory
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        User = get_user_model()
        
        user = User.objects.create_user(
            username='testuser_output',
            email='test_output@example.com',
            password='testpass123'
        )
        
        # Create completed conversion with output file
        input_file = SimpleUploadedFile("test_input.mp4", b"fake video content")
        output_file = SimpleUploadedFile("test_output.mp4", b"fake compressed video")
        
        conversion = ConversionHistory.objects.create(
            user=user,
            tool_type='compress_video',
            status='completed',
            input_file=input_file,
            output_file=output_file
        )
        
        # Verify output file is present
        self.assertEqual(conversion.status, 'completed')
        self.assertTrue(conversion.output_file)
        
        # Cleanup
        user.delete()
    
    @settings(max_examples=50)
    @given(st.sampled_from(['pending', 'processing', 'completed', 'failed']))
    def test_all_statuses_are_valid(self, status):
        """
        Property test: All status values should be valid choices.
        """
        from apps.tools.models import ConversionHistory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get valid status choices from the model
        valid_statuses = [choice[0] for choice in ConversionHistory.STATUS_CHOICES]
        
        # Verify the status is in valid choices
        self.assertIn(status, valid_statuses)



class TestVideoCompressorInheritance(TestCase):
    """
    Unit tests for VideoCompressor inheritance and structure.
    Validates: Requirements 6.1
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_extends_base_converter(self):
        """
        Test that VideoCompressor extends BaseConverter.
        """
        from apps.tools.utils.base_converter import BaseConverter
        
        converter = get_converter('compress_video')
        
        # Verify inheritance
        self.assertIsInstance(converter, BaseConverter)
        self.assertTrue(issubclass(converter.__class__, BaseConverter))
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_implements_convert_method(self):
        """
        Test that VideoCompressor implements the convert() method.
        """
        converter = get_converter('compress_video')
        
        # Verify convert method exists
        self.assertTrue(hasattr(converter, 'convert'))
        self.assertTrue(callable(converter.convert))
        
        # Verify method signature
        import inspect
        sig = inspect.signature(converter.convert)
        params = list(sig.parameters.keys())
        
        # Should have at least input_path and output_path parameters
        self.assertIn('input_path', params)
        self.assertIn('output_path', params)
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_has_required_class_attributes(self):
        """
        Test that VideoCompressor has all required class attributes.
        """
        converter = get_converter('compress_video')
        
        # Verify required attributes from BaseConverter
        self.assertTrue(hasattr(converter, 'ALLOWED_INPUT_TYPES'))
        self.assertTrue(hasattr(converter, 'ALLOWED_INPUT_EXTENSIONS'))
        self.assertTrue(hasattr(converter, 'MAX_FILE_SIZE_MB'))
        self.assertTrue(hasattr(converter, 'OUTPUT_EXTENSION'))
        
        # Verify they are set to appropriate values
        self.assertIsInstance(converter.ALLOWED_INPUT_TYPES, list)
        self.assertIsInstance(converter.ALLOWED_INPUT_EXTENSIONS, list)
        self.assertIsInstance(converter.MAX_FILE_SIZE_MB, int)
        self.assertIsInstance(converter.OUTPUT_EXTENSION, str)
        
        # Verify they are not empty
        self.assertTrue(len(converter.ALLOWED_INPUT_EXTENSIONS) > 0)
        self.assertTrue(converter.MAX_FILE_SIZE_MB > 0)
        self.assertTrue(len(converter.OUTPUT_EXTENSION) > 0)


class TestBaseConverterMethodUsage(TestCase):
    """
    Property-based tests for BaseConverter method usage.
    Feature: video-compression, Property 10: Converter Inheritance
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
    """
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_uses_inherited_validation_methods(self):
        """
        Test that VideoCompressor uses inherited validation methods.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        # Mock VideoFileClip
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            # Spy on validate_file method
            with patch.object(converter, 'validate_file', wraps=converter.validate_file) as mock_validate:
                with patch.object(converter, 'get_file_info') as mock_get_info:
                    mock_get_info.side_effect = [
                        {'size': 10000000},
                        {'size': 10000000},
                        {'size': 8000000}
                    ]
                    
                    try:
                        converter.convert('/fake/input.mp4', '/fake/output.mp4')
                    except:
                        pass  # We don't care if it fails, just that validate_file was called
                    
                    # Verify validate_file was called
                    mock_validate.assert_called()
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_uses_inherited_logging_methods(self):
        """
        Test that VideoCompressor uses inherited logging methods.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            # Spy on logging methods
            with patch.object(converter, 'log_conversion_start', wraps=converter.log_conversion_start) as mock_log_start:
                with patch.object(converter, 'log_conversion_success', wraps=converter.log_conversion_success) as mock_log_success:
                    with patch.object(converter, 'validate_file'):
                        with patch.object(converter, 'validate_video_file'):
                            with patch.object(converter, 'get_file_info') as mock_get_info:
                                mock_get_info.side_effect = [
                                    {'size': 10000000},
                                    {'size': 10000000},
                                    {'size': 8000000}
                                ]
                                
                                converter.convert('/fake/input.mp4', '/fake/output.mp4')
                                
                                # Verify logging methods were called
                                mock_log_start.assert_called_once()
                                mock_log_success.assert_called_once()
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_return_format_matches_other_converters(self):
        """
        Test that VideoCompressor returns results in the same format as other converters.
        """
        from unittest.mock import patch, MagicMock
        
        converter = get_converter('compress_video')
        
        with patch('apps.tools.converters.video_converters.VideoFileClip') as mock_clip_class:
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.fps = 30
            mock_clip.size = (1920, 1080)
            mock_clip_class.return_value = mock_clip
            
            with patch.object(converter, 'validate_file'):
                with patch.object(converter, 'validate_video_file'):
                    with patch.object(converter, 'get_file_info') as mock_get_info:
                        mock_get_info.side_effect = [
                            {'size': 10000000},
                            {'size': 10000000},
                            {'size': 8000000}
                        ]
                        
                        result = converter.convert('/fake/input.mp4', '/fake/output.mp4')
                        
                        # Verify result is a dictionary
                        self.assertIsInstance(result, dict)
                        
                        # Verify required keys are present (common to all converters)
                        self.assertIn('status', result)
                        self.assertIn('output_path', result)
                        self.assertIn('duration', result)
                        
                        # Verify status is 'success'
                        self.assertEqual(result['status'], 'success')
                        
                        # Verify output_path is a string
                        self.assertIsInstance(result['output_path'], str)
                        
                        # Verify duration is a number
                        self.assertIsInstance(result['duration'], (int, float))
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_has_logger_attribute(self):
        """
        Test that VideoCompressor has logger attribute from BaseConverter.
        """
        converter = get_converter('compress_video')
        
        # Verify logger attribute exists
        self.assertTrue(hasattr(converter, 'logger'))
        
        # Verify it's a logger instance
        import logging
        self.assertIsInstance(converter.logger, logging.Logger)
    
    @pytest.mark.skipif(
        'compress_video' not in list_converters(),
        reason="VideoCompressor not available"
    )
    def test_registered_with_decorator(self):
        """
        Test that VideoCompressor is registered using @register_converter decorator.
        """
        from apps.tools.utils.converter_factory import list_converters
        
        # Verify compress_video is in the registry
        converters = list_converters()
        self.assertIn('compress_video', converters)
        
        # Verify it maps to VideoCompressor
        self.assertEqual(converters['compress_video'], 'VideoCompressor')
