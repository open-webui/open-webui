# Open Cowork UI

Open Cowork UI is Losus AI's fork of Open WebUI. It adds a projects sidebar, an agent task inbox that backend processes push issues into, agent-limited projects (a project that only specific agents may work in), and a custom theme.

- Repository: `losus-ai/opencowork-ui` on GitHub
- Base version: Open WebUI v0.11.4 (commit `8bd8b4fac`, merged 2026-09-21)
- Working branch: `cowork` (`main` mirrors upstream and receives no commits)
- Status: planning finished, no product code written yet

## Decisions (ADRs)

- [0001. Fork Open WebUI at v0.11.4 into the losus-ai organization](adr/0001-fork-open-webui-at-v0-11-4.md)
- [0002. Projects extend upstream folders](adr/0002-projects-extend-upstream-folders.md)
- [0003. Agent-limited projects are enforced on the server](adr/0003-agent-limited-projects-enforced-on-server.md)
- [0004. Cowork API prefix and project-scoped intake keys](adr/0004-cowork-api-prefix-and-scoped-intake-keys.md)

## Specs

- [Projects and tasks](specs/projects-and-tasks.md): data model, API, live updates
- [Agent-limited projects](specs/agent-limited-projects.md): the rules and the routes they apply to
- [Frontend components](specs/frontend-components.md): five screens mapped to Svelte components
- [Theme and branding](specs/theme-and-branding.md): tokens, `custom.css`, license limits

## Plans

- [Build phases](plans/build-phases.md)
- [TODO](plans/TODO.md)

## Process

- [Fork, local layout and upstream rebase](process/fork-and-upstream-rebase.md)

## Investigations

- [2026-10-09: routes that start or continue a chat](investigate/2026-10-09-chat-routes.md)

## Outside references

- Five-screen mockup (Claude artifact): https://claude.ai/artifact/AGtb5uEbi3uLFevywXt8Tx
- Original fork plan (Claude doc): https://claude.ai/artifact/WDC4kHEBz8sU39DwGUXZP8

## How these docs were produced

They were drafted in a planning session with Claude, then checked against the v0.11.4 source on 2026-10-09. Claims marked "observed" were read from that source. Everything else is a hypothesis for the repo session to verify; see the verification tasks in [Build phases](plans/build-phases.md).
