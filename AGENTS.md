# Agent Guide

This repository powers **PlusAI** at `plusai.art`, a product-led Open WebUI fork expected to diverge substantially over time. Product requirements take priority when they are explicit; keep changes modular so useful upstream improvements can still be adopted selectively. Keep this file short: load detailed context from [`docs/ai-context/`](docs/ai-context/README.md) only when it is relevant to the task.

## Start here

1. Read [`docs/ai-context/README.md`](docs/ai-context/README.md) and the task-specific files it routes to.
2. Check `git status --short` before editing. Preserve all unrelated and pre-existing changes.
3. If `.codegraph/` exists, use CodeGraph before broad text search when locating symbols or tracing behavior. Otherwise use `rg`/`rg --files`.
4. Re-read the current source around every symbol you change. Context documents are maps, not substitutes for code.

## Sources of truth

Use this precedence when information conflicts:

1. Current repository source, manifests, migrations, and tests.
2. Repository context in `docs/ai-context/`.
3. Official Open WebUI documentation at <https://docs.openwebui.com/>.
4. Assumptions, which must be stated and verified before they affect behavior.

The context bundle was grounded at commit `01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`. Verify time-sensitive details against the current checkout.

## Working rules

- Prefer cohesive, isolated product changes. Preserve upstream compatibility where it reduces maintenance, but do not let it override an explicit product requirement.
- Do not change public API shapes, persisted data, configuration semantics, or provider payloads incidentally.
- Never read, quote, copy, commit, or expose secrets from `.env`, data directories, databases, logs, or key files. Use `.env.example` for documented examples.
- Treat Tools, Functions, Pipes, Filters, Pipelines, and MCP integrations as privileged execution surfaces. Preserve authentication, access-control, validation, and sanitization boundaries.
- For database changes, update SQLAlchemy models and add an Alembic migration; do not edit an applied migration.
- Frontend API calls belong in `src/lib/apis/`; shared state belongs in `src/lib/stores/`; backend HTTP surfaces belong in `backend/open_webui/routers/` unless they are deliberate app-level compatibility endpoints.
- Do not run formatters or code generators across unrelated files. Do not erase user changes to make checks pass.

## Validation

Choose the smallest checks that cover the changed surface, then expand when risk crosses subsystems:

- Frontend types/build: `nvm exec npm run check`, `nvm exec npm run build`
- Frontend tests: `nvm exec npm run test:frontend`
- Frontend formatting check: use Prettier's check mode on changed files; repository `nvm exec npm run format` rewrites broadly
- Backend formatting/lint: `ruff format --check <paths>` and `ruff check <paths>`
- Backend tests: run targeted `pytest` tests when present
- Documentation-only changes: validate links/paths and run `git diff --check`

Before handing off, report checks run, checks not run, and any pre-existing working-tree changes left untouched.
