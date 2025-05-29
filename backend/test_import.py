import sys
import os

# Add the backend directory to sys.path to allow direct import of open_webui
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from open_webui.routers.agents import router as agents_router
    print("Successfully imported agents_router!")
except ImportError as e:
    print(f"Failed to import agents_router: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
