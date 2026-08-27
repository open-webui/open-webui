"""
Thin HTTP/back-compat shim for the Ollama engine.

The engine implementation now lives in `open_webui.inference.ollama`. This
module only re-exports it so code importing from the old router path keeps
working, and so `main.py` can still mount the `/ollama` router.
"""

from open_webui.inference.ollama import *  # noqa: F401,F403
from open_webui.inference.ollama import router  # noqa: F401