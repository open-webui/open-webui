"""
SSRF Protection Module

This module provides Server-Side Request Forgery (SSRF) protection for web fetching functionality.
It validates URLs against known dangerous targets like cloud metadata endpoints, and supports
configurable blocklists for custom deployment scenarios.
"""

import logging
import ipaddress
import socket
from urllib.parse import urlparse
from typing import List, Optional

log = logging.getLogger(__name__)


# Default blocklist of known dangerous targets
DEFAULT_BLOCKED_HOSTNAMES = [
    # AWS Metadata (IPv4)
    "169.254.169.254",
    # AWS Metadata (IPv6)
    "fd00:ec2::254",
    # GCP Metadata
    "metadata.google.internal",
    "metadata.goog",
    # Azure Metadata
    "169.254.169.254",
    # Alibaba Cloud Metadata
    "100.100.100.200",
    # Oracle Cloud Metadata
    "169.254.169.254",
    # DigitalOcean Metadata
    "169.254.169.254",
]

# Default blocked IP ranges (represented as CIDR notation)
DEFAULT_BLOCKED_IP_RANGES = [
    # These are commented out by default to preserve backward compatibility
    # Admins can enable them via configuration
    # "127.0.0.0/8",      # Loopback
    # "::1/128",          # IPv6 loopback
    # "10.0.0.0/8",       # Private network
    # "172.16.0.0/12",    # Private network
    # "192.168.0.0/16",   # Private network
    # "169.254.0.0/16",   # Link-local
    # "fe80::/10",        # IPv6 link-local
]


class SSRFProtectionError(Exception):
    """Exception raised when SSRF protection blocks a URL"""

    pass


def is_ip_in_blocked_ranges(ip_str: str, blocked_ranges: List[str]) -> bool:
    """
    Check if an IP address is in any of the blocked ranges.

    Args:
        ip_str: IP address as a string
        blocked_ranges: List of CIDR notation strings representing blocked IP ranges

    Returns:
        True if the IP is in a blocked range, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        for blocked_range in blocked_ranges:
            if ip in ipaddress.ip_network(blocked_range, strict=False):
                return True
        return False
    except (ValueError, ipaddress.AddressValueError):
        return False


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolve a hostname to an IP address.

    Args:
        hostname: The hostname to resolve

    Returns:
        IP address as a string, or None if resolution fails
    """
    try:
        return socket.gethostbyname(hostname)
    except (socket.gaierror, socket.error) as e:
        log.debug(f"Failed to resolve hostname {hostname}: {e}")
        return None


def validate_url_against_ssrf(
    url: str,
    enable_protection: bool = True,
    blocked_hostnames: Optional[List[str]] = None,
    blocked_ip_ranges: Optional[List[str]] = None,
    allowed_schemes: Optional[List[str]] = None,
) -> None:
    """
    Validate a URL against SSRF protection rules.

    Args:
        url: The URL to validate
        enable_protection: Whether SSRF protection is enabled
        blocked_hostnames: List of blocked hostnames (uses defaults if None)
        blocked_ip_ranges: List of blocked IP ranges in CIDR notation (uses defaults if None)
        allowed_schemes: List of allowed URL schemes (defaults to ['http', 'https'])

    Raises:
        SSRFProtectionError: If the URL is blocked by SSRF protection rules
        ValueError: If the URL is malformed
    """
    if not enable_protection:
        return

    if not url:
        raise ValueError("URL cannot be empty")

    # Use defaults if not provided
    if blocked_hostnames is None:
        blocked_hostnames = DEFAULT_BLOCKED_HOSTNAMES

    if blocked_ip_ranges is None:
        blocked_ip_ranges = DEFAULT_BLOCKED_IP_RANGES

    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    # Validate scheme
    if parsed.scheme.lower() not in allowed_schemes:
        raise SSRFProtectionError(
            f"URL scheme '{parsed.scheme}' is not allowed. Only {', '.join(allowed_schemes)} are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a hostname")

    # Normalize hostname to lowercase for comparison
    hostname_lower = hostname.lower()

    # Check if hostname is in blocked list
    for blocked in blocked_hostnames:
        if hostname_lower == blocked.lower():
            raise SSRFProtectionError(
                f"Access to '{hostname}' is blocked by SSRF protection. "
                "This target is identified as a sensitive endpoint (e.g., cloud metadata service)."
            )

    # Check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        # Check if IP is in blocked ranges
        if is_ip_in_blocked_ranges(str(ip), blocked_ip_ranges):
            raise SSRFProtectionError(
                f"Access to IP address '{hostname}' is blocked by SSRF protection. "
                "This IP is in a blocked range."
            )
    except ValueError:
        # Not a direct IP address, need to resolve hostname
        resolved_ip = resolve_hostname(hostname)
        if resolved_ip:
            # Check if resolved IP is in blocked ranges
            if is_ip_in_blocked_ranges(resolved_ip, blocked_ip_ranges):
                raise SSRFProtectionError(
                    f"Access to '{hostname}' (resolves to {resolved_ip}) is blocked by SSRF protection. "
                    "The resolved IP is in a blocked range."
                )

            # Double-check against blocked hostnames in case it's a metadata hostname
            for blocked in blocked_hostnames:
                try:
                    blocked_ip = resolve_hostname(blocked)
                    if blocked_ip and resolved_ip == blocked_ip:
                        raise SSRFProtectionError(
                            f"Access to '{hostname}' is blocked by SSRF protection. "
                            "This hostname resolves to a blocked endpoint."
                        )
                except Exception:
                    continue

    log.debug(f"URL '{url}' passed SSRF protection validation")


def parse_blocklist_from_env(env_value: str) -> List[str]:
    """
    Parse a comma-separated blocklist from an environment variable.

    Args:
        env_value: Comma-separated string of hostnames or IPs

    Returns:
        List of parsed values, with empty strings filtered out
    """
    if not env_value:
        return []

    return [item.strip() for item in env_value.split(",") if item.strip()]
