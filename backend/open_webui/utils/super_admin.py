import os
from typing import List, Set


def _get_super_admin_emails() -> Set[str]:
    """
    Get super admin emails from environment variable.
    Environment variable format: comma-separated emails (e.g., "email1@nyu.edu,email2@nyu.edu")
    Falls back to default list if env var is not set.
    """
    env_emails = os.environ.get("SUPER_ADMIN_EMAILS", "").strip()
    
    if env_emails:
        # Parse comma-separated emails, strip whitespace, and convert to lowercase for comparison
        emails = [email.strip().lower() for email in env_emails.split(",") if email.strip()]
        return set(emails)
    else:
        # Fallback to default list for backward compatibility
        default_emails = [
            "sm11538@nyu.edu",
            "ms15138@nyu.edu", 
            "mb484@nyu.edu",
            "cg4532@nyu.edu",
            "ht2490@nyu.edu",
            "ps5226@nyu.edu"
        ]
        return set(email.lower() for email in default_emails)


def get_super_admin_emails() -> List[str]:
    """
    Get list of super admin emails (for API responses).
    Returns emails in their original case as stored in env var or default list.
    """
    env_emails = os.environ.get("SUPER_ADMIN_EMAILS", "").strip()
    
    if env_emails:
        emails = [email.strip() for email in env_emails.split(",") if email.strip()]
        return emails
    else:
        # Fallback to default list
        return [
            "sm11538@nyu.edu",
            "ms15138@nyu.edu", 
            "mb484@nyu.edu",
            "cg4532@nyu.edu",
            "ht2490@nyu.edu",
            "ps5226@nyu.edu"
        ]


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