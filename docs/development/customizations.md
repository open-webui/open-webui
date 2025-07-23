# mAI Customizations Checklist

This document lists all custom mAI features that must be preserved during Open WebUI updates.

## 🎯 Critical Custom Features to Check

### 1. **Application Branding** (Commit: `9ae41e806`)
**Files to check:**
- `package.json` - Keep `"name": "mai"` 
- `src/lib/constants.ts` - Keep `APP_NAME = "mAI"`
- `backend/open_webui/env.py` - Keep `WEBUI_NAME = "mAI"`
- `src/app.html` - Title and meta tags with "mAI"
- `pyproject.toml` - Project name and description
- PWA manifests: `static/static/site.webmanifest`, `backend/open_webui/static/site.webmanifest`
- `static/opensearch.xml` - Search provider name

**✅ What to verify:** Application shows "mAI" not "Open WebUI" in browser title, PWA name, search descriptions

### 2. **Custom Tagline** (Commits: `8f0e70f3c`, `e2d5e937f`)
**Files to check:**
- `src/lib/components/chat/Placeholder.svelte` - Main tagline display with Polish support
- `src/lib/constants.ts` - `APP_TAGLINE` constant
- `src/app.html` - Meta description with tagline
- PWA manifests - Description fields
- `static/opensearch.xml` - Description with tagline

**✅ What to verify:** 
- English: "You + AI = superpowers! 🚀"
- Polish: "Ty + AI = supermoce! 🚀" (when interface is Polish)
- Appears in chat placeholder, browser meta, PWA description

### 3. **Background Patterns Feature** (Commits: `4366bab6f`, `bb5084e36`, `deba899e1`)
**Location:** Settings > General Tab > Background Pattern section

**Files to check:**
- `src/lib/components/chat/Chat.svelte` - Pattern integration in chat container
- `src/lib/components/chat/Settings/General.svelte` - Settings UI (moved from Appearance tab)
- `src/lib/components/chat/SettingsModal.svelte` - Settings modal integration
- `static/static/custom.css` - CSS pattern definitions
- `backend/open_webui/static/custom.css` - Backend static CSS
- Translation files with pattern setting keys

**✅ What to verify:**
- General tab contains "Background Pattern" section
- Pattern Type dropdown: None, Dots, Grid, Diagonal
- Pattern Opacity slider (0-100%)
- Patterns display correctly in chat interface
- Works in both light/dark themes

### 4. **Complete mAI Visual Identity System** (Commit: `c17dee8b0`)
**Location:** All graphic assets replaced across frontend and backend

**Files to check:**
- `static/static/` - Frontend assets (11 files)
- `backend/open_webui/static/` - Backend assets (11 files)  
- `mai_logos/` - Source files folder

**Assets list:**
- `logo.png` - Main application logo
- `favicon.png`, `favicon.svg`, `favicon-dark.png`, `favicon-96x96.png` - Browser favicons
- `ai-assistant.svg` - AI assistant icon
- `splash.png`, `splash-dark.png` - Splash screen graphics
- `apple-touch-icon.png` - iOS app icon
- `web-app-manifest-192x192.png`, `web-app-manifest-512x512.png` - PWA icons

**✅ What to verify:**
- Main logo appears in application interface (not OWUI logo)
- Browser tabs show mAI favicon
- PWA installation uses mAI icons
- Splash screens display mAI branding
- All assets properly sized and displaying correctly

### 5. **Custom mAI Themes** (Based on screenshot)
**Location:** Settings > General Tab > Theme section

**Themes to verify exist:**
- 🔧 **mAI Professional** (brown/professional theme)
- ⚡ **mAI Minimalist** (lightning bolt theme)
- 🎨 **mAI Creative** (purple/creative theme)  
- 🔥 **mAI Warm** (orange/warm theme)
- Plus standard themes: System, OLED Dark

**✅ What to verify:**
- All custom mAI themes appear in theme selector
- Themes apply correctly when selected
- Theme names include "mAI" branding
- Custom colors and styling work properly

### 5. **Font Size Feature** (Visible in screenshot)
**Location:** Settings > General Tab > Font Size section

**Files to check:**
- Settings components with font size controls
- Font size application in chat messages

**✅ What to verify:**
- Font Size dropdown with Normal/other options
- "Adjust text size for chat messages and hints" description
- Font changes apply correctly to chat interface

### 6. **Polish Localization** (Commit: `1b79baf9b`)
**Files to check:**
- `src/lib/i18n/locales/pl-PL/translation.json` - Complete Polish translation
- `src/lib/components/chat/Placeholder.svelte` - Language-aware tagline

**✅ What to verify:**
- 373 Polish translation entries are intact
- Tagline switches to Polish when interface language is Polish
- All UI elements properly translated

### 7. **Error Handling Improvements** (Commit: `e2d5e937f`)
**Files to check:**
- `backend/open_webui/utils/middleware.py:1085` - Follow-up generation error handling

**✅ What to verify:**
- Ollama model failures don't crash chat sessions
- Background tasks protected with try-catch blocks
- No "model runner has unexpectedly stopped" errors

### 8. **OpenRouter Model Restriction Feature** (Commits: `709d3ff27`, `158790e28`, `529a3e31d`, `cbc228cb6`)
**Location:** Admin Settings & Backend Configuration

**Files to check:**
- `/scripts/openrouter/production_fix.py` - Production-ready initialization script
- `/scripts/openrouter/manage_models.py` - Model management utility
- `/scripts/openrouter/fix_openrouter_docker.py` - Direct database fix for Docker
- `/scripts/openrouter/verify_config.py` - Configuration verification tool
- `/docs/openrouter/README.md` - Comprehensive documentation hub
- `/docs/openrouter/production-config.md` - Production best practices
- `/docs/openrouter/manage-models.md` - Model management guide
- `/docs/openrouter/quick-reference.md` - Quick reference guide
- **Dockerfile** - Scripts now included in Docker image (line 173)

**✅ What to verify:**
- **Scripts are included in Docker image** (no manual copying needed)
- Admin can configure model restrictions via scripts
- Support for 12 specific OpenRouter models:
  - anthropic/claude-sonnet-4
  - google/gemini-2.5-flash
  - google/gemini-2.5-pro
  - deepseek/deepseek-chat-v3-0324
  - anthropic/claude-3.7-sonnet
  - google/gemini-2.5-flash-lite-preview-06-17
  - openai/gpt-4.1
  - x-ai/grok-4
  - openai/gpt-4o-mini
  - openai/o4-mini-high
  - openai/o3
  - openai/chatgpt-4o-latest
- Configuration persists across restarts
- Scripts function correctly in Docker environments
- Same configuration applies to all 20 company deployments

## 📋 Post-Update Testing Checklist

### Core Branding
- [ ] Browser title shows "mAI" not "Open WebUI"
- [ ] PWA name is "mAI" when installed
- [ ] Chat placeholder shows correct tagline
- [ ] Package.json name remains "mai"
- [ ] **Visual Identity Assets:** All mAI logos and icons display correctly
- [ ] **Main logo:** Application interface shows mAI logo (not OWUI)
- [ ] **Favicons:** Browser tabs show mAI favicon
- [ ] **PWA icons:** App installation uses mAI icons

### Settings > General Tab
- [ ] Theme section shows all custom mAI themes
- [ ] Background Pattern section exists with dropdown and slider
- [ ] Font Size section with description and dropdown
- [ ] All controls function properly

### Background Patterns
- [ ] Pattern Type dropdown: None/Dots/Grid/Diagonal
- [ ] Pattern Opacity slider functions (0-100%)
- [ ] Patterns display in chat interface
- [ ] Works in both light and dark themes

### Custom Themes
- [ ] mAI Professional theme works
- [ ] mAI Minimalist theme works  
- [ ] mAI Creative theme works
- [ ] mAI Warm theme works
- [ ] Theme switching functions properly

### Language Features
- [ ] Polish interface fully translated
- [ ] Tagline switches: English → "You + AI = superpowers! 🚀"
- [ ] Tagline switches: Polish → "Ty + AI = supermoce! 🚀"

### Error Handling
- [ ] No Ollama crashes during chat
- [ ] Background tasks don't interrupt main flow
- [ ] Error messages are graceful

### OpenRouter Configuration
- [ ] Model restriction configuration accessible to admins
- [ ] 12 specific models appear when configured
- [ ] Wildcard patterns work (e.g., "openai/*")
- [ ] Configuration persists after restart
- [ ] Scripts in /scripts/openrouter/ execute properly

## 🚨 Critical Files Never to Lose

1. `src/lib/components/chat/Placeholder.svelte` - **Main tagline & branding**
2. `src/lib/components/chat/Chat.svelte` - **Background patterns integration**
3. `src/lib/components/chat/Settings/General.svelte` - **Custom settings UI**
4. `src/lib/constants.ts` - **App name and tagline constants**
5. `package.json` - **Keep name as "mai"**
6. `static/static/custom.css` - **Pattern CSS + custom theme definitions**
7. `src/lib/i18n/locales/pl-PL/translation.json` - **Polish translations**
8. Custom theme files - **mAI branded themes**
9. `/scripts/openrouter/` - **OpenRouter configuration scripts**
10. `/docs/openrouter/` - **OpenRouter documentation**

## 🔄 Update Process Notes

1. **Always backup** before updating
2. **Check each file** in the critical files list
3. **Test all features** in the checklist
4. **Verify themes** work in both light/dark modes
5. **Test Polish language** switching
6. **Document any new conflicts** in docs/development/upgrade-guide.md

Last Updated: July 23, 2025 - OpenRouter Docker Integration