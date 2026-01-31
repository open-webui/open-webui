# Pull Request Workflow and Token Management

This document provides detailed information about creating and managing pull requests, including GitHub token requirements for automated PR operations.

## Table of Contents

- [Creating Pull Requests](#creating-pull-requests)
- [GitHub Token Requirements](#github-token-requirements)
- [PR Workflow Best Practices](#pr-workflow-best-practices)
- [Troubleshooting](#troubleshooting)

## Creating Pull Requests

### Prerequisites

Before creating a pull request, ensure you have:

1. **Forked the repository** or have write access to a feature branch
2. **Created a feature branch** from the target branch (typically `main` or `dev`)
3. **Made your changes** and committed them with clear, descriptive messages
4. **Pushed your branch** to the remote repository

### Standard PR Creation Process

1. **Open a Discussion First** (for first-time contributors or large features):
   - Go to [Discussions](https://github.com/open-webui/open-webui/discussions/new/choose)
   - Discuss your idea/fix with the community before creating a PR
   - This helps ensure the feature aligns with project goals

2. **Ensure Your Branch is Up-to-Date**:

   ```bash
   git fetch origin main
   git rebase origin/main  # or merge, depending on your workflow
   ```

3. **Create the Pull Request**:
   - Push your branch: `git push -u origin your-branch-name`
   - Go to the repository on GitHub
   - Click "New Pull Request"
   - Select your branch and the target branch (usually `main` or `dev`)
   - Fill out the PR template completely

4. **Monitor CI/CD Status**:
   - Wait for all CI checks to pass
   - Address any failing tests or formatting issues
   - Respond to review comments promptly

### Target Branch Guidelines

> [!WARNING]
> **Important**: Most PRs should target the `dev` branch, not `main`. PRs targeting `main` directly may be closed immediately unless explicitly approved by maintainers.

- **Feature branches** → `dev` branch
- **Hotfixes** → `main` branch (with maintainer approval)
- **Documentation updates** → `dev` branch

## GitHub Token Requirements

When using automated tools, CI/CD systems, or API-based PR management, you'll need a GitHub Personal Access Token (PAT) with appropriate permissions.

### Token Types

GitHub supports two types of Personal Access Tokens:

1. **Classic PAT** (starts with `ghp_`)
   - Recommended for most use cases
   - Simpler permission model
   - Works with all GitHub API endpoints

2. **Fine-grained PAT** (starts with `ghs_`)
   - More granular permissions
   - Repository-specific access
   - May have limitations with some GitHub CLI operations

### Required Permissions/Scopes

For creating and managing pull requests, your token needs:

#### Classic PAT Scopes:

- ✅ **`repo`** - Full control of private repositories
  - This includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`
- ✅ **`read:org`** (optional but recommended) - Read org and team membership

#### Fine-grained PAT Permissions:

- ✅ **Pull requests**: Read and write
- ✅ **Contents**: Read and write
- ✅ **Metadata**: Read (always included)

### Creating a GitHub Token

1. **Go to GitHub Settings**:
   - Navigate to: https://github.com/settings/tokens
   - Or: Profile → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Generate New Token (Classic)**:
   - Click "Generate new token" → "Generate new token (classic)"
   - Give it a descriptive name (e.g., "PR Management Token")
   - Set expiration (recommend 90 days or custom)
   - Select scopes:
     - ✅ **repo** (all sub-scopes)
     - ✅ **read:org** (optional, for org-related queries)

3. **Generate Token**:
   - Click "Generate token" at the bottom
   - **IMPORTANT**: Copy the token immediately (starts with `ghp_`)
   - Store it securely - you won't be able to see it again

4. **Using the Token**:

   ```bash
   # Set as environment variable
   export GITHUB_TOKEN=ghp_your_token_here

   # Or use with GitHub CLI
   gh auth login --with-token < token.txt

   # Or configure git remote
   git remote set-url origin https://ghp_your_token_here@github.com/username/repo.git
   ```

### Token Security Best Practices

> [!IMPORTANT]
> **Security Guidelines**:
>
> - **Never commit tokens to version control**
> - **Never share tokens in public channels**
> - **Use environment variables** or secure secret management
> - **Rotate tokens regularly** (every 90 days recommended)
> - **Use fine-grained tokens** when possible for minimal permissions
> - **Revoke tokens immediately** if compromised

### Common Token Issues

#### Issue: "Resource not accessible by integration" (HTTP 403)

**Cause**: Token lacks required permissions or is the wrong type.

**Solutions**:

1. Verify token starts with `ghp_` (Classic PAT)
2. Ensure `repo` scope is selected
3. Check token hasn't expired
4. Verify token has access to the specific repository

#### Issue: "Bad credentials" (HTTP 401)

**Cause**: Invalid or expired token.

**Solutions**:

1. Verify token is correct (no extra spaces/characters)
2. Check token expiration date
3. Regenerate token if expired

#### Issue: Token works locally but not in CI/CD

**Cause**: Token not properly configured in CI environment.

**Solutions**:

1. Add token as GitHub Secret in repository settings
2. Reference secret in workflow: `${{ secrets.GITHUB_TOKEN }}` or `${{ secrets.PAT_TOKEN }}`
3. Ensure CI workflow has `permissions:` section configured

## PR Workflow Best Practices

### Before Creating a PR

- [ ] Code follows project style guidelines
- [ ] All tests pass locally
- [ ] Documentation is updated (if needed)
- [ ] Commit messages are clear and descriptive
- [ ] Branch is up-to-date with target branch
- [ ] No merge conflicts exist

### During PR Review

- [ ] Respond to review comments promptly
- [ ] Address all CI/CD failures
- [ ] Keep PR focused on a single feature/fix
- [ ] Update PR description if scope changes
- [ ] Request re-review after making changes

### After PR is Merged

- [ ] Delete the feature branch (if not auto-deleted)
- [ ] Update local main branch:
  ```bash
  git checkout main
  git pull origin main
  ```
- [ ] Clean up any local branches:
  ```bash
  git branch -d feature-branch-name
  ```

## Troubleshooting

### PR Creation Fails

**Problem**: Cannot create PR via API/CLI

**Check**:

1. Token has `repo` scope
2. Token is valid and not expired
3. Branch exists and is pushed to remote
4. You have write access to the repository

### Merge Conflicts

**Problem**: PR has merge conflicts

**Solution**:

```bash
git fetch origin main
git checkout your-branch
git rebase origin/main  # or git merge origin/main
# Resolve conflicts
git add .
git rebase --continue  # or git commit
git push --force-with-lease
```

### CI/CD Failures

**Problem**: Tests or formatting checks fail

**Common Issues**:

- **Formatting**: Run `black` (Python) or `prettier` (Frontend) locally
- **Linting**: Fix linting errors before pushing
- **Tests**: Run tests locally and fix failures
- **Dependencies**: Ensure `package-lock.json` or `requirements.txt` are updated

### Token Not Working with GitHub CLI

**Problem**: `gh` CLI commands fail with token

**Solution**:

```bash
# Authenticate with token
gh auth login --with-token <<< "ghp_your_token_here"

# Or set environment variable
export GITHUB_TOKEN=ghp_your_token_here
gh pr list
```

## Additional Resources

- [GitHub Personal Access Tokens Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [GitHub API Documentation](https://docs.github.com/en/rest)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [Project Contributing Guidelines](../CONTRIBUTING.md)

## Requesting Token Access

If you need a token for automated PR operations:

1. **Create your own token** following the steps above (recommended)
2. **Request token from maintainers** (for CI/CD systems):
   - Open an issue or discussion
   - Explain the use case
   - Specify required permissions
   - Maintainers will provide guidance

> [!NOTE]
> For security reasons, maintainers typically cannot provide pre-generated tokens. You'll need to create your own token with the appropriate permissions.

---

**Last Updated**: 2026-01-30  
**Maintained By**: Project Contributors
