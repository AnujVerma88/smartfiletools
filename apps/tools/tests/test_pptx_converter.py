"""
Property-based tests for PPTX to PDF converter.

Feature: pptx-to-pdf-quality-improvement
"""
import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock, Mock
from hypothesis import given, strategies as st, settings
from pathlib import Path

from apps.tools.converters.pdf_converters import PPTXToPDFConverter
from apps.tools.utils.base_converter import ConversionError


class TestPPTXConverterMethodSelection(unittest.TestCase):
    """
    Property-based tests for PPTX converter method selection.
    """
    
    @settings(max_examples=100)
    @given(
        powerpoint_available=st.booleans(),
        libreoffice_available=st.booleans(),
    )
    def test_method_selection_on_windows(self, powerpoint_available, libreoffice_available):
        """
        Feature: pptx-to-pdf-quality-improvement, Property 4: Method selection on Windows
        
        For any conversion on Windows platform, when PowerPoint is available, 
        COM automation must be attempted first; when PowerPoint is unavailable 
        but LibreOffice is available, LibreOffice must be used.
        
        **Validates: Requirements 2.1, 2.2, 4.1**
        """
        # Mock platform detection to return Windows
        with patch('apps.tools.utils.platform_utils.get_platform', return_value='windows'):
            with patch('apps.tools.utils.platform_utils.is_powerpoint_available', return_value=powerpoint_available):
                with patch('apps.tools.utils.platform_utils.is_libreoffice_available', return_value=libreoffice_available):
                    
                    from apps.tools.utils.platform_utils import get_available_conversion_method
                    
                    # Get the method that should be selected
                    method = get_available_conversion_method()
                    
                    # Verify correct method selection on Windows
                    if powerpoint_available:
                        self.assertEqual(
                            method, 'powerpoint',
                            "On Windows with PowerPoint available, should select 'powerpoint'"
                        )
                    elif libreoffice_available:
                        self.assertEqual(
                            method, 'libreoffice',
                            "On Windows without PowerPoint but with LibreOffice, should select 'libreoffice'"
                        )
                    else:
                        self.assertEqual(
                            method, 'none',
                            "On Windows without any tools, should return 'none'"
                        )


class TestPowerPointCOMConversion(unittest.TestCase):
    """
    Unit tests for PowerPoint COM automation conversion method.
    """
    
    def test_convert_with_powerpoint_success(self):
        """
        Test that _convert_with_powerpoint successfully converts a PPTX file.
        """
        converter = PPTXToPDFConverter()
        
        # Create temporary paths
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as input_file:
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Mock win32com.client
            mock_powerpoint = MagicMock()
            mock_presentation = MagicMock()
            mock_powerpoint.Presentations.Open.return_value = mock_presentation
            
            with patch('win32com.client.Dispatch', return_value=mock_powerpoint):
                # Call the conversion method
                converter._convert_with_powerpoint(input_path, output_path)
                
                # Verify PowerPoint was dispatched
                mock_powerpoint.Presentations.Open.assert_called_once()
                
                # Verify SaveAs was called with PDF format (32)
                mock_presentation.SaveAs.assert_called_once()
                call_args = mock_presentation.SaveAs.call_args
                # Check if FileFormat=32 was passed (either as positional or keyword arg)
                if len(call_args[0]) > 1:
                    self.assertEqual(call_args[0][1], 32, "Should save with FileFormat=32 (PDF)")
                else:
                    self.assertEqual(call_args[1].get('FileFormat'), 32, "Should save with FileFormat=32 (PDF)")
                
                # Verify cleanup was called
                mock_presentation.Close.assert_called_once()
                mock_powerpoint.Quit.assert_called_once()
        
        finally:
            # Clean up temp files
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_convert_with_powerpoint_cleanup_on_error(self):
        """
        Test that _convert_with_powerpoint cleans up COM objects even on error.
        """
        converter = PPTXToPDFConverter()
        
        # Create temporary paths
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as input_file:
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Mock win32com.client to raise an error during SaveAs
            mock_powerpoint = MagicMock()
            mock_presentation = MagicMock()
            mock_presentation.SaveAs.side_effect = Exception("SaveAs failed")
            mock_powerpoint.Presentations.Open.return_value = mock_presentation
            
            with patch('win32com.client.Dispatch', return_value=mock_powerpoint):
                # Call should raise ConversionError
                with self.assertRaises(ConversionError):
                    converter._convert_with_powerpoint(input_path, output_path)
                
                # Verify cleanup was still called
                mock_presentation.Close.assert_called_once()
                mock_powerpoint.Quit.assert_called_once()
        
        finally:
            # Clean up temp files
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == '__main__':
    unittest.main()
