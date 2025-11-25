"""
Property-based tests for platform detection and tool availability utilities.

Feature: pptx-to-pdf-quality-improvement
"""
import unittest
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings
import platform

from apps.tools.utils.platform_utils import (
    get_platform,
    is_powerpoint_available,
    is_libreoffice_available,
    get_libreoffice_path,
    get_available_conversion_method,
)


class TestPlatformDetection(unittest.TestCase):
    """
    Property-based tests for platform detection utilities.
    """
    
    @settings(max_examples=100)
    @given(
        platform_system=st.sampled_from(['Windows', 'Linux', 'Darwin', 'FreeBSD', 'SunOS']),
        powerpoint_available=st.booleans(),
        libreoffice_available=st.booleans(),
    )
    def test_platform_appropriate_method_selection(
        self, platform_system, powerpoint_available, libreoffice_available
    ):
        """
        Feature: pptx-to-pdf-quality-improvement, Property 6: Platform-appropriate method selection
        
        For any platform and tool availability combination, the converter must select 
        a valid conversion method or raise an appropriate error.
        
        **Validates: Requirements 4.3**
        """
        with patch('platform.system', return_value=platform_system):
            with patch('apps.tools.utils.platform_utils.is_powerpoint_available', return_value=powerpoint_available):
                with patch('apps.tools.utils.platform_utils.is_libreoffice_available', return_value=libreoffice_available):
                    
                    # Get the detected platform
                    detected_platform = get_platform()
                    
                    # Verify platform detection returns valid values
                    self.assertIn(
                        detected_platform,
                        ['windows', 'linux', 'mac', 'unknown'],
                        f"Platform detection returned invalid value: {detected_platform}"
                    )
                    
                    # Get the available conversion method
                    method = get_available_conversion_method()
                    
                    # Verify method is one of the valid options
                    self.assertIn(
                        method,
                        ['powerpoint', 'libreoffice', 'none'],
                        f"Invalid conversion method returned: {method}"
                    )
                    
                    # Verify platform-specific logic
                    if detected_platform == 'windows':
                        # On Windows, PowerPoint should be preferred if available
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
                    
                    elif detected_platform in ['linux', 'mac']:
                        # On Linux/Mac, only LibreOffice is available
                        if libreoffice_available:
                            self.assertEqual(
                                method, 'libreoffice',
                                f"On {detected_platform} with LibreOffice available, should select 'libreoffice'"
                            )
                        else:
                            self.assertEqual(
                                method, 'none',
                                f"On {detected_platform} without LibreOffice, should return 'none'"
                            )
                    
                    else:
                        # Unknown platforms should return 'none'
                        self.assertEqual(
                            method, 'none',
                            "Unknown platforms should return 'none'"
                        )


if __name__ == '__main__':
    unittest.main()
