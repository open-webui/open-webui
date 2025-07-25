# mAI Development Changelog

This document tracks successful changes and improvements made to the mAI application.

## Format
**Date:** YYYY-MM-DD  
**Version:** Open WebUI version base  
**Type:** [FEATURE/FIX/UPDATE/THEME]  
**Impact:** [HIGH/MEDIUM/LOW]

---

## 2025-07-23 - OpenRouter Docker Integration 🐳

**Type:** UPDATE  
**Impact:** HIGH  
**Commit:** `cbc228cb6`

### ✅ Successfully Completed
- **Integrated OpenRouter scripts into Docker image** - No manual copying needed
- **Production-ready deployment** - Scripts included in build process
- **Multi-company ready** - Same image works for all 20 deployments

### 🎯 Implementation
- Added single line to Dockerfile: `COPY --chown=$UID:$GID ./scripts /app/scripts`
- Scripts now part of image, survive container recreation
- Initialization runs once per deployment

### 📝 Notes
- Eliminates manual script copying previously required
- Ensures consistency across all deployments
- Ready for Hetzner production deployment

---

## 2025-07-23 - OpenRouter Model Restriction & Repository Cleanup 🚀

**Type:** FEATURE + UPDATE  
**Impact:** HIGH  
**Commits:** `bef5dc1b6`, `529a3e31d`, `5481372d8`, `709d3ff27`, `e43f06e05`, `158790e28`

### ✅ Successfully Completed
- **Implemented OpenRouter model restriction** allowing admins to limit available models
- **Added wildcard pattern matching** for flexible model filtering (e.g., "openai/*", "anthropic/*")
- **Created production-ready configuration system** with database persistence
- **Organized all OpenRouter assets** into dedicated directories
- **Cleaned up repository** removing obsolete files and scripts
- **Comprehensive documentation** in /docs/openrouter/ directory

### 🎯 Features
- **Model Restriction Capabilities:**
  - Support for 12 curated OpenRouter models
  - Wildcard pattern matching for provider-based filtering
  - Environment variable and API-based configuration
  - Persistent configuration across restarts
  
- **Production Scripts Created:**
  - `production_fix.py` - Production-ready initialization
  - `manage_models.py` - Model management utility
  - `fix_openrouter_docker.py` - Docker-specific fixes
  - `verify_config.py` - Configuration verification

### 🏗️ Implementation Details
- **File Organization:**
  - Scripts moved to `/scripts/openrouter/`
  - Documentation centralized in `/docs/openrouter/`
  - Removed obsolete test files and backups
  
- **Supported Models:**
  - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, o1-preview, o1-mini
  - Anthropic: claude-3.5-sonnet:beta, claude-3.5-haiku:beta
  - Google: gemini-pro-1.5
  - X.AI: grok-2-latest
  - Meta: llama-3.1-405b-instruct
  - Perplexity: llama-3.1-sonar-huge-128k-online
  - DeepSeek: deepseek-coder

### 📝 Notes
- Feature provides cost control and simplified model selection
- Database-level implementation ensures consistency
- Comprehensive documentation for various deployment scenarios
- Repository is now cleaner and more maintainable

---

## 2025-07-23 - Documentation Structure Cleanup 📚

**Type:** UPDATE  
**Impact:** MEDIUM  
**Commit:** `d85f1c6eb`

### ✅ Successfully Completed
- **Cleaned up documentation structure** by removing outdated and redundant files
- **Updated CLAUDE.md** with current project status and simplified guidelines
- **Streamlined project documentation** for better maintainability
- **Applied changes consistently** across production, customization, and staging branches

### 🎯 Changes Made
- ✅ **Removed outdated files:**
  - `docs/customization/extraction-plan.md` - Obsolete extraction planning document
  - `docs/development/contributing.md` - Redundant contribution guidelines
- ✅ **Updated CLAUDE.md:**
  - Corrected recent status date to July 2025
  - Simplified branch strategy documentation
  - Removed redundant quick actions section
- ✅ **Updated docs/README.md** with current project structure

### 🏗️ Implementation Details
- **Branch consistency:** Applied same changes to production, customization, and staging
- **Conflict resolution:** Resolved merge conflicts during cherry-pick to staging branch
- **Documentation focus:** Maintained essential documentation while removing redundancy

### 📝 Notes
- Documentation now reflects current project state more accurately
- Reduced maintenance overhead by removing obsolete files
- Branch-specific documentation conflicts resolved cleanly

---

## 2025-01-20 - Complete mAI Visual Identity System 🎨

**Type:** FEATURE  
**Impact:** HIGH  
**Commit:** `c17dee8b0`

### ✅ Successfully Completed
- **Complete visual identity replacement** with custom mAI branding across all 11 graphic assets
- **Systematic replacement process** covering both frontend and backend locations
- **Source asset management** with dedicated mai_logos/ folder for future reference
- **Asset verification** ensuring all files replaced correctly with proper sizes

### 🎯 Assets Replaced
- ✅ **logo.png** - Main application logo (19.8KB)
- ✅ **favicon.png** - Browser favicon (19.8KB)  
- ✅ **favicon.svg** - Scalable favicon (3.2KB)
- ✅ **favicon-dark.png** - Dark theme favicon (20.1KB)
- ✅ **favicon-96x96.png** - Standard favicon size (4.7KB)
- ✅ **ai-assistant.svg** - AI assistant icon (3.2KB)
- ✅ **splash.png** - Light theme splash screen (19.8KB)
- ✅ **splash-dark.png** - Dark theme splash screen (20.1KB)
- ✅ **apple-touch-icon.png** - iOS app icon (7.3KB)
- ✅ **web-app-manifest-192x192.png** - PWA icon small (7.6KB)
- ✅ **web-app-manifest-512x512.png** - PWA icon large (19.5KB)

### 🏗️ Implementation Details
- **Frontend location:** `/static/static/` (11 files updated)
- **Backend location:** `/backend/open_webui/static/` (11 files updated)
- **Source management:** `/mai_logos/` folder created with all source files
- **Process:** Step-by-step systematic replacement with verification

### 📝 Notes
- All assets now display mAI branding throughout the application
- Browser cache clearing required to see changes immediately
- Complete visual consistency achieved across all interface elements

---

## 2025-01-19 - Open WebUI v0.6.17 Upgrade ⭐

**Type:** UPDATE  
**Impact:** HIGH  
**Commit:** `b6b8d8a61`, `41003e260`, `d648b8087`

### ✅ Successfully Completed
- **Merged Open WebUI v0.6.17** while preserving all mAI customizations
- **Upgraded Tiptap** from v2 to v3 for rich text editing
- **Installed FFmpeg** for full audio processing support
- **Resolved merge conflicts** in package.json, Chat.svelte, Polish translations
- **Updated dependencies** with `npm install --force`
- **Created comprehensive documentation** (UPGRADE-GUIDE.md, updated claude.md)

### 🎯 Preserved Features
- ✅ mAI branding (name, tagline, PWA manifests)
- ✅ Custom background patterns (moved to General tab)
- ✅ Polish localization with dynamic tagline
- ✅ Custom mAI themes (Professional, Minimalist, Creative, Warm)
- ✅ Error handling improvements for Ollama failures
- ✅ Font size controls

### 🚀 New Upstream Features Gained
- Dedicated folder views with chat lists
- Direct file uploads to folder knowledge
- Image upload and inline insertion in notes
- Chat preview in search results
- Copy notes as rich text
- Fade-in streaming text experience
- Configurable follow-up prompt settings
- Enhanced error handling and stability

### 📝 Notes
- Used `npm install --force` due to Tiptap v3 upgrade warnings
- Reverted workflow file to avoid GitHub permission issues
- FFmpeg resolves audio processing warnings

---

## 2025-01-18 - Polish Localization & Error Handling 🇵🇱

**Type:** FEATURE + FIX  
**Impact:** HIGH  
**Commits:** `1b79baf9b`, `e2d5e937f`

### ✅ Successfully Completed
- **Complete Polish translation** with 373 new entries for 100% localization
- **Language-aware tagline** that displays Polish version when interface is in Polish
- **Enhanced error handling** for Ollama model runner failures
- **Background task protection** to prevent chat crashes

### 🎯 Features
- Tagline switches automatically:
  - English: "You + AI = superpowers! 🚀"
  - Polish: "Ty + AI = supermoce! 🚀"
- Graceful handling of Ollama resource limitations
- Protected background tasks with try-catch blocks

---

## 2025-01-18 - Background Patterns Feature 🎨

**Type:** FEATURE  
**Impact:** MEDIUM  
**Commits:** `4366bab6f`, `bb5084e36`, `deba899e1`

### ✅ Successfully Completed
- **Restored background patterns** with dots, grid, and diagonal designs
- **Added pattern controls** in Settings (originally Appearance tab, moved to General)
- **Implemented opacity control** with real-time preview (0-100%)
- **Theme compatibility** for both light and dark modes

### 🎯 Features
- Pattern Type selector: None, Dots, Grid, Diagonal
- Live opacity adjustment with visual feedback
- CSS variable-based real-time updates
- Clean integration with existing settings

### 📝 Notes
- Initially created separate Appearance tab, later moved to General tab
- Optimized patterns for performance and visual appeal

---

## 2025-01-18 - Font Size & Content Scaling 📝

**Type:** FEATURE  
**Impact:** MEDIUM  
**Commit:** `e7b151544`

### ✅ Successfully Completed
- **Rebuilt font size feature** with improved controls
- **Fixed markdown content scaling** for better readability
- **Added font size selector** in General settings

### 🎯 Features
- Font size options: Normal and other sizes
- Proper scaling for chat messages and hints
- Markdown content properly adjusts with font changes

---

## 2025-01-18 - Core mAI Branding 🚀

**Type:** FEATURE  
**Impact:** HIGH  
**Commits:** `9ae41e806`, `8f0e70f3c`

### ✅ Successfully Completed
- **Renamed application** from "Open WebUI" to "mAI"
- **Added custom tagline** "You + AI = superpowers! 🚀"
- **Updated all branding touchpoints** (PWA, meta tags, manifests)
- **Maintained SEO and accessibility** standards

### 🎯 Brand Elements
- Application name: "mAI"
- Tagline: "You + AI = superpowers! 🚀"
- Package name: "mai"
- Updated in: browser title, PWA manifest, meta descriptions, search provider

### 📝 Notes
- Comprehensive branding update across frontend and backend
- Maintained Open WebUI functionality while establishing unique identity

---

## 2025-07-25 - Polish Złoty (PLN) Currency Conversion 💰

**Type:** FEATURE  
**Impact:** HIGH  
**Commit:** `8152c4821`

### ✅ Successfully Completed
- **Implemented Polish złoty (PLN) currency conversion** for all usage tracking displays
- **Integrated National Bank of Poland (NBP) API** for real-time exchange rates
- **Enhanced user interface** with dual currency display format: "$12.50 (50.00 zł)"
- **Added intelligent caching system** with NBP-aware refresh schedules
- **Implemented graceful fallback** when NBP API is unavailable

### 🎯 Features
- **Real-time Exchange Rates:**
  - Fetches USD/PLN rates from NBP Table C (sell rates)
  - Smart caching with 24-hour TTL and 8:15 AM CET refresh alignment
  - Weekend/holiday handling using most recent available rates
  - Exchange rate indicators with effective dates

- **Comprehensive UI Integration:**
  - Today's Cost cards show dual currency with live exchange rate
  - Monthly Total displays with Polish złoty equivalents
  - User and model usage tables include PLN columns
  - Exchange rate status notifications and warnings

- **Technical Implementation:**
  - Async NBP API client following OpenRouter client patterns
  - Non-blocking error handling preserves USD functionality
  - Enhanced currency formatting with Polish locale support
  - Proper resource cleanup in FastAPI lifespan management

### 🏗️ Implementation Details
- **Backend Components:**
  - `backend/open_webui/utils/nbp_client.py` - NBP API client with caching
  - `backend/open_webui/routers/client_organizations.py` - Enhanced APIs with PLN conversion
  - `backend/open_webui/main.py` - NBP client lifecycle management

- **Frontend Updates:**
  - `src/lib/components/admin/Settings/MyOrganizationUsage.svelte` - Dual currency display
  - Enhanced `formatCurrency()` and new `formatDualCurrency()` functions
  - Exchange rate status indicators and fallback messaging

- **API Response Enhancements:**
  - Added `cost_pln`, `exchange_rate`, `exchange_rate_date` fields
  - Root-level `exchange_rate_info` with NBP metadata
  - Graceful degradation flag `pln_conversion_available`

### 📝 Notes
- Provides transparent cost visibility for Polish business clients
- Maintains full backward compatibility with existing USD workflows
- No database schema changes required (conversion at API response time)
- Ready for 20+ Polish client deployments on Hetzner infrastructure

---

## Template for Future Entries

```markdown
## YYYY-MM-DD - [Feature Name] [Emoji]

**Type:** [FEATURE/FIX/UPDATE/THEME]  
**Impact:** [HIGH/MEDIUM/LOW]  
**Commit:** `commit-hash`

### ✅ Successfully Completed
- [What was implemented]
- [Key achievements]

### 🎯 Features
- [Specific features added]
- [User-facing improvements]

### 📝 Notes
- [Technical notes]
- [Lessons learned]
- [Future considerations]
```

---

**Legend:**
- ⭐ Major updates/upgrades
- 🇵🇱 Localization work  
- 🎨 UI/Design features
- 📝 Content/Text features
- 🚀 Core functionality
- 🔧 Technical improvements
- 🎭 Themes
- 🔊 Audio features