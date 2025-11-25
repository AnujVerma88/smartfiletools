"""
IP Whitelist Management Utilities.
Provides functions for managing and validating IP whitelists for API keys.
"""
import ipaddress
import logging

logger = logging.getLogger('apps.api')


def validate_ip_address(ip_string):
    """
    Validate if a string is a valid IP address (IPv4 or IPv6).
    
    Args:
        ip_string: IP address string to validate
        
    Returns:
        tuple: (is_valid: bool, normalized_ip: str or None, error: str or None)
    """
    try:
        # Try to parse as IP address
        ip_obj = ipaddress.ip_address(ip_string.strip())
        return True, str(ip_obj), None
    except ValueError as e:
        return False, None, str(e)


def validate_ip_network(network_string):
    """
    Validate if a string is a valid IP network (CIDR notation).
    
    Args:
        network_string: IP network string to validate (e.g., "192.168.1.0/24")
        
    Returns:
        tuple: (is_valid: bool, normalized_network: str or None, error: str or None)
    """
    try:
        # Try to parse as IP network
        network_obj = ipaddress.ip_network(network_string.strip(), strict=False)
        return True, str(network_obj), None
    except ValueError as e:
        return False, None, str(e)


def is_ip_in_whitelist(ip_address, whitelist):
    """
    Check if an IP address is in the whitelist.
    Supports both individual IPs and CIDR ranges.
    
    Args:
        ip_address: IP address to check (string)
        whitelist: List of allowed IPs/networks (strings)
        
    Returns:
        bool: True if IP is in whitelist
    """
    if not whitelist:
        # Empty whitelist means all IPs are allowed
        return True
    
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        
        for allowed in whitelist:
            try:
                # Try as individual IP first
                if ipaddress.ip_address(allowed) == ip_obj:
                    return True
            except ValueError:
                # Try as network/CIDR range
                try:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if ip_obj in network:
                        return True
                except ValueError:
                    logger.warning(f"Invalid IP/network in whitelist: {allowed}")
                    continue
        
        return False
        
    except ValueError as e:
        logger.error(f"Invalid IP address to check: {ip_address} - {str(e)}")
        return False


def add_ip_to_whitelist(api_key, ip_address):
    """
    Add an IP address to an API key's whitelist.
    
    Args:
        api_key: APIKey object
        ip_address: IP address or network to add
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate IP
    is_valid, normalized_ip, error = validate_ip_address(ip_address)
    
    if not is_valid:
        # Try as network
        is_valid, normalized_ip, error = validate_ip_network(ip_address)
        
        if not is_valid:
            return False, f"Invalid IP address or network: {error}"
    
    # Initialize whitelist if None
    if api_key.allowed_ips is None:
        api_key.allowed_ips = []
    
    # Check if already in whitelist
    if normalized_ip in api_key.allowed_ips:
        return False, f"IP {normalized_ip} is already in the whitelist"
    
    # Add to whitelist
    api_key.allowed_ips.append(normalized_ip)
    api_key.save(update_fields=['allowed_ips'])
    
    logger.info(
        f"IP {normalized_ip} added to whitelist for API key {api_key.id} "
        f"(Merchant: {api_key.merchant.company_name})"
    )
    
    return True, f"IP {normalized_ip} added to whitelist successfully"


def remove_ip_from_whitelist(api_key, ip_address):
    """
    Remove an IP address from an API key's whitelist.
    
    Args:
        api_key: APIKey object
        ip_address: IP address or network to remove
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if not api_key.allowed_ips:
        return False, "Whitelist is empty"
    
    if ip_address not in api_key.allowed_ips:
        return False, f"IP {ip_address} is not in the whitelist"
    
    # Remove from whitelist
    api_key.allowed_ips.remove(ip_address)
    api_key.save(update_fields=['allowed_ips'])
    
    logger.info(
        f"IP {ip_address} removed from whitelist for API key {api_key.id} "
        f"(Merchant: {api_key.merchant.company_name})"
    )
    
    return True, f"IP {ip_address} removed from whitelist successfully"


def clear_whitelist(api_key):
    """
    Clear all IPs from an API key's whitelist.
    This allows all IPs to access the API key.
    
    Args:
        api_key: APIKey object
        
    Returns:
        tuple: (success: bool, message: str)
    """
    api_key.allowed_ips = []
    api_key.save(update_fields=['allowed_ips'])
    
    logger.info(
        f"Whitelist cleared for API key {api_key.id} "
        f"(Merchant: {api_key.merchant.company_name})"
    )
    
    return True, "Whitelist cleared successfully. All IPs are now allowed."


def get_whitelist_info(api_key):
    """
    Get information about an API key's whitelist.
    
    Args:
        api_key: APIKey object
        
    Returns:
        dict: Whitelist information
    """
    whitelist = api_key.allowed_ips or []
    
    return {
        'enabled': len(whitelist) > 0,
        'count': len(whitelist),
        'ips': whitelist,
        'allows_all': len(whitelist) == 0,
    }


def validate_whitelist_format(whitelist):
    """
    Validate a list of IPs/networks for whitelist format.
    
    Args:
        whitelist: List of IP addresses/networks
        
    Returns:
        tuple: (is_valid: bool, errors: list, normalized: list)
    """
    errors = []
    normalized = []
    
    for ip_string in whitelist:
        # Try as IP address
        is_valid, normalized_ip, error = validate_ip_address(ip_string)
        
        if is_valid:
            normalized.append(normalized_ip)
            continue
        
        # Try as network
        is_valid, normalized_network, error = validate_ip_network(ip_string)
        
        if is_valid:
            normalized.append(normalized_network)
            continue
        
        # Invalid
        errors.append(f"{ip_string}: {error}")
    
    return len(errors) == 0, errors, normalized


def get_client_ip_info(request):
    """
    Get detailed information about the client's IP address.
    
    Args:
        request: Django request object
        
    Returns:
        dict: IP information
    """
    from apps.api.utils import get_client_ip
    
    client_ip = get_client_ip(request)
    
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        
        return {
            'ip': client_ip,
            'version': ip_obj.version,
            'is_private': ip_obj.is_private,
            'is_loopback': ip_obj.is_loopback,
            'is_multicast': ip_obj.is_multicast,
            'is_global': ip_obj.is_global,
        }
    except ValueError:
        return {
            'ip': client_ip,
            'error': 'Invalid IP address',
        }


# Common IP ranges for reference
COMMON_IP_RANGES = {
    'localhost': ['127.0.0.0/8', '::1/128'],
    'private_ipv4': ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'],
    'private_ipv6': ['fc00::/7', 'fe80::/10'],
    'cloudflare': [
        '173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22',
        '103.31.4.0/22', '141.101.64.0/18', '108.162.192.0/18',
        '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22',
        '198.41.128.0/17', '162.158.0.0/15', '104.16.0.0/13',
        '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22'
    ],
}


def suggest_ip_ranges(context='general'):
    """
    Suggest common IP ranges based on context.
    
    Args:
        context: Context for suggestions ('localhost', 'private', 'cloudflare', etc.)
        
    Returns:
        list: Suggested IP ranges
    """
    if context in COMMON_IP_RANGES:
        return COMMON_IP_RANGES[context]
    
    return []
