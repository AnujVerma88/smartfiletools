"""
Platform detection and tool availability utilities for PPTX to PDF conversion.
"""
import os
import platform
import logging
from pathlib import Path

logger = logging.getLogger('apps.tools')


def get_platform():
    """
    Detect the operating system platform.
    
    Returns:
        str: Platform identifier ('windows', 'linux', 'mac', or 'unknown')
    """
    system = platform.system()
    if system == 'Windows':
        return 'windows'
    elif system == 'Linux':
        return 'linux'
    elif system == 'Darwin':
        return 'mac'
    return 'unknown'


def is_powerpoint_available():
    """
    Check if Microsoft PowerPoint is available via COM automation.
    Only works on Windows.
    
    Returns:
        bool: True if PowerPoint is available, False otherwise
    """
    if get_platform() != 'windows':
        return False
    
    try:
        import win32com.client
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        # Try to access a property to verify it's working
        _ = powerpoint.Version
        powerpoint.Quit()
        return True
    except Exception as e:
        logger.debug(f"PowerPoint not available: {str(e)}")
        return False


def is_libreoffice_available():
    """
    Check if LibreOffice is available on the system.
    
    Returns:
        bool: True if LibreOffice is available, False otherwise
    """
    libreoffice_path = get_libreoffice_path()
    return libreoffice_path is not None


def get_libreoffice_path():
    """
    Locate the LibreOffice executable on the system.
    Searches common installation paths for different platforms.
    
    Returns:
        str or None: Path to LibreOffice executable if found, None otherwise
    """
    current_platform = get_platform()
    
    # Define common LibreOffice paths for each platform
    search_paths = []
    
    if current_platform == 'windows':
        search_paths = [
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
            r'C:\Program Files\LibreOffice 7\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice 7\program\soffice.exe',
        ]
    elif current_platform == 'linux':
        search_paths = [
            '/usr/bin/libreoffice',
            '/usr/bin/soffice',
            '/usr/local/bin/libreoffice',
            '/usr/local/bin/soffice',
            '/snap/bin/libreoffice',
        ]
    elif current_platform == 'mac':
        search_paths = [
            '/Applications/LibreOffice.app/Contents/MacOS/soffice',
            '/usr/local/bin/libreoffice',
            '/usr/local/bin/soffice',
        ]
    
    # Check each path
    for path in search_paths:
        if os.path.exists(path) and os.path.isfile(path):
            logger.debug(f"Found LibreOffice at: {path}")
            return path
    
    # Try to find in PATH
    import shutil
    for executable in ['libreoffice', 'soffice']:
        path = shutil.which(executable)
        if path:
            logger.debug(f"Found LibreOffice in PATH: {path}")
            return path
    
    logger.debug("LibreOffice not found on system")
    return None


def get_available_conversion_method():
    """
    Determine which conversion method is available on the current platform.
    
    Returns:
        str: 'powerpoint', 'libreoffice', or 'none'
    """
    current_platform = get_platform()
    
    # On Windows, try PowerPoint first, then LibreOffice
    if current_platform == 'windows':
        if is_powerpoint_available():
            return 'powerpoint'
        elif is_libreoffice_available():
            return 'libreoffice'
    # On Linux/Mac, only LibreOffice is available
    elif current_platform in ['linux', 'mac']:
        if is_libreoffice_available():
            return 'libreoffice'
    
    return 'none'
