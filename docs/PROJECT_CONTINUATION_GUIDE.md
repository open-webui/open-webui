# Project Continuation Guide

**Last Updated**: 2026-01-30  
**Project**: DSL KidsGPT Open WebUI  
**Repository**: https://github.com/jjdrisco/DSL-kidsgpt-open-webui

This document provides all necessary information to continue development on this project, including features in development, token requirements, workflows, and documentation locations.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features in Development](#features-in-development)
3. [GitHub Token Requirements](#github-token-requirements)
4. [Cypress Testing Workflow](#cypress-testing-workflow)
5. [Development Setup](#development-setup)
6. [Project Structure](#project-structure)
7. [Documentation Index](#documentation-index)
8. [Recent Changes & Context](#recent-changes--context)
9. [CI/CD Information](#cicd-information)
10. [Troubleshooting Quick Reference](#troubleshooting-quick-reference)

---

## Project Overview

This is a fork of Open WebUI customized for a research study involving children and AI interactions. The project includes:

- **Moderation workflow** for parents to review AI responses
- **Child profile system** with personality-based scenario generation
- **Survey system** for data collection (initial survey, exit survey)
- **Workflow management** for tracking study progress
- **Cypress E2E testing** for critical user flows

**Base Framework**: Open WebUI (SvelteKit + FastAPI)  
**Version**: 0.7.2  
**Node.js**: v20.x (required for Cypress)  
**Python**: 3.12+

---

## Features in Development

### 1. Separate Quiz Workflow (Recently Merged - PR #10)

**Status**: ✅ Merged to main (2026-01-30)

**Key Changes**:
- Separated quiz/survey workflow from main chat interface
- Added "Survey View" and "Chat View" navigation buttons
- Improved sidebar visibility logic for survey pages
- Fixed navigation issues with "Open WebUI" and "New Chat" buttons

**Related Files**:
- `src/lib/components/layout/Sidebar/UserMenu.svelte` - Survey/Chat View buttons
- `src/lib/components/admin/Settings/General.svelte` - Open WebUI button
- `src/lib/components/layout/Sidebar.svelte` - New Chat navigation
- `src/routes/(app)/+layout.svelte` - Sidebar visibility logic
- `src/routes/(app)/+page.svelte` - Root route handling

### 2. Moderation & Survey System

**Status**: Active Development

**Components**:
- **Moderation Scenario Flow**: Parents review AI responses to child prompts
- **Initial Survey**: Collects child profile and personality data
- **Exit Survey**: Post-study data collection
- **Personality-Based Scenarios**: Generates scenarios from child profile characteristics

**Key Routes**:
- `/moderation-scenario` - Main moderation interface
- `/initial-survey` - Child profile creation
- `/exit-survey` - Post-study survey
- `/kids/profile` - Child profile management
- `/parent` - Parent dashboard

**Documentation**: See `docs/MODERATION_SURVEY_FLOW.md` and `docs/SCENARIO_SYSTEM.md`

### 3. Workflow Management

**Status**: Active Development

**Endpoints**:
- `GET /workflow/state` - Current workflow state
- `GET /workflow/current-attempt` - Attempt tracking
- `GET /workflow/session-info` - Session information
- `GET /workflow/completed-scenarios` - Completed scenarios
- `GET /workflow/study-status` - Study completion status
- `POST /workflow/reset` - Reset workflow
- `POST /workflow/reset-moderation` - Reset moderation only
- `POST /workflow/moderation/finalize` - Finalize moderation

**Testing**: See `cypress/e2e/workflow.cy.ts`

### 4. Child Profile Features

**Status**: Active Development

**Features**:
- Child profile creation with personality traits
- Parent-child profile management
- Profile-based scenario generation
- Attention check integration

**Testing**: See `cypress/e2e/kids-profile.cy.ts` and `cypress/e2e/parent-child-profile.cy.ts`

---

## GitHub Token Requirements

### For Pull Request Operations

**Token Type**: Classic Personal Access Token (PAT)  
**Token Format**: Starts with `ghp_`  
**Required Scopes**:
- ✅ **`repo`** - Full control of private repositories (includes PR operations)
- ✅ **`read:org`** (optional but recommended) - For org-related queries

### Creating a Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: "PR Management Token" (or similar)
4. Expiration: 90 days (or custom)
5. Select scopes: **`repo`** (all sub-scopes)
6. Generate and **copy immediately** (starts with `ghp_`)

### Using the Token

```bash
# Set as environment variable
export GITHUB_TOKEN=ghp_your_token_here

# Or use with GitHub CLI
gh auth login --with-token <<< "ghp_your_token_here"

# Or configure git remote
git remote set-url origin https://ghp_your_token_here@github.com/username/repo.git
```

### Common Issues

- **"Resource not accessible by integration" (HTTP 403)**: Token lacks `repo` scope or is wrong type (must be `ghp_`, not `ghs_`)
- **"Bad credentials" (HTTP 401)**: Token expired or invalid
- **Token works locally but not in CI/CD**: Add as GitHub Secret and reference in workflow

**Full Documentation**: See `docs/PULL_REQUEST_WORKFLOW.md`

---

## Cypress Testing Workflow

### Prerequisites

1. **Node.js v20.x** (required - Cypress has compatibility issues with v22)
2. **Python 3.12+** for backend
3. **System dependencies** (Linux):
   ```bash
   sudo apt-get update
   sudo apt-get install -y xvfb libgtk-3-0 libgbm-dev libnotify-dev libnss3 libxss1
   ```

### Installation

```bash
# Install frontend dependencies (use --legacy-peer-deps for Node v20 compatibility)
npm install --legacy-peer-deps

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

### Running Tests

#### 1. Start Services

**Backend** (port 8080):
```bash
cd backend
./start.sh
# Or: PORT=8080 python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

**Frontend** (port 5173 or 5174):
```bash
npm run dev
# Note the port Vite prints
```

#### 2. Run Tests

**Workflow API Tests**:
```bash
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173  # Use actual port
xvfb-run -a npx cypress run --headless --spec cypress/e2e/workflow.cy.ts
```

**Child Profile Tests**:
```bash
RUN_CHILD_PROFILE_TESTS=1 CYPRESS_baseUrl=http://localhost:5173 \
  npx cypress run --headless --spec "cypress/e2e/kids-profile.cy.ts,cypress/e2e/parent-child-profile.cy.ts"
```

**All Tests**:
```bash
RUN_CHILD_PROFILE_TESTS=1 CYPRESS_baseUrl=http://localhost:5173 \
  xvfb-run -a npx cypress run --headless
```

**Interactive Mode** (requires display):
```bash
npx cypress open
```

### Test Account

**Default Credentials**:
- Email: `jjdrisco@ucsd.edu`
- Password: `0000`

**Override with Environment Variables**:
- `INTERVIEWEE_EMAIL` / `INTERVIEWEE_PASSWORD` (kids spec)
- `PARENT_EMAIL` / `PARENT_PASSWORD` (parent spec)
- `TEST_EMAIL` / `TEST_PASSWORD` (both)

### Available Test Suites

| Test File | Description |
|-----------|-------------|
| `workflow.cy.ts` | Workflow API endpoints and state management |
| `kids-profile.cy.ts` | Child profile creation and management |
| `parent-child-profile.cy.ts` | Parent-child profile interactions |
| `navigation.cy.ts` | Navigation and routing tests |
| `chat.cy.ts` | Chat interface tests |
| `registration.cy.ts` | User registration flow |
| `settings.cy.ts` | Settings page tests |
| `documents.cy.ts` | Document management tests |

### Common Issues

- **Missing X server**: Use `xvfb-run -a` wrapper for headless execution
- **Frontend/Backend not running**: Verify services on correct ports
- **Authentication failures**: Check test account exists and credentials match
- **Dependency conflicts**: Always use `npm install --legacy-peer-deps`
- **Node.js v22 crashes**: Use Node.js v20.x instead

**Full Documentation**: See `docs/CYPRESS_TEST_SETUP.md` and `cypress/README_CHILD_PROFILE_TESTS.md`

---

## Development Setup

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Backend
OLLAMA_BASE_URL='http://localhost:11434'
OPENAI_API_BASE_URL=''
OPENAI_API_KEY=''
CORS_ALLOW_ORIGIN='*'
FORWARDED_ALLOW_IPS='*'

# Analytics
SCARF_NO_ANALYTICS=true
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false
```

### Development Commands

```bash
# Frontend development
npm run dev              # Start dev server (port 5173/5174)
npm run build           # Production build
npm run format          # Format frontend code (prettier)
npm run i18n:parse      # Parse i18n translations

# Backend development
cd backend
./start.sh              # Start backend (port 8080)
python -m black .       # Format Python code

# Testing
npm run cy:open         # Open Cypress UI
npm run test:frontend   # Run frontend unit tests
```

### Code Formatting

**Frontend**:
```bash
npm run format          # Prettier (JS/TS/Svelte/CSS/MD/HTML/JSON)
npm run i18n:parse      # Parse and format i18n files
```

**Backend**:
```bash
python -m black . --exclude ".venv/|/venv/"
```

**CI Requirements**:
- Black version: 26.1.0 (check `pyproject.toml`)
- Prettier: Latest (from `package.json`)
- All files must pass formatting checks before PR merge

---

## Project Structure

```
/workspace/
├── backend/                    # FastAPI backend
│   ├── open_webui/            # Main application
│   │   ├── routers/           # API routes
│   │   ├── models/            # Database models
│   │   ├── internal/          # Internal utilities
│   │   └── migrations/        # Database migrations
│   ├── requirements.txt       # Python dependencies
│   └── start.sh              # Backend startup script
│
├── src/                       # SvelteKit frontend
│   ├── lib/
│   │   ├── components/       # Reusable components
│   │   │   ├── layout/      # Layout components (Sidebar, etc.)
│   │   │   ├── admin/       # Admin components
│   │   │   └── chat/        # Chat components
│   │   ├── routes/          # Page routes
│   │   │   └── (app)/       # Authenticated routes
│   │   │       ├── moderation-scenario/
│   │   │       ├── exit-survey/
│   │   │       ├── initial-survey/
│   │   │       ├── kids/profile/
│   │   │       └── parent/
│   │   └── i18n/            # Internationalization
│   └── routes/               # Route definitions
│
├── cypress/                  # E2E tests
│   ├── e2e/                 # Test files
│   │   ├── workflow.cy.ts
│   │   ├── kids-profile.cy.ts
│   │   ├── parent-child-profile.cy.ts
│   │   └── ...
│   └── support/             # Test utilities
│
├── docs/                     # Documentation
│   ├── CONTRIBUTING.md
│   ├── PULL_REQUEST_WORKFLOW.md
│   ├── CYPRESS_TEST_SETUP.md
│   ├── MODERATION_SURVEY_FLOW.md
│   ├── SCENARIO_SYSTEM.md
│   └── ...
│
├── .github/                  # GitHub config
│   ├── workflows/           # CI/CD workflows
│   └── pull_request_template.md
│
├── package.json             # Frontend dependencies
├── pyproject.toml          # Python project config
└── README.md               # Main project README
```

---

## Documentation Index

### Core Documentation

| Document | Location | Description |
|----------|----------|-------------|
| **Project Continuation Guide** | `docs/PROJECT_CONTINUATION_GUIDE.md` | This document - comprehensive project overview |
| **Contributing Guidelines** | `docs/CONTRIBUTING.md` | General contribution guidelines |
| **PR Workflow & Tokens** | `docs/PULL_REQUEST_WORKFLOW.md` | Pull request process and GitHub token setup |
| **Cypress Test Setup** | `docs/CYPRESS_TEST_SETUP.md` | Cypress testing setup and configuration |
| **Child Profile Tests** | `cypress/README_CHILD_PROFILE_TESTS.md` | Child profile test details |

### Feature Documentation

| Document | Location | Description |
|----------|----------|-------------|
| **Moderation Survey Flow** | `docs/MODERATION_SURVEY_FLOW.md` | Moderation workflow and decision tree |
| **Scenario System** | `docs/SCENARIO_SYSTEM.md` | Scenario generation and management |
| **Moderation Tool** | `docs/MODERATION_TOOL_DOCUMENTATION.md` | Moderation tool features |
| **Survey Implementation** | `docs/SURVEY_IMPLEMENTATION.md` | Survey system details |

### Infrastructure Documentation

| Document | Location | Description |
|----------|----------|-------------|
| **Heroku Backup Setup** | `docs/HEROKU_BACKUP_SETUP.md` | Heroku deployment and backup |
| **Apache Configuration** | `docs/apache.md` | Apache server setup |
| **Security Guidelines** | `docs/SECURITY.md` | Security practices and reporting |

### Additional Resources

- **Main README**: `README.md` - Project overview and installation
- **Database README**: `backend/README_DATABASE.md` - Database setup
- **Docs Index**: `docs/README.md` - Documentation overview

---

## Recent Changes & Context

### Recently Merged (2026-01-30)

**PR #10: Feature: Separate Quiz Workflow**
- Separated survey/quiz workflow from main chat interface
- Added navigation buttons for "Survey View" and "Chat View"
- Fixed sidebar visibility on survey pages
- Improved "Open WebUI" and "New Chat" button navigation

**Key Files Changed**:
- `src/lib/components/layout/Sidebar/UserMenu.svelte`
- `src/lib/components/admin/Settings/General.svelte`
- `src/lib/components/layout/Sidebar.svelte`
- `src/routes/(app)/+layout.svelte`
- `src/routes/(app)/+page.svelte`

### Active Development Areas

1. **Moderation System**: Ongoing improvements to scenario selection and moderation workflow
2. **Child Profile System**: Personality-based scenario generation
3. **Survey System**: Initial and exit survey flows
4. **Workflow Management**: State tracking and progress management
5. **Cypress Testing**: Expanding test coverage for critical flows

### Important Context

- **User Types**: The system supports multiple user types (parent, child, admin, interviewee) with different workflows
- **Prolific Integration**: Special handling for Prolific study participants
- **Personality-Based Scenarios**: Scenarios are generated from child profile characteristics, not hardcoded
- **Attention Checks**: Randomly injected into moderation scenarios for data quality
- **Session Management**: Uses localStorage for scenario package persistence

---

## CI/CD Information

### GitHub Workflows

Located in `.github/workflows/`:

- **`format-backend.yaml`**: Python code formatting with Black (3.11.x and 3.12.x)
- **`format-build-frontend.yaml`**: Frontend formatting (Prettier), i18n parsing, and build
- **`build-release.yml`**: Release builds
- **`deploy-to-hf-spaces.yml`**: HuggingFace Spaces deployment
- **`docker-build.yaml`**: Docker image builds

### CI Requirements

**Backend Formatting**:
- Black version: 26.1.0 (see `pyproject.toml`)
- Must format all Python files before PR merge
- Command: `python -m black . --exclude ".venv/|/venv/"`

**Frontend Formatting**:
- Prettier for JS/TS/Svelte/CSS/MD/HTML/JSON
- i18n parsing required
- Command: `npm run format && npm run i18n:parse`

**Frontend Build**:
- Requires `package-lock.json` (must be committed)
- Uses `npm ci` (not `npm install`)
- Node.js v20.x recommended

### Common CI Failures

1. **Formatting Mismatches**: Local formatter version differs from CI
   - **Fix**: Upgrade local Black to 26.1.0, run formatters locally

2. **Missing package-lock.json**: Required for `npm ci`
   - **Fix**: Run `npm install --package-lock-only` and commit

3. **Syntax Errors**: Prettier/Black can't parse files
   - **Fix**: Fix syntax errors, then format

4. **Line Ending Issues**: CRLF vs LF conflicts
   - **Fix**: Use `git config core.autocrlf false` or normalize line endings

---

## Troubleshooting Quick Reference

### Git Issues

**Problem**: Can't pull changes, "local changes would be overwritten"
```bash
# Check what's modified
git status

# Stash changes
git stash

# Pull
git pull origin main

# Restore stashed changes
git stash pop
```

**Problem**: Line ending conflicts (CRLF vs LF)
```bash
# Force sync with remote
git fetch origin main
git reset --hard origin/main
```

### Development Issues

**Problem**: Frontend won't start
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

**Problem**: Backend won't start
```bash
# Check Python version (need 3.12+)
python --version

# Install dependencies
cd backend
pip install -r requirements.txt

# Check port availability
lsof -i :8080
```

**Problem**: Cypress tests fail
```bash
# Verify Node.js version (need v20.x)
node --version

# Verify services running
curl http://localhost:8080/health
curl http://localhost:5173

# Check test account exists
# Verify credentials match environment variables
```

### PR Issues

**Problem**: Can't create PR via API
- Verify token has `repo` scope
- Token must start with `ghp_` (Classic PAT)
- Check token hasn't expired

**Problem**: CI formatting failures
- Run formatters locally: `npm run format` and `python -m black .`
- Commit formatted files
- Ensure Black version matches CI (26.1.0)

---

## Quick Start Checklist

When starting work on this project:

- [ ] **Environment Setup**
  - [ ] Node.js v20.x installed
  - [ ] Python 3.12+ installed
  - [ ] Dependencies installed (`npm install --legacy-peer-deps`, `pip install -r requirements.txt`)
  - [ ] `.env` file configured

- [ ] **GitHub Access**
  - [ ] GitHub token created (Classic PAT with `repo` scope)
  - [ ] Token configured (`export GITHUB_TOKEN=ghp_...`)

- [ ] **Documentation Review**
  - [ ] Read `docs/CONTRIBUTING.md`
  - [ ] Read `docs/PULL_REQUEST_WORKFLOW.md`
  - [ ] Read `docs/CYPRESS_TEST_SETUP.md` (if working on tests)
  - [ ] Read relevant feature docs (`MODERATION_SURVEY_FLOW.md`, etc.)

- [ ] **Development Workflow**
  - [ ] Create feature branch from `main`
  - [ ] Make changes and test locally
  - [ ] Run formatters (`npm run format`, `python -m black .`)
  - [ ] Run tests if applicable
  - [ ] Commit with clear messages
  - [ ] Push and create PR targeting `main` or `dev` (check project guidelines)

---

## Contact & Support

- **Repository**: https://github.com/jjdrisco/DSL-kidsgpt-open-webui
- **Documentation**: See `docs/` directory
- **Issues**: Use GitHub Issues for bug reports
- **Discussions**: Use GitHub Discussions for questions

---

**Last Updated**: 2026-01-30  
**Maintained By**: Project Contributors
