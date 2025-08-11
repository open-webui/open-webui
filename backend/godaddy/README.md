# GoDaddy Integration for Open WebUI

This directory contains GoDaddy-specific extensions for Open WebUI, including Active Directory integration for OAuth group management.

## Features

- **Active Directory Group Integration**: When users authenticate via OAuth, their group memberships are fetched from the GoDaddy Active Directory API instead of relying solely on the groups returned in the OAuth claims.
- **JWT Generation**: Uses the AWS IAM role to generate a JWT token for authenticating with the Active Directory API.
- **Minimal Changes to Core Code**: All extensions are implemented in the `backend/godaddy` directory to minimize changes to the main codebase, making it easier to rebase from the upstream repo.

## Configuration

The following environment variables can be configured:

| Variable | Description | Default |
|----------|-------------|---------|
| `ACTIVE_DIRECTORY_BASE_URL` | Base URL for the Active Directory API | `https://active-directory.gdcorp.tools` |
| `ACTIVE_DIRECTORY_SSO_HOST` | SSO host for token generation | `sso.gdcorp.tools` |
| `ACTIVE_DIRECTORY_TOKEN_REFRESH_MINUTES` | How often to refresh SSO tokens in minutes | `45.0` |
| `USE_ACTIVE_DIRECTORY_GROUPS` | Enable/disable Active Directory group integration | `true` |

## Usage

1. The integration is automatically initialized during application startup.
2. When a user authenticates via OAuth, the Active Directory API is called to retrieve the user's groups.
3. The groups are then used to update the user's group memberships in Open WebUI.

## Implementation Details

- `active_directory.py`: Client for the Active Directory API
- `oauth_extension.py`: Extends the OAuth manager to use Active Directory for group management
- `config.py`: Configuration settings for GoDaddy-specific integrations
- `__init__.py`: Initializes the GoDaddy extensions

## Development

To run Open WebUI with GoDaddy extensions:

```bash
cd backend
./dev.sh
```

The script sets the necessary environment variables for the GoDaddy integration.