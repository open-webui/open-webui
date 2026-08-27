"""
Thin HTTP/back-compat shim for the OpenAI(-compatible) engine.

The engine implementation now lives in `open_webui.inference.openai`. This
module only re-exports it so code importing from the old router path keeps
working, and so `main.py` can still mount the `/openai` router.
"""

from open_webui.inference.openai import *  # noqa: F401, F403
from open_webui.inference.openai import router  # noqa: F401
