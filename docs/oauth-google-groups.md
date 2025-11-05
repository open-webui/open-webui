# Google OAuth with Cloud Identity Groups Support

This example demonstrates how to configure Open WebUI to use Google OAuth with Cloud Identity API for group-based role management.

## Configuration

### Environment Variables

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-google-client-secret"

# IMPORTANT: Include the Cloud Identity Groups scope
GOOGLE_OAUTH_SCOPE="openid email profile https://www.googleapis.com/auth/cloud-identity.groups.readonly"

# Enable OAuth features
ENABLE_OAUTH_SIGNUP=true
ENABLE_OAUTH_ROLE_MANAGEMENT=true
ENABLE_OAUTH_GROUP_MANAGEMENT=true

# Configure admin roles using Google group emails
OAUTH_ADMIN_ROLES="admin@yourcompany.com,superadmin@yourcompany.com"
OAUTH_ALLOWED_ROLES="users@yourcompany.com,employees@yourcompany.com"

# Optional: Configure group creation
ENABLE_OAUTH_GROUP_CREATION=true
```

## How It Works

1. **Scope Detection**: When a user logs in with Google OAuth, the system checks if the `https://www.googleapis.com/auth/cloud-identity.groups.readonly` scope is present in `GOOGLE_OAUTH_SCOPE`.

2. **Groups Fetching**: If the scope is present, the system uses the Google Cloud Identity API to fetch all groups the user belongs to, instead of relying on claims in the OAuth token.

3. **Role Assignment**: 
   - If the user belongs to any group listed in `OAUTH_ADMIN_ROLES`, they get admin privileges
   - If the user belongs to any group listed in `OAUTH_ALLOWED_ROLES`, they get user privileges
   - Default role is applied if no matching groups are found

4. **Group Management**: If `ENABLE_OAUTH_GROUP_MANAGEMENT` is enabled, Open WebUI groups are synchronized with Google Workspace groups.

## Google Cloud Console Setup

1. **Enable APIs**:
   - Cloud Identity API
   - Cloud Identity Groups API

2. **OAuth 2.0 Setup**:
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs
   - Configure consent screen

3. **Required Scopes**:
   ```
   openid
   email
   profile
   https://www.googleapis.com/auth/cloud-identity.groups.readonly
   ```

## Example Groups Structure

```
Your Google Workspace:
├── admin@yourcompany.com (Admin group)
├── superadmin@yourcompany.com (Super admin group)
├── users@yourcompany.com (Regular users)
├── employees@yourcompany.com (All employees)
└── developers@yourcompany.com (Development team)
```

## Fallback Behavior

If the Cloud Identity scope is not present or the API call fails, the system falls back to the traditional method of reading roles from OAuth token claims.

## Security Considerations

- The Cloud Identity API requires proper authentication and authorization
- Only users with appropriate permissions can access group membership information
- Groups are fetched server-side, not exposed to the client
- Access tokens are handled securely and not logged

## Troubleshooting

1. **Groups not detected**: Ensure the Cloud Identity API is enabled and the OAuth client has the required scope
2. **Permission denied**: Verify the service account or OAuth client has Cloud Identity API access
3. **No admin role**: Check that the user belongs to a group listed in `OAUTH_ADMIN_ROLES`

## Benefits Over Token Claims

- **Real-time**: Groups are fetched fresh on each login
- **Complete**: Gets all group memberships, including nested groups
- **Accurate**: No dependency on ID token size limits
- **Flexible**: Can handle complex group hierarchies in Google Workspace