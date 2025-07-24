# CLAUDE.md

## Claude Behavior Guidelines

**CRITICAL RULES:**
- **NEVER test solutions by running development server** - user always has server running and sees changes in real time
- **ALWAYS work on `customization` branch** - never commit directly to main
- **ALWAYS create backups before asset modifications**: `cp -r static/static customization-backup/static-$(date +%Y%m%d)`
- **Focus on code verification** through build processes and type checking instead of runtime testing
- **Be specific and precise** - avoid unnecessary explanations, provide step-by-step solutions
- **Challenge user's assumptions** if they conflict with better task execution
- **Always update necessary .md files in docs folder** after commit changes
- **Always use Sequential thinking MCP** to solve complex problems

[Important!] User is the mAI provider (OWUI fork). The future of the project (always take this into account when designing solutions): mAI implementations for about 20 small companies in Poland, where each will have from 5 to 20 employees. Single Hetzner Cloud server running multiple Docker instances (one per client) with complete data isolation.

**Client User Structure (Per Instance):**
- **1 Admin User**: First person to register automatically becomes admin, manages OpenRouter API key and creates user accounts
- **4-19 Regular Users**: Created by admin through mAI web interface (Settings → Admin → Users)
- **Single Organization**: All users mapped to one organization per instance with individual external_user auto-learning
- **Automated Usage Tracking**: Each user gets unique external_user from OpenRouter, tracked under shared API key
**WORKFLOW PRIORITIES:**
1. Code quality and type safety first
2. Preserve all mAI customizations during changes
3. Follow commit prefixes: `brand:`, `theme:`, `ui:`, `assets:`
### Business model:
- hybrid pricing (subscription + token usage from OepenRouter x1.3)

## Project Overview

**mAI** - Customized Open WebUI fork
- **Frontend**: SvelteKit + TypeScript + TailwindCSS
- **Backend**: FastAPI + Python 3.11-3.12
- **Current Branch**: `customization` (main: `main`)
- **Key Features**: Complete mAI visual identity, custom background patterns, multi-language support

**Recent Status**: Successfully merged Open WebUI v0.6.18 preserving all customizations (July 2025)

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

##crawl4ai-mai MCP & Knowledge Integration
- **Before starting any task**: Use `get_available_sources` to check existing knowledge base
- **For implementation patterns**: Use `search_code_examples` before writing code
- **For research**: Use `perform_rag_query` with specific source filtering

##Research → Implement → Validate Workflow
1. **Research Phase**:
   - `query_knowledge_graph` for framework patterns
   - `search_code_examples` for specific implementations
   - `perform_rag_query` with source filtering for documentation