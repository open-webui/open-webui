# Repository Guidelines

## Project Structure & Module Organization
Frontend code lives in `src/`: routes `src/routes/(app)`, components `src/lib/components`, locales `src/lib/i18n`, assets `static/`. Backend services sit in `backend/open_webui` with routers in `routers/`, data models in `models/`, and migrations/utilities in `internal/`. Persistent data is stored under `backend/data`, Cypress specs in `cypress/`, deployment scripts and manifests at the root.

## Build, Test, and Development Commands
Run `npm install` then `npm run dev` (or `dev:5050`) to serve the UI after the Pyodide fetch. `npm run build` creates production bundles and `npm run preview` validates them. The API runs with `pip install -r backend/requirements.txt` plus `python -m uvicorn open_webui.main:app --reload`, or via `docker compose up -d` / `make install`. Keep hygiene with `npm run lint`, `npm run format`, and `npm run check`.

## Architecture & LLM Endpoints
`backend/open_webui/main.py` wires CORS, session, audit middleware, and serves the compiled frontend. `routers/openai.py` and `routers/ollama.py` proxy chat, embedding, and image calls to remote runners, applying per-model params, optional user headers, and streaming responses. `routers/models.py`, `routers/retrieval.py`, and `socket/main.py` handle model CRUD, retrieval pipelines, and realtime updates, with Redis coordination when websockets are enabled.

## Coding Style & Naming Conventions
Frontend follows Prettier/ESLint: two-space indents, camelCase state, PascalCase components, kebab-case filenames with colocated CSS. Backend honors Black (4 spaces) and Pylint, using snake_case for functions/modules and CapWords for classes; share helpers in `backend/open_webui/utils` and mount new routers from `backend/open_webui/routers`.

## Testing Guidelines
Use `npm run test:frontend` (Vitest), `npm run cy:open` (Cypress), and `pytest backend/open_webui/test`; house fixtures in `test/test_files` or `backend/open_webui/test/util` and name suites `test_<feature>.py`.

## Commit & Pull Request Guidelines
Prefix commits with `feat:`, `fix:`, `refac`, `doc:`, etc., keeping subjects ≤72 characters. PRs should summarize the change, list env/config additions, link issues, include command logs (`npm run lint`, `pytest`), and attach screenshots or traces for UI/contract tweaks.

## Security & Configuration Tips
`backend/start.sh` loads `WEBUI_SECRET_KEY` and JWT values from env or `.webui_secret_key`; do not commit secrets. Mount `backend/data` in Docker (`-v open-webui:/app/backend/data`) to retain user content and validate credentials before enabling Ollama, Playwright, or external tool servers.

## Fork Maintenance & Upstream Sync
Active fork: `Arconte112/open-webui-soren`; `upstream` targets `open-webui/open-webui`. Keep work on feature branches (e.g., `doc/repository-guidelines`) and merge through PRs. To sync releases safely: `git checkout main`, `git fetch upstream`, `git merge upstream/main` (or `git rebase`), resolve conflicts, rerun `npm run lint`, `pytest`, `npm run test:frontend`, then `git push origin main`. Rebase active branches onto the refreshed `main` before continuing.
