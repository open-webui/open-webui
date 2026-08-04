import os
import tempfile

# Importing open_webui.config empties STATIC_DIR and refills it from the frontend
# build. Point it at a throwaway directory first, or collecting these tests wipes
# backend/open_webui/static in the working tree.
os.environ.setdefault('STATIC_DIR', tempfile.mkdtemp(prefix='open-webui-test-static-'))
os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret-key')
