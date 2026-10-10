# Routes that start or continue a chat (v0.11.4)

## 1. Which routes must go through the agent-limited check

### Context

**Source:** a search of the v0.11.4 source in a clone of the fork on 2026-10-09 (route definitions and a few function bodies were read directly, not recalled from a prior session).

[ADR 0003](../adr/0003-agent-limited-projects-enforced-on-server.md) needs the full list of routes that start, continue, move or write into a chat. The route table lives in [agent-limited projects](../specs/agent-limited-projects.md).

### Investigation Checklist

- [x] List chat-related route definitions across `main.py` and `routers/`
- [x] Read `chat_completion` and find how it learns the chat and folder
- [x] Find where chat creation and moves already check folder access
- [ ] Read `POST /api/v1/chats/import`
- [ ] Read `POST /api/v1/chats/{id}/clone/shared`
- [ ] Read `POST /api/v1/chats/{id}/fork`
- [ ] Read `POST /api/v1/chats/{id}`
- [ ] Read `POST /api/v1/chats/{id}/messages/{message_id}`
- [ ] Read `POST /api/v1/messages` and check whether it calls `chat_completion`
- [ ] Confirm the direct proxies (`/openai/chat/completions`, `/ollama/*`) cannot reach project knowledge

### Findings

- Generation has one entry: `chat_completion` in `main.py`, serving `/api/chat/completions` and `/api/v1/chat/completions`. It already calls `check_model_access`.
- Its request body supplies `chat_id` and `folder_id`; `folder_id` is copied into the metadata as sent by the client. The server therefore cannot trust it for existing chats.
- `POST /api/v1/chats/new`, `POST /api/v1/chats/{id}/folder` and the clone route already reject folders the user cannot write to via `has_folder_write_access`.
- Upstream mounts its own tasks router at `/api/v1/tasks` (title, tag and other generation helpers).
- Hypothesis, not confirmed: the direct model proxies carry no project context, so they cannot reach project knowledge.

### Actions Taken

- Searched route decorators for chat, completions, messages and folder paths across the backend.
- Read `chat_completion` and the folder checks in `chats.py`.

### Resolution

partially resolved. The choke point and the folder-check pattern are confirmed. Six route bodies remain unread, and the direct proxies are unconfirmed.

### Follow-ups

- Read the unchecked routes above and update the route table in [agent-limited projects](../specs/agent-limited-projects.md).
- Add the route-inventory test so routes added by future upstream releases are flagged.
