from typing import Optional, Union, List, Dict, Any
from open_webui.apps.webui.models.groups import Groups
import json

from open_webui.config import (
    ALLOW_ALL_MODELS_TO_USERS,
)

def check_model_access(
    role: str,
) -> bool:
    """
    Checks the user role, and returns true, if the user is of role "user"
    and the global env var "ALLOW_ALL_MODELS_TO_USERS" is false.
    """
    return role == "user" and not ALLOW_ALL_MODELS_TO_USERS