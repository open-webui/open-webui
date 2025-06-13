from typing import Optional
import hashlib
from open_webui.models.users import User
from open_webui.env import (
    IONOS_USER_ID_PSEUDONYMIZATION_SALT,
)

def pseudonymized_user_id(user: User) -> Optional[str]:
    """
    Generate pseudonymized user ID for aggregation in surveys
    """

    if not IONOS_USER_ID_PSEUDONYMIZATION_SALT:
        return None
    salted = f"{user.id}{IONOS_USER_ID_PSEUDONYMIZATION_SALT}"
    return hashlib.md5(salted.encode("ascii")).hexdigest()
