# CANChat observability & logging: Jira tickets

Source plan: [Canchat-v2-Logging Architecture-v2.md](Canchat-v2-Logging%20Architecture-v2.md) (v2.1). Section references (§) point to that document.

## How to use this file

- Tickets are grouped into **epics** that follow the plan's rollout order (PR 1 to PR 8). Epic 0 holds the decisions and gates that block later work.
- Each ticket lists **Depends on**. Tickets with no dependency can start right away.
- Suggested ID prefix: `OBS-`. Replace it with real Jira keys when you create the tickets.
- Every ticket's Definition of Done includes the **common DoD** below, plus its own items.

### Common Definition of Done (applies to every ticket)

- Code reviewed and merged to the main branch through a PR that references the ticket.
- New and existing pytest / frontend tests pass in CI, and the new tests were confirmed to actually run (not skipped or filtered out).
- No prompt text, response text, credentials, tokens, email or names added to stdout, operational logs, span attributes or browser telemetry.
- New configuration variables added to the §12 configuration reference and to `.env`/Helm/Kubernetes examples where relevant.
- Architecture doc updated if the implementation differs from the plan.
- `CHANGELOG.md` and `CHANGELOG-FR.md` updated for user- or operator-visible changes.

### Epic overview

| Epic | Rollout step | Tickets |
|---|---|---|
| E0 Decisions & implementation gates | Before PR 1–3 | OBS-01 to OBS-06 |
| E1 Safe foundations | PR 1 | OBS-10 to OBS-19 |
| E2 Tracing & metrics | PR 2 | OBS-20 to OBS-30 |
| E3 Durable audit | PR 3 | OBS-40 to OBS-47 |
| E4 Observability infrastructure | PR 4 | OBS-50 to OBS-59 |
| E5 Retention TTLs | PR 5 | OBS-60 to OBS-61 |
| E6 Frontend observability & analytics (Faro) | PR 6 | OBS-70 to OBS-78 |
| E7 Remaining logging clean-up & acceptance | PR 7 | OBS-80 to OBS-82 |
| E8 Optional content audit | PR 8 | OBS-90 to OBS-91 |

---

## E0: Decisions & implementation gates

**Epic description**

**Goal:** Make the decisions, version pins and approvals that the build work depends on, so later PRs don't have to be redone.

**Why:** The plan names six implementation gates. Two design choices change which code PR 2 and PR 3 touch: whether `message_metrics` stays the single place chat data is written, and how a change and its audit record get saved in one transaction. Retention, audit schema and production hosting also need SSC approval before the matching work can finish.

**Scope:** decision records, spikes, dependency resolution, and external sign-off from SSC Security, IM and ATIP, plus infrastructure owners.

**Out of scope:** production code changes, apart from proof-of-concept tests.

**Done when:** every gate in the plan's *Implementation gates* section has an approved, recorded answer linked from the tickets it unblocks.

### OBS-01: Decide whether `message_metrics` is the single chat-metadata write point

**Type:** Decision / Spike | **Depends on:** none | **Ref:** §5, Gate 6

**Description**
The existing `message_metrics` table already stores user, domain, model, token counts, chat ID and MCP tool for each message. The plan proposes a `category=chat` audit event and an `llm_tokens_total` metric that overlap with it. Choose between:
- **(a) recommended:** extend `MessageMetrics.insert_new_metrics` and make it the single write point for the token metric and the chat audit event (outbox record in the same transaction);
- **(b)** a separate audit table, with reconciliation against `message_metrics`.

This decision changes which call sites PR 2 and PR 3 instrument.

**Acceptance criteria**
- [ ] Written decision record (ADR or design note in the PR 1 description) choosing (a) or (b), with reasons.
- [ ] List of every current `insert_new_metrics` call site (`utils/middleware.py` HTTP paths, `socket/main.py` CrewAI path) and confirmation of which one each finalization path uses.
- [ ] List of columns to add (feature flags, outcome, correlation IDs) if (a) is chosen.
- [ ] Impact on the admin metrics dashboard (`routers/metrics.py`) documented.

**Testing**
- None (decision). Call-site inventory checked with a code search and reviewed by a second developer.

**Definition of done**
- Common DoD.
- Decision approved by the tech lead and linked from OBS-24 and OBS-45.

---

### OBS-02: Design the session-injection / unit-of-work pattern for same-transaction audit writes

**Type:** Spike / Design | **Depends on:** none | **Ref:** §5 Persistence and delivery, Gate 6

**Description**
Each model class currently opens its own session with `with get_db() as db:` and commits per call (`internal/db.py`, for example `models/chats.py`). To write a state change and its audit outbox record atomically, the affected methods need an injected session or an equivalent unit-of-work pattern. Scope the refactor for users, groups, configs, chats, files, knowledge and MCP servers.

**Acceptance criteria**
- [ ] Design note describing the chosen pattern (optional `db` parameter, context-managed unit of work, or other), with a code example.
- [ ] Inventory of model methods that must change, grouped by audit event category.
- [ ] Backward compatibility approach for existing callers that do not pass a session.
- [ ] Effort estimate per model area, to size OBS-40.

**Testing**
- Proof-of-concept test showing a state change and an outbox row committed together and both rolled back on failure.

**Definition of done**
- Common DoD.
- Design approved and attached to OBS-40.

---

### OBS-03: Resolve and pin OTel instrumentation dependencies with CrewAI/LiteLLM

**Type:** Spike | **Depends on:** none | **Ref:** §9 Dependencies, Gate 1

**Description**
`requirements.txt` pins only `opentelemetry-api`, `-sdk` and `-exporter-otlp` (1.42.0). CrewAI and LiteLLM pull their own OTel-adjacent packages. Run a full `pip` resolution of `opentelemetry-instrumentation-{fastapi,aiohttp-client,requests,sqlalchemy,redis}==0.63b0` (and the logging bridge) alongside the pinned `crewai`, and identify which HTTP client CrewAI's `LLM`/LiteLLM uses.

**Acceptance criteria**
- [ ] Resolved, conflict-free set of package versions recorded.
- [ ] Logging bridge (SDK `LoggingHandler` / logs exporter) confirmed to work with the pinned SDK.
- [ ] HTTP client used by CrewAI/LiteLLM identified, and whether an existing instrumentor covers it.
- [ ] Image/version pins proposed for collector-contrib, Loki 3.x, Tempo, Prometheus, Grafana (Alloy and Faro deferred to OBS-70/OBS-76).

**Testing**
- Clean virtualenv install of `backend/requirements.txt` plus the new packages; backend starts and the existing pytest suite passes.

**Definition of done**
- Common DoD.
- Versions recorded in the Gate 1 section of the architecture doc and ready to be applied in OBS-20.

---

### OBS-04: Approve audit event schema, cardinality limits and audit fail policy

**Type:** Decision | **Depends on:** OBS-01 | **Ref:** §5, Gates 2 and 4 | **Decision record:** [Canchat-v2-OBS-04-Audit-Event-Schema.md](Canchat-v2-OBS-04-Audit-Event-Schema.md)

**Description**
Define and get approval for the versioned audit event schema (`event_id`, schema version, UTC time, trusted actor ID, action, outcome, bounded target metadata, correlation IDs), the list of actions, the per-action failure policy (`AUDIT_FAIL_POLICY`), the keyed pseudonymization scheme for failed logins, and metric/label cardinality limits.

**Acceptance criteria**
- [ ] JSON Schema (or Pydantic model spec) for audit events v1, including allowed `category`/`action` values.
- [ ] Explicit list of forbidden fields (secrets, email, names, message text).
- [ ] Per-action failure policy table (fail closed vs fail open with alert) approved by Security.
- [ ] Pseudonymization key management and rotation approach documented.
- [ ] Allowed metric label values (model, provider, tool, event, outcome) and bounding approach documented.
- [ ] SIEM/archive delivery receipt definition, outage behaviour and undelivered-event retention documented.

**Testing**
- None (decision). Schema validated against sample events from each category.

**Definition of done**
- Common DoD.
- Signed off by SSC Security and the tech lead; linked from OBS-41 and OBS-46.

---

### OBS-05: Confirm SSC records mapping and retention clocks

**Type:** Decision (external) | **Depends on:** none | **Ref:** §11, Gate 3 | **Decision request:** [Canchat-v2-OBS-05-Retention-Mapping.md](Canchat-v2-OBS-05-Retention-Mapping.md) (provisional answers recorded 2026-10-14; waiting for SSC confirmation)

**Description**
SSC Information Management, Security and ATIP must confirm the proposed retention mapping table in §11 (Loki `app`/`frontend`/`audit`, SIEM/evidence, chat DB, Tempo, Prometheus), including disposal authority and clock triggers.

**Acceptance criteria**
- [ ] Each row in the §11 table is confirmed or changed, with the approved value and basis.
- [ ] Clock triggers confirmed (event time, last chat activity, last administrative use).
- [ ] Content-audit need confirmed (needed or not) for OBS-91.
- [ ] Records-management follow-up owner named (OBS-61).

**Testing**
- None (decision).

**Definition of done**
- Common DoD.
- Approved values copied into the §11 table and used by OBS-60.

---

### OBS-06: Specify production capacity, availability and ownership for the observability stack

**Type:** Design | **Depends on:** OBS-03 | **Ref:** §9 Production deployment, Gate 5 | **Design:** [Canchat-v2-OBS-06-Production-Deployment.md](Canchat-v2-OBS-06-Production-Deployment.md) (proposed 2026-10-14)

**Description**
Compose demonstrates local integration only. Define production capacity, HA, backups/restore, credentials, network policies, egress restrictions and infrastructure ownership for the collector, Loki, Tempo, Prometheus (both), Grafana, Alloy, audit worker and tenant proxy. Identify which platform metrics are needed for DB, Redis, GPU and model-server health.

**Acceptance criteria**
- [ ] Sizing estimate (ingest volume, storage, CPU/memory) per component.
- [ ] HA and backup/restore approach per store, with RPO/RTO.
- [ ] Network policy and egress allow-list per component; vendor usage reporting disabled.
- [ ] Ownership (team) per component and on-call expectations.
- [ ] Decision on managed SSC services vs self-run components.

**Testing**
- None (design).

**Definition of done**
- Common DoD.
- Design linked from OBS-58.

---

## E1: Safe foundations (PR 1)

**Epic description**

**Goal:** Stop sensitive data leaking into logs, fix the CrewAI token defect, and put the shared logging, correlation and OTel setup in place that all later work builds on.

**Why:** Today the socket handler logs prompt and Graph token fragments at INFO. The CrewAI path stores the user's token in global state that concurrent requests share. Logging is configured in 13 places, and most lines show `request_id=N/A`. Collecting more logs before fixing this would just spread the leaks further.

**Scope:**
- Remove sensitive values where they are logged.
- Pass the CrewAI token per invocation.
- Fix the `web_search_logger` DEBUG output and the `METRIC_DEFINITIONS` parsing.
- Create the `observability` package and provider lifecycle with `OTEL_ENABLED`.
- Centralize JSON logging that follows the log record contract.
- Replace the current middleware with a pure ASGI `RequestContextMiddleware`.
- Build a canary test harness that proves no sensitive data reaches the sinks.
- Stop exception text and the remaining low-risk metadata found in the OBS-10 scan from reaching logs.

**Out of scope:** traces, new domain metrics, audit, new infrastructure.

**Done when:** canary tests show no prompt, token, credential, email or name in any operational sink. Every request returns and logs a validated `X-Request-Id`, and logs are structured JSON from one central configuration.

### OBS-10: Remove prompt and Graph token fragments from socket logs

**Type:** Security bug | **Priority:** Highest | **Depends on:** none | **Ref:** Context, §7, Rollout 1

**Description**
`backend/open_webui/socket/main.py` logs the first 100 characters of the user's prompt at INFO (~line 434) and the first 50 characters of the user's Graph access token at INFO (~line 481). Remove these at the source. Also scan the rest of the backend for similar prompt, response, token or credential logging at any level (including exception messages).

**Acceptance criteria**
- [ ] Prompt and token fragments are no longer logged at any level in `socket/main.py`.
- [ ] Replaced, if useful, with non-sensitive metadata (length, model, chat ID, presence of token as a boolean).
- [ ] Code search for other `log.*`/`print` calls that output prompt, response, token, password, API key or Authorization header values; each finding fixed or ticketed.

**Testing**
- Unit test that drives the `crew-mcp-query` handler with a canary prompt and canary token and asserts neither appears in captured log output at DEBUG level.

**Definition of done**
- Common DoD.
- List of fixed locations recorded in the PR description.

---

### OBS-11: Fix the process-global `set_user_token` defect in CrewAI

**Type:** Security bug | **Priority:** Highest | **Depends on:** none | **Ref:** Context (CrewAI), §4 CrewAI, Rollout 1

**Description**
The `crew-mcp-query` socket handler calls `crew_mcp_manager.set_user_token(...)` (`socket/main.py` ~lines 500–512), which stores the caller's Graph token in process-global state. Two concurrent CrewAI requests can run the second user's crew with the first user's token (or `None`). Pass the token per invocation, either as an argument to `run_intelligent_crew` or through a contextvar captured with `contextvars.copy_context()` and run inside the executor.

**Acceptance criteria**
- [ ] No process-global mutable token storage remains in the CrewAI path.
- [ ] Each crew run uses only the token of the authenticated user who started it.
- [ ] Executor work runs inside a copied context (or receives the token explicitly).
- [ ] Missing token handled explicitly (clear error, no fallback to another user's token).

**Testing**
- Concurrency test: start two crew runs for different users in parallel with stubbed MCP tools that record the token they received; assert each run sees only its own token, repeated many times.
- Regression test for a normal single-user CrewAI request.

**Definition of done**
- Common DoD.
- Security reviewer has approved the fix.

---

### OBS-12: Isolate sensitive DEBUG output in `web_search_logger.py`

**Type:** Security | **Depends on:** none | **Ref:** §6, Rollout 1

**Description**
`retrieval/web/web_search_logger.py` keeps query/email/name out of its INFO dispatch record but emits them at DEBUG. Remove the sensitive DEBUG emission from operational handlers (or route explicitly approved details to the restricted content path later). Remove email/name from shared metadata helpers and review URL paths, exception text and malformed-URL fallbacks.

**Acceptance criteria**
- [ ] Query, email and name never reach operational log handlers at any level.
- [ ] Existing INFO behaviour and web-search OTel metrics unchanged.
- [ ] Exception and malformed-URL fallback paths do not include the raw query or user details.

**Testing**
- Existing `test_web_search_logging.py` tests still pass (update the DEBUG assertions to expect absence).
- New test with canary query/email/name at DEBUG level asserting they are absent from all captured output.

**Definition of done**
- Common DoD.

---

### OBS-13: Parse `METRIC_DEFINITIONS` from the environment as JSON

**Type:** Bug | **Depends on:** none | **Ref:** Context, §3

**Description**
When `METRIC_DEFINITIONS` is set as an environment variable, `config.py` (~line 824) passes a string to `MetricsService`, which then fails while iterating. Parse it with `json.loads` and validate the structure.

**Acceptance criteria**
- [ ] Env value parsed with `json.loads`; built-in default used when unset.
- [ ] Invalid JSON or invalid definitions produce a clear startup error (or a logged warning and the default, as agreed), not a crash deep in `MetricsService`.

**Testing**
- Unit tests: unset, valid JSON, invalid JSON, valid JSON with a bad definition.

**Definition of done**
- Common DoD.

---

### OBS-14: Create the `observability` package and provider lifecycle

**Type:** Story | **Depends on:** OBS-03 | **Ref:** §1, §12

**Description**
Create `backend/open_webui/observability/` with `__init__.py`, `providers.py` and `context.py`. Initialize meter, tracer and logger providers once per process with shared resource attributes (service name, version, environment), before any application instruments are created. Add `OTEL_ENABLED`, `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_METRIC_EXPORT_INTERVAL`, keeping existing `INSTRUMENTATION_*` names as lower-precedence aliases (strip `/v1/metrics` from the old endpoint). Keep `instrumentation.py` as a compatibility shim exporting `meter`.

**Acceptance criteria**
- [ ] Providers initialize exactly once and flush/shut down on app shutdown.
- [ ] `OTEL_ENABLED=false` disables SDK export only; stdout logging still works and no export errors are produced.
- [ ] Alias precedence works as documented in §12.
- [ ] No circular imports with `config.py`/`env.py`.
- [ ] Existing web-search metrics still export.
- [ ] Startup/shutdown order documented in the PR.

**Testing**
- Unit tests for config precedence and alias handling.
- Test with in-memory metric reader that the existing web-search metrics are recorded.
- Manual: start the app with the collector down and `OTEL_ENABLED=false`; confirm no export errors.

**Definition of done**
- Common DoD.

---

### OBS-15: Centralize structured JSON logging (log record contract and logger policy)

**Type:** Story | **Depends on:** OBS-14 | **Ref:** §1 Log record contract and Logger policy, §7, §12

**Description**
Add `observability/logging_config.py` with a JSON formatter that follows the §1 log record contract (timestamp, severity, body, logger, resource fields, trace/span IDs, request/operation IDs, user ID, chat/message/model/provider, event, exception fields, source). Replace the 11 in-process `logging.basicConfig` calls (including the `force=True` call in `env.py`) with one central configuration. Keep standalone entrypoints (MCP servers, `backend/scripts/*`) bootstrapping their own logging. Implement the logger policy: `LOG_FORMAT=json|text`, noisy third-party loggers pinned to WARNING, `open_webui.audit*` loggers with `propagate=False`, and a per-logger rate limit (`LOG_RATE_LIMIT`, default `100/10s`) that emits a summary line when it drops records. Add `AUDIT` and `MCP` to `log_sources` in `env.py`.

**Acceptance criteria**
- [ ] Every operational log line on stdout is one JSON object matching the contract when `LOG_FORMAT=json`; text format still available for local dev.
- [ ] Same filter chain applied to stdout and (when enabled) the OTLP log handler.
- [ ] `SRC_LOG_LEVELS` still controls per-subsystem levels; `AUDIT` and `MCP` sources added.
- [ ] No remaining in-process `basicConfig` calls; MCP subprocess servers and scripts still log correctly when run standalone.
- [ ] SQLAlchemy never logs bound parameters.
- [ ] Rate limiter drops bursts and emits one summary line; `0` disables it.

**Testing**
- Unit tests for the formatter (all fields, exception fields, missing context).
- Unit test for the rate limiter.
- Test that `open_webui.audit` records do not reach the root handler.
- Manual run of one MCP server and one script to confirm their logging still works.

**Definition of done**
- Common DoD.
- Sample JSON log line included in the PR description.

---

### OBS-16: Replace `LoggingMiddleware` with a pure ASGI `RequestContextMiddleware`

**Type:** Story | **Depends on:** OBS-14, OBS-15 | **Ref:** §2

**Description**
Replace the `BaseHTTPMiddleware`-based `LoggingMiddleware` in `custom_logging.py` with a pure ASGI middleware in `observability/middleware.py`. It validates or generates `X-Request-Id`, echoes it in the response, sets request/user contextvars, measures duration until the last body chunk, and emits one completion access record under `open_webui.access`.

**Acceptance criteria**
- [ ] Non-`http` scopes (`websocket`, `lifespan`) pass straight through; Socket.IO upgrades and long-poll still work.
- [ ] Incoming `X-Request-Id` accepted only if it matches `^[A-Za-z0-9._-]{8,64}$`; otherwise a `uuid4` is generated. The ID is returned in response headers.
- [ ] Duration measured until the final `http.response.body` (`more_body=False`); streamed `/ollama` and `/openai` responses are timed correctly.
- [ ] Exactly one completion access record per request, with method, route, status, body size, `duration_ms`, client address; uvicorn's own access record no longer duplicates it.
- [ ] `/health` excluded from the access record (existing `EndpointFilter` behaviour kept).
- [ ] User ID taken from the resolved authentication context for session, bearer and API-key users.
- [ ] Contextvars reset in `finally`; disconnects, exceptions and cancellation handled without being swallowed.
- [ ] Middleware order documented.

**Testing**
- Tests for valid, malformed, too-long and missing request IDs.
- Streaming test asserting duration covers the full body and byte count is correct.
- Tests for API-key, session and bearer identity.
- Concurrency test showing contextvars do not leak between requests.
- Client disconnect mid-stream test.
- Websocket/Socket.IO connection smoke test.

**Definition of done**
- Common DoD.
- `LoggingMiddleware` removed.

---

### OBS-17: Source-confidentiality canary test harness

**Type:** Test infrastructure | **Depends on:** OBS-15 | **Ref:** §7, Verification (Source confidentiality)

**Description**
Build a reusable pytest fixture/harness that injects synthetic canary prompts, emails, API keys and token fragments into requests and checks every operational sink: stdout/stderr, all log handlers (including OTLP via an in-memory exporter), span attributes and subprocess stderr. An empty `caplog` alone is not enough proof. Later tickets reuse this harness.

**Acceptance criteria**
- [ ] Fixture captures stdout, stderr, all handler output and in-memory span/log exporters.
- [ ] Helper asserts that no canary value appears in any captured output.
- [ ] Covers success, error, DEBUG and exception paths for the HTTP chat path and the CrewAI socket path.
- [ ] Documented in the test folder README or module docstring.

**Testing**
- Self-test: a deliberately leaky test logger is detected by the harness.

**Definition of done**
- Common DoD.
- Used by at least OBS-10, OBS-11 and OBS-12 tests.

---

### OBS-18: Stop exception text from leaking prompts, payloads and credentials into logs

**Type:** Security | **Priority:** High | **Depends on:** OBS-15, OBS-17 | **Ref:** §7, OBS-10 scan follow-up

**Description**
The OBS-10 scan fixed direct logging of prompts, responses and credentials, but did not change the generic exception logging. Backend runtime code (`open_webui`, `mcp_backend`) has about 139 `log.exception(...)` calls, about 198 `log.*` calls that format the exception into the message (`{e}`, `{str(e)}`, `{err}`) and 10 `exc_info=True` calls. Exception text can repeat sensitive input:
- provider and LiteLLM/CrewAI errors that echo the prompt or request body;
- `requests`/`aiohttp` errors that include the full URL (query strings, API keys, webhook secrets);
- SQLAlchemy errors that include bound parameters;
- MCP tool errors that include tool arguments or results.

Also, when a logging handler fails, `logging.Handler.handleError` prints the record and the active (chained) exception to stderr, bypassing the filters.

OBS-10 already handled the exception paths in `socket/main.py` (`crew-mcp-query`), `retrieval/web/utils.py` (`request_json_with_timeout`), `utils/webhook.py` and `utils/oauth.py`. Use those as the pattern: log the exception type and safe fields (status code, provider name, error code) instead of the message.

**Acceptance criteria**
- [ ] Shared redaction filter (from OBS-15) applied to the formatted message, `args`, `exc_text` and the formatted traceback for stdout and OTLP handlers. It masks URL query strings, `Authorization`/`Bearer` values, JWT-shaped strings and known secret config values.
- [ ] Exception logging in the chat path (`utils/middleware.py`, `routers/openai.py`, `routers/ollama.py`, `main.py` `chat_completion`), CrewAI/MCP path (`mcp_backend/routers/*`, `mcp_backend/integration/*`, `mcp_backend/management/mcp_manager.py`) and web search/RAG path (`routers/retrieval.py`, `retrieval/*`) reviewed; each call either logs type plus safe fields or relies on the filter, with the decision recorded.
- [ ] Tracebacks keep frame locations (file, line, function) so debugging still works.
- [ ] Handler failures (`handleError`) do not print record content or chained exception messages to stderr.
- [ ] SQLAlchemy errors logged without bound parameters (`hide_parameters=True` on the engine, or equivalent).

**Testing**
- Canary harness (OBS-17): stub a provider, an outbound HTTP call, an MCP tool and a DB write to raise exceptions whose message contains a canary prompt, API key, token and URL query string; assert no canary reaches any sink, with exception frames still present.
- Unit tests for the redaction filter (URL query, bearer token, JWT, configured secret, nested chained exception).
- Test that a failing handler does not print the canary to stderr.

**Definition of done**
- Common DoD.
- List of reviewed call sites and their decision (fixed, covered by filter) recorded in the PR description.

---

### OBS-19: Remove remaining low-risk query metadata from logs

**Type:** Security | **Priority:** Medium | **Depends on:** none | **Ref:** §7, OBS-10 scan follow-up

**Description**
The OBS-10 scan found these smaller items that were left out of scope:
- `grounding/wiki_search_utils.py` logs Wikipedia article titles at INFO ("Boosted '{title}'" ~lines 621 and 660, "top result: {title}" ~line 631). Titles reveal the topic of the user's question.
- `grounding/wiki_search_utils.py` logs an 8-character prefix of an unsalted MD5 hash of the query at DEBUG (~lines 149–205). Short or common queries can be recovered by dictionary lookup.
- `mcp_backend/servers/sharepoint_oauth_client.py` logs the raw Entra ID / Graph error body (`error_text`) at ERROR/WARNING (~lines 126, 166, 271, 492, 541, 609). These bodies usually hold error codes and correlation IDs, but Graph errors can include item paths or names.
- `backend/scripts/generate_test_chats.py` prints user email and name. It is a standalone developer script, so this is accepted as intentional output; confirm it is never run in shared environments or redact it.

**Acceptance criteria**
- [ ] Wikipedia titles replaced with counts, ranks or scores only.
- [ ] Query hash removed from logs, or replaced with a keyed HMAC (key from config) if lock correlation is still needed.
- [ ] SharePoint/Graph error logs keep status, `error.code` and correlation/request IDs only; the raw body is not logged.
- [ ] Decision on `generate_test_chats.py` recorded (accept with a note in the script, or redact).

**Testing**
- Unit test for the wiki grounding path with a canary query and canary result title, asserting neither appears in captured log output at DEBUG level.
- Unit test for the SharePoint error path with a canary path in the error body, asserting it is not logged and the error code is.

**Definition of done**
- Common DoD.

---

## E2: Tracing & metrics (PR 2)

**Epic description**

**Goal:** Make each chat, RAG, MCP, CrewAI and Socket.IO operation traceable from start to finish, and record domain metrics that are accurate and safe to label.

**Why:** There are no traces today. The HTTP metrics that exist are never recorded. Generations outlive their HTTP request, so HTTP latency doesn't measure LLM performance. The CrewAI and Socket.IO paths lose context at the executor and event boundaries.

**Scope:**
- Auto-instrumentation using the stable HTTP conventions.
- `MetricsService` fixes.
- Payload, RAG and web-search spans.
- A generation context that finishes exactly once in all three response modes, with time to first token (TTFT).
- `llm_tokens_total` recorded from the same call site as `message_metrics`.
- `gen_ai.*` metadata on the provider routers.
- Context propagation for the CrewAI executor and Socket.IO.
- Spans for Qdrant, embeddings and MCP.
- Task lifecycle metrics.

**Out of scope:** audit events, storage and dashboards (E4), browser tracing (E6).

**Done when:** the generation test matrix passes (background stream, direct stream, JSON, failure, cancellation, CrewAI). Spans link correctly across task and executor boundaries. Token counts match `message_metrics`, and no metric uses an unbounded label.

### OBS-20: Enable tracing and auto-instrumentation with stable HTTP conventions

**Type:** Story | **Depends on:** OBS-03, OBS-14, OBS-16 | **Ref:** §1 tracing.py, §2, §12

**Description**
Add `observability/tracing.py`. Instrument FastAPI, aiohttp, requests, SQLAlchemy and Redis with the pinned versions. Set `OTEL_SEMCONV_STABILITY_OPT_IN=http` before instrumentors load. Add a parent-based ratio sampler (`OTEL_TRACES_SAMPLER_RATIO`) and `OTEL_TRACES_HEALTHCHECKS`. Disable per-chunk ASGI send/receive spans where supported. Allow-list span attributes and propagation destinations. Retire the unused hand-made `http_requests_total`/`http_request_duration_ms` instruments.

**Acceptance criteria**
- [ ] Server spans for HTTP routes with route templates (bounded cardinality).
- [ ] `http.server.request.duration` exported in seconds; request counts derived from its histogram count.
- [ ] Client spans for aiohttp, requests, SQLAlchemy and Redis calls; SQL parameter values never captured.
- [ ] `traceparent` propagated only to internal/approved destinations, never to external LLM providers with user baggage.
- [ ] Health checks produce no spans unless `OTEL_TRACES_HEALTHCHECKS=true`.
- [ ] Log records include `trace_id`/`span_id` when a span is active.
- [ ] Actual metric names and labels verified against the pinned collector/Prometheus and recorded.

**Testing**
- In-memory span exporter tests for a route, a DB call and an outbound aiohttp call.
- Test that the log formatter picks up the active trace/span IDs.
- Test sampler behaviour with missing, malformed and adversarial `traceparent` headers.

**Definition of done**
- Common DoD.
- Custom HTTP instruments removed from `METRIC_DEFINITIONS`.

---

### OBS-21: Fix and extend `MetricsService`

**Type:** Story | **Depends on:** OBS-13, OBS-14 | **Ref:** §3, §4 Tasks

**Description**
Add `record(name, value, attrs)` for counters and histograms, register observable-gauge callbacks at instrument creation (or via a registry-owned dispatcher), define histogram buckets and units suited to long LLM operations, and enforce label allow-lists. Replace `print()` calls with `log.*`. Decide whether `task_queue_size` is renamed (it measures active local tasks, not a durable queue) and document it.

**Acceptance criteria**
- [ ] Counters, histograms and observable gauges work through one API.
- [ ] Histogram boundaries/units defined for LLM duration, TTFT, RAG and MCP latencies.
- [ ] Labels outside the allow-list (user, session, request, chat, trace IDs) are rejected or dropped with a warning.
- [ ] No `print()` left in `metrics/service.py`.
- [ ] `task_queue_size` renamed or documented as active local tasks, aggregated correctly across instances.

**Testing**
- Unit tests with an in-memory metric reader for each instrument type, gauge callbacks and label rejection.

**Definition of done**
- Common DoD.

---

### OBS-22: Instrument chat payload processing, tools, files and web search

**Type:** Story | **Depends on:** OBS-20 | **Ref:** §4 Chat payload, Chat request lifecycle

**Description**
Add manual spans in `main.py` (`chat_completion`) and `utils/middleware.py` for `chat.process_payload`, tool handling, file handling and web search, plus an end-to-end chat operation duration that spans preprocessing and response delivery (separate from provider latency). Title/tag generation and retries are separate operations.

**Acceptance criteria**
- [ ] Spans for payload processing, tools, files and web search with allow-listed attributes only (model, chat ID, feature flags; no content).
- [ ] End-to-end chat duration metric recorded once per chat operation.
- [ ] Title/tag generation recorded as distinct operations, not extra completions.

**Testing**
- In-memory exporter test of a chat request with web search and a file; assert span tree and attributes.
- Canary harness (OBS-17) run against the chat path.

**Definition of done**
- Common DoD.

---

### OBS-23: LLM generation operation context across all response modes

**Type:** Story | **Depends on:** OBS-20, OBS-21 | **Ref:** §4 Provider operation, Chat request lifecycle

**Description**
Create an explicit operation context in `observability/context.py` (span, monotonic start, IDs, completion state). Start `llm.chat` and its timer immediately before the provider call. Hand responsibility for finalizing it to whichever path consumes the response: the background Socket.IO task (`process_chat_response` with session/chat/message metadata), a direct HTTP `StreamingResponse`, or a non-streaming JSON response. Record `llm_requests_total{model,provider,outcome}` and `llm_request_duration_ms`. Measure TTFT from invocation to the first parsed content token.

**Acceptance criteria**
- [ ] Operation finalizes exactly once in all three response modes, including provider errors, mid-stream failure and cancellation.
- [ ] TTFT excludes headers, SSE keepalives and task start; not recorded for non-streaming responses.
- [ ] Retries have attempt-level spans; the operation is counted once.
- [ ] Missing usage data recorded as unknown, not zero.
- [ ] No per-token spans or per-chunk INFO logs.
- [ ] The `llm.chat` span may outlive its HTTP parent span without breaking the trace.

**Testing**
- Generation matrix tests (stubbed provider): background Socket.IO stream, direct HTTP stream, JSON, failure before headers, mid-stream failure, cancellation, multi-model request.
- Assert provider-start timestamp precedes the handoff, TTFT excludes keepalives, and metrics finalize exactly once.

**Definition of done**
- Common DoD.

---

### OBS-24: Emit `llm_tokens_total` from the `MessageMetrics.insert_new_metrics` call sites

**Type:** Story | **Depends on:** OBS-01, OBS-21, OBS-23 | **Ref:** §4 Provider operation, §5 Relationship to `message_metrics`

**Description**
Emit `llm_tokens_total{type}` from the same call site (or a thin wrapper) as `MessageMetrics.insert_new_metrics` in `utils/middleware.py` and `socket/main.py`, so the OTel counter and the admin dashboard cannot drift.

**Acceptance criteria**
- [ ] One wrapper writes the `message_metrics` row and records `llm_tokens_total` (prompt/completion).
- [ ] All existing call sites use the wrapper; no separate token-count code path.
- [ ] Admin metrics dashboard values unchanged.

**Testing**
- Test that for a stubbed completion the DB row token totals equal the recorded counter values.
- Existing metrics router tests pass.

**Definition of done**
- Common DoD.

---

### OBS-25: Add approved `gen_ai.*` metadata to provider routers

**Type:** Story | **Depends on:** OBS-23 | **Ref:** §4 Provider routers

**Description**
Add only approved `gen_ai.*` attributes (for example system/provider, request model, response model, token usage) in `routers/openai.py` and `routers/ollama.py`. Cover direct provider endpoints and function/pipeline models, not just normal chat.

**Acceptance criteria**
- [ ] Approved attribute list documented; no prompt or completion content captured.
- [ ] Direct `/openai` and `/ollama` endpoints and function/pipeline models produce the attributes.

**Testing**
- In-memory exporter tests for each provider router and a pipeline model.

**Definition of done**
- Common DoD.

---

### OBS-26: Instrument the CrewAI path with explicit context propagation

**Type:** Story | **Depends on:** OBS-11, OBS-23 | **Ref:** §4 CrewAI, CrewAI lifecycle

**Description**
Instrument `crew-mcp-query` independently of the HTTP chat path. Copy the current context explicitly into each `run_in_executor` call. Add spans for crew orchestration, model invocations (using the client identified in OBS-03), MCP tools, token usage, errors/cancellation, and its own timer and finalization.

**Acceptance criteria**
- [ ] Parent/child context survives the executor boundary.
- [ ] Crew, model and tool spans linked to the socket event's operation context.
- [ ] Metrics and token usage finalize exactly once, including errors and cancellation.
- [ ] Actor on spans comes from the authenticated socket session (requires OBS-11).

**Testing**
- Test with stubbed crew/tools asserting span tree, context propagation and single finalization.
- Concurrency test that two crews have separate trace and user context.

**Definition of done**
- Common DoD.

---

### OBS-27: Socket.IO per-event context and browser operation carrier

**Type:** Story | **Depends on:** OBS-20 | **Ref:** §4 Socket.IO, §10 Trace correlation

**Description**
Create per-event context on the server from the authenticated session identity and a validated operation carrier (`traceparent`, operation/request ID) sent by the browser. Add the carrier to Socket.IO business events (at least `crew-mcp-query`) on the client side in `Chat.svelte`. Reset context after each event, handle reconnects and add bounded connection/event/outcome counters.

**Acceptance criteria**
- [ ] Client sends a validated operation ID and `traceparent` with business events.
- [ ] Server validates the carrier (same rules as `X-Request-Id`) and ignores invalid values.
- [ ] Context reset after every event; no leakage between events on the same socket.
- [ ] Socket ID and Faro session ID are never used as an operation ID.
- [ ] Connection gauge and event/outcome counters with bounded labels.

**Testing**
- Server tests for valid, invalid and missing carriers and for context reset.
- Frontend unit test that the carrier is attached to the event payload.

**Definition of done**
- Common DoD.

---

### OBS-28: Instrument RAG (Qdrant and embeddings)

**Type:** Story | **Depends on:** OBS-20, OBS-21 | **Ref:** §4 RAG

**Description**
Wrap Qdrant client calls (`retrieval/vector/dbs/qdrant.py`) in manual spans (no OTel instrumentor exists for `qdrant-client`). Add embedding spans, latency and result-count metrics. Note that Ollama/OpenAI embeddings use synchronous `requests.post` on the event loop (`retrieval/utils.py`); create a follow-up ticket to move them to a thread or async client.

**Acceptance criteria**
- [ ] Spans for embedding generation and vector query/insert/delete with collection name and result count (no query text).
- [ ] `rag_*` latency and result-count metrics recorded.
- [ ] Follow-up ticket created for the blocking embeddings call.

**Testing**
- In-memory exporter tests with a stubbed Qdrant client and embedding function.

**Definition of done**
- Common DoD.

---

### OBS-29: Instrument MCP tool calls and the stdio boundary

**Type:** Story | **Depends on:** OBS-20, OBS-21 | **Ref:** §4 MCP

**Description**
Instrument `mcp_manager.call_tool` (`mcp_backend/management/mcp_manager.py`) and any crew-specific tool boundary with spans and latency/outcome metrics. Treat stdio as an explicit propagation boundary. Filter subprocess stderr before forwarding it to logs.

**Acceptance criteria**
- [ ] Span and metrics for each tool call with server and tool name (bounded) and outcome; no arguments or results captured.
- [ ] Stdio boundary documented; no attempt to pass trace context unless a supported carrier exists.
- [ ] Subprocess stderr passes through the shared source filter before logging.

**Testing**
- Test with a stub MCP server; assert span/metrics and that canary values in stderr are filtered (OBS-17 harness).

**Definition of done**
- Common DoD.

---

### OBS-30: Task lifecycle metrics in `tasks.py`

**Type:** Story | **Depends on:** OBS-21 | **Ref:** §4 Tasks

**Description**
Record active local task counts and task outcomes from the registry in `tasks.py`, and make sure generation operations finalize correctly when tasks are cancelled or the process shuts down.

**Acceptance criteria**
- [ ] Active task gauge (name agreed in OBS-21) and task outcome counter.
- [ ] Cancelled tasks and shutdown finalize their operation once.

**Testing**
- Tests for task completion, cancellation and shutdown finalization.

**Definition of done**
- Common DoD.

---

## E3: Durable audit (PR 3)

**Epic description**

**Goal:** Record security-relevant actions as metadata-only audit events that are durable, schema-validated, and delivered to the SSC SIEM/evidence archive with a Loki search copy.

**Why:** Audit logging today is limited to one module and delivered on a best-effort basis. A logger call or an OTLP success is not a durable record. Security events need a consistent schema, stable IDs, an atomic write with the state change, and delivery that can be shown to have arrived.

**Scope:**
- Session-injection refactor for the audited models.
- Outbox table and the `emit_audit_event` API.
- Delivery worker with receipts, retries and backlog metrics.
- Audit events for auth, admin, access, resources and exports.
- Chat-metadata audit through `message_metrics`.
- `AUDIT_FAIL_POLICY`.
- Shared helpers with `web_search_logger`.

**Out of scope:** storing chat content (E8), the SIEM adapter implementation (E4), hold and disposition workflows (records-management design).

**Done when:** each audited action writes its event in the same transaction as the change. Events reach both destinations with stored receipts. Crash and replay tests show no silent loss and no duplicates, and privileged actions fail closed when auditing fails.

### OBS-40: Implement the session-injection refactor for audited models

**Type:** Story | **Depends on:** OBS-02 | **Ref:** §5 Persistence and delivery

**Description**
Apply the pattern chosen in OBS-02 to the model methods for users, groups, configs, chats, files, knowledge and MCP servers so a state change and its audit outbox row can be written in one transaction.

**Acceptance criteria**
- [ ] All methods listed in the OBS-02 inventory accept an injected session or unit of work.
- [ ] Existing callers keep working without changes.
- [ ] No change in behaviour for non-audited callers.

**Testing**
- Existing model and router tests pass.
- Transaction tests per model area: state change and a dummy outbox row commit together and roll back together.

**Definition of done**
- Common DoD.

---

### OBS-41: Audit outbox schema, migration and `emit_audit_event` API

**Type:** Story | **Depends on:** OBS-04, OBS-40 | **Ref:** §1 audit.py, §5 | **Schema:** [OBS-04 decision](Canchat-v2-OBS-04-Audit-Event-Schema.md), [JSON Schema v1](obs04-audit-event-v1.schema.json)

**Description**
Add `observability/audit.py` with `emit_audit_event(...)` that validates the approved v1 schema and writes an outbox row with a stable `event_id` in the caller's transaction. Add the Alembic migration for the outbox table (event, status per destination, attempts, timestamps). Add `AUDIT_ENABLED`. Encrypt stored events at rest as required by the approved design.

**Acceptance criteria**
- [ ] Migration applies and rolls back cleanly on SQLite and Postgres.
- [ ] Invalid events (unknown action, forbidden fields, oversize metadata) rejected.
- [ ] Event written in the same transaction as the state change when a session is passed.
- [ ] `OTEL_ENABLED=false` does not disable audit persistence.
- [ ] Audit events are never trace-sampled.

**Testing**
- Schema validation tests (valid, forbidden field, unknown action).
- Transaction tests (commit and rollback).
- Test that `OTEL_ENABLED=false` still writes outbox rows.

**Definition of done**
- Common DoD.

---

### OBS-42: Audit delivery worker with receipts and retries

**Type:** Story | **Depends on:** OBS-41 | **Ref:** §5 Persistence and delivery, Gate 4

**Description**
Add a delivery worker that reads the outbox and delivers each event to (1) the authoritative SIEM/evidence destination and (2) the Loki search copy (via `open_webui.audit` logger / OTLP), tracking each destination separately. Use idempotent delivery by `event_id`, retry with backoff, shutdown draining and crash recovery. Keep rows until the required durable receipt is recorded. Add `AUDIT_DELIVERY_ENABLED`, `AUDIT_SIEM_URL`, `AUDIT_SIEM_AUTH_*`, and queue-age/backlog metrics.

**Acceptance criteria**
- [ ] Per-destination delivery status and receipt stored.
- [ ] Retries with bounded backoff; duplicates prevented by `event_id`.
- [ ] Worker restart resumes undelivered events without loss or duplicate logical events.
- [ ] `AUDIT_DELIVERY_ENABLED=false` keeps the outbox and exposes backlog metrics for alerting.
- [ ] Backlog age and size metrics exported.
- [ ] Only one worker processes a given event when multiple app replicas run.

**Testing**
- Tests with fake SIEM and fake Loki endpoints: success, transient failure, permanent failure, worker crash and restart, duplicate delivery, multi-replica locking.

**Definition of done**
- Common DoD.

---

### OBS-43: Audit events for authentication

**Type:** Story | **Depends on:** OBS-41 | **Ref:** §5

**Description**
Emit audit events for login success/failure, logout and token refresh failure in `routers/auths.py` and `utils/auth.py`. For failed logins, use the approved keyed pseudonymization (`AUDIT_PSEUDONYM_KEY_ID`) instead of the email.

**Acceptance criteria**
- [ ] Events emitted for each action with trusted actor ID (when known), outcome and correlation IDs.
- [ ] Failed-login events never contain the email or name; pseudonym is stable for the same input and key.
- [ ] Failures recorded independently of any state change transaction.

**Testing**
- Router tests for each auth action asserting outbox contents.
- Test that pseudonyms are stable and change after key rotation.

**Definition of done**
- Common DoD.

---

### OBS-44: Audit events for admin, access and resource changes

**Type:** Story | **Depends on:** OBS-40, OBS-41 | **Ref:** §5

**Description**
Emit audit events for user role and group changes, admin config changes (`routers/configs.py`), model access denied (`check_model_access`), file upload/delete, knowledge-base changes, MCP server changes, and metrics exports (next to `ExportLogs.insert_new_export_log` and the export endpoint in `routers/metrics.py`). Write them in the same transaction as the state change.

**Acceptance criteria**
- [ ] One event type per action listed above, matching the approved schema.
- [ ] No config secret values, file names, KB names, email or names in events (IDs and bounded metadata only).
- [ ] State change and audit row are atomic.

**Testing**
- Router tests per action asserting the outbox row and atomic rollback on failure.

**Definition of done**
- Common DoD.

---

### OBS-45: Chat-metadata audit event via `message_metrics`

**Type:** Story | **Depends on:** OBS-01, OBS-24, OBS-41 | **Ref:** §5 Relationship to `message_metrics`

**Description**
Following option (a) from OBS-01: extend the `message_metrics` row with the missing feature flags (files, web search, knowledge, tools), outcome and correlation IDs, and enqueue the `category=chat`, `action=message` audit event in the same `insert_new_metrics` transaction. Cover the HTTP and CrewAI paths. (If OBS-01 chose option (b), rewrite this ticket for a separate audit table with reconciliation tests.)

**Acceptance criteria**
- [ ] Migration adds the new columns; existing rows remain valid.
- [ ] One audit event per finalized message, in the same transaction as the metrics row.
- [ ] No message content in the row or event.
- [ ] Admin metrics dashboard still works.

**Testing**
- Tests for HTTP and CrewAI paths asserting one metrics row and one outbox event with matching IDs and token counts.
- Rollback test.

**Definition of done**
- Common DoD.

---

### OBS-46: Implement `AUDIT_FAIL_POLICY`

**Type:** Story | **Depends on:** OBS-04, OBS-41 | **Ref:** §5, §12 | **Policy:** [OBS-04 §5](Canchat-v2-OBS-04-Audit-Event-Schema.md#5-failure-policy-audit_fail_policy)

**Description**
Implement the approved failure policy when the audit record cannot be persisted: `block_privileged` (admin/config/export actions fail closed; chat/auth fail open with alert) or `block_all`.

**Acceptance criteria**
- [ ] Privileged actions return an error and do not apply the change when the audit write fails.
- [ ] Fail-open actions succeed, log a non-sensitive error and increment a failure metric that drives an alert.
- [ ] Policy selectable with `AUDIT_FAIL_POLICY`.

**Testing**
- Tests simulating outbox write failure for a privileged action and for a chat/auth action under both policies.

**Definition of done**
- Common DoD.

---

### OBS-47: Refactor `web_search_logger.py` to share audit helpers

**Type:** Story | **Depends on:** OBS-12, OBS-41 | **Ref:** §6

**Description**
Share schema/serialization helpers between `web_search_logger.py` and `observability/audit.py` while keeping the web-search metrics and existing INFO sanitization. Do not treat the existing best-effort INFO logger as a durable audit sink.

**Acceptance criteria**
- [ ] Shared helpers used by both modules.
- [ ] Web-search metrics and INFO records unchanged.

**Testing**
- Existing `test_web_search_logging.py` tests pass unchanged (apart from OBS-12 updates).

**Definition of done**
- Common DoD.

---

## E4: Observability infrastructure (PR 4)

**Epic description**

**Goal:** Run a pinned, self-hosted observability stack that stores, isolates, displays and alerts on the backend's telemetry, both locally and in production.

**Why:** Only the collector and Prometheus exist today, and they live inside the Qdrant compose file. Logs and traces have nowhere to go. Operations, audit and analytics data must be kept apart, because Grafana Viewer permissions alone don't restrict queries against raw data.

**Scope:**
- A `docker-compose.observability.yaml` overlay.
- Collector ingress classes with authentication, filtering and routing.
- A tenant-enforcing proxy in front of Loki.
- A separate aggregate-only Prometheus for analytics.
- Three Grafana orgs (Operations, Audit, Analytics) with SSO mapping.
- Operations and audit dashboards, plus alert rules.
- The SIEM adapter.
- Kubernetes manifests.
- One log shipping path per environment.

**Out of scope:** Faro and Alloy (E6), retention values (E5).

**Done when:** the end-to-end scenario shows correlated logs, traces and metrics in Grafana. Authorization tests show each org can reach only its own data, and forged tenant headers are rejected. Alerts fire and resolve, and the stack deploys to a test cluster with a tested restore.

### OBS-50: Create `docker-compose.observability.yaml` with the pinned stack

**Type:** Story | **Depends on:** OBS-03 | **Ref:** §9 New docker-compose.observability.yaml

**Description**
Move `otel-collector` and `prometheus` out of `docker-compose.qdrant.yaml` into a new `docker-compose.observability.yaml` overlay. Add Loki 3.x (with compactor retention and persistent storage), the tenant-enforcing proxy, Tempo, Grafana and an isolated `prometheus-analytics`. Use pinned image versions. (Alloy is added in OBS-76.)

**Acceptance criteria**
- [ ] `docker compose -f docker-compose.yaml -f docker-compose.observability.yaml up` starts all services healthy.
- [ ] `docker-compose.qdrant.yaml` still works without observability services.
- [ ] All images pinned by version.
- [ ] `run-compose.sh`, `INSTALLATION.md` and the Makefile updated if they reference the moved services.

**Testing**
- Manual: start the overlay, send a chat request, confirm logs in Loki, traces in Tempo and metrics in Prometheus.
- Config validation with the pinned binaries (for example `otelcol validate`, `loki -verify-config`).

**Definition of done**
- Common DoD.

---

### OBS-51: Collector configuration: trusted ingress, filtering and routing

**Type:** Story | **Depends on:** OBS-50 | **Ref:** §9 otel-collector-config.yaml

**Description**
Rework `otel-collector-config.yaml`: TLS and service authentication on internal OTLP receivers; separate receivers/pipelines for backend, frontend and audit-delivery classes; `memory_limiter`, batching and persistent exporter queues; structured-body parsing and field policies for logs and trace attributes; trusted routing metadata set at ingress (overwriting client values); `otlphttp` to Loki `/otlp` with fixed tenant headers; OTLP to Tempo; reject/drop policy for unknown telemetry with counters. Remove raw-payload debug exporters from production configs.

**Acceptance criteria**
- [ ] Each ingress class authenticated and routed to its own tenant; client-supplied `service.name`, scope or `X-Scope-OrgID` cannot change the tenant.
- [ ] Legacy `loki` exporter not used.
- [ ] Collector health, queue, rejected-data and export-failure metrics scraped separately.
- [ ] No debug exporter dumping payloads in production config.
- [ ] Browsers can never reach a general OTLP receiver.

**Testing**
- Config validation with the pinned binary.
- Integration test sending forged tenant headers / `service.name` from each class and asserting the data lands in the correct tenant (or is dropped).
- Test with an unauthenticated client being rejected.

**Definition of done**
- Common DoD.

---

### OBS-52: Loki tenant-enforcing proxy

**Type:** Story | **Depends on:** OBS-50 | **Ref:** §9, Products (Loki)

**Description**
Put a proxy in front of Loki that fixes the tenant per caller identity (`app`, `frontend`, `audit`) and strips or rejects client-supplied `X-Scope-OrgID`. Do not log sensitive query literals in the proxy's operational logs.

**Acceptance criteria**
- [ ] Each Grafana data source and each writer can only reach its own tenant.
- [ ] Tenant header overrides rejected.
- [ ] Proxy logs contain no query bodies.

**Testing**
- Tests that each identity can read/write only its tenant and that forged headers are rejected.

**Definition of done**
- Common DoD.

---

### OBS-53: Isolated aggregate-only analytics Prometheus

**Type:** Story | **Depends on:** OBS-50 | **Ref:** §9, §10 Aggregation contract

**Description**
Configure `prometheus-analytics` with a remote-write receiver restricted to trusted aggregation producers, no access to operational stores, and a label allow-list that excludes user, session, request and trace IDs.

**Acceptance criteria**
- [ ] Only authenticated aggregation producers can remote-write.
- [ ] Series with disallowed labels rejected or dropped.
- [ ] No scrape or query path to raw Loki/Tempo/operational Prometheus.

**Testing**
- Test that an unauthorized writer is rejected and a series with a `user_id` label is dropped.

**Definition of done**
- Common DoD.

---

### OBS-54: Provision Grafana orgs, data sources and SSO mapping

**Type:** Story | **Depends on:** OBS-51, OBS-52, OBS-53 | **Ref:** §9 Grafana access model

**Description**
Provision three Grafana orgs: **Operations** (app/frontend Loki, Tempo, operational Prometheus), **Audit** (audit Loki tenant and evidence access) and **Analytics** (only `prometheus-analytics`). Configure fixed-tenant data sources, trace-to-log mappings and explicit SSO group mappings. Record the human actor on audit queries/exports.

**Acceptance criteria**
- [ ] Analytics Viewers cannot query raw Loki/Tempo/operational Prometheus, including through the data source API.
- [ ] Operations users cannot query audit stores.
- [ ] Trace-to-logs links work in Operations.
- [ ] Audit query/export actions are attributed to the human user.
- [ ] Field names used in queries verified against actual OTLP-to-Loki output.

**Testing**
- Authorization tests per role using the Grafana HTTP API (`/api/ds/query`) against each data source.

**Definition of done**
- Common DoD.

---

### OBS-55: Operations and Audit dashboards

**Type:** Story | **Depends on:** OBS-54, OBS-23, OBS-28, OBS-30, OBS-43 | **Ref:** §9 Grafana dashboards (1–4, 7)

**Description**
Provision JSON dashboards: Service health (RED per route), LLM (requests, TTFT, duration, tokens, failures, cancellations), RAG & web search, Socket & tasks, and Security audit (auth failures, admin changes, access denied).

**Acceptance criteria**
- [ ] Dashboards provisioned from files in the repo, in the correct org.
- [ ] Every panel shows data in the local Compose environment after a test run.
- [ ] Queries use only bounded labels.

**Testing**
- Manual: run chat, RAG, CrewAI and failed-login scenarios and confirm each panel updates.

**Definition of done**
- Common DoD.
- Screenshots attached to the PR.

---

### OBS-56: Alert rules

**Type:** Story | **Depends on:** OBS-55, OBS-42 | **Ref:** §9 Alerts

**Description**
Provision alert rules for HTTP/LLM error rates, TTFT regression, auth-failure spikes, audit backlog age/size, rejected data, exporter/storage failures and ingestion silence (accounting for expected inactivity). Frontend alerts are added in OBS-78.

**Acceptance criteria**
- [ ] Rules provisioned as code with documented thresholds and owners.
- [ ] Contact points configured per environment.

**Testing**
- Trigger each alert in the local stack (for example stop the collector, pause audit delivery, inject errors) and confirm it fires and resolves.

**Definition of done**
- Common DoD.

---

### OBS-57: SIEM / evidence archive adapter

**Type:** Story | **Depends on:** OBS-04, OBS-42 | **Ref:** §5, §9, §11 Central SIEM

**Description**
Implement the SSC-approved protocol/adapter used by the delivery worker for the authoritative destination, including documented acknowledgements, replay and deduplication.

**Acceptance criteria**
- [ ] Adapter returns a durable receipt only when the SIEM/archive confirms storage.
- [ ] Replay and deduplication by `event_id` supported.
- [ ] Credentials loaded from secrets, not config files.

**Testing**
- Integration test against an SSC test endpoint or an agreed stub; interrupt the SIEM and verify replay without loss or duplicates.

**Definition of done**
- Common DoD.
- Interface approved by SSC Security.

---

### OBS-58: Kubernetes/production manifests for the observability stack

**Type:** Story | **Depends on:** OBS-06, OBS-50 to OBS-57 | **Ref:** §9 Production deployment

**Description**
Add the app settings to `kubernetes/manifest/base/webui-deployment.yaml` and provide manifests (or approved managed-service integrations) for all receivers, stores, workers, proxies and persistent volumes, following OBS-06. Include network policies, secrets and resource limits.

**Acceptance criteria**
- [ ] All components deployable in a test cluster with persistent storage.
- [ ] Network policies restrict traffic to the documented flows; egress blocked except approved destinations.
- [ ] Backup and restore procedure documented and tested for each store.

**Testing**
- Deploy to a test cluster, run the end-to-end scenario, and perform a restore test for Loki and the audit outbox DB.

**Definition of done**
- Common DoD.
- Runbook added under `docs/`.

---

### OBS-59: Choose one operational log shipping path per environment

**Type:** Decision / Task | **Depends on:** OBS-51 | **Ref:** §9 One operational log shipping path

**Description**
Decide per environment whether operational logs are shipped by OTLP or by container-log collection, and disable the other to avoid duplicates. Stdout remains filtered either way.

**Acceptance criteria**
- [ ] Decision recorded per environment.
- [ ] Configuration ensures each log line is ingested once.

**Testing**
- Send a uniquely tagged log line and verify exactly one copy in Loki.

**Definition of done**
- Common DoD.

---

## E5: Retention TTLs (PR 5)

**Epic description**

**Goal:** Configure each telemetry store to keep data for the period SSC approved under the Treasury Board requirements.

**Why:** Every store needs a defined retention period. The plan maps records to minimum periods (PBMM log floors, the 30-day chat lifecycle, administrative-use rules). Holds, deletion enforcement and the evidence archive belong to a separate records-management program.

**Scope:**
- Retention settings per tenant and per store for Loki, Tempo and both Prometheus instances, using the values approved in OBS-05.
- TTL tests.
- Creating the separate records-management design document.

**Out of scope:** implementing the hold model, hold-aware deletion, the immutable archive and disposition verification. These are tracked from the records-management design and do not block other epics.

**Done when:** configured retention matches the approved table, tests with shortened retention show data expiring correctly, and the records-management design has an owner and its own epic.

### OBS-60: Apply retention TTLs to Loki, Tempo and Prometheus

**Type:** Story | **Depends on:** OBS-05, OBS-50 | **Ref:** §11 table, Rollout 5

**Description**
Configure per-tenant Loki retention (`app` 6 months, `frontend` 6 months, `audit` 2 years, or the values approved in OBS-05), Tempo 30 days, and 13 months for both Prometheus instances. Translate calendar periods into supported durations deliberately, accounting for deletion delays and backups.

**Acceptance criteria**
- [ ] Retention values match the approved §11 table.
- [ ] Compactor/retention settings validated with the pinned binaries.
- [ ] Backup/object-version lifecycle does not keep data longer than allowed without a documented reason.

**Testing**
- TTL tests with shortened test retention and controlled clocks, confirming data expires per store.

**Definition of done**
- Common DoD.

---

### OBS-61: Create the separate records-management design document

**Type:** Task | **Depends on:** OBS-05 | **Ref:** §11 Scope note

**Description**
Create `docs/observability/Canchat-v2-Records-Management.md` covering the hold model, hold-aware deletion enforcement across all chat/file/vector deletion paths, the immutable evidence archive and disposition verification. This is not a blocker for PRs 1–4 or 6–7 and gets its own tickets once designed.

**Acceptance criteria**
- [ ] Document created with the requirements carried over from §11 Implementation.
- [ ] Owner and follow-up epic created in Jira.

**Testing**
- None (document).

**Definition of done**
- Common DoD.
- Reviewed by SSC IM/Security.

---

## E6: Frontend observability & analytics, Grafana Faro (PR 6)

**Epic description**

**Goal:** Give CANChat visibility into browser errors, web vitals and traces, plus privacy-safe usage analytics, all through Grafana Faro on the self-hosted stack.

**Why:** The frontend has no visibility today: it captures no client errors, sends no correlation headers and produces no usage data beyond server-side `message_metrics`. Product owners need adoption metrics without access to raw user-level data.

**Scope:**
- Faro runtime config served through `/api/config`.
- Bootstrap, navigation and `page_view` handling.
- Error bridge and session handling.
- Fetch correlation and trace propagation.
- Typed wrapper for the allow-listed events.
- `beforeSend` privacy filtering.
- Alloy `faro.receiver` behind a same-origin `/faro/collect` route.
- Aggregation jobs that write to the analytics Prometheus.
- Frontend health and usage dashboards, and frontend alerts.

**Out of scope:** treating browser telemetry as security evidence. It is not a prerequisite for E1–E4.

**Done when:** browser→backend traces link in Tempo, and canary tests show no free text or IDs in Faro payloads. Forged payloads cannot reach other tenants. Windowed distinct counts pass the fixture tests, and Analytics users can see only aggregates.

### OBS-70: Pin Faro/Alloy versions and expose Faro runtime config

**Type:** Story | **Depends on:** none | **Ref:** §10 Runtime configuration, §12, Gate 1

**Description**
Pin `@grafana/faro-web-sdk`, `@grafana/faro-web-tracing` and Alloy versions; capture real payload samples. Add `ENABLE_FARO`, `FARO_COLLECTOR_URL`, `FARO_SESSION_SAMPLE_RATE`, `FARO_TRACES_SAMPLE_RATE` and `FARO_ENVIRONMENT` to the backend and expose them through `/api/config`.

**Acceptance criteria**
- [ ] Versions pinned in `package.json`; SDK bundled (no CDN).
- [ ] Settings returned by `/api/config` with defaults from §12.
- [ ] `FARO_TRACES_SAMPLE_RATE` and `OTEL_TRACES_SAMPLER_RATIO` alignment documented.

**Testing**
- Backend test for the `/api/config` fields.

**Definition of done**
- Common DoD.

---

### OBS-71: Faro bootstrap, navigation, page views, errors and sessions

**Type:** Story | **Depends on:** OBS-70 | **Ref:** §10 Bootstrap

**Description**
Initialize Faro once in `src/hooks.client.ts` when runtime config is loaded, using a dynamic import so disabled Faro chunks are not downloaded. Use `afterNavigate` in `src/routes/+layout.svelte` to set the view (normalized route ID) and emit one `page_view` per successful navigation. Bridge SvelteKit `handleError` to Faro with deduplication. Disable broad console capture. Implement the session contract (per tab, survives reload, rotates on logout/account change, inactivity timeout) and user association on login and session restore.

**Acceptance criteria**
- [ ] Faro initialized exactly once; not loaded when `ENABLE_FARO=false`.
- [ ] One `page_view` per navigation, including between two chats with the same route template.
- [ ] Errors from `handleError` and automatic instrumentation deduplicated.
- [ ] Console capture disabled by default.
- [ ] Sessions are per tab, survive reloads, rotate on logout/account switch and expire after the documented timeout.
- [ ] Only the approved user ID is attached; reset on logout.

**Testing**
- Frontend unit tests for init-once, disabled mode, page-view emission and error deduplication.
- Playwright tests for reload, two tabs, logout/login as another user, and same-template navigation.

**Definition of done**
- Common DoD.

---

### OBS-72: Fetch correlation and browser trace propagation

**Type:** Story | **Depends on:** OBS-16, OBS-71 | **Ref:** §10 Correlation, Trace correlation

**Description**
In `src/lib/apis/client.ts`, add a bounded `X-Request-Id` to internal API calls and attach it to failures. Configure Faro fetch tracing with an allow-list of internal origins/paths and exclusions for `/faro/collect`, health checks and telemetry exporters. Keep the logical operation ID across 401 retries while giving each network attempt its own span.

**Acceptance criteria**
- [ ] Internal calls carry `X-Request-Id` and `traceparent`; external origins receive neither.
- [ ] Faro's own requests are not traced.
- [ ] No double wrapping with the existing auth fetch interceptor; 401 retries remain visible.
- [ ] Browser span links to the backend server span in Tempo.

**Testing**
- Unit tests for header injection and exclusions.
- Manual end-to-end: confirm a browser→backend trace in Tempo.

**Definition of done**
- Common DoD.

---

### OBS-73: Typed analytics wrapper and allow-listed usage events

**Type:** Story | **Depends on:** OBS-71 | **Ref:** §10 Usage events

**Description**
Create `src/lib/utils/analytics.ts`, a typed wrapper over `faro.api.pushEvent` that only accepts the allow-listed events and attributes in §10 (page_view, chat_started, message_sent, model_selected, web_search_toggled, file_uploaded, knowledge_used, mcp_tool_enabled, response_feedback, response_copied, response_regenerated, language_changed, settings_opened). Validate values at runtime (enums, length limits, unknown fields rejected). Define for each event whether it means attempted or successful and where it is emitted. Add event IDs for deduplication.

**Acceptance criteria**
- [ ] Wrapper rejects unknown events, unknown attributes and invalid values at runtime.
- [ ] Each event emitted from exactly one documented place.
- [ ] No free text (prompts, file names, KB names, queries, titles, email) can be sent.
- [ ] Booleans/numbers mapped to the SDK's accepted attribute types.

**Testing**
- Unit tests for each event (valid, invalid value, unknown key).
- Component tests confirming events fire once per user action.

**Definition of done**
- Common DoD.
- Collector/Alloy allow-list and §10 table updated in the same PR.

---

### OBS-74: Browser telemetry privacy filter (`beforeSend`)

**Type:** Story | **Depends on:** OBS-71 | **Ref:** §10 Bootstrap, Privacy

**Description**
Implement and test a `beforeSend` policy that applies to all Faro signal types and nested attributes: normalize or remove chat/file IDs, query strings, fragments, credentials and content from URLs, error messages, stack metadata and spans, while keeping the payload structure the SDK requires.

**Acceptance criteria**
- [ ] URLs reduced to normalized route IDs or stripped of IDs, query and fragment.
- [ ] Error messages and stack metadata scrubbed of canary values.
- [ ] Policy applies to logs, errors, events, measurements and spans.

**Testing**
- Unit tests with canary values in each signal type.
- Playwright test capturing outgoing `/faro/collect` payloads and asserting no canaries.

**Definition of done**
- Common DoD.

---

### OBS-75: Alloy `faro.receiver` ingestion and same-origin route

**Type:** Story | **Depends on:** OBS-51, OBS-70 | **Ref:** §9 Faro ingestion through Alloy, §10 Ingestion and security

**Description**
Add Alloy to the observability overlay with `faro.receiver`. Route logs through `otelcol.receiver.loki` to OTLP and traces directly to OTel consumers, then to the collector's frontend ingress class. Set rate/payload limits, bounded decompression and schema validation. Disable unrestricted remote source-map downloads; resolve source maps from approved build artifacts. Route `/faro/collect` to Alloy in `Caddyfile.localhost` and `kubernetes/manifest/base/webui-ingress.yaml`. Document that deployments setting `CONTENT_SECURITY_POLICY` must include `connect-src 'self'`.

**Acceptance criteria**
- [ ] Browser only talks to its own origin; Faro data lands in the `frontend` tenant.
- [ ] Field mapping (trace/span IDs, resource fields) verified against captured pinned-version payloads.
- [ ] Oversized, over-compressed or malformed payloads rejected; bursts rate-limited.
- [ ] Forged tenant/scope/service fields cannot route data elsewhere.
- [ ] Source maps resolved from approved artifacts only.
- [ ] CSP note added to install docs.

**Testing**
- Untrusted ingestion tests: oversize, compression bomb, burst, forged `service.name`/tenant headers, unknown events.
- Manual: browser error with stack trace appears in Loki with resolved source map.

**Definition of done**
- Common DoD.

---

### OBS-76: Analytics aggregation jobs/rules

**Type:** Story | **Depends on:** OBS-53, OBS-73, OBS-75 | **Ref:** §10 Aggregation contract

**Description**
Implement and test the Loki recording rules or aggregation jobs that produce approved series in `prometheus-analytics`: daily, trailing-7-day and trailing-30-day distinct users/sessions computed from deduplicated raw data per complete UTC window; non-overlapping event counts; histogram bucket counts for vitals. Apply SSC-approved small-population suppression.

**Acceptance criteria**
- [ ] Distinct counts computed per window, never by summing daily values.
- [ ] Only allow-listed low-cardinality labels exported.
- [ ] Duplicate events, measurement updates, missing data and sampling do not inflate counts.
- [ ] Small-population suppression applied where required.

**Testing**
- Fixture test with the same user on several days and a session spanning midnight; check each window.
- Histogram reaggregation test against raw samples.
- Test that no identifiers reach the aggregate store.

**Definition of done**
- Common DoD.

---

### OBS-77: Frontend health and usage analytics dashboards

**Type:** Story | **Depends on:** OBS-54, OBS-76 | **Ref:** §9 Grafana dashboards (5–6), §10

**Description**
Provision the *Frontend health* dashboard (Operations: errors by route/version/browser, web vitals p75 by route, slow fetches, browser→backend trace links) and the *Usage analytics* dashboard (Analytics: active users/sessions per window, page views, feature adoption). Add a cross-check view comparing browser `message_sent` trends with server-side `message_metrics` counts.

**Acceptance criteria**
- [ ] Dashboards provisioned in the correct orgs.
- [ ] Usage analytics uses only `prometheus-analytics`.
- [ ] Cross-check panel and its known population differences documented.

**Testing**
- Manual: generate browser activity and confirm panels; log in as an Analytics Viewer and confirm no raw data access.

**Definition of done**
- Common DoD.
- Screenshots attached to the PR.

---

### OBS-78: Frontend alert rules

**Type:** Story | **Depends on:** OBS-56, OBS-77 | **Ref:** §9 Alerts

**Description**
Add alerts for frontend errors by release, web-vitals regression and Alloy rejected-data/health.

**Acceptance criteria**
- [ ] Rules provisioned as code with thresholds and owners.

**Testing**
- Trigger each alert in the local stack and confirm it fires and resolves.

**Definition of done**
- Common DoD.

---

## E7: Remaining logging clean-up & acceptance (PR 7)

**Epic description**

**Goal:** Finish the logging clean-up and prove the whole suite works before turning on production collection.

**Why:** About 131 backend `print()` calls skip log levels and filtering. MCP subprocesses need their own logging setup and filtered stderr. The plan's verification matrix has to pass as a whole, not just as individual tickets.

**Scope:**
- Convert the remaining safe `print()` calls.
- Logging bootstrap and stderr filtering for standalone and subprocess processes.
- Run the full acceptance matrix, including audit durability, authorization, untrusted ingestion and regression.
- Fix the frontend test script so it fails when no tests are selected.

**Out of scope:** new features.

**Done when:** no unintended `print()` calls remain, and canary tests pass for subprocesses. A signed-off test report covers every item in the Verification section, and production collection is approved.

### OBS-80: Convert remaining safe `print()` calls to logging

**Type:** Task | **Depends on:** OBS-15 | **Ref:** §7, Context (~131 `print()` calls)

**Description**
Convert the remaining backend `print()` calls (config, routers, MCP, etc.; tests excluded) to `log.*` at the right level, after checking each one for sensitive content. Keep the startup banner text-only.

**Acceptance criteria**
- [ ] No `print()` left in backend runtime code except the startup banner and standalone script output that is intentionally user-facing.
- [ ] Each converted call reviewed for sensitive values.

**Testing**
- Code search shows no remaining unintended `print()` calls.
- Canary harness (OBS-17) passes.

**Definition of done**
- Common DoD.

---

### OBS-81: MCP subprocess logging bootstrap and stderr filtering

**Type:** Task | **Depends on:** OBS-15, OBS-29 | **Ref:** §1 logging_config.py, §4 MCP, §7

**Description**
Inventory all separate-process entrypoints (built-in MCP servers, `backend/scripts/*`) and give each a minimal logging bootstrap using the shared JSON formatter and filters. Confirm subprocess stderr is filtered before the parent forwards it.

**Acceptance criteria**
- [ ] Each standalone entrypoint logs JSON with the same filters when run on its own.
- [ ] Canary values written to subprocess stderr do not appear in parent logs.

**Testing**
- Run each MCP server and script standalone; check output format.
- Canary harness test on subprocess stderr.

**Definition of done**
- Common DoD.

---

### OBS-82: Full acceptance matrix and end-to-end verification

**Type:** Test | **Depends on:** E1–E6 tickets | **Ref:** Verification

**Description**
Run the full acceptance matrix from the Verification section before enabling production collection: backend, generation matrix, source confidentiality, Faro lifecycle, untrusted ingestion, analytics correctness, authorization, audit durability (interrupt app, worker, collector, SIEM and archive independently), retention TTLs, end-to-end Compose scenario and regression. Fix the frontend test script so an empty test selection fails.

**Acceptance criteria**
- [ ] Every Verification bullet has at least one automated or documented manual test with a recorded result.
- [ ] Audit durability tests show no silent loss and no duplicate logical events.
- [ ] Existing pytest suite, `npm run test:frontend -- --run` and relevant Playwright projects pass.
- [ ] `npm run test:frontend` fails when no tests are selected.
- [ ] Collector/Alloy/Loki/Tempo configs validated with pinned binaries.

**Testing**
- This ticket is the test run; results recorded in a test report attached to the ticket.

**Definition of done**
- Common DoD.
- Test report reviewed and production collection approved.

---

## E8: Optional content audit (PR 8)

**Epic description**

**Goal:** Give authorized reviewers access to chat content for audit purposes. By default this is an audited export of existing chats; a restricted capture repository is added only if full capture is required.

**Why:** Some investigations may need prompt and response content. Content must never enter operational logs, traces or the ordinary SIEM stream. It must follow the 30-days-after-last-activity chat lifecycle and respect holds, not a blanket log TTL.

**Scope:**
- An audited export of chats by authorized roles (baseline).
- If OBS-05 confirms full capture is required, a restricted `content_audit` repository with per-chat expiry, access control, durable write receipts and truncation markers, off by default.

**Out of scope:** storing content in Loki as the authoritative record, and enabling capture before Security/IM sign-off.

**Done when:** the audited export works with access control and an audit event for each export. If the repository is built, canary tests show content only in that repository, and lifecycle tests with controlled clocks pass.

### OBS-90: Audited chat export baseline

**Type:** Story | **Depends on:** OBS-41 | **Ref:** §8 Baseline

**Description**
Provide an authorized, audited export of existing chat records as the baseline alternative to full content capture. Each export emits an audit event (actor, scope, record count), with no content in the event.

**Acceptance criteria**
- [ ] Export restricted to authorized roles.
- [ ] Each export emits a metadata-only audit event.
- [ ] Documentation states that stored conversations may differ from the enriched payload sent to providers.

**Testing**
- Router tests for authorized/unauthorized access and the emitted audit event.

**Definition of done**
- Common DoD.

---

### OBS-91: Restricted content audit repository (only if required)

**Type:** Story | **Depends on:** OBS-05 (content audit confirmed as required), OBS-61 | **Ref:** §8, Rollout 8

**Description**
Only if OBS-05 confirms full capture is required: implement `observability/content_audit.py` with `record_prompt`/`record_response` writing to a restricted repository with per-chat lifecycle metadata (30 days after last chat activity, subject to holds), explicit access control and durable write receipts. Capture actual provider requests and final/partial responses on the HTTP, background-stream and CrewAI paths; mark truncation (`CONTENT_AUDIT_MAX_BYTES`) and failure/cancellation. Off by default (`ENABLE_CONTENT_AUDIT=false`).

**Acceptance criteria**
- [ ] Content never reaches app logs, stdout, general outboxes, span attributes or the ordinary SIEM stream.
- [ ] `open_webui.audit.content` logger (if used) has no operational handlers and does not propagate.
- [ ] Expiry calculated from last chat activity, with hold checks before deletion.
- [ ] Access restricted and every access audited.
- [ ] Disabled by default; enabling without the repository configured fails at startup.

**Testing**
- Canary harness: repository receives the record, all operational sinks do not.
- Lifecycle tests with controlled clocks (chat updated on day 20 extends expiry).
- Access control tests.

**Definition of done**
- Common DoD.
- Security/IM sign-off before enabling in any environment.
