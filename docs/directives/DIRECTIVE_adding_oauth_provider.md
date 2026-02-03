# Directive: Adding an OAuth Provider

> **Pattern type:** Authentication integration
> **Complexity:** Medium-High
> **Files touched:** 3-5

---

## Prerequisites

- `ADR_007_auth_strategy.md` — Authentication architecture
- `DOMAIN_GLOSSARY.md` — OAuth, JWT terms

---

## Structural Pattern

When adding a new OAuth identity provider:

1. **Configure provider settings** via environment variables
2. **Register OAuth routes** for authorization flow
3. **Map user claims** to Open WebUI user model
4. **Handle account linking** for existing users

| Component | Location | Purpose |
|-----------|----------|---------|
| Configuration | `backend/open_webui/env.py` | Provider settings |
| OAuth manager | `backend/open_webui/utils/oauth.py` | Provider registration |
| Auth routes | `backend/open_webui/routers/auths.py` | OAuth endpoints |
| Frontend UI | `src/routes/auth/+page.svelte` | Login button |

---

## Illustrative Application

Adding a new OIDC provider follows this pattern:

### Step 1: Add Environment Configuration

```python
# backend/open_webui/env.py

# Provider-specific settings
OAUTH_PROVIDER_CLIENT_ID = os.environ.get("OAUTH_PROVIDER_CLIENT_ID", "")
OAUTH_PROVIDER_CLIENT_SECRET = os.environ.get("OAUTH_PROVIDER_CLIENT_SECRET", "")
OAUTH_PROVIDER_DISCOVERY_URL = os.environ.get(
    "OAUTH_PROVIDER_DISCOVERY_URL",
    "https://provider.com/.well-known/openid-configuration"
)
OAUTH_PROVIDER_SCOPE = os.environ.get("OAUTH_PROVIDER_SCOPE", "openid email profile")
OAUTH_PROVIDER_NAME = os.environ.get("OAUTH_PROVIDER_NAME", "Provider")
ENABLE_OAUTH_PROVIDER = os.environ.get("ENABLE_OAUTH_PROVIDER", "false").lower() == "true"
```

### Step 2: Register Provider in OAuth Manager

```python
# backend/open_webui/utils/oauth.py
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()


def register_oauth_providers(app):
    """Register all configured OAuth providers."""

    # Existing providers...

    # New provider
    if ENABLE_OAUTH_PROVIDER and OAUTH_PROVIDER_CLIENT_ID:
        oauth.register(
            name="provider",
            client_id=OAUTH_PROVIDER_CLIENT_ID,
            client_secret=OAUTH_PROVIDER_CLIENT_SECRET,
            server_metadata_url=OAUTH_PROVIDER_DISCOVERY_URL,
            client_kwargs={
                "scope": OAUTH_PROVIDER_SCOPE,
            },
        )

    return oauth
```

### Step 3: Add OAuth Routes

```python
# backend/open_webui/routers/auths.py
from open_webui.utils.oauth import oauth

@router.get("/oauth/provider/login")
async def oauth_provider_login(request: Request):
    """Initiate OAuth flow with provider."""
    if not ENABLE_OAUTH_PROVIDER:
        raise HTTPException(400, "Provider OAuth not enabled")

    redirect_uri = request.url_for("oauth_provider_callback")
    return await oauth.provider.authorize_redirect(request, redirect_uri)


@router.get("/oauth/provider/callback")
async def oauth_provider_callback(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
):
    """Handle OAuth callback from provider."""
    try:
        token = await oauth.provider.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(400, f"OAuth error: {str(e)}")

    # Get user info from provider
    userinfo = token.get("userinfo")
    if not userinfo:
        # Some providers require explicit userinfo call
        userinfo = await oauth.provider.userinfo(token=token)

    # Extract claims
    email = userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("preferred_username")
    picture = userinfo.get("picture")
    oauth_sub = userinfo.get("sub")

    if not email:
        raise HTTPException(400, "Email not provided by OAuth provider")

    # Find or create user
    user = Users.get_user_by_email(email, db=db)

    if user:
        # Update OAuth subject if not set
        if not user.oauth_sub:
            user.oauth_sub = f"provider:{oauth_sub}"
            db.commit()
    else:
        # Create new user if signup enabled
        if not ENABLE_OAUTH_SIGNUP:
            raise HTTPException(403, "OAuth signup disabled")

        user = Users.insert_user(
            UserCreate(
                email=email,
                name=name,
                profile_image_url=picture,
                role=DEFAULT_USER_ROLE,
                oauth_sub=f"provider:{oauth_sub}",
            ),
            db=db,
        )

    # Generate JWT token
    jwt_token = create_token({"id": user.id})

    # Set cookie
    response.set_cookie(
        key="token",
        value=jwt_token,
        httponly=True,
        secure=WEBUI_AUTH_COOKIE_SECURE,
        samesite=WEBUI_SESSION_COOKIE_SAME_SITE,
    )

    # Store OAuth token for refresh (optional)
    if OAUTH_PROVIDER_STORE_TOKENS:
        OAuthSessions.upsert_session(
            user_id=user.id,
            provider="provider",
            token=encrypt_token(token),
            expires_at=token.get("expires_at"),
            db=db,
        )

    # Redirect to app
    return RedirectResponse(url="/", status_code=302)
```

### Step 4: Add Login Button to Frontend

```svelte
<!-- src/routes/auth/+page.svelte -->
<script lang="ts">
  import { WEBUI_API_BASE_URL } from '$lib/constants';

  // Check if provider is enabled (from config endpoint)
  export let data;
  const { oauthProviders } = data;
</script>

<div class="login-form">
  <!-- Existing login form... -->

  {#if oauthProviders.includes('provider')}
    <div class="oauth-divider">
      <span>or</span>
    </div>

    <a
      href="{WEBUI_API_BASE_URL}/auths/oauth/provider/login"
      class="oauth-button provider"
    >
      <img src="/icons/provider.svg" alt="Provider" />
      Sign in with Provider
    </a>
  {/if}
</div>
```

### Step 5: Add Provider Icon

```
src/
└── static/
    └── icons/
        └── provider.svg  # Provider logo
```

---

## Transfer Prompt

**When you need to add an OAuth provider:**

1. **Add environment variables** in `backend/open_webui/env.py`:
   ```python
   OAUTH_{PROVIDER}_CLIENT_ID = os.environ.get("OAUTH_{PROVIDER}_CLIENT_ID", "")
   OAUTH_{PROVIDER}_CLIENT_SECRET = os.environ.get("OAUTH_{PROVIDER}_CLIENT_SECRET", "")
   OAUTH_{PROVIDER}_DISCOVERY_URL = os.environ.get("OAUTH_{PROVIDER}_DISCOVERY_URL", "")
   ENABLE_OAUTH_{PROVIDER} = os.environ.get("ENABLE_OAUTH_{PROVIDER}", "false").lower() == "true"
   ```

2. **Register provider** in `backend/open_webui/utils/oauth.py`:
   ```python
   oauth.register(
       name="{provider}",
       client_id=OAUTH_{PROVIDER}_CLIENT_ID,
       client_secret=OAUTH_{PROVIDER}_CLIENT_SECRET,
       server_metadata_url=OAUTH_{PROVIDER}_DISCOVERY_URL,
       client_kwargs={"scope": "openid email profile"},
   )
   ```

3. **Add routes** in `backend/open_webui/routers/auths.py`:
   - `GET /oauth/{provider}/login` — Initiate flow
   - `GET /oauth/{provider}/callback` — Handle callback

4. **Map claims** to user fields:
   - `email` — Required
   - `name` / `preferred_username` — Display name
   - `picture` — Profile image
   - `sub` — OAuth subject (store as `oauth_sub`)

5. **Add frontend button** in login page

6. **Handle edge cases:**
   - Existing user with same email (link accounts)
   - Missing email claim (reject or prompt)
   - Token refresh (store in oauth_sessions)

**Provider-specific notes:**
- Google: Uses `.well-known/openid-configuration`
- GitHub: Not OIDC, needs custom userinfo call
- Microsoft/Azure: Tenant-specific discovery URL
- Custom OIDC: Standard discovery URL

**Signals that this pattern applies:**
- Enterprise SSO requirement
- Social login request
- Integrating with identity provider

---

## Related Documents

- `ADR_007_auth_strategy.md` — Authentication design
- `DATABASE_SCHEMA.md` — oauth_sessions table
- `backend/open_webui/routers/auths.py` — Reference

---

*Last updated: 2026-02-03*
