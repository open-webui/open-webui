# Token Issue Diagnosis

## Current Situation

- **Token Type:** GitHub App token (identified as `cursor[bot]`)
- **Token Prefix:** `ghs_` (36 characters)
- **Error:** "Resource not accessible by integration" (HTTP 403)

## The Problem

Even though you mentioned it's a Personal Access Token with `repo` permissions, GitHub is treating it as an integration token (GitHub App). This is indicated by:

1. Account name: `cursor[bot]` (not a user account)
2. Error message: "Resource not accessible by integration"
3. Token prefix: `ghs_` (can be either GitHub App or fine-grained PAT, but behavior suggests App)

## Possible Causes

### 1. Organization Settings Blocking Integrations

Your organization may have settings that restrict what integration tokens can do:

- Check: https://github.com/organizations/jjdrisco/settings/oauth_application_policy
- Look for "Third-party access restrictions"

### 2. GitHub App Permissions

If this is actually a GitHub App token:

- It needs "Pull requests: Read and write" permission
- Check: https://github.com/settings/apps
- Find the app → Permissions & events → Repository permissions

### 3. Repository Settings

The repository might have branch protection or settings that prevent PR creation:

- Check: https://github.com/jjdrisco/DSL-kidsgpt-open-webui/settings

## Solutions

### Option 1: Create a Classic Personal Access Token (PAT)

Classic PATs start with `ghp_` (not `ghs_`):

1. Go to: https://github.com/settings/tokens/new
2. Select "Generate new token (classic)"
3. Check `repo` scope
4. Generate token (starts with `ghp_`)
5. Update authentication:
   ```bash
   export GITHUB_TOKEN=ghp_your_new_token
   gh auth login --with-token <<< "ghp_your_new_token"
   ```

### Option 2: Check Organization Settings

If using an integration token, ensure:

- Organization allows third-party access
- No restrictions on PR creation
- Settings: https://github.com/organizations/jjdrisco/settings/oauth_application_policy

### Option 3: Update GitHub App Permissions

If this is a GitHub App:

1. Go to: https://github.com/settings/apps
2. Find the app → Edit → Permissions & events
3. Set "Pull requests" to "Read and write"
4. Reinstall on repository

## Verification

After updating, test with:

```bash
export GITHUB_TOKEN=your_token
gh pr create --base main --head feature/separate-quiz-workflow --title "Test" --body "Test"
```

If successful, you'll get a PR number. If it fails, check the error message.
