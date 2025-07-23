# CLAUDE.md

## Claude Behavior Guidelines

**CRITICAL RULES:**
- **NEVER test solutions by running development server** - user always has server running and sees changes in real time
- **ALWAYS work on `customization` branch** - never commit directly to main
- **ALWAYS create backups before asset modifications**: `cp -r static/static customization-backup/static-$(date +%Y%m%d)`
- **Focus on code verification** through build processes and type checking instead of runtime testing
- **Be specific and precise** - avoid unnecessary explanations, provide step-by-step solutions
- **Challenge user's assumptions** if they conflict with better task execution

**WORKFLOW PRIORITIES:**
1. Code quality and type safety first
2. Preserve all mAI customizations during changes
3. Follow commit prefixes: `brand:`, `theme:`, `ui:`, `assets:`

## Project Overview

**mAI** - Customized Open WebUI fork
- **Frontend**: SvelteKit + TypeScript + TailwindCSS
- **Backend**: FastAPI + Python 3.11-3.12
- **Current Branch**: `customization` (main: `main`)
- **Key Features**: Complete mAI visual identity, custom background patterns, multi-language support

**Recent Status**: Successfully merged Open WebUI v0.6.17 preserving all customizations (July 2025)

## Detailed Documentation

**Development Commands & Scripts**: @docs/commands.md
**Architecture & Technical Details**: @docs/architecture.md  
**Docker & Deployment**: @docs/deployment.md
**Customization Workflows**: @docs/workflows.md
**File Locations & Structure**: @docs/file-locations.md

## Critical Customization Rules

**Files to Preserve During Upgrades:**
- `package.json`: Keep "name": "mai"
- `src/lib/components/chat/Chat.svelte`: Background pattern functionality
- `src/lib/i18n/locales/pl-PL/translation.json`: Polish customizations
- All theme and asset files in `static/`

**Branch Strategy:**
- Work only on `customization` branch
- Create feature branches for specific improvements
