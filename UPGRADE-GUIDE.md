# mAI Upgrade Guide

This document describes the process for upgrading mAI (a customized fork of Open WebUI) to newer versions while preserving customizations.

## Last Upgrade: v0.6.16 → v0.6.17

**Date:** January 19, 2025  
**Performed by:** Claude Code AI Assistant

### Overview

Successfully upgraded mAI from Open WebUI v0.6.16 to v0.6.17, preserving all custom branding, features, and Polish localization.

### Prerequisites

Before starting any upgrade:

1. **Ensure clean working directory**
   ```bash
   git status  # Should show no uncommitted changes
   ```

2. **Have upstream remote configured**
   ```bash
   git remote -v  # Should show upstream pointing to open-webui/open-webui
   ```
   
   If not configured:
   ```bash
   git remote add upstream https://github.com/open-webui/open-webui.git
   ```

3. **Be on your customization branch**
   ```bash
   git checkout customization
   ```

### Step-by-Step Upgrade Process

#### 1. Create Backup Branch
Always create a backup before major updates:
```bash
git checkout -b backup-before-[VERSION]-update
git checkout customization
```

#### 2. Fetch Latest Changes
```bash
git fetch upstream --tags
```

#### 3. Merge Upstream Version
```bash
git merge v[VERSION]  # e.g., v0.6.17
```

#### 4. Resolve Merge Conflicts

Common conflict areas in mAI:

**a) package.json**
- Keep "name": "mai" (not "open-webui")
- Update version number to match upstream
- Preserve any custom dependencies

**b) Chat Component (src/lib/components/chat/Chat.svelte)**
- Preserve custom background pattern functionality
- Keep mAI-specific UI customizations
- Merge new features carefully

**c) Translation Files**
- Polish translation (pl-PL/translation.json) often has conflicts
- Generally accept upstream changes unless they override customizations
- May need to manually clean up conflict markers

**d) Workflow Files (.github/workflows/)**
- Often cannot be pushed without special GitHub permissions
- May need to revert these changes if you don't have workflow scope

#### 5. Update Dependencies
Due to major dependency updates (like Tiptap v2 → v3):
```bash
npm install --force
```

#### 6. Build and Test
```bash
npm run build  # Should complete without errors
npm run check  # Type checking (may show warnings)
```

#### 7. Commit and Push
```bash
git add -A
git commit -m "merge: update to Open WebUI v[VERSION] while preserving mAI customizations"
git push origin customization
```

### Handling Common Issues

#### Workflow Permission Errors
If you get errors about workflow files when pushing:
```bash
git checkout HEAD~1 -- .github/workflows/[filename]
git add .github/workflows/[filename]
git commit -m "revert: restore original workflow file"
git push origin customization
```

#### Polish Translation Conflicts
If the Polish translation has many conflicts:
1. Try accepting upstream version: `git checkout --theirs src/lib/i18n/locales/pl-PL/translation.json`
2. Or use a script to clean conflict markers while preserving upstream changes

#### Dependency Conflicts
When npm install fails:
1. Delete `node_modules` and `package-lock.json`
2. Run `npm install --force`
3. Commit the new `package-lock.json`

### mAI Customizations to Preserve

Always ensure these customizations remain intact:

1. **Branding**
   - Application name: "mAI" (not "Open WebUI")
   - Custom tagline: "You + AI = superpowers! 🚀"
   - Polish tagline: "Ty + AI = supermoce! 🚀"

2. **Custom Features**
   - Background patterns in chat interface
   - Background opacity controls
   - Any custom theme modifications

3. **File Locations**
   - Logo assets: `static/static/`
   - Custom CSS: `static/custom.css`
   - Theme files: `static/themes/`

### Post-Upgrade Checklist

- [ ] Application builds successfully
- [ ] Development server starts without errors
- [ ] mAI branding is preserved
- [ ] Custom background patterns work
- [ ] Polish translations are intact
- [ ] All new features from upstream are working
- [ ] No regression in existing functionality

### Version History

| From Version | To Version | Date | Major Changes | Notes |
|--------------|------------|------|---------------|-------|
| 0.6.16 | 0.6.17 | 2025-01-19 | Tiptap v3, Folder features, Note improvements | Workflow file reverted due to permissions |

### Troubleshooting

**Build Failures**
- Check for unresolved merge conflicts: `grep -r "<<<<<<< HEAD" src/`
- Ensure all dependencies are installed: `npm install --force`
- Clear build cache: `rm -rf .svelte-kit build`

**Runtime Errors**
- Check browser console for errors
- Verify all environment variables are set
- Ensure backend is compatible with frontend version

**Git Issues**
- If merge goes wrong: `git merge --abort`
- To reset to backup: `git reset --hard backup-before-[VERSION]-update`
- Check commit history: `git log --oneline -10`

### Resources

- [Open WebUI Releases](https://github.com/open-webui/open-webui/releases)
- [Open WebUI Changelog](https://github.com/open-webui/open-webui/blob/main/CHANGELOG.md)
- [mAI Repository](https://github.com/pilpat/mAI)

### Future Improvements

Consider automating parts of this process:
1. Script to handle common merge conflicts
2. Automated testing suite for customizations
3. GitHub Action for dependency updates (with proper permissions)