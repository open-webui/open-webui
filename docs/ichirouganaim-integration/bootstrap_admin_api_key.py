"""Enable API keys and mint one for the admin user -- run *inside* the container.

open-webui has no CLI/API path to do this from outside: API-key auth has to
already be enabled and a key already exist before any authenticated API call
(including the functions API `sync_pipe.py` needs) can work. This script
uses the app's own DB models directly, in-process, to do the one-time
chicken-and-egg bootstrap step. After this, everything else (`sync_pipe.py`,
setting Valves, etc.) goes through the normal HTTP API.

Usage (from the host, against a running container named `open-webui`):

    docker cp docs/ichirouganaim-integration/bootstrap_admin_api_key.py \\
      open-webui:/app/backend/bootstrap_admin_api_key.py
    docker exec -w /app/backend open-webui bash -c \\
      'WEBUI_SECRET_KEY=$(cat .webui_secret_key 2>/dev/null || echo "$WEBUI_SECRET_KEY") \\
       python3 bootstrap_admin_api_key.py'
    docker exec open-webui rm -f /app/backend/bootstrap_admin_api_key.py

(If `docker-compose.override.yaml` sets a fixed `WEBUI_SECRET_KEY` -- see
SETUP.md -- that env var is already present in the container's own
environment and the `$(cat .webui_secret_key ...)` fallback above is a
no-op; it only matters if you're running with the auto-generate-on-boot
default instead.)

Alternative: do this by hand in the browser instead -- Admin Settings >
Authentication > "API Keys" toggle, then Settings > Account > "Create new
key" on the account you want to use. Either path ends at the same place: an
`sk-...` key for an admin account, with API-key auth enabled. This script
just makes it scriptable for a headless/first-boot server setup.

Requires at least one user to already exist (sign up once through the web
UI first -- the first registered account becomes admin automatically).

Safe to re-run: by default, if the admin already has a key, this reuses and
reprints it rather than rotating it -- so running the combined
`bootstrap.sh` more than once (e.g. re-running the whole setup script after
an unrelated failure partway through) doesn't silently invalidate a key
something else might already be using. Pass `--rotate` to force a fresh key
anyway.
"""

import asyncio
import sys

from open_webui.models.config import Config
from open_webui.models.users import Users
from open_webui.utils.auth import create_api_key


async def main():
    force_rotate = '--rotate' in sys.argv

    await Config.upsert({'auth.enable_api_keys': True})

    admin = await Users.get_super_admin_user()
    if not admin:
        print('NO_ADMIN_USER_FOUND -- sign up through the web UI first, then re-run this.')
        return

    existing_key = await Users.get_user_api_key_by_id(admin.id)
    if existing_key and not force_rotate:
        print(f'ADMIN_EMAIL={admin.email}')
        print(f'ADMIN_ID={admin.id}')
        print(f'API_KEY={existing_key}')
        print('REUSED_EXISTING_KEY=true')
        return

    api_key = create_api_key()
    await Users.update_user_api_key_by_id(admin.id, api_key)

    print(f'ADMIN_EMAIL={admin.email}')
    print(f'ADMIN_ID={admin.id}')
    print(f'API_KEY={api_key}')
    if existing_key:
        print('ROTATED_EXISTING_KEY=true', file=sys.stderr)
        print(
            'WARNING: rotated an existing API key -- anything already using the old key will break.',
            file=sys.stderr,
        )


asyncio.run(main())
