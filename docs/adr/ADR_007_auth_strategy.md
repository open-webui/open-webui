# ADR 007: Multi-Strategy Authentication Architecture

> **Status:** Accepted
> **Date:** Foundational decision
> **Deciders:** Open WebUI core team

## Context

Open WebUI supports diverse deployment scenarios with different authentication requirements:
- **Personal use:** Simple email/password, possibly no auth
- **Team deployment:** SSO integration (Google, GitHub, etc.)
- **Enterprise:** LDAP/Active Directory, strict security policies
- **API access:** Programmatic access for integrations

Requirements:
- Support multiple auth methods simultaneously
- Maintain session across browser refreshes
- Enable API access without interactive login
- Support role-based access control (admin/user)

## Decision

Implement a **multi-strategy authentication system** with:
1. **Local authentication:** Email/password with bcrypt/argon2 hashing
2. **JWT tokens:** Stateless API authentication
3. **OAuth 2.0/OIDC:** External identity providers
4. **LDAP:** Enterprise directory integration
5. **API keys:** Long-lived programmatic access

Key design choices:
- **JWT as primary:** All authenticated requests use Bearer tokens
- **Cookie fallback:** Tokens stored in cookies for browser convenience
- **Role-based:** `admin` and `user` roles with different capabilities
- **Configurable:** Auth can be disabled for single-user deployments

## Consequences

### Positive
- **Flexibility:** Supports personal to enterprise deployments
- **Security:** Industry-standard protocols (OAuth 2.0, JWT)
- **Integration:** Works with existing identity infrastructure
- **API-friendly:** Programmatic access via API keys

### Negative
- **Complexity:** Multiple auth paths to maintain and secure
- **Configuration:** Many options can confuse users
- **Token management:** Must handle expiration, refresh, revocation
- **Attack surface:** More auth methods = more potential vulnerabilities

### Neutral
- Requires secure secret management
- OAuth providers have different claim formats

## Implementation

**Authentication flow:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Authentication Methods                        │
├─────────────┬──────────────┬──────────────┬──────────────┬─────────┤
│   Local     │    OAuth     │    LDAP      │   API Key    │  None   │
│ email/pass  │   Google/    │   AD/LDAP    │  Bearer key  │(disabled)│
│             │   GitHub/etc │              │              │         │
└──────┬──────┴──────┬───────┴──────┬───────┴──────┬───────┴────┬────┘
       │             │              │              │            │
       └─────────────┴──────────────┴──────────────┘            │
                            │                                   │
                            ▼                                   │
                   ┌─────────────────┐                          │
                   │  Validate User  │                          │
                   │  Create/Update  │                          │
                   └────────┬────────┘                          │
                            │                                   │
                            ▼                                   │
                   ┌─────────────────┐                          │
                   │  Generate JWT   │◀─────────────────────────┘
                   │     Token       │     (API key → user lookup)
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Set Cookie or   │
                   │ Return Token    │
                   └─────────────────┘
```

**JWT token generation:**

```python
# utils/auth.py
from jose import jwt
from datetime import datetime, timedelta

def create_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, WEBUI_SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, WEBUI_SECRET_KEY, algorithms=["HS256"])
    except jwt.JWTError:
        return None
```

**Dependency injection for auth:**

```python
# utils/auth.py
async def get_current_user(
    request: Request,
    db: Session = Depends(get_session)
) -> Optional[UserModel]:
    """Extract user from JWT token in header or cookie."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.cookies.get("token")

    if not token:
        return None

    data = decode_token(token)
    if not data or "id" not in data:
        return None

    return Users.get_user_by_id(data["id"], db=db)

async def get_verified_user(user = Depends(get_current_user)) -> UserModel:
    """Require authenticated user."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

async def get_admin_user(user = Depends(get_verified_user)) -> UserModel:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user
```

**OAuth flow:**

```python
# routers/auths.py
@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_session)
):
    """Handle OAuth callback from provider."""
    # Verify state parameter
    # Exchange code for tokens
    # Get user info from provider
    # Create or update user account
    # Generate JWT token
    # Set cookie and redirect
```

**LDAP authentication:**

```python
@router.post("/ldap/signin")
async def ldap_signin(
    form_data: SigninForm,
    db: Session = Depends(get_session)
):
    """Authenticate against LDAP directory."""
    # Connect to LDAP server
    # Bind with user credentials
    # Get user attributes
    # Create or update local user
    # Generate JWT token
```

**API key authentication:**

```python
# API keys are hashed and stored in api_keys table
# Validated by looking up key hash

async def get_current_user_by_api_key(
    request: Request,
    db: Session = Depends(get_session)
) -> Optional[UserModel]:
    """Authenticate via API key in header."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

    # Check if it's an API key (not JWT)
    key_record = ApiKeys.get_key_by_value(api_key, db=db)
    if key_record:
        return Users.get_user_by_id(key_record.user_id, db=db)

    return None
```

## Configuration

```python
# Environment variables
WEBUI_AUTH = True  # Enable/disable auth requirement
WEBUI_SECRET_KEY = "..."  # JWT signing key

# Local auth
ENABLE_SIGNUP = True
DEFAULT_USER_ROLE = "pending"  # or "user"

# OAuth
ENABLE_OAUTH_SIGNUP = True
OAUTH_MERGE_ACCOUNTS_BY_EMAIL = True
OAUTH_PROVIDERS = {
    "google": {"client_id": "...", "client_secret": "..."},
    "github": {"client_id": "...", "client_secret": "..."},
}

# LDAP
ENABLE_LDAP = False
LDAP_SERVER_URL = "ldap://..."
LDAP_BIND_DN = "cn=admin,dc=example,dc=com"
```

## Alternatives Considered

### Session-Based Auth Only
- Server-side session storage
- Simpler token management
- Doesn't scale well across instances without shared session store
- Rejected for API access limitations

### OAuth Only
- Simpler, delegate auth to providers
- Requires external provider for all deployments
- Can't support offline/air-gapped scenarios
- Rejected for deployment flexibility

### Passport.js Style
- Unified auth middleware pattern
- Python ecosystem doesn't have equivalent
- Would need custom implementation
- Rejected for implementation effort

## Related Documents

- `DIRECTIVE_adding_oauth_provider.md` — How to add OAuth providers
- `DOMAIN_GLOSSARY.md` — Auth, Role, JWT Token terms
- `DATABASE_SCHEMA.md` — auths, api_keys, oauth_sessions tables

---

*Last updated: 2026-02-03*
