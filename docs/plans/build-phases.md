# Open Cowork UI Implementation Plan

## Goal

Ship Open Cowork UI on top of Open WebUI v0.11.4: a theme, projects, a task inbox, and agent-limited projects, in that order, each phase leaving the app working.

## Context

Design is in the specs under `../specs/` and the decisions in `../adr/`. Phase 0 is finished: the `losus-ai` organization exists, the fork `losus-ai/opencowork-ui` exists, the `cowork` branch is pushed at the v0.11.4 commit, and a local clone with the right git identity is in place (see [the fork process](../process/fork-and-upstream-rebase.md)).

Some facts below were observed in the v0.11.4 source on 2026-10-09 and are marked as such in the specs. Everything else came from planning conversations and is a hypothesis until a verification task confirms it.

## Tasks

### Verification (do these first, build nothing yet)

- [ ] Confirm `git log -1` on `cowork` is `8bd8b4fac` and `package.json` says 0.11.4
- [ ] Run the unmodified app (standard image or dev servers) and confirm login, a chat and a folder work
- [ ] Read the bodies of the "Listed" routes in [agent-limited projects](../specs/agent-limited-projects.md) and update the table
- [ ] Confirm the Alembic head is still `d4c1a8e37b62`, and that migrations are applied on startup in this setup
- [ ] Confirm how folder deletion works upstream and whether an extension row needs a cascade
- [ ] Confirm which chat-page component renders the model selector (for the lock chip)
- [ ] Confirm the `--cw-*` tokens and the `dark` class behave in the running app

### Phase 1: baseline

- [ ] Build a Docker image from the fork and run it on the Spark
- [ ] Record the exact build and run commands in the process doc

Done when the unmodified fork behaves like the stock install.

### Phase 2: theme and branding

- [ ] Add the `--cw-*` tokens to `static/static/custom.css` (light and dark)
- [ ] Add the `cowork_setting` table and migration
- [ ] Add the generated-CSS route
- [ ] Build `ThemeSettings` and mount it in the settings area
- [ ] Check the license condition before changing any app name or logo

Done when light and dark both read correctly and the accent can be changed.

### Phase 3: projects

- [ ] Add `cowork_project` and its migration
- [ ] Add the project routes (list, create, update)
- [ ] Build `ProjectsSection`, `ProjectOverview` and the projects store
- [ ] Mount the projects section in `Sidebar.svelte`

Done when a new project holds chats and appears in the sidebar.

### Phase 4: task inbox

- [ ] Add `cowork_task` and `cowork_intake_key` and their migration
- [ ] Add the intake-key dependency, the push route and the task routes
- [ ] Emit the `cowork:task` socket event
- [ ] Build `InboxSection`, `TaskCard`, `TaskFilters` and the tasks store
- [ ] Add the open-chat route and test it end to end with `curl`

Done when a pushed task appears live and "Resolve" opens a chat seeded with its payload.

### Phase 5: agent-limited projects

- [ ] Add `cowork_project_agent` and its migration
- [ ] Write `check_project_agent_access` and wire it into every route in the table
- [ ] Add the knowledge and tool isolation behavior
- [ ] Add the route-inventory test
- [ ] Build `ProjectAccess`, `AgentAllowList`, `RestrictedBanner`, `AgentLockChip` and `AgentBlockedNotice`

Done when each enforcement row has a test that returns 403 for a disallowed agent.

### Phase 6: harden

- [ ] Rehearse a rebase onto the next upstream release
- [ ] Back up the new tables
- [ ] Write a short runbook

Done when the rebase builds without manual fixes.

## Notes

- Do not edit upstream files beyond `Sidebar.svelte`, the chat page and the router registration in `main.py` without recording why.
- Open questions are listed at the end of each spec; resolve them in the phase that needs them.
