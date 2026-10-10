# 0003. Agent-limited projects are enforced on the server

## Status

Proposed

## Context

Some projects (for example Susol Lending, worked by an agent named Lori) must only be used with specific agents, and must not leak knowledge or tools to other agents. Hiding choices in the interface is not a boundary, because a client can send any request.

Observed in the v0.11.4 source:

- Generation goes through one function, `chat_completion` in `main.py` (`POST /api/chat/completions` and `/api/v1/chat/completions`). It already calls `check_model_access`.
- The request body supplies `chat_id` and `folder_id`; `folder_id` is copied into the metadata as sent by the client.
- Several other routes create, import, clone, move or write into chats.

## Decision

We will add one server-side helper that answers whether a user may use a given agent in a given project. Every route that starts, continues, moves or writes into a chat calls it. A denial returns HTTP 403 with the code `agent_not_allowed`. For an existing chat, the project is resolved from the chat's stored folder, never from a `folder_id` sent in the request. For a new chat, the sent `folder_id` is used only after write access to it is confirmed.

Allowed agents are stored in a `cowork_project_agent` table. An agent is an upstream workspace model id.

## Consequences

- Each protected route needs a test that expects 403 for a disallowed agent.
- A route added by a future upstream release could bypass the helper. A test that lists registered routes and flags unreviewed ones is required.
- Knowledge retrieval and tool lists must also respect the allow-list; this is more work than the route checks.
- One extra project lookup per completion request.

## Related decisions

- [0002. Projects extend upstream folders](0002-projects-extend-upstream-folders.md)
