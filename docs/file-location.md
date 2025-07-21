# Key File Locations

## Configuration Files

### Core Configuration
- `backend/open_webui/config.py` - Main backend configuration
- `backend/open_webui/constants.py` - Application constants  
- `src/lib/constants.ts` - Frontend constants
- `svelte.config.js` - SvelteKit configuration
- `vite.config.ts` - Vite build configuration

### Environment & Build
- `.env` - Environment variables (local)
- `package.json` - NPM dependencies and scripts
- `pyproject.toml` - Python dependencies and config
- `requirements.txt` - Python requirements
- `docker-compose.yaml` - Docker development setup

## Backend Structure

### API & Routes
- `backend/open_webui/routers/` - FastAPI route handlers
  - `auth.py` - Authentication endpoints
  - `chats.py` - Chat management
  - `models.py` - Model management
  - `users.py` - User management

### Data Models
- `backend/open_webui/models/` - SQLAlchemy ORM models
  - `users.py` - User model
  - `chats.py` - Chat model
  - `auths.py` - Authentication model

### Utilities
- `backend/open_webui/utils/` - Utility functions
  - `misc.py` - General utilities, logging
  - `auth.py` - Authentication helpers
  - `webhook.py` - Webhook handling

### Static Assets (Backend)
- `backend/open_webui/static/` - Backend static files
  - `favicon.ico` - Main favicon
  - `favicon.png` - PNG favicon
  - `logo.png` - Application logo

## Frontend Structure

### Core Components
- `src/lib/components/` - Reusable Svelte components
  - `chat/` - Chat interface components
    - `Chat.svelte` - Main chat component (background patterns)
    - `Placeholder.svelte` - Custom branding placeholder
    - `Messages/` - Message rendering components
    - `MessageInput.svelte` - Chat input component
  - `common/` - Shared UI components
  - `layout/` - Layout components

### Pages & Routes
- `src/routes/` - SvelteKit pages and layouts
  - `+layout.svelte` - Root layout
  - `+page.svelte` - Home page
  - `auth/` - Authentication pages
  - `c/[id]/` - Chat pages

### State Management
- `src/lib/stores/` - Svelte stores for global state
  - `user.ts` - User state
  - `chats.ts` - Chat state  
  - `models.ts` - Model state
  - `settings.ts` - Application settings

### API Integration
- `src/lib/apis/` - Frontend API client functions
  - `auth/` - Authentication API calls
  - `chats/` - Chat API calls
  - `models/` - Model API calls
  - `users/` - User API calls

### Internationalization
- `src/lib/i18n/` - Internationalization files
  - `locales/` - Translation files by language
    - `en-US/translation.json` - English translations
    - `pl-PL/translation.json` - Polish translations (customized)
  - `index.ts` - i18n configuration

## Static Assets (Frontend)

### Branding Assets
- `static/static/` - Main static assets
  - `favicon.ico` - Browser favicon (complete mAI identity)
  - `favicon.png` - PNG favicon (complete mAI identity)
  - `logo.svg` - SVG logo (complete mAI identity)
  - `apple-touch-icon.png` - iOS icon
  - `android-chrome-*.png` - Android icons

### PWA Assets
- `static/manifest.json` - PWA manifest with mAI branding
- `static/sw.js` - Service worker (if present)

### Themes & Styling
- `static/themes/` - Custom theme definitions
  - `dark.css` - Dark theme
  - `light.css` - Light theme
  - `oled.css` - OLED theme
- `static/custom.css` - Custom CSS overrides

### Source Assets
- `mai_logos/` - Source files for all mAI graphic assets (11 files)
  - Original design files
  - Various formats and sizes
  - Brand guidelines assets

## Build Output

### Frontend Build
- `build/` - SvelteKit production build output
  - `_app/` - Application bundles
  - `static/` - Static assets
  - `index.html` - Main HTML file

### Backend Build
- `backend/data/` - Runtime data directory
  - `webui.db` - SQLite database (default)
  - `uploads/` - User uploaded files
  - `vector_db/` - Vector database files

## Development Files

### Configuration
- `.vscode/` - VS Code settings
- `.cursor/` - Cursor AI settings
  - `rules/project.mdc` - Project-specific rules
- `.gitignore` - Git ignore patterns
- `.prettierrc` - Prettier configuration
- `eslint.config.js` - ESLint configuration

### Documentation
- `docs/` - Project documentation
  - `development/` - Development guides
  - `deployment/` - Deployment instructions
  - `customization/` - mAI-specific docs
  - `operations/` - Operations guides
- `README.md` - Project overview
- `CHANGELOG.md` - Version history

## Database Files

### SQLAlchemy Models
- `backend/open_webui/models/` - Database models
- `backend/alembic/` - Database migrations
  - `versions/` - Migration files
  - `alembic.ini` - Alembic configuration

### Vector Databases
- `backend/data/vector_db/` - Vector database storage
  - ChromaDB files
  - Qdrant data
  - Other vector DB backends

## Critical Files for mAI Customizations

### Must Preserve During Upgrades
- `package.json` - Keep "name": "mai"
- `src/lib/components/chat/Chat.svelte` - Background pattern functionality
- `src/lib/components/chat/Placeholder.svelte` - Custom branding
- `src/lib/i18n/locales/pl-PL/translation.json` - Polish customizations
- `static/static/*` - All favicon and logo assets
- `static/manifest.json` - PWA manifest with mAI branding
- `src/app.html` - Favicon references

### Backup Before Changes
- `static/static/` - All branding assets
- `static/themes/` - Custom themes
- `static/custom.css` - Custom styling
- `src/lib/i18n/locales/pl-PL/` - Polish translations