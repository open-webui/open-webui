# 0002. Projects extend upstream folders

## Status

Proposed

## Context

The sidebar needs projects that hold chats, instructions, knowledge, a default agent and an access mode. Observed in the v0.11.4 source:

- Chats have a nullable `folder_id`, and `POST /api/v1/chats/new` rejects a `folder_id` the user cannot write to (it calls `has_folder_write_access`).
- Folders have `data` and `meta` JSON columns and nested parents.
- Folders are shared through the access-grants table with resource type `folder`, matched by user, group or public principal.
- A `folders` route and sidebar already exist, with `ENABLE_FOLDERS` as a config switch.

## Decision

A project is an upstream folder plus one row in a new `cowork_project` table, keyed by `folder_id`. Chat membership, nesting and people-sharing keep using upstream folders and access grants. We add no columns to upstream tables.

## Consequences

- Chats, sharing and the sidebar tree keep working without changes to upstream tables, which keeps rebases small.
- Folder nesting means a project folder can contain child folders. The helper that resolves a chat's project must walk to the project row, or projects must be limited to top-level folders. This is an open question in the [agent-limited projects spec](../specs/agent-limited-projects.md).
- `ENABLE_FOLDERS` must be on for projects to work.
- Deleting a folder upstream must also remove the extension row; the migration or a cleanup hook must handle this.

## Alternatives considered

- A separate projects table that duplicates chat membership: rejected because it would shadow upstream folders and widen the rebase surface.

## Related decisions

- [0001. Fork Open WebUI at v0.11.4 into the losus-ai organization](0001-fork-open-webui-at-v0-11-4.md)
