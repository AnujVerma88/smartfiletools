"""
Converter factory for getting the appropriate converter based on tool type.
"""
import logging

logger = logging.getLogger('apps.tools')


class ConverterRegistry:
    """
    Registry for managing converter classes.
    Allows dynamic registration and retrieval of converters.
    """
    
    def __init__(self):
        self._converters = {}
    
    def register(self, tool_type, converter_class):
        """
        Register a converter class for a specific tool type.
        
        Args:
            tool_type: Tool type identifier (e.g., 'pdf_to_docx')
            converter_class: Converter class to register
        """
        self._converters[tool_type] = converter_class
        logger.debug(f"Registered converter: {tool_type} -> {converter_class.__name__}")
    
    def get(self, tool_type):
        """
        Get converter class for a tool type.
        
        Args:
            tool_type: Tool type identifier
            
        Returns:
            Converter class or None if not found
        """
        return self._converters.get(tool_type)
    
    def get_all(self):
        """Get all registered converters."""
        return self._converters.copy()


# Global converter registry
_registry = ConverterRegistry()


def register_converter(tool_type):
    """
    Decorator to register a converter class.
    
    Usage:
        @register_converter('pdf_to_docx')
        class PDFToDocxConverter(BaseConverter):
            pass
    """
    def decorator(converter_class):
        _registry.register(tool_type, converter_class)
        return converter_class
    return decorator


def get_converter(tool_type):
    """
    Get an instance of the appropriate converter for the given tool type.
    
    Args:
        tool_type: Tool type identifier (e.g., 'pdf_to_docx')
        
    Returns:
        Converter instance
        
    Raises:
        ValueError: If no converter is registered for the tool type
    """
    converter_class = _registry.get(tool_type)
    
    if converter_class is None:
        raise ValueError(
            f"No converter registered for tool type: {tool_type}. "
            f"Available converters: {list(_registry.get_all().keys())}"
        )
    
    logger.info(f"Creating converter instance: {converter_class.__name__} for {tool_type}")
    return converter_class()


def list_converters():
    """
    List all registered converters.
    
    Returns:
        dict: Mapping of tool types to converter class names
    """
    return {
        tool_type: converter_class.__name__
        for tool_type, converter_class in _registry.get_all().items()
    }
