from .core import *
from .integrations import *
from .features import *

setup_logging()

run_migrations()
migrate_legacy_config()
