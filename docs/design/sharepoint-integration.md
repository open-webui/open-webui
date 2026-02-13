# SharePoint Integration Design

## Overview

Add ability to upload files from SharePoint/OneDrive to OpenWebUI chats, allowing users to reference documents stored in Microsoft 365.

## User Flow

```
User clicks "Upload from SharePoint" button
    |
    v
[First time] Microsoft OAuth login popup
    |
    v
SharePoint file browser dialog
    |
    v
User selects file(s)
    |
    v
Backend downloads file from SharePoint
    |
    v
File stored in OpenWebUI storage
    |
    v
File attached to chat (same as local upload)
```

## Architecture

### Components

1. **Microsoft OAuth Integration** (`backend/open_webui/utils/microsoft_auth.py`)
   - PKCE flow for Microsoft Graph API
   - Store tokens in OAuthSessions table (provider="microsoft")
   - Scopes: `Files.Read.All`, `Sites.Read.All`, `User.Read`

2. **SharePoint API Router** (`backend/open_webui/routers/sharepoint.py`)
   ```
   GET  /sharepoint/auth/login     - Start OAuth flow
   GET  /sharepoint/auth/callback  - Handle OAuth callback
   GET  /sharepoint/auth/status    - Check auth status
   POST /sharepoint/auth/logout    - Disconnect account
   GET  /sharepoint/sites          - List accessible SharePoint sites
   GET  /sharepoint/drives         - List drives (OneDrive + SharePoint)
   GET  /sharepoint/files          - Browse files in a drive/folder
   POST /sharepoint/download       - Download file to OpenWebUI storage
   ```

3. **Frontend Components**
   - `SharePointButton.svelte` - Button in file upload area
   - `SharePointBrowser.svelte` - File browser modal
   - `SharePointAuth.svelte` - OAuth connection UI

### Database Schema

Uses existing `OAuthSessions` table with:
- `provider = "microsoft"`
- `token = { access_token, refresh_token, expires_at, ... }`

### API Endpoints

#### List Drives
```
GET /sharepoint/drives
Response: {
  "drives": [
    {
      "id": "drive_id",
      "name": "OneDrive",
      "type": "personal|business|documentLibrary",
      "site_name": "SharePoint Site Name"  // for SharePoint drives
    }
  ]
}
```

#### Browse Files
```
GET /sharepoint/files?drive_id=xxx&folder_id=root
Response: {
  "items": [
    {
      "id": "item_id",
      "name": "document.pdf",
      "type": "file|folder",
      "size": 12345,
      "mime_type": "application/pdf",
      "modified": "2025-02-06T00:00:00Z",
      "download_url": "..."  // for files only
    }
  ],
  "next_page": "token_or_null"
}
```

#### Download File
```
POST /sharepoint/download
Body: {
  "drive_id": "xxx",
  "item_id": "yyy"
}
Response: {
  "file": {
    "id": "openwebui_file_id",
    "name": "document.pdf",
    "size": 12345,
    "type": "file",
    "url": "/api/v1/files/xxx/content"
  }
}
```

## Implementation Plan

### Phase 1: Backend OAuth & API (MVP)
1. Create `microsoft_auth.py` with PKCE OAuth flow
2. Create `sharepoint.py` router with auth endpoints
3. Add Microsoft OAuth callback to main.py
4. Implement drive listing endpoint
5. Implement file browsing endpoint
6. Implement file download endpoint

### Phase 2: Frontend Integration
1. Add SharePoint button to file upload area
2. Create SharePoint auth connection UI in settings
3. Create file browser modal component
4. Wire up file selection to existing upload flow

### Phase 3: Polish
1. Add file type icons
2. Add search within SharePoint
3. Add recent files list
4. Add folder breadcrumb navigation
5. Cache drive/site listings

## Configuration

### Environment Variables
```
MICROSOFT_CLIENT_ID=xxx              # Azure AD app client ID
MICROSOFT_TENANT_ID=common           # 'common' for multi-tenant, or specific tenant
ENABLE_SHAREPOINT_INTEGRATION=true   # Feature flag
```

### Azure AD App Registration
1. Create app in Azure Portal > App registrations
2. Add redirect URI: `http://localhost:8168/sharepoint/callback`
3. Add API permissions:
   - Microsoft Graph: `Files.Read.All`, `Sites.Read.All`, `User.Read`
4. Enable "Allow public client flows" (for PKCE)

## Security Considerations

1. **Token Storage**: Tokens stored encrypted in database
2. **Scope Limitation**: Read-only access (no write/delete)
3. **User Isolation**: Each user has own Microsoft connection
4. **Token Refresh**: Auto-refresh before expiration
5. **Audit Logging**: Log file access for compliance

## Dependencies

- `msal` - Microsoft Authentication Library
- `msgraph-core` - Microsoft Graph SDK (optional, can use raw HTTP)

## File Size Limits

- Max file size: 100MB (configurable)
- Larger files: Show warning, offer to download first N pages for PDFs

## Error Handling

| Error | User Message | Action |
|-------|-------------|--------|
| Token expired | "Session expired, please reconnect" | Show reconnect button |
| File too large | "File exceeds 100MB limit" | Suggest alternatives |
| Permission denied | "No access to this file" | Check sharing settings |
| Network error | "Connection failed, retrying..." | Auto-retry 3x |

## Metrics

Track:
- SharePoint connections per user
- Files downloaded from SharePoint
- Most accessed SharePoint sites
- Download errors/failures
