from typing import Optional
import logging
import sys
from open_webui.models.tenants import Tenants
from open_webui.models.users import UserModel
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

DEFAULT_MODEL = "lux_docquestion"


def _all_model_names() -> list[str]:
    models = Tenants.get_all_model_names()
    return models if models else [DEFAULT_MODEL]


def get_luxtronic_model_names(
    user: Optional[UserModel] = None, restrict_to_user: bool = False
) -> list[str]:
    log.info(f"GETTING MODEL NNAMES user: {user}")
    if restrict_to_user:
        if not user or user.role == "admin":
            return _all_model_names()
        if not user.tenant_id:
            return []
        result = Tenants.get_model_names_for_tenant(user.tenant_id) or []
        log.info(f"Tenants.get_model_names_for_tenant({user.tenant_id}): {result}")
        return result

    return _all_model_names()


def user_can_access_lux_model(user: Optional[UserModel], model_id: str) -> bool:
    if not model_id.startswith("luxor:"):
        return True
    if not user or user.role == "admin":
        return True
    allowed = set(get_luxtronic_model_names(user, restrict_to_user=True))
    if not allowed:
        return False
    _, _, name = model_id.partition(":")
    return name in allowed
