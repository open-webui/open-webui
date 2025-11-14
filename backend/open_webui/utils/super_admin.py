SUPER_ADMIN_EMAILS = [
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
    
    return (
        user.id == Users.get_first_user().id or 
        user.email in SUPER_ADMIN_EMAILS
    )

def is_email_super_admin(email) -> bool:
    return email in SUPER_ADMIN_EMAILS