def is_super_admin(user) -> bool:
    """Check if user is super admin based on existing logic"""
    from open_webui.models.users import Users
    
    if not user:
        return False
        
    super_admin_emails = [
        "sm11538@nyu.edu",
        "ms15138@nyu.edu", 
        "mb484@nyu.edu",
        "cg4532@nyu.edu"
    ]
    
    return (
        user.id == Users.get_first_user().id or 
        user.email in super_admin_emails
    )