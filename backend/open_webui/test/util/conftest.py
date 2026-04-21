import os

# Set required env vars before any open_webui modules are imported during collection.
if not os.environ.get('WEBUI_SECRET_KEY'):
    os.environ['WEBUI_SECRET_KEY'] = 'test-secret-key-for-unit-tests'
