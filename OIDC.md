# Open WebUI OIDC Integration Guide

This document provides comprehensive information about OIDC (OpenID Connect) and OAuth integration in Open WebUI backend.

## Overview

Open WebUI has **complete OIDC integration** built-in with advanced features including role management, group synchronization, account merging, and support for multiple identity providers. The system follows modern security best practices and supports both OAuth 2.0 and OIDC protocols.

## Architecture

### Authentication Flow
1. **JWT-based sessions** with configurable expiration
2. **HTTP-only secure cookies** (primary method)
3. **Authorization Bearer header** (fallback)
4. **PKCE (Proof Key for Code Exchange)** support for enhanced security

### Database Schema

#### `auth` Table
```sql
id (String, PK)
email (String)
password (Text) -- bcrypt hashed
active (Boolean)
```

#### `user` Table  
```sql
id (String, PK)
name (String)
email (String)
role (String) -- "admin", "user", "pending"
profile_image_url (Text)
last_active_at (BigInteger)
updated_at (BigInteger)
created_at (BigInteger)
api_key (String, UNIQUE, NULLABLE)
settings (JSON, NULLABLE)
info (JSON, NULLABLE)
oauth_sub (Text, UNIQUE, NULLABLE) -- OAuth subject identifier
```

## Supported Identity Providers

### 1. Google OAuth/OIDC
- **Provider ID**: `google`
- **Type**: OIDC (OpenID Connect)
- **Discovery Endpoint**: `https://accounts.google.com/.well-known/openid-configuration`
- **OAuth Endpoints**: 
  - Login: `/oauth/google/login`
  - Callback: `/oauth/google/callback`

#### Configuration Variables:
```bash
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_OAUTH_SCOPE="openid email profile"  # Default
GOOGLE_REDIRECT_URI=https://your-domain/oauth/google/callback
```

### 2. Microsoft Azure AD/OIDC
- **Provider ID**: `microsoft`
- **Type**: OIDC (OpenID Connect)
- **Discovery Endpoint**: `https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration`
- **OAuth Endpoints**:
  - Login: `/oauth/microsoft/login`
  - Callback: `/oauth/microsoft/callback`
- **Special Features**: Profile picture sync from Microsoft Graph API

#### Configuration Variables:
```bash
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
MICROSOFT_CLIENT_TENANT_ID=your_tenant_id
MICROSOFT_OAUTH_SCOPE="openid email profile"  # Default
MICROSOFT_REDIRECT_URI=https://your-domain/oauth/microsoft/callback
```

### 3. GitHub OAuth
- **Provider ID**: `github`
- **Type**: OAuth 2.0 (custom implementation)
- **OAuth Endpoints**:
  - Login: `/oauth/github/login`
  - Callback: `/oauth/github/callback`
- **API Endpoints**: 
  - Authorize: `https://github.com/login/oauth/authorize`
  - Token: `https://github.com/login/oauth/access_token`
  - User Info: `https://api.github.com/user`
- **Special Features**: Automatic email fetching from GitHub API if public email not available

#### Configuration Variables:
```bash
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_CLIENT_SCOPE="user:email"  # Default
GITHUB_CLIENT_REDIRECT_URI=https://your-domain/oauth/github/callback
```

### 4. Generic OIDC Provider (Universal)
- **Provider ID**: `oidc`
- **Type**: OIDC (OpenID Connect) - **Supports any OIDC-compliant provider**
- **OAuth Endpoints**:
  - Login: `/oauth/oidc/login`  
  - Callback: `/oauth/oidc/callback`
- **Special Features**: 
  - PKCE support (S256 code challenge method)
  - Custom claim mapping
  - Works with any OIDC-compliant identity provider

#### Configuration Variables:
```bash
# Required
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
OPENID_PROVIDER_URL=https://your-idp/.well-known/openid-configuration
OPENID_REDIRECT_URI=https://your-domain/oauth/oidc/callback

# Optional
OAUTH_SCOPES="openid email profile"  # Default
OAUTH_CODE_CHALLENGE_METHOD="S256"   # PKCE (auto-enabled)
OAUTH_PROVIDER_NAME="Your Provider"  # Display name
```

## Supported Cloud/Enterprise Providers

The **Generic OIDC Provider** supports any OIDC-compliant service:

### Auth0
```bash
OAUTH_CLIENT_ID=your_auth0_client_id
OAUTH_CLIENT_SECRET=your_auth0_client_secret
OPENID_PROVIDER_URL=https://your-domain.auth0.com/.well-known/openid_configuration
OPENID_REDIRECT_URI=https://your-app/oauth/oidc/callback
```

### Keycloak
```bash
OAUTH_CLIENT_ID=your_keycloak_client_id
OAUTH_CLIENT_SECRET=your_keycloak_client_secret
OPENID_PROVIDER_URL=https://your-keycloak.com/auth/realms/{realm}/.well-known/openid-configuration
OPENID_REDIRECT_URI=https://your-app/oauth/oidc/callback
```

### Okta
```bash
OAUTH_CLIENT_ID=your_okta_client_id
OAUTH_CLIENT_SECRET=your_okta_client_secret
OPENID_PROVIDER_URL=https://your-org.okta.com/.well-known/openid-configuration
OPENID_REDIRECT_URI=https://your-app/oauth/oidc/callback
```

### AWS Cognito
```bash
OAUTH_CLIENT_ID=your_cognito_client_id
OAUTH_CLIENT_SECRET=your_cognito_client_secret
OPENID_PROVIDER_URL=https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/openid-configuration
OPENID_REDIRECT_URI=https://your-app/oauth/oidc/callback
```

### Azure AD B2C
```bash
OAUTH_CLIENT_ID=your_b2c_client_id
OAUTH_CLIENT_SECRET=your_b2c_client_secret
OPENID_PROVIDER_URL=https://your-tenant.b2clogin.com/your-tenant.onmicrosoft.com/your-policy/v2.0/.well-known/openid-configuration
OPENID_REDIRECT_URI=https://your-app/oauth/oidc/callback
```

## Advanced Configuration

### Authentication Management
```bash
# Enable OAuth signup for new users
ENABLE_OAUTH_SIGNUP=true

# Merge OAuth accounts with existing email-based accounts
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true

# Update profile picture on each login
OAUTH_UPDATE_PICTURE_ON_LOGIN=true
```

### Claim Mapping
```bash
# Customize which claims to extract from the ID token
OAUTH_USERNAME_CLAIM="name"          # Default: "name"
OAUTH_EMAIL_CLAIM="email"            # Default: "email"
OAUTH_PICTURE_CLAIM="picture"        # Default: "picture"
OAUTH_ROLES_CLAIM="roles"            # Default: "roles"
OAUTH_GROUPS_CLAIM="groups"          # Default: "groups"
```

### Role Management
```bash
# Enable automatic role assignment based on OAuth claims
ENABLE_OAUTH_ROLE_MANAGEMENT=true

# Define which OAuth roles map to "user" role
OAUTH_ALLOWED_ROLES='["user", "member", "employee"]'

# Define which OAuth roles map to "admin" role  
OAUTH_ADMIN_ROLES='["admin", "administrator", "super-admin"]'
```

### Group Management
```bash
# Enable automatic group synchronization
ENABLE_OAUTH_GROUP_MANAGEMENT=true

# Automatically create missing groups from OAuth claims
ENABLE_OAUTH_GROUP_CREATION=true

# Groups that should be ignored during sync
OAUTH_BLOCKED_GROUPS='["internal", "system"]'
```

### Domain Restrictions
```bash
# Restrict login to specific email domains
OAUTH_ALLOWED_DOMAINS='["company.com", "subsidiary.com"]'

# Use "*" to allow all domains
OAUTH_ALLOWED_DOMAINS='["*"]'
```

### Session Configuration
```bash
# JWT token expiration (supports: "1h", "30m", "7d", etc.)
JWT_EXPIRES_IN="24h"

# Cookie security settings
WEBUI_AUTH_COOKIE_SAME_SITE="lax"    # "strict", "lax", "none"
WEBUI_AUTH_COOKIE_SECURE=true        # Require HTTPS
```

## Security Features

### PKCE (Proof Key for Code Exchange)
- **Automatically enabled** for Generic OIDC provider
- Uses **S256 code challenge method**
- Protects against authorization code interception attacks

### Token Security
- **HTTP-only cookies** prevent XSS attacks
- **Secure cookie flag** when HTTPS is used
- **SameSite protection** against CSRF attacks
- **JWT tokens** with configurable expiration

### Password Security
- **bcrypt hashing** for local passwords
- **Random UUID passwords** for OAuth-only accounts
- **API key authentication** with `sk-{uuid}` format

## Implementation Details

### Key Files
- **OAuth Manager**: `/open_webui/utils/oauth.py` - Core OAuth/OIDC logic
- **Configuration**: `/open_webui/config.py` - Provider configuration and loading
- **Auth Routes**: `/open_webui/routers/auths.py` - Authentication endpoints
- **User Model**: `/open_webui/models/users.py` - User database operations

### OAuth Flow Implementation

1. **Login Initiation**: User clicks provider login button
   ```
   GET /oauth/{provider}/login
   → Redirects to provider's authorization endpoint
   ```

2. **Provider Authentication**: User authenticates with identity provider

3. **Authorization Callback**: Provider redirects back with authorization code
   ```
   GET /oauth/{provider}/callback?code=...&state=...
   ```

4. **Token Exchange**: Backend exchanges authorization code for access token and ID token

5. **User Information**: Extract user details from ID token claims

6. **Account Processing**: 
   - Find existing user by `oauth_sub` or email
   - Create new user if signup enabled
   - Update role and group memberships
   - Download and store profile picture

7. **Session Creation**: Issue JWT token and set secure cookie

8. **Frontend Redirect**: Redirect to frontend with authentication token

### Role Assignment Logic

```python
def get_user_role(user, user_data):
    # First user or only user gets admin role
    if Users.get_num_users() <= 1:
        return "admin"
    
    # If role management enabled, check OAuth claims
    if ENABLE_OAUTH_ROLE_MANAGEMENT:
        oauth_roles = extract_nested_claim(user_data, OAUTH_ROLES_CLAIM)
        
        # Check for admin roles first (highest priority)
        if any(role in oauth_roles for role in OAUTH_ADMIN_ROLES):
            return "admin"
            
        # Check for allowed user roles
        if any(role in oauth_roles for role in OAUTH_ALLOWED_ROLES):
            return "user"
            
        # Default role if no matching roles found
        return DEFAULT_USER_ROLE
    
    # Role management disabled - preserve existing role or use default
    return user.role if user else DEFAULT_USER_ROLE
```

### Group Synchronization Logic

```python
def update_user_groups(user, user_data, default_permissions):
    oauth_groups = extract_nested_claim(user_data, OAUTH_GROUPS_CLAIM)
    current_groups = Groups.get_groups_by_member_id(user.id)
    
    # Create missing groups if creation enabled
    if ENABLE_OAUTH_GROUP_CREATION:
        for group_name in oauth_groups:
            if not Groups.get_group_by_name(group_name):
                Groups.create_group(group_name, default_permissions)
    
    # Remove user from groups no longer in OAuth claims
    for group in current_groups:
        if group.name not in oauth_groups and group.name not in OAUTH_BLOCKED_GROUPS:
            Groups.remove_user_from_group(group.id, user.id)
    
    # Add user to new groups from OAuth claims
    for group_name in oauth_groups:
        if group_name not in OAUTH_BLOCKED_GROUPS:
            group = Groups.get_group_by_name(group_name)
            if group and user.id not in group.user_ids:
                Groups.add_user_to_group(group.id, user.id)
```

## Troubleshooting

### Common Issues

1. **"Invalid credentials" error**
   - Check client ID and secret are correct
   - Verify redirect URI matches exactly
   - Ensure discovery endpoint is accessible

2. **"Email domain not allowed"**
   - Check `OAUTH_ALLOWED_DOMAINS` configuration
   - Verify user's email domain is in allowed list

3. **"Access prohibited" error**
   - Ensure `ENABLE_OAUTH_SIGNUP=true` for new users
   - Check if role management is blocking access

4. **Profile picture not updating**
   - Verify `OAUTH_UPDATE_PICTURE_ON_LOGIN=true`
   - Check if provider supports picture claim
   - Ensure picture URL is accessible

### Debugging

Enable debug logging:
```bash
# Set log level for OAuth operations
OAUTH_LOG_LEVEL=DEBUG
```

Check logs for OAuth flow details:
```bash
# Look for OAuth-related log entries
grep -i "oauth\|oidc" /path/to/logs
```

### Testing Configuration

Use OAuth provider's testing tools:
- **Google**: [OAuth Playground](https://developers.google.com/oauthplayground/)
- **Microsoft**: [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
- **Auth0**: Management Dashboard test connection
- **Keycloak**: Admin console client testing

## Migration Guide

### From Other Auth Systems

1. **LDAP Migration**: OAuth can run alongside LDAP authentication
2. **SAML Migration**: Use OIDC-compatible SAML bridges or identity provider OIDC endpoints
3. **Custom Auth**: Use trusted header authentication or API keys as bridge

### Account Merging

Enable account merging to connect existing local accounts:
```bash
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true
```

This allows users with existing local accounts to login via OAuth without losing data.

## Best Practices

### Security
1. **Always use HTTPS** in production
2. **Enable PKCE** for public clients
3. **Restrict domains** to your organization
4. **Regular key rotation** for client secrets
5. **Monitor OAuth flows** for suspicious activity

### Performance
1. **Cache provider metadata** (automatic in implementation)
2. **Optimize profile picture** downloads
3. **Batch group operations** during sync

### User Experience
1. **Provide clear provider names** with `OAUTH_PROVIDER_NAME`
2. **Handle email collection** gracefully
3. **Support profile picture** updates
4. **Maintain session persistence** across deployments

## Support and Extensions

### Adding Custom Providers

To add a new OAuth provider, modify `/open_webui/config.py`:

```python
# Add configuration variables
CUSTOM_CLIENT_ID = PersistentConfig(
    "CUSTOM_CLIENT_ID",
    "oauth.custom.client_id", 
    os.environ.get("CUSTOM_CLIENT_ID", ""),
)

# Add to load_oauth_providers() function
if CUSTOM_CLIENT_ID.value and CUSTOM_CLIENT_SECRET.value:
    def custom_oauth_register(client):
        client.register(
            name="custom",
            client_id=CUSTOM_CLIENT_ID.value,
            client_secret=CUSTOM_CLIENT_SECRET.value,
            server_metadata_url="https://custom-provider/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    
    OAUTH_PROVIDERS["custom"] = {
        "register": custom_oauth_register,
    }
```

### Enterprise Features

The OAuth implementation supports enterprise requirements:
- **Multi-tenant deployments** with provider isolation
- **Custom claim processing** for complex role structures  
- **Webhook integration** for user signup notifications
- **Audit logging** for compliance requirements
- **API key fallback** for service accounts

## Resources

- **OpenID Connect Specification**: https://openid.net/connect/
- **OAuth 2.0 Security Best Practices**: https://tools.ietf.org/html/draft-ietf-oauth-security-topics
- **PKCE Specification**: https://tools.ietf.org/html/rfc7636
- **Authlib Documentation**: https://docs.authlib.org/