# Customization Workflows

## Branch Strategy

### Core Rules
- **ALWAYS** work on `customization` branch (never commit to main)
- **ALWAYS** create backups before modifications: `cp -r static/static customization-backup/static-$(date +%Y%m%d)`
- **Main branch**: Keep clean for upstream merges from Open WebUI
- **Feature branches**: Create from `customization` for specific improvements

### Branch Commands
```bash
# Switch to customization branch
git checkout customization

# Create feature branch
git checkout -b feature/new-theme customization

# Merge feature to customization
git checkout customization
git merge feature/new-theme
```

## Customization Process

### Asset Modification Workflow
1. **Create Backup**
   ```bash
   cp -r static/static customization-backup/static-$(date +%Y%m%d)
   ```

2. **Make Changes**
   - Logo files: `static/static/` and `backend/open_webui/static/`
   - CSS overrides: `static/custom.css`
   - Themes: `static/themes/`

3. **Test Requirements**
   - All theme variants (Light/Dark/OLED/"Her")
   - Mobile responsiveness
   - WCAG 2.1 AA compliance
   - Contrast ratios 4.5:1 minimum

4. **Commit with Proper Prefix**
   ```bash
   git add .
   git commit -m "brand: Update logo assets and favicon"
   ```

### Commit Prefixes
- `brand:` - Logo, branding, identity changes
- `theme:` - Color schemes, CSS theme modifications
- `ui:` - User interface, layout changes
- `assets:` - Static assets, images, icons
- `i18n:` - Internationalization, translations
- `fix:` - Bug fixes
- `feat:` - New features

## Asset Requirements

### Logo Guidelines
- **File Size**: <100KB per file
- **Formats**: PNG for logos, ICO for favicons, SVG for scalable graphics
- **Dimensions**: Multiple sizes for responsive design
- **Quality**: High resolution for retina displays

### Accessibility Standards
- **WCAG 2.1 AA Compliance**: Required for all UI elements
- **Contrast Ratios**: Minimum 4.5:1 for normal text, 3:1 for large text
- **Color Independence**: Information not conveyed by color alone
- **Keyboard Navigation**: All interactive elements accessible

## Upgrading from Open WebUI

### Pre-Upgrade Preparation
1. **Ensure Clean Working Directory**
   ```bash
   git status  # Should be clean
   git stash   # If needed
   ```

2. **Create Backup Branch**
   ```bash
   git checkout customization
   git branch backup-before-upgrade-$(date +%Y%m%d)
   ```

3. **Verify Upstream Remote**
   ```bash
   git remote -v
   git remote add upstream https://github.com/open-webui/open-webui.git
   ```

### Merge Process
1. **Fetch Upstream**
   ```bash
   git fetch upstream
   git fetch upstream --tags
   ```

2. **Merge Specific Version**
   ```bash
   git merge v0.6.17  # Replace with target version
   ```

3. **Resolve Conflicts**
   - **Critical Files to Preserve**:
     - `package.json`: Keep "name": "mai"
     - `src/lib/components/chat/Chat.svelte`: Background pattern functionality
     - `src/lib/i18n/locales/pl-PL/translation.json`: Polish customizations
     - All theme and asset files in `static/`

### Post-Merge Tasks
1. **Update Dependencies**
   ```bash
   npm install --force
   ```

2. **Build and Test**
   ```bash
   npm run build
   npm run check
   npm run lint
   ```

3. **Revert Workflow Files** (if lacking GitHub permissions)
   ```bash
   git checkout HEAD~1 -- .github/workflows/
   ```

4. **Document Changes**
   - Update version in CLAUDE.md
   - Note any new conflicts in upgrade guide
   - Test all customizations work properly

## Theme Development

### Custom Theme Creation
1. **Create Theme File**
   ```bash
   # Create new theme in static/themes/
   cp static/themes/dark.css static/themes/my-theme.css
   ```

2. **Modify CSS Variables**
   ```css
   :root {
     --primary-color: #your-color;
     --background-color: #your-bg;
     /* ... other variables */
   }
   ```

3. **Test All Variants**
   - Light mode compatibility
   - Dark mode compatibility
   - OLED mode compatibility
   - Mobile responsiveness

### Background Pattern System
- **Location**: `src/lib/components/chat/Chat.svelte`
- **CSS**: `static/custom.css`
- **Opacity Controls**: Built-in opacity adjustment
- **Pattern Options**: Geometric, abstract, minimal patterns

## Quality Assurance

### Pre-Commit Checklist
- [ ] All theme variants tested
- [ ] Mobile responsiveness verified
- [ ] Accessibility standards met
- [ ] Build passes without errors
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Backup created
- [ ] Proper commit prefix used

### Testing Commands
```bash
# Quality checks
npm run check && npm run lint && npm run build

# Theme testing
# Manually test: Settings > Appearance > Theme switcher

# Mobile testing
# Use browser dev tools responsive mode
```

## Documentation Maintenance

### Keep Updated
- Version numbers in CLAUDE.md
- New conflicts in upgrade guide
- Changed file locations
- New dependencies or requirements

### File Organization
- **Main docs**: `docs/` directory with subdirectories
- **Deployment**: `docs/deployment/`
- **Development**: `docs/development/`
- **Customization**: `docs/customization/`
- **Operations**: `docs/operations/`