# Backend layering: routers → services → repositories

Target architecture for `backend/open_webui`. Applies to **new code and to code you are
already substantially changing**. It is not a mandate to refactor working modules.

## Why

Today the backend has two layers:

```
routers/*.py  (1.6k–2.8k lines)   ─── HTTP + authorisation + business logic + orchestration
models/*.py   (0.5k–1.8k lines)   ─── SQLAlchemy tables + Pydantic schemas + all SQL
```

Concretely, as of today:

| File                   | Lines |
| ---------------------- | ----: |
| `routers/retrieval.py` |  2769 |
| `routers/channels.py`  |  1838 |
| `routers/knowledge.py` |  1649 |
| `models/chats.py`      |  1760 |
| `models/knowledge.py`  |  1359 |

The costs we actually hit:

- **Endpoints can't be unit-tested.** `POST /knowledge/{id}/files/batch/add` is ~120
  lines of policy and orchestration wrapped in a `Depends(...)` signature, so the only
  way to exercise it is an HTTP round-trip through `httpx.ASGITransport`.
- **Logic gets duplicated per endpoint.** `routers/knowledge.py` has a
  `_verify_knowledge_write_access` helper (line 1387) used by 9 handlers — and still
  ~11 hand-inlined `permission='write'` gates elsewhere in the same file, because the
  helper was introduced after most of the endpoints.
- **`mccabe.max-complexity = 10`** (`pyproject.toml`) makes long handlers fail lint,
  which pushes people toward `# noqa` rather than toward decomposition.
- **Services can't reuse endpoints without importing routers.** `services/files_service.py`
  imports `process_file` from `routers.retrieval` and `transcribe` from `routers.audio`.
  That inversion (service → router) is the clearest symptom of the missing layer.

## The three layers

### Router — `routers/*.py`

The HTTP adapter. Registered in `main.py` (~line 1419+) under `/api/v1/<name>`.

**Does:** declare the route and `response_model`; take `user=Depends(get_verified_user)`
(or `get_admin_user`) and `db: AsyncSession = Depends(get_async_session)`; validate the
Pydantic form; run the authorisation gate; call **one** service function; translate
service failures into `HTTPException` with `ERROR_MESSAGES`.

**Does not:** contain multi-step business logic, emit `select()`/`update()`, call the
vector DB or storage directly, or be imported by a service.

A handler that is thin enough is usually under ~30 lines.

```python
@router.post('/{id}/files/batch/add', response_model=KnowledgeFilesResponse | None)
async def add_files_to_knowledge_batch(
    request: Request,
    id: str,
    form_data: list[KnowledgeFileIdForm],
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    knowledge = await _verify_knowledge_write_access(id, user, db)
    try:
        return await knowledge_service.add_files_batch(
            request=request, knowledge=knowledge, entries=form_data, user=user, db=db
        )
    except FileNotFoundInLibrary as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
```

### Service — `services/*.py`

Where a use case lives. This layer already exists: `files_service.py`,
`file_analysis.py`, `process_file_queue.py`.

**Does:** orchestrate repositories, `Storage`, `ASYNC_VECTOR_DB_CLIENT`, LLM calls via
`utils.chat.generate_chat_completion`, and the processing queue; own transaction scope
by threading a single `db` through every repository call; enforce cross-aggregate
invariants (e.g. "linking a file also ensures its directory path exists").

**Does not:** import from `routers/`, raise `HTTPException`, or write SQL.

Signature convention — mirror the existing services: `async def verb_noun(...,
user, db: Optional[AsyncSession] = None)`, `request` first only when the app state
(embedding function, task model config) is genuinely needed.

```python
async def link_file_to_knowledge(knowledge_id, file_item, file_metadata, user, db=None):
    """Link an uploaded file into a knowledge base at its correct folder. Idempotent."""
```

Raise **domain exceptions**, not HTTP ones, so the same service is callable from the
queue worker and from a router:

```python
class KnowledgeServiceError(Exception): ...
class FileNotFoundInLibrary(KnowledgeServiceError): ...
```

### Repository — `models/*.py`

The `*Table` classes are already repositories; the naming just hides it. Each module
ends with the singleton that everything imports:

```python
Knowledges = KnowledgeTable()   # models/knowledge.py:1359
Files      = FilesTable()       # models/files.py:477
Chats      = ChatTable()        # models/chats.py:1760
```

**Does:** define the SQLAlchemy table and its Pydantic schemas; hold every `select()` /
`insert()` / `update()` / `delete()` for **its own aggregate**; map rows to Pydantic
models; keep denormalised caches consistent (`_recompute_directory_counts`).

**Does not:** call an LLM, touch storage or the vector DB, or decide authorisation policy.

Keep the optional-session contract on **every** method:

```python
async def get_knowledge_by_id(self, id: str, db: Optional[AsyncSession] = None):
    async with get_async_db_context(db) as db:
        ...
```

`get_async_db_context(db)` reuses a caller's session or opens one — this is what lets a
service compose many repository calls into one transaction.

**Do not rename `models/` to `repositories/`.** ~30 modules and hundreds of call sites
import `from open_webui.models.x import X`. The layer boundary is conceptual and
enforced by review, not by a directory move. If we ever want the physical split, the
migration is: extract `Table` classes into `repositories/<domain>.py`, leave
`Base`/Pydantic in `models/`, re-export from `models/` for one release.

## Rules

1. **A router never contains a `select()`.** If you're reaching for SQLAlchemy in a
   handler, you need a repository method.
2. **A service never imports from `routers/`.** If you need `process_file`, that logic
   belongs in a service the router also calls. Fixing the existing inversions in
   `files_service.py` is a good first cleanup when retrieval is next touched.
3. **A repository method covers one aggregate.** Cross-aggregate coordination
   (knowledge + files + vector DB) is service work. Note that `KnowledgeTable` currently
   owns `knowledge`, `knowledge_directory` **and** `knowledge_file` — that's acceptable,
   they are one aggregate. `Knowledges` calling into `Users`/`Groups`/`AccessGrants`
   for read-mapping is the borderline case; don't add more of it.
4. **One request, one session.** Thread `db=db` everywhere. Omitting it silently opens a
   second session and breaks atomicity.
5. **Authorisation stays visible in the router**, expressed via a named helper
   (`_verify_knowledge_write_access`) rather than copy-pasted. Services may assume the
   caller is authorised; they must not be the only gate.
6. **Fail-open behaviour is a feature where it's documented.** `file_analysis.py`
   returns "eligible" on any LLM/parse failure so a classifier outage can't drop
   uploads. Don't tighten that without a decision.
7. **New service = new module in `services/`**, named `<domain>_service.py` for CRUD-ish
   orchestration or a behaviour name (`file_analysis`, `process_file_queue`) for a
   pipeline.

## Opportunistic refactoring

When you add a feature or make a non-trivial change to an endpoint:

- **New endpoint** → router thin from day one, logic in a service.
- **Editing an existing fat endpoint** → extract _that_ handler's body into a service
  function and leave the rest of the router alone. One handler per commit.
- **Touching a repository method** → keep it SQL-only; move any LLM/storage/vector-DB
  call you find there up into the service.
- **Never** reformat or restructure a module you weren't otherwise changing. It buries
  the real diff and makes upstream merges painful.

Good precedent from this repo's own history: `a23684c2b test(knowledge): extract
withStatsOutdated util + vitest tests` — a small extraction made _because_ the
surrounding code was being changed, shipped with a test.

## Testing

Full policy and harness details: **[testing.md](testing.md)**. Every change ships with
tests; every feature gets an integration test that drives the real endpoint against a
real DB.

Testability is the primary reason for this layering, and it maps cleanly onto the layers:

- **Service** → call it directly with a real temp-SQLite session, mocking only the LLM /
  storage / vector-DB boundary. **This is where feature logic gets covered.**
  `test_file_analysis.py` already does exactly this.
- **Router** → one integration test per endpoint, for status codes and the auth gate.
- **Repository** → only non-obvious SQL (subtree deletes, count recomputation, pagination).

A **service test is the end-to-end feature test minus the HTTP hop** — same coverage,
faster, and it also matches how the queue worker calls the code. Logic left inside a
120-line handler can only be reached over HTTP; that asymmetry is the layering's
concrete payoff, not a stylistic preference.

Rule of thumb: **new business logic ships with a service-level test**, and the HTTP test
proves wiring and authorisation.
