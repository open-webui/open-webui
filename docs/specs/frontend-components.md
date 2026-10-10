# Frontend components specification

## Summary

The five mockup screens need about thirteen new Svelte components in one new folder, plus two small edits to upstream files. The chat view itself is reused.

## Goals

- Keep all new frontend code under `src/lib/components/cowork/` and new route files.
- Edit upstream files only where unavoidable, to keep rebases small.

## Design

Observed in the v0.11.4 source: the sidebar is `src/lib/components/layout/Sidebar.svelte` and renders folders and the chat list as `SidebarSection` blocks using `Folders` and `ChatItem`. The app routes live under `src/routes/(app)/` and include `c/[id]` (chat), `folders/[folderId]`, `workspace`, `channels`, `notes` and `admin`.

| Mockup screen | New components | Where it mounts |
| --- | --- | --- |
| Workspace (inbox and chat) | `InboxSection`, `TaskCard`, `TaskFilters` | Inbox section in the sidebar; list view on a new inbox route; opening a task goes to the normal chat route |
| Project overview | `ProjectOverview`, `ProjectActivity`, `IntakeCard` | New project route |
| Project access and agents | `ProjectAccess`, `AgentAllowList` | Settings tab of the project route |
| Restricted project chat | `RestrictedBanner`, `AgentLockChip`, `AgentBlockedNotice` | Wrapped around the upstream chat view: the lock chip replaces the model selector, the banner sits above the header |
| Theme and branding | `ThemeSettings` | New tab in the settings area |

Supporting pieces: a `ProjectsSection` for the sidebar (a lock icon on agent-limited rows) and two stores, one for tasks and one for projects. The tasks store listens for the `cowork:task` socket event and drives the sidebar badge.

Upstream edits:

- `Sidebar.svelte`: mount the inbox and projects sections.
- The chat page: render the banner and chip when the chat's project is agent-limited.

New routes go under a new folder in `src/routes/(app)/`, for example `cowork/`, so no upstream route files change.

## Open questions

- Should the project overview reuse the existing `folders/[folderId]` route or live under a new `cowork/projects/[projectId]` route? A new route keeps upstream files untouched.
- Where exactly does the chat page pick its model selector, so the lock chip can replace it with a small edit?
- Mockup fidelity: the mockup is a design reference, not code; match its structure and tokens, not its markup.

## Related docs

- [Theme and branding](theme-and-branding.md)
- [Agent-limited projects](agent-limited-projects.md)
