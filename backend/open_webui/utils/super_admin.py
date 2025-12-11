import os
from typing import List, Set

# Default super admin email - used if SUPER_ADMIN_EMAILS env var is not set
DEFAULT_SUPER_ADMIN_EMAIL = "ms15138@nyu.edu"


def _get_super_admin_emails() -> Set[str]:
    """
    Get super admin emails from environment variable.
    Environment variable format: comma-separated emails (e.g., "email1@nyu.edu,email2@nyu.edu")
    
    If SUPER_ADMIN_EMAILS is not set, defaults to DEFAULT_SUPER_ADMIN_EMAIL (ms15138@nyu.edu).
    """
    env_emails = os.environ.get("SUPER_ADMIN_EMAILS", "").strip()
    
    if env_emails:
        # Parse comma-separated emails, strip whitespace, and convert to lowercase for comparison
        emails = [email.strip().lower() for email in env_emails.split(",") if email.strip()]
        return set(emails)
    else:
        # Use default super admin email
        return {DEFAULT_SUPER_ADMIN_EMAIL.lower()}


def get_super_admin_emails() -> List[str]:
    """
    Get list of super admin emails (for API responses).
    Returns emails in their original case.
    
    If SUPER_ADMIN_EMAILS is not set, defaults to DEFAULT_SUPER_ADMIN_EMAIL (ms15138@nyu.edu).
    """
    env_emails = os.environ.get("SUPER_ADMIN_EMAILS", "").strip()
    
    if env_emails:
        emails = [email.strip() for email in env_emails.split(",") if email.strip()]
        return emails
    else:
        # Use default super admin email
        return [DEFAULT_SUPER_ADMIN_EMAIL]


def is_super_admin(user) -> bool:
    """Check if user is super admin based on existing logic"""
    from open_webui.models.users import Users
    
    if not user:
        return False
    
    super_admin_emails = _get_super_admin_emails()
    
    first_user = Users.get_first_user()
    is_first_user = first_user is not None and user.id == first_user.id
    
    return (
        is_first_user or 
        (user.email and user.email.lower() in super_admin_emails)
    )


def is_email_super_admin(email) -> bool:
    """
    Check if an email address belongs to a super admin.
    Case-insensitive comparison.
    """
    if not email:
        return False
    super_admin_emails = _get_super_admin_emails()
    return email.lower() in super_admin_emails