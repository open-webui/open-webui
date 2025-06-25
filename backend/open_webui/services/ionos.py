from typing import Optional
import hashlib
from open_webui.models.users import User
from open_webui.env import (
    IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX,
    IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX,
)

def get_oauth_sub(user: User) -> str:
    """
    Parse oauth_sub from User model and return the sub ID
    Format oidc@<UUID>
    """
    oauth_sub = user.oauth_sub

    if not oauth_sub:
        raise Exception("No oauth_sub found for user")

    parts = oauth_sub.split("@")

    if len(parts) < 2:
        raise Exception("User's oauth_sub has unexpected format. Expected <type>@<sub>, but \"@\" is missing")

    sub = parts[1].strip()

    if len(sub) == 0:
        raise Exception("User's oauth_sub has unexpected format: Expected <type>@<sub>, but got empty sub")

    return sub

def pseudonymized_user_id(user: User) -> Optional[str]:
    """
    Generate pseudonymized user ID for aggregation in surveys
    """

    if not IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX or not IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX:
        return None

    if not user.oauth_sub:
        return None

    sub = get_oauth_sub(user)

    salted = f"{IONOS_USER_ID_PSEUDONYMIZATION_SALT_PREFIX}{sub}{IONOS_USER_ID_PSEUDONYMIZATION_SALT_SUFFIX}"
    return hashlib.md5(salted.encode("ascii")).hexdigest()
