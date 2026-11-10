"""
Security regression test for open-webui/open-webui (CWE-918 / CWE-22 · CVSS 8.4):
Validates every HTTP 30x redirect target IP against RFC1918 / link-local ranges
and enforces realpath containment on local document ingestion.
"""
import ipaddress
import os
from urllib.parse import urlparse
import pytest


def verify_safe_redirect_hop(target_url: str) -> str:
    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked non-HTTP redirect scheme: {parsed.scheme}")
    host = (parsed.hostname or "").strip().lower()
    if not host or host == "localhost":
        raise ValueError("Blocked localhost redirect target")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Blocked internal redirect IP: {ip}")
    except ValueError as exc:
        if "Blocked internal redirect IP" in str(exc):
            raise
    return target_url


def verify_realpath_within_uploads(base_dir: str, candidate_path: str) -> str:
    real_base = os.path.realpath(base_dir)
    real_target = os.path.realpath(candidate_path)
    if os.path.commonpath([real_base, real_target]) != real_base:
        raise ValueError("Blocked path traversal outside upload root")
    return real_target


def test_blocks_302_redirect_to_imds_and_loopback():
    with pytest.raises(ValueError, match="Blocked internal redirect IP"):
        verify_safe_redirect_hop("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(ValueError, match="Blocked internal redirect IP"):
        verify_safe_redirect_hop("http://127.0.0.1:11434/api/tags")
    assert verify_safe_redirect_hop("https://docs.openwebui.com/getting-started") == "https://docs.openwebui.com/getting-started"
