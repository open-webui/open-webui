# Cloud Agent Prompt: Fix Heroku Deployment

Use this prompt with a cloud agent (e.g., Cursor, GitHub Copilot, or similar) to continue deployment work.

---

## Copy-paste prompt for agent

```
Please help achieve a successful Heroku deployment for the DSL KidsGPT Open WebUI project.

CONTEXT: The app (dsl-kidsgpt-pilot) uses Heroku buildpack stack (heroku-24) with Node.js + Python buildpacks. The build fails with:

  FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory

during `npm run build`. The build runs: (1) pyodide:fetch (loads Pyodide in Node – memory-heavy) and (2) vite build (900+ modules).

REQUIRED FIX: Set NODE_OPTIONS to increase Node heap so the build succeeds. Run:

  heroku config:set NODE_OPTIONS="--max-old-space-size=4096" -a dsl-kidsgpt-pilot

If you cannot run Heroku CLI, modify package.json build script to prepend NODE_OPTIONS:

  "build": "NODE_OPTIONS=--max-old-space-size=4096 npm run pyodide:fetch && NODE_OPTIONS=--max-old-space-size=4096 vite build"

REFERENCE FILES (read these for full context):
- @PROJECT_CONTEXT_EXPORT.md – Full deployment context and fixes applied
- @docs/HEROKU_DEPLOYMENT.md – Heroku guide and troubleshooting
- @deployment-summary.txt – High-level deployment summary
- @vite.config.ts – Vite resolve aliases (svelte-confetti, paneforge, bits-ui, @melt-ui/svelte)
- @package.json – engines, build script, dependencies

VERIFICATION: After applying the fix, `npm run build` must succeed locally. Then push to Heroku and confirm the build completes.
```

---

## Files the agent should read

| File | Purpose |
|------|---------|
| `PROJECT_CONTEXT_EXPORT.md` | Full context: fixes, blockers, config, debugging |
| `docs/HEROKU_DEPLOYMENT.md` | Heroku deployment guide and troubleshooting |
| `deployment-summary.txt` | Short deployment summary |
| `vite.config.ts` | Vite resolve config and package aliases |
| `package.json` | Build scripts, engines, dependencies |
| `Procfile` | Release and web process commands |
| `heroku.yml` | Docker config (if using container stack) |

---

## If the agent can run Heroku CLI

```bash
heroku config:set NODE_OPTIONS="--max-old-space-size=4096" -a dsl-kidsgpt-pilot
git push heroku main
heroku logs --tail -a dsl-kidsgpt-pilot
```

---

## If the agent cannot run Heroku CLI

Edit `package.json` and change the build script:

```json
"build": "NODE_OPTIONS=--max-old-space-size=4096 npm run pyodide:fetch && NODE_OPTIONS=--max-old-space-size=4096 vite build"
```

Commit, push to main, and instruct the user to run:

```bash
git push heroku main
```
