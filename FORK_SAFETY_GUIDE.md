# Fork Safety Guide - Preventing Accidental Pushes to Upstream

## Overview
This guide ensures you never accidentally push your custom changes to the original Open WebUI repository.

## Initial Setup

### 1. Fork Configuration
When you clone, always clone YOUR fork, not the original:
```bash
# CORRECT - Clone your fork
git clone https://github.com/YOUR-USERNAME/open-webui.git xynthorai-open-webui

# WRONG - Don't clone the original
# git clone https://github.com/open-webui/open-webui.git
```

### 2. Remote Configuration
Set up remotes properly:
```bash
cd xynthorai-open-webui

# Your fork should be 'origin' (standard Git convention)
git remote -v
# origin    git@github.com:YOUR-USERNAME/open-webui.git (fetch)
# origin    git@github.com:YOUR-USERNAME/open-webui.git (push)

# Add upstream as read-only
git remote add upstream https://github.com/open-webui/open-webui.git
git remote set-url --push upstream DISABLE
```

### 3. Verify Remote Safety
```bash
# Check push URLs
git remote -v
# origin    https://github.com/YOUR-USERNAME/open-webui.git (fetch)
# origin    https://github.com/YOUR-USERNAME/open-webui.git (push)
# upstream  https://github.com/open-webui/open-webui.git (fetch)
# upstream  DISABLE (push)  <-- This prevents accidental pushes
```

## Protection Methods

### Method 1: Disable Push to Upstream
```bash
# Completely disable push to upstream
git remote set-url --push upstream DISABLE

# Or use a non-existent URL
git remote set-url --push upstream no_push
```

### Method 2: Git Hook Protection
Create `.git/hooks/pre-push`:
```bash
#!/bin/bash
# Prevent push to upstream repository

protected_remote="upstream"
protected_urls=(
    "github.com/open-webui/open-webui"
    "github.com:open-webui/open-webui"
)

remote="$1"
url="$2"

# Check if pushing to protected remote
if [ "$remote" = "$protected_remote" ]; then
    echo "⛔ ERROR: Pushing to upstream is not allowed!"
    echo "Push to your fork instead: git push origin"
    exit 1
fi

# Check if URL contains protected patterns
for protected_url in "${protected_urls[@]}"; do
    if [[ "$url" == *"$protected_url"* ]]; then
        echo "⛔ ERROR: Pushing to Open WebUI upstream repository is not allowed!"
        echo "This looks like the upstream repository: $url"
        echo "Push to your fork instead."
        exit 1
    fi
done

exit 0
```

Make it executable:
```bash
chmod +x .git/hooks/pre-push
```

### Method 3: Global Git Config
Add to `~/.gitconfig`:
```ini
[url "DISABLE"]
    pushInsteadOf = https://github.com/open-webui/open-webui.git
    pushInsteadOf = git@github.com:open-webui/open-webui.git
```

### Method 4: Branch Protection
```bash
# Create a custom branch for all your work
git checkout -b custom-dpl-integration

# Never work directly on main
git branch -m main upstream-main

# Create your own main
git checkout -b main
```

## Safe Workflow

### 1. Daily Development
```bash
# Always work on custom branches
git checkout -b feature/my-customization

# Commit your changes
git add .
git commit -m "Add custom feature"

# Push to YOUR fork only
git push origin feature/my-customization
```

### 2. Syncing with Upstream
```bash
# Fetch upstream changes (safe - read only)
git fetch upstream

# Merge upstream changes to your branch
git checkout main
git merge upstream/main

# Push to YOUR fork
git push origin main
```

### 3. Creating Pull Requests
- Create PRs from YOUR fork to YOUR fork's main branch
- Never create PRs to open-webui/open-webui
- If you want to contribute back, create a separate clean branch

## Verification Commands

### Check Your Remotes
```bash
# List all remotes
git remote -v

# Ensure upstream has DISABLE or no_push for push URL
git config --get remote.upstream.pushurl
# Should output: DISABLE or no_push
```

### Test Push Safety
```bash
# This should fail
git push upstream main
# fatal: 'DISABLE' does not appear to be a git repository

# This should work (to your fork)
git push origin main
```

### Check Current Branch
```bash
# See what branch you're on
git branch --show-current

# See all branches
git branch -a
```

## Recovery Procedures

### If You Accidentally Push to Wrong Remote
1. Don't panic - if set up correctly, the push should fail
2. If it somehow succeeded:
   - Immediately contact the repository maintainers
   - Prepare a revert PR if needed
   - Learn from the mistake and add more protections

### Reset Your Fork
If your fork gets messy:
```bash
# Save your custom patches first!
cp -r patches ~/backup-patches

# Reset to upstream
git fetch upstream
git checkout main
git reset --hard upstream/main
git push origin main --force

# Reapply your patches
cp -r ~/backup-patches patches
git add patches
git commit -m "Restore custom patches"
```

## Additional Safety Tips

### 1. Use Different SSH Keys
```bash
# ~/.ssh/config
Host github-fork
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_rsa_fork

Host github-upstream
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_rsa_readonly
```

### 2. Visual Reminders
Add to your shell prompt:
```bash
# ~/.bashrc or ~/.zshrc
git_safety_check() {
    if git remote -v 2>/dev/null | grep -q "open-webui/open-webui"; then
        echo "⚠️  UPSTREAM DETECTED - BE CAREFUL!"
    fi
}
PS1='$(git_safety_check)'$PS1
```

### 3. Separate Directories
```bash
# Keep upstream clean for reference
~/projects/open-webui-upstream/  # Never modify

# Your working directory
~/projects/xynthorai-open-webui/    # All customizations here
```

### 4. Use Aliases
```bash
# ~/.gitconfig
[alias]
    push-safe = push origin
    push-fork = push origin
    push-check = remote -v
```

## Checklist Before Starting Work

- [ ] Cloned from YOUR fork, not upstream
- [ ] Upstream remote is set to DISABLE for push
- [ ] Pre-push hook is installed
- [ ] Working on custom branch, not main
- [ ] Patches directory is backed up
- [ ] Remote URLs verified with `git remote -v`

## Emergency Contacts

If you accidentally push to upstream:
1. Open WebUI Discord: https://discord.gg/5rJgQTnV4s
2. Create an issue immediately explaining the situation
3. Prepare a revert commit if needed

Remember: It's always better to be overly cautious when working with forks!