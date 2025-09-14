from .legacy import *
from .logging import setup_logging
from .database import (
    run_migrations,
    migrate_legacy_config,
    save_to_db,
    reset_config,
    get_config,
)
from .base import (
    PERSISTENT_CONFIG_REGISTRY,
    CONFIG_DATA,
    ENABLE_OAUTH_PERSISTENT_CONFIG,
    PersistentConfig,
    ENABLE_PERSISTENT_CONFIG,
    AppConfig,
    save_config,
)

setup_logging()

run_migrations()
migrate_legacy_config()
