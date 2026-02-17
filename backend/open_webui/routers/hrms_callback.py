"""
Router for handling the HRMS SSO callback redirect.

After a user authenticates via SSO, the identity provider redirects to
GET /api/v1/hrms/callback?token=<bearer_token>&state=<state_uuid>

This endpoint resolves the state to a user_id, stores the token, and
returns a simple HTML page confirming success.
"""

import time
import logging

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from open_webui.tools.hrms_mcp import (
    load_hrms_data,
    save_hrms_data,
    PENDING_STATE_TTL,
)

log = logging.getLogger(__name__)

router = APIRouter()

_SUCCESS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>HRMS Authentication</title>
  <style>
    body { font-family: system-ui, sans-serif; display: flex; justify-content: center;
           align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }
    .card { background: #fff; border-radius: 12px; padding: 2rem 3rem;
            box-shadow: 0 2px 12px rgba(0,0,0,.08); text-align: center; max-width: 420px; }
    .card h1 { color: #22c55e; margin-bottom: .5rem; }
    .card p  { color: #555; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Authentication Successful</h1>
    <p>Your HRMS token has been saved. You can close this tab and return to Open WebUI.</p>
  </div>
</body>
</html>
"""

_ERROR_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>HRMS Authentication Error</title>
  <style>
    body {{ font-family: system-ui, sans-serif; display: flex; justify-content: center;
           align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
    .card {{ background: #fff; border-radius: 12px; padding: 2rem 3rem;
            box-shadow: 0 2px 12px rgba(0,0,0,.08); text-align: center; max-width: 420px; }}
    .card h1 {{ color: #ef4444; margin-bottom: .5rem; }}
    .card p  {{ color: #555; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Authentication Failed</h1>
    <p>{message}</p>
  </div>
</body>
</html>
"""


@router.get("/callback")
async def hrms_sso_callback(
    token: str = Query(default=None),
    state: str = Query(default=None),
) -> HTMLResponse:
    """
    Handle the SSO redirect.  The identity provider sends the user here with
    ``?token=<bearer>&state=<uuid>``.  We resolve the state to a user_id,
    store the token, and show a success page.
    """

    if not token or not state:
        return HTMLResponse(
            _ERROR_HTML_TEMPLATE.format(
                message="Missing token or state parameter. Please try logging in again."
            ),
            status_code=400,
        )

    data = load_hrms_data()
    pending = data.get("pending_states", {})
    entry = pending.get(state)

    if not entry:
        return HTMLResponse(
            _ERROR_HTML_TEMPLATE.format(
                message="Invalid or already-used state token. Please try logging in again from the chat."
            ),
            status_code=400,
        )

    # Check TTL
    created_at = entry.get("created_at", 0)
    if time.time() - created_at > PENDING_STATE_TTL:
        # Clean up the expired state
        del pending[state]
        save_hrms_data(data)
        return HTMLResponse(
            _ERROR_HTML_TEMPLATE.format(
                message="This login link has expired. Please request a new one from the chat."
            ),
            status_code=400,
        )

    user_id = entry["user_id"]

    # Store the token for this user
    data.setdefault("tokens", {})[user_id] = {
        "access_token": token.strip(),
        "saved_at": int(time.time()),
    }

    # Remove the consumed state
    del pending[state]
    save_hrms_data(data)

    log.info(f"HRMS SSO callback: token stored for user {user_id}")
    return HTMLResponse(_SUCCESS_HTML)
