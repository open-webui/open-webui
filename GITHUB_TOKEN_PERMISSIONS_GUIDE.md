# GitHub Token Permissions Guide for PR Creation

## Current Token Type

Your token is a **GitHub App Installation Token** (starts with `ghs_`). This type of token has permissions controlled by the GitHub App configuration.

## Required Permissions for PR Creation

### For GitHub App Tokens

To allow PR creation, you need to enable the following permissions in your GitHub App:

#### Repository Permissions (Required):

1. **Pull requests: Read and write** ✅ (Currently likely missing or read-only)
   - This is the critical permission needed to create PRs
   - Location: GitHub App Settings → Permissions & events → Repository permissions

2. **Contents: Read and write** (Recommended)
   - Needed for accessing repository content
3. **Metadata: Read-only** (Always enabled)
   - Basic repository metadata access

#### Account Permissions:

- None required for PR creation

## Steps to Enable PR Creation

### Option 1: Update GitHub App Permissions (Recommended)

1. **Go to GitHub App Settings:**

   ```
   https://github.com/settings/apps
   ```

2. **Find your app** (likely named "cursor" or similar) and click **"Edit"**

3. **Navigate to "Permissions & events"**

4. **Under "Repository permissions", set:**
   - **Pull requests:** Change from "Read-only" or "No access" to **"Read and write"**
   - **Contents:** Ensure it's set to "Read and write" (if you need to modify files)

5. **Save the changes**

6. **Reinstall the app on your repository:**
   - You'll be prompted to reinstall after changing permissions
   - Or go to: `https://github.com/jjdrisco/DSL-kidsgpt-open-webui/settings/installations`
   - Click "Configure" → "Update permissions" or "Reinstall"

7. **The token will automatically get new permissions** (no need to regenerate)

### Option 2: Use a Personal Access Token (PAT)

If you prefer more control, create a Personal Access Token:

1. **Create a new PAT:**

   ```
   https://github.com/settings/tokens/new
   ```

2. **Select scopes:**
   - For **Classic tokens:** Select `repo` scope (full control)
   - For **Fine-grained tokens:**
     - Repository access: Select your repository
     - Permissions → Pull requests: **Read and write**
     - Permissions → Contents: **Read and write**

3. **Update authentication:**
   ```bash
   export GITHUB_TOKEN=your_new_token
   # or
   gh auth login --with-token < token_file.txt
   ```

## Verify Permissions

After updating permissions, verify with:

```bash
# Test PR creation
gh api repos/jjdrisco/DSL-kidsgpt-open-webui/pulls -X POST \
  -f title="Test PR" \
  -f head="feature/separate-quiz-workflow" \
  -f base="main" \
  -f body="Test"

# If successful, you'll get a PR number
# If it fails, you'll see the permission error
```

## Current Token Status

Your current token (`ghs_ygCHXHzYvz...`) is a GitHub App token that:

- ✅ Can read repository data
- ✅ Can read PRs
- ✅ Can check CI status
- ❌ **Cannot create PRs** (missing "Pull requests: Write" permission)
- ❌ **Cannot merge PRs** (missing "Pull requests: Write" permission)

## Quick Fix Summary

**For GitHub App:**

1. Go to: https://github.com/settings/apps
2. Edit your app → Permissions & events
3. Set "Pull requests" to **"Read and write"**
4. Reinstall app on repository

**For PAT:**

1. Create token at: https://github.com/settings/tokens/new
2. Select `repo` scope (classic) or "Pull requests: Read and write" (fine-grained)
3. Set `GITHUB_TOKEN` environment variable

## After Enabling Permissions

Once permissions are updated:

1. The token will automatically have new permissions (for GitHub Apps)
2. You can create PRs using:
   ```bash
   gh pr create --base main --head feature/separate-quiz-workflow --title "..." --body "..."
   ```
3. Or via API:
   ```bash
   gh api -X POST repos/jjdrisco/DSL-kidsgpt-open-webui/pulls -f title="..." -f head="..." -f base="main"
   ```
