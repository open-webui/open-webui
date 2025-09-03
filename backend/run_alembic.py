import os
import subprocess
import sys

sys.path.append("/app")

os.chdir("/app/backend/open_webui")
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"])
