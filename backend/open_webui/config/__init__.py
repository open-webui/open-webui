from .base import *
from .logging import *
from .database import *

from .llm import *
from .auth import *
from .legacy import *

setup_logging()

run_migrations()
migrate_legacy_config()
