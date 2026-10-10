# 0004. Cowork API prefix and project-scoped intake keys

## Status

Proposed

## Context

Backend processes (the DGX agents, cron jobs, a lending backend) need to push issues into an inbox. The first mockup used `POST /api/v1/tasks`.

Observed in the v0.11.4 source: `main.py` already mounts upstream's own tasks router at `/api/v1/tasks`, and it serves title, tag and other generation helpers, not an inbox. A route there would collide with, and confuse, upstream code.

## Decision

All new routes live under `/api/v1/cowork/`. Task intake uses keys that start with `cw_`, are stored only as a hash plus a visible prefix, and are bound to exactly one project. A key is accepted only on the task-intake route, only for its own project, and never on upstream routes. Pushes carry an `external_key` so a repeated push updates the task instead of duplicating it.

## Consequences

- No route collisions with present or future upstream tasks routes.
- A leaked key can only add tasks to one project; revoking it is a single update.
- A separate authentication dependency must be written and tested, including a test that a key cannot reach any other route.
- Raw keys are shown once at creation and cannot be recovered.

## Related decisions

- [0003. Agent-limited projects are enforced on the server](0003-agent-limited-projects-enforced-on-server.md)
