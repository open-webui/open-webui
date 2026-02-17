
1) in src/lib/constants.ts

        export const APP_NAME = 'Geomas';

2) IN backend/open_webui/env.py
line 93 
remove or comment:
if WEBUI_NAME != "Open WebUI":
    WEBUI_NAME += " (Open WebUI)"


3) update reqs
pip install strenum

4) backend/open_webui/utils/plugin.py
add return at the start of last two functions

5) backend/open_webui/retrieval/vector/type.py
try:
    from enum import StrEnum  # Python 3.11+
except ImportError:
    from strenum import StrEnum  # Backport for older Python

6) replace images in:

    1) static/
    2) static/static
    3) backend/open_webui/static
7) yarn run build 

