# OBS-02: Unit of work for same-transaction audit writes

Status: **Proposed**, waiting for tech lead approval | Unblocks: OBS-40, OBS-41, OBS-44, OBS-45, OBS-46 | Ref: [Logging Architecture v2 §5](Canchat-v2-Logging%20Architecture-v2.md#5-audit-events-emit_audit_event-metadata-only), Gate 6

Proof of concept: [test_unit_of_work_poc.py](../backend/open_webui/test/util/test_unit_of_work_poc.py), 9 tests passing on SQLite. Postgres is still to be checked in OBS-40.

## 1. Problem

Every table method opens its own session through `with get_db() as db:` ([internal/db.py](../backend/open_webui/internal/db.py)) and commits before it returns. That causes three problems for audit:

1. A state change and its audit outbox row can't be committed or rolled back together.
2. Methods that call other methods are already non-atomic. Some examples:
   - [`AuthsTable.insert_new_auth`](../backend/open_webui/models/auths_table.py#L26) commits the `user` row through `Users.insert_new_user` before it commits the `auth` row.
   - [`UsersTable.delete_user_by_id`](../backend/open_webui/models/users.py#L322) runs three separate transactions: groups, then chats, then the user.
   - Admin user edits in [routers/users.py](../backend/open_webui/routers/users.py#L439) call password, email and profile updates one after another.
3. Most methods catch `Exception` and return `None`/`False`. Inside a shared transaction that would hide a failed write, and the caller could still commit the audit event with `outcome=success`.

## 2. Options considered

| Option | Summary | Verdict |
|---|---|---|
| **A. Explicit `db` parameter + `unit_of_work()`** | Mutating methods take a keyword-only `db: Optional[Session] = None`. Routers open a `unit_of_work()` and pass `db` both to the model method and to `emit_audit_event`. | **Chosen** |
| B. Ambient session (contextvar) | `get_db()` returns a session stored in a contextvar while a unit of work is active, so signatures don't change. | Rejected. Starlette's threadpool and `asyncio.create_task` both copy the context, so a background task or thread could pick up the request's session and use it concurrently. Sessions aren't thread- or task-safe. Joining a transaction would also happen invisibly, including for reads. |
| C. SAVEPOINT join (`join_transaction_mode="create_savepoint"`) | Keep `db.commit()` in the methods and bind the session to an outer connection transaction, so each commit only releases a savepoint. | Rejected. pysqlite needs event hooks for savepoints to work. The swallowed exceptions still leave the session in an unclear state. It's hard to reason about during review. |
| D. Repository/service layer rewrite | Move all writes into new service classes. | Rejected for now. Too large, and it makes merging from upstream Open WebUI harder. |

## 3. Chosen pattern

### 3.1 Helpers (add to `internal/db.py` in OBS-40)

```python
_UOW_KEY = "canchat.unit_of_work"

@contextmanager
def unit_of_work(db: Optional[Session] = None) -> Iterator[Session]:
    """One transaction for a state change and its audit record. Commits on success, rolls back on any exception."""
    if db is not None:                       # join an outer unit of work
        if not db.info.get(_UOW_KEY):
            raise RuntimeError("unit_of_work(db) requires a unit-of-work session")
        yield db
        return
    with get_db() as session:
        session.info[_UOW_KEY] = True
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise

@contextmanager
def get_db_context(db: Optional[Session] = None) -> Iterator[Session]:
    if db is None:
        with get_db() as session:            # legacy path: own session, own commit
            yield session
        return
    if not db.info.get(_UOW_KEY):
        raise RuntimeError("Pass only sessions created by unit_of_work()")
    yield db

def commit_or_flush(db: Session) -> None:
    if db.info.get(_UOW_KEY):
        db.flush()                           # the unit of work owns the commit
    else:
        db.commit()
```

### 3.2 Refactoring a model method

Every method in scope gets the same three mechanical edits:

1. Add the keyword-only parameter `*, db: Optional[Session] = None`.
2. Replace `with get_db() as db:` with `with get_db_context(db) as session:`, and `db.commit()` with `commit_or_flush(session)`.
3. In each `except` that swallows errors, re-raise when `db is not None`.

```python
def update_user_role_by_id(
    self, id: str, role: str, *, db: Optional[Session] = None
) -> Optional[UserModel]:
    try:
        with get_db_context(db) as session:
            session.query(User).filter_by(id=id).update({"role": role})
            commit_or_flush(session)
            user = session.query(User).filter_by(id=id).first()
            return UserModel.model_validate(user)
    except Exception:
        if db is not None:
            raise                  # never hide a failed write inside a unit of work
        return None
```

Methods that call other model methods must pass `db=db` along. Examples are `insert_new_auth` → `Users.insert_new_user`, and `delete_auth_by_id` → `Users.delete_user_by_id` → `Groups.remove_user_from_all_groups` + `Chats.delete_chats_by_user_id`.

### 3.3 Router usage

```python
@router.post("/update/role")
async def update_user_role(form_data: UserRoleUpdateForm, user=Depends(get_admin_user)):
    ...
    with unit_of_work() as db:
        before = Users.get_user_by_id(form_data.id, db=db)
        updated = Users.update_user_role_by_id(form_data.id, form_data.role, db=db)
        emit_audit_event(
            db, category="admin", action="user.role_change", actor_id=user.id,
            target={"type": "user", "id": form_data.id, "from": before.role, "to": form_data.role},
            outcome="success",
        )
    return updated
```

Events with no state change (login failure, token refresh failure, model access denied) open their own `with unit_of_work() as db: emit_audit_event(db, ...)`. `emit_audit_event(db=None)` can do that internally.

### 3.4 Rules (enforced in review; add a short checklist to the OBS-40 PR)

- **No `await`, network calls or provider calls inside a `unit_of_work()` block.** A long transaction holds the SQLite write lock and a Postgres pool connection. Do the I/O before the block, or after it.
- **Never pass the session to `run_in_executor`, `asyncio.create_task`, threads or background tasks.**
- **Non-database side effects** (object storage, Qdrant, Redis, MCP process start/stop) can't be rolled back:
  - Deletes: commit the unit of work first, then remove blobs and vectors. A failure leaves an orphan for the existing cleanup jobs, never a missing record.
  - Creates: upload first, then record and audit in the unit of work. If the unit of work fails, delete the upload.
- **`emit_audit_event` builds, validates and encrypts the event in Python before it touches the session.** A schema error therefore rolls back cleanly, and the only database step is the `INSERT`.
- Only pass sessions from `unit_of_work()`. `get_db_context` raises if it gets a plain `get_db()` session.

### 3.5 How this supports `AUDIT_FAIL_POLICY` (OBS-46)

- **Fail closed (privileged actions):** this is the default behaviour. If `emit_audit_event` raises, the whole unit of work rolls back and the router returns an error.
- **Fail open (chat/auth):** catch exceptions from the *build/validate/encrypt* step only, record the failure metric, and skip the `INSERT`. If the `INSERT` itself fails, the database is failing and the state change would fail too. This avoids SAVEPOINTs, which behave poorly on pysqlite.

### 3.6 Configs (special case)

Config isn't a table method. Each assignment `request.app.state.config.X = v` calls [`AppConfig.__setattr__`](../backend/open_webui/config.py#L321) → [`PersistentConfig.save`](../backend/open_webui/config.py#L302) → [`save_to_db`](../backend/open_webui/config.py#L48). That changes the in-memory `CONFIG_DATA` and commits the whole JSON document every time. There are about 150 assignment sites across 10 routers. Proposal:

- `save_to_db(data, *, db=None)` and `save_config(config, *, db=None)` use `get_db_context` / `commit_or_flush`.
- `AppConfig.bind(db)` is a context manager. It stores `db` in a **contextvar**, not on the shared `AppConfig` instance, because concurrent requests share that instance. It also takes a snapshot of `CONFIG_DATA` and every `PersistentConfig.value`. `save()` passes the bound `db` along. If an exception reaches the context manager, it restores the snapshot so memory matches the rolled-back database.
- One audit event per endpoint call. It lists the changed keys and **never** the values, because config contains secrets (API keys, LDAP passwords, OAuth client secrets).

```python
with unit_of_work() as db, request.app.state.config.bind(db):
    request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST
    emit_audit_event(db, category="admin", action="config.update", actor_id=user.id,
                     target={"type": "config", "keys": ["DEFAULT_MODELS", "MODEL_ORDER_LIST"]})
```

Known limitation, not new: other requests can see the new in-memory values before the commit. Other replicas don't see config changes until they restart. Both are out of scope.

## 4. Backward compatibility

- `db` is **keyword-only and last**, so existing positional and keyword calls keep working unchanged.
- With `db=None` a method behaves exactly as it does today: its own session, its own commit, the same swallowed exceptions and the same return values. Unaudited callers keep using that path, including the scheduler, `backend/scripts/*`, CrewAI title/tag updates and streaming `upsert_message_*`.
- **Read methods** get `db` only where a unit of work has to read the "before" state or read its own writes: `Users.get_user_by_id`, `Groups.get_group_by_id`, `Files.get_file_by_id`, `Knowledges.get_knowledge_by_id`, `MCPServers.get_server_by_id`. Other read methods stay as they are.
- **Test doubles** that replace model methods with fixed signatures must accept `db=None`/`**kwargs` once callers start passing `db`. One example is `rotate_session_token` in [test_auth_refresh_rotation.py](../backend/open_webui/test/util/test_auth_refresh_rotation.py).
- Merging from upstream: the change is mechanical and limited to the methods in §5, so conflicts stay local to those methods.
- Atomicity fixes (§1 point 2) apply only when a caller passes `db`. The legacy path keeps today's partial-failure behaviour.

## 5. Inventory of model methods to change

Only **mutating** methods called from an audited path are listed. Category and action names are provisional until OBS-04 approves them.

### auth: login, logout, token refresh, credentials

| Method | Audited call sites | Notes |
|---|---|---|
| `RefreshSessions.create_session`, `rotate_session_token` ([refresh_sessions_table.py](../backend/open_webui/models/refresh_sessions_table.py#L26)) | `utils/auth.issue_tokens_for_user` (signin, ldap, signup, oauth, refresh) | `login.success` written with the session row |
| `RefreshSessions.revoke_session_by_id`, `revoke_sessions_by_user_id` | `routers/auths.py` signout, refresh failure, password change | `logout`, `refresh.failure` |
| `Auths.insert_new_auth` ([auths_table.py](../backend/open_webui/models/auths_table.py#L26)) → `Users.insert_new_user` | signup, `/add`, ldap, oauth | Fixes the non-atomic user + auth insert |
| `Auths.update_user_password_by_id`, `update_email_by_id` | `/update/password`, admin edit in `routers/users.py` | `password.change`; never log the email value |
| `Users.update_user_api_key_by_id` | `/api_key` create/delete | `api_key.create` / `api_key.delete` |
| none (no state change) | signin/ldap failure, refresh failure | Standalone unit of work; failed login uses a pseudonym (OBS-43) |

### admin: users, roles, groups

| Method | Audited call sites | Notes |
|---|---|---|
| `Users.update_user_role_by_id` ([users.py](../backend/open_webui/models/users.py#L243)) | `routers/users.py` role update, `utils/oauth.py` role sync | |
| `Users.update_user_by_id` | admin user edit; `oauth_sub` link | Settings and profile updates by the user themselves stay legacy |
| `Users.update_user_oauth_sub_by_id` | `utils/oauth.py` | Account linking |
| `Auths.delete_auth_by_id` → `Users.delete_user_by_id` → `Groups.remove_user_from_all_groups`, `Chats.delete_chats_by_user_id` | `routers/users.py` delete | Makes user deletion atomic |
| `Groups.insert_new_group`, `update_group_by_id`, `delete_group_by_id` ([groups.py](../backend/open_webui/models/groups.py#L138)) | `routers/groups.py`, `utils/oauth.py` group sync | Members listed by ID only |
| `Domains.insert_new_domain`, `update_domain_by_id`, `delete_domain_by_id` | `routers/domains.py` | **Not in §5. Recommend adding** (admin, small) |

### admin: configuration

| Method | Audited call sites | Notes |
|---|---|---|
| `save_to_db`, `save_config`, `PersistentConfig.save`, `AppConfig.__setattr__` + new `AppConfig.bind` | `routers/configs.py` (8 assignments + `/import`), `auths.py` (14), `retrieval.py` (51), `images.py` (29), `audio.py` (26), `tasks.py` (11), `openai.py` (7), `ollama.py` (4), `users.py` (1), `evaluations.py` (1) | Changed keys only. `reset_config()` at startup stays legacy |

### access

| Method | Audited call sites | Notes |
|---|---|---|
| none | `check_model_access` denial | Standalone unit of work |

### resources: files and knowledge

| Method | Audited call sites | Notes |
|---|---|---|
| `Files.insert_new_file`, `delete_file_by_id`, `delete_all_files` ([files.py](../backend/open_webui/models/files.py#L102)) | `routers/files.py` upload/delete/delete-all, `routers/knowledge.py` remove-file, `routers/retrieval.py` deletes | Storage/vector side effects follow §3.4. The hash/data/metadata updates during processing are not audited and stay legacy |
| `Knowledges.insert_new_knowledge`, `update_knowledge_by_id`, `update_knowledge_data_by_id`, `delete_knowledge_by_id`, `delete_all_knowledge` ([knowledge.py](../backend/open_webui/models/knowledge.py#L102)) | `routers/knowledge.py`, `routers/retrieval.py` reset | `update_knowledge_data_by_id` covers file add/remove/reset |

### resources: MCP servers

| Method | Audited call sites | Notes |
|---|---|---|
| `MCPServers.insert_new_server`, `update_server_by_id`, `delete_server_by_id` ([mcp_servers.py](../backend/mcp_backend/models/mcp_servers.py#L85)) | `mcp_backend/routers/mcp.py` create/update/delete | Never put `env`/`args` values in the event (they may hold secrets) |
| `update_server_status` (wrapper around `update_server_by_id`) | `mcp.py` activate/deactivate/restart | Pass `db` through. Process start/stop happens after the commit |

### export

| Method | Audited call sites | Notes |
|---|---|---|
| `ExportLogs.insert_new_export_log` ([export_logs.py](../backend/open_webui/models/export_logs.py#L50)) | `routers/metrics.py` export | The existing export log row and the audit event are written together |

### chat: metadata (OBS-01 option a)

| Method | Audited call sites | Notes |
|---|---|---|
| `MessageMetrics.insert_new_metrics` ([message_metrics.py](../backend/open_webui/models/message_metrics.py#L51)) | `utils/middleware.py` (3 sites), `socket/main.py` (1), **`mcp_backend/routers/crew_mcp.py` (2, missing from OBS-01's list)** | Opens its own unit of work internally and writes metrics row + outbox row. Call sites don't change |
| `Chats.insert_shared_chat_by_chat_id`, `delete_shared_chat_by_chat_id` | `routers/chats.py` share/unshare | **Recommend adding** a `chat.share` action in OBS-04 (exposes content through a link) |
| `Chats.delete_chat_list` | retention cleanup | Deferred to the records-management design (OBS-61) |

Other `Chats` writes (title, tags, pin, archive, folder, message upserts) are not audited and stay unchanged.

## 6. Effort estimate for OBS-40 (story points)

Each estimate includes the refactor, passing `db` through nested calls, updating test doubles, and per-area transaction tests (commit together / roll back together).

| Area | Methods | Points | Main risk |
|---|---:|---:|---|
| Shared helpers (`unit_of_work`, `get_db_context`, `commit_or_flush`) + review checklist | 3 | 2 | none |
| Auth + refresh sessions + users (incl. delete chain) | ~14 | 5 | Login/refresh hot path; test doubles with fixed signatures |
| Groups (+ domains if accepted) | 4 (+3) | 2 (+1) | oauth group sync |
| Configs (`save_to_db`, `PersistentConfig`, `AppConfig.bind`) | 4 + ~150 assignment sites | 8 | In-memory rollback; secret-safe key diff; number of routers touched |
| Files + knowledge | 8 (+2 reads) | 5 | Ordering of storage/vector side effects |
| MCP servers | 3 (+1 read) | 2 | Process start/stop ordering |
| Export logs | 1 | 1 | none |
| Message metrics (+ share actions if accepted) | 1 (+2) | 2 (+1) | Hot path latency; covered with OBS-45 |
| **Total** | | **27 (+2 optional)** | |

Suggestion: split OBS-40 into sub-tasks along these rows. Configs is the largest single item and can land last, because the other areas don't depend on it.

## 7. Open questions for approval

1. Accept option A (explicit `db` + `unit_of_work`) over the ambient contextvar session?
2. Add `domain.*`, `chat.share` and `api_key.*` actions to the OBS-04 schema?
3. Config events record **changed keys only**. Is that enough for Security, or do they also want a keyed hash of the old and new values?
4. Should user deletion become atomic (the outbox and the delete chain in one transaction)? It holds a longer transaction for users with many chats.
