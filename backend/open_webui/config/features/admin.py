import os
from open_webui.config.core.base import PersistentConfig

####################################
# ADMIN CONFIGURATION
####################################

ENABLE_ADMIN_EXPORT = os.environ.get("ENABLE_ADMIN_EXPORT", "True").lower() == "true"

ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS = (
    os.environ.get("ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS", "True").lower() == "true"
)

BYPASS_ADMIN_ACCESS_CONTROL = (
    os.environ.get(
        "BYPASS_ADMIN_ACCESS_CONTROL",
        os.environ.get("ENABLE_ADMIN_WORKSPACE_CONTENT_ACCESS", "True"),
    ).lower()
    == "true"
)

ENABLE_ADMIN_CHAT_ACCESS = (
    os.environ.get("ENABLE_ADMIN_CHAT_ACCESS", "True").lower() == "true"
)

SHOW_ADMIN_DETAILS = PersistentConfig(
    "SHOW_ADMIN_DETAILS",
    "auth.admin.show",
    os.environ.get("SHOW_ADMIN_DETAILS", "true").lower() == "true",
)

ADMIN_EMAIL = PersistentConfig(
    "ADMIN_EMAIL",
    "auth.admin.email",
    os.environ.get("ADMIN_EMAIL", None),
)
