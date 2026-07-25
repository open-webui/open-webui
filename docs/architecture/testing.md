# Testing policy

**Every change ships with tests. Every feature is covered end-to-end by an integration
test.** This is a definition-of-done requirement, not a nice-to-have.

## The rules

1. **Every new or changed feature needs at least one integration test that drives the
   real HTTP endpoint against a real database**, mocking only external boundaries (LLM,
   S3, remote vector DBs). A test that only exercises a helper does not discharge this.
2. **Every pure function gets a unit test.** If logic is hard to test, that's a layering
   signal — extract it (see [backend-layers.md](backend-layers.md),
   [frontend-components.md](frontend-components.md)) and test the extraction.
3. **A bug fix starts with a failing test** that reproduces it. No test, no fix.
4. **Each pipeline keeps at least one full-stack test with nothing mocked.** Mocks drift;
   this is the test that notices.
5. Tests live beside the code they cover: backend in `backend/tests/`, frontend as
   `*.test.ts` colocated with the module.

Done means: `pytest` green, `npm run test:frontend` green, `npm run check` clean,
`ruff format` clean — and a new test that fails if your change is reverted. If you can't
write that last one, say so explicitly rather than shipping silently uncovered code.

## What "integration test" means here

The existing suite (`backend/tests/`, 1068 lines across 4 files) is the reference. It is
deliberately **not** a mock-everything unit suite:

| Real in tests                                          | Mocked                                                        |
| ------------------------------------------------------ | ------------------------------------------------------------- |
| The FastAPI app, routing, `response_model` validation  | LLM calls (`generate_chat_completion`)                        |
| The database — temp SQLite, migrations run             | S3 (assert the guard instead)                                 |
| Local storage provider, writing into a temp `DATA_DIR` | `process_file` when the test isn't about extraction/embedding |
| Repositories (`Knowledges`, `Files`) — real SQL        |                                                               |
| The file-processing queue                              |                                                               |

And one test proves the whole chain with **nothing** mocked —
`test_worker_full_process_extracts_and_embeds` runs real extraction, real local
sentence-transformers embeddings, and a real chroma write, asserting
`file.meta['collection_name']` because that field is only set after a successful vector
write. Keep a test like that for every pipeline you add.

## The backend harness

`backend/tests/conftest.py` gives you three fixtures:

| Fixture        | What it is                                                                                   |
| -------------- | -------------------------------------------------------------------------------------------- |
| `app`          | the real `open_webui.main.app` (session-scoped)                                              |
| `test_user`    | a real user row (`test-user-id`), idempotent across tests                                    |
| `async_client` | `httpx.AsyncClient` over `ASGITransport`, with `get_verified_user` overridden to `test_user` |

`conftest.py` forces `DATABASE_URL` to a throwaway temp SQLite file **before importing
`open_webui`**, because the engine and Alembic bind at import time. Never add an
`open_webui` import above that block, and never `setdefault` there — forcing it is what
guarantees a test run can't touch a real database.

`pyproject.toml` sets `asyncio_mode = "auto"`, so `async def test_*` needs no decorator.

### ASGITransport does not run the app lifespan

This is the source of nearly every confusing test failure. Four consequences, each with
the established workaround:

**1. The background file worker never starts.** That's a feature — the queue stays under
the test's control. Drive it explicitly:

```python
job = get_file_processing_queue().get_nowait()
await _process_queued_file(app, job)
```

**2. `app.state.main_loop` is unset.** `save_docs_to_vector_db` schedules onto it. Set it
when a test embeds for real:

```python
app.state.main_loop = asyncio.get_running_loop()
```

**3. `app.state.MODELS` is empty**, so task-model resolution returns `None` and any LLM
feature silently no-ops. Inject and restore:

```python
@pytest.fixture
def models_available(app):
    original = app.state.MODELS
    app.state.MODELS = {'test-model': {'connection_type': 'local', 'id': 'test-model'}}
    yield
    app.state.MODELS = original
```

**4. Config flags sit at their defaults.** Flip them in a fixture that restores after —
see the `analysis_enabled` fixture toggling `ENABLE_INGESTION_ANALYSIS`.

### The processing queue is global — drain it

Jobs leak between tests otherwise. Every file-touching module uses an autouse fixture:

```python
@pytest.fixture(autouse=True)
def _clean_queue():
    _drain(get_file_processing_queue())
    yield
    _drain(get_file_processing_queue())
```

### Patch where a symbol is used, not where it's defined

`files_service.py` does `from open_webui.routers.retrieval import process_file`, binding
the name locally. So:

```python
# correct — patches the name files_service actually calls
monkeypatch.setattr('open_webui.services.files_service.process_file', fake_process_file)

# wrong — files_service already holds its own reference
monkeypatch.setattr('open_webui.routers.retrieval.process_file', fake_process_file)
```

The standard stub, when the test is about linking/folders rather than ingestion:

```python
async def fake_process_file(request, form_data, user=None, db=None):
    await Files.update_file_data_by_id(form_data.file_id, {'status': 'completed'}, db=db)
    return {'status': True}
```

## Writing a feature test

Template for a new knowledge endpoint — real HTTP in, real DB assertions out:

```python
"""Integration tests for <feature>.

Covers: <the contract, as bullet points>.
External boundaries (<what>) are mocked; storage and DB are real.
"""

async def test_endpoint_does_the_thing(async_client, test_user):
    kb = await _new_kb(test_user.id)

    resp = await async_client.post(f'/api/v1/knowledge/{kb.id}/thing', json={...})

    assert resp.status_code == 200
    assert resp.json()['...'] == ...
    # Assert persisted state, not just the response body.
    assert await Knowledges.get_thing(kb.id) == ...
```

Conventions the existing suite follows — match them:

- **Module docstring states the contract covered and what is mocked.** All four existing
  test files do this. It's the fastest way for the next person to know what's guarded.
- **Test names describe behaviour**, not methods:
  `test_upload_accepts_marks_pending_and_enqueues`,
  `test_upload_stores_relative_path_but_keeps_flat_storage`,
  `test_directory_counts_after_delete_without_moving_files`.
- **Small local factories**, not fixture towers: `_new_kb(user_id)`, `_upload(client, ...)`,
  `_upload_into_kb(client, app, kb_id, name)`.
- **`@pytest.mark.parametrize` for pure functions** — see the `sanitize_relative_path`
  table, which encodes the traversal-safety cases (`'../../etc/passwd' → 'passwd'`).
- **Assert the DB, not only the response.** Most real bugs here are persistence bugs.
- **Cover the negative path too**: the reference guard in `test_knowledge_delete.py` (a
  file linked to a second KB must survive), the fail-open LLM path
  (`_raising_completion`), `test_presign_requires_s3_provider`.

## What each layer owes

| Layer                | Test kind                                     | Cost                                                                    |
| -------------------- | --------------------------------------------- | ----------------------------------------------------------------------- |
| Router               | integration via `async_client`                | one per endpoint: status codes + the auth gate                          |
| Service              | direct call, real temp DB, mocked LLM/storage | **where feature logic gets covered**                                    |
| Repository           | direct call                                   | only non-obvious SQL — subtree deletes, count recomputation, pagination |
| Pure util (py or ts) | unit, parametrized                            | cheapest; no excuse to skip                                             |

This is the concrete payoff of the layering: a **service test is the end-to-end feature
test minus the HTTP hop** — same coverage, faster, and callable from the queue worker's
perspective too. Logic left inside a 120-line router body can only be reached through
HTTP; logic in a service can be tested both ways.

## Frontend

`npm run test:frontend` → vitest, default config (there is no `test` block in
`vite.config.ts`), specs colocated as `*.test.ts`.

Test **pure logic** in `lib/utils/*.ts`. Don't try to mount the 1800-line containers —
extract the logic worth asserting and test that. `lib/utils/knowledge.test.ts` is the
model: it asserts behaviour _and_ the reference-identity contract Svelte reactivity
depends on (`expect(withStatsOutdated(noMeta)).toBe(noMeta)` for the no-op case,
`not.toBe` when it must change).

So for a frontend feature, "covered by tests" means: pull the decision-making out of the
component into `lib/utils/<domain>.ts` and unit-test it there, and cover the endpoint it
calls with a backend integration test. That pair is the practical E2E for a UI change.

### Known gaps — read before assuming coverage

- **`--passWithNoTests` is set**, so the frontend suite passes when it finds nothing. A
  green run is not evidence of coverage. There is currently **one** frontend test file.
- **No browser-level E2E exists.** Cypress is vestigial upstream baggage: the dependency
  and a `cy:open` script are present, but there is no `cypress.config.ts` and no specs.
  `docker-compose.playwright.yaml` is _not_ a test harness — it's the Playwright web
  **loader** engine for scraping. Until we choose a browser E2E tool, the backend
  integration suite is the only real end-to-end net, which is why rule 1 above is strict.

## CI

| Workflow                          | Runs                                                           |
| --------------------------------- | -------------------------------------------------------------- |
| `.github/workflows/backend.yaml`  | `ruff format --check`, then **`pytest -q`** on 3.11 + 3.12     |
| `.github/workflows/frontend.yaml` | prettier + i18n + clean-tree check, production build, `vitest` |

The pytest job runs the **full** suite, including the nothing-mocked embedding test, and
caches `~/.cache/huggingface` so `all-MiniLM-L6-v2` is downloaded once rather than on
every run. It sets `PYTHONPATH=backend` instead of installing the project: `pip install -e .`
would invoke `hatch_build.py`, which force-includes the frontend `build/` directory that
doesn't exist in a backend-only job. `env.py` resolves `VERSION` from the repo-root
`package.json` (not dist metadata), so no install is needed.

Note the path filters: `backend.yaml` only triggers on `backend/**`, `pyproject.toml`,
`uv.lock`. A change that touches **only** frontend files will not run pytest — and
`frontend.yaml` conversely ignores `backend/**`.
