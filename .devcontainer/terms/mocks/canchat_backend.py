"""Development-only CANChat API mock. Never deploy this in production."""
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

if os.getenv("CANCHAT_DEV_MOCK", "") != "1":
    raise RuntimeError("Refusing to start outside explicitly enabled local mock mode")

app = FastAPI(title="CANChat LOCAL MOCK ONLY", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):[0-9]+$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Local in-memory state. Cleared on restart. Not a real authentication system.
USER_ID = "local-terms-reviewer"
TOKEN = "local-development-only-token"
accepted: dict[str, dict] = {}

def local_user():
    return {
        "id": USER_ID,
        "email": "terms-reviewer@localhost.invalid",
        "name": "Local Terms Reviewer",
        "role": "admin",
        "profile_image_url": "",
        "token": TOKEN,
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 86400 * 30,
        "permissions": {},
    }

def require_local_token(request: Request):
    if request.headers.get("authorization", "") != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="Local mock token required")

@app.get("/health")
def health():
    return {"status": "ok", "mode": "LOCAL MOCK ONLY"}

@app.get("/api/config")
def config():
    return {
        "status": True, "name": "CANChat (local mock)", "version": "dev-mock",
        "default_locale": "en-GB", "onboarding": False, "default_models": "",
        "default_prompt_suggestions": [], "docs_url": "", "docs_url_fr": "",
        "survey_url": "", "survey_url_fr": "",
        "features": {
            "auth": True, "auth_trusted_header": False,
            "enable_api_key": False, "enable_signup": False,
            "enable_login_form": False, "enable_websocket": False,
            "enable_web_search": False, "enable_google_drive_integration": False,
            "enable_image_generation": False, "enable_admin_export": False,
            "enable_admin_chat_access": False, "enable_community_sharing": False,
        },
        "oauth": {"providers": {}},
    }

@app.get("/api/v1/auths/")
@app.post("/api/v1/auths/refresh")
def auth_session():
    return local_user()

@app.get("/api/v1/terms/status/{version}")
def terms_status(version: str, request: Request):
    require_local_token(request)
    return accepted.get(version)

class AcceptTerms(BaseModel):
    version: str = Field(min_length=1)

@app.post("/api/v1/terms/accept")
def accept_terms(payload: AcceptTerms, request: Request):
    require_local_token(request)
    now = int(datetime.now(timezone.utc).timestamp())
    item = {
        "id": str(uuid4()), "user_id": USER_ID,
        "accepted_at": now, "version": payload.version.strip()
    }
    accepted[payload.version.strip()] = item
    return item

# Additional authenticated views may request these. Empty placeholders are
# deliberately limited; extend based on observed browser network requests.
@app.get("/api/v1/chats/")
@app.get("/api/v1/chats/list")
@app.get("/api/v1/chats/tags/all")
def empty_lists(request: Request):
    require_local_token(request)
    return []

@app.get("/api/v1/models")
def models(request: Request):
    require_local_token(request)
    return {"data": []}
