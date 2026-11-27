"""Wait until the local Open WebUI answers, then open it in the default browser."""
import sys
import time
import urllib.request
import webbrowser

port = sys.argv[1] if len(sys.argv) > 1 else "8080"
for _ in range(900):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
        break
    except Exception:
        time.sleep(1)
webbrowser.open(f"http://localhost:{port}")
