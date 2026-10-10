# 0001. Fork Open WebUI at v0.11.4 into the losus-ai organization

## Status

Accepted

## Context

Losus AI wants a workspace UI with a projects sidebar, an inbox where backend agents push issues that open a chat with the right agent, projects restricted to specific agents, and its own theme. Open WebUI already provides the chat core, model connections, auth, retrieval and folders.

The wanted features need new database tables, new backend routes and Svelte changes. A stock Docker image with only `custom.css` cannot provide them.

Open WebUI's license is BSD-3-style with a branding clause (clause 4). Observed in the v0.11.4 LICENSE: the "Open WebUI" name and logo may not be altered or removed unless the deployment has 50 or fewer end users in any rolling 30 days, written permission exists, or an enterprise license is held. The repo's `static/BRANDING.md` repeats this.

Upstream's latest release when checked on 2026-10-09 was v0.11.4 (released 2026-09-21). Its release notes include access-control and knowledge-base access fixes.

## Decision

We will fork `open-webui/open-webui` into the `losus-ai` GitHub organization as `opencowork-ui`, base the work on the v0.11.4 commit, and keep all work on a branch named `cowork`. `main` stays a mirror of upstream. The `upstream` remote stays configured so later releases can be rebased in.

## Consequences

- We own a long-lived fork and must rebase `cowork` onto each upstream release we adopt. The cost grows with every upstream file we edit, so new code goes in new files.
- The branding clause applies. Until the 50-user, permission or enterprise condition is confirmed, the Open WebUI name and logo stay where the license protects them.
- Code we write in new files belongs to its author and can carry its own terms. Upstream notices must be kept in the fork and in distributed builds. This is not legal advice; a lawyer should confirm before the product is sold or redistributed.
- Starting from a tagged release gives a tested base instead of a moving `main`.

## Alternatives considered

- Stock image plus `custom.css` only: rejected because it cannot add tables, routes or sidebar sections.
- Branching from upstream `main`: rejected in favor of the tagged release.

## Related decisions

- [0002. Projects extend upstream folders](0002-projects-extend-upstream-folders.md)
- [0003. Agent-limited projects are enforced on the server](0003-agent-limited-projects-enforced-on-server.md)
