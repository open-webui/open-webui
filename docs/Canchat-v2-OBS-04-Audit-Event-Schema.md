# OBS-04: Audit event schema v1, cardinality limits and audit fail policy

Status: **Proposed**, waiting for SSC Security and tech lead sign-off (§10) | Depends on: OBS-01 (option a, as assumed in [OBS-02](Canchat-v2-OBS-02-Unit-of-Work.md)) | Unblocks: OBS-41, OBS-42, OBS-43, OBS-44, OBS-45, OBS-46 | Ref: [Logging Architecture v2 §5](Canchat-v2-Logging%20Architecture-v2.md#5-audit-events-emit_audit_event-metadata-only), Gates 2 and 4

Artifacts:

- **Pydantic model spec and samples:** [test_audit_event_schema_poc.py](../backend/open_webui/test/util/test_audit_event_schema_poc.py). It validates one sample event for each of the 45 actions (all 7 categories), plus forbidden-field, free-text, envelope, size, fail-policy and pseudonym tests. 324 tests pass. OBS-41 moves the models into `observability/audit.py` unchanged.
- **JSON Schema (draft 2020-12):** [obs04-audit-event-v1.schema.json](obs04-audit-event-v1.schema.json), generated from the Pydantic spec. A test fails if the file is out of date. To regenerate it: `OBS04_WRITE_SCHEMA=1 pytest backend/open_webui/test/util/test_audit_event_schema_poc.py`.

## 1. Design rules

1. **No field accepts free text.** Every string is either an enum, a UUID, or matches a narrow pattern that excludes whitespace and `@`. Emails, names, sentences and secrets therefore fail validation even if a caller puts them in an allowed field.
2. **Every object is closed** (`additionalProperties: false`). Unknown keys are rejected, not dropped.
3. **Validation happens at the producer.** `emit_audit_event` validates before it touches the session ([OBS-02 §3.4](Canchat-v2-OBS-02-Unit-of-Work.md#34-rules-enforced-in-review-add-a-short-checklist-to-the-obs-40-pr)). A schema error is a bug, and the fail policy (§5) decides what happens next.
4. **The actor comes from the resolved server-side auth context** (session, API key, OAuth or LDAP result), never from the request body, headers or socket payload. CrewAI events need the per-invocation token fix from PR 1 first.
5. **Audit events are never sampled.** Trace sampling does not apply to them.

## 2. Envelope v1

| Field | Type | Required | Notes |
|---|---|---|---|
| `event_id` | UUID v4 | yes | Created once by `emit_audit_event`. It is the idempotency key for every destination |
| `schema_version` | `"1.0"` | yes | See *Versioning* below |
| `time` | RFC 3339, UTC, ms precision | yes | When the action took effect (commit time for state changes). Offsets other than `Z`/`+00:00` and naive times are rejected |
| `category` | enum | yes | `auth`, `admin`, `access`, `resource`, `mcp`, `export`, `chat` |
| `action` | enum | yes | §3. The discriminator: it decides which `target` and `details` are allowed |
| `outcome` | enum | yes | `success`, `failure`, `denied`, `error`, `cancelled`. Each action allows only some of these (§3) |
| `actor.type` | enum | yes | `user` or `anonymous` |
| `actor.id` | UUID | for `user` | Internal user ID. Not allowed for `anonymous` |
| `actor.role` | enum | no | `admin`, `user`, `pending` at the time of the action |
| `actor.auth_method` | enum | login/signup only | `password`, `ldap`, `oauth`, `trusted_header`, `api_key`, `session`, `refresh_token` |
| `actor.subject_pseudonym` | `ps1:<kid>:<22 chars>` | `login.failure` only | Keyed pseudonym of the submitted login identifier (§6) |
| `target` | object | depends on action | `{type, id}`. `type` is fixed per action. `id` is a UUID, a model ID (`^[A-Za-z0-9._:/-]{1,128}$`) or a built-in MCP server name. `config`/`permissions` targets have no `id` |
| `details` | object | depends on action | A closed, action-specific model (§3) |
| `correlation` | object | no | `request_id`, `operation_id` (`^[A-Za-z0-9._-]{8,64}$`, same rule as `X-Request-Id` validation), `trace_id` (32 hex), `span_id` (16 hex), `session_id` (refresh-session UUID) |
| `client.address` | IPv4/IPv6 | no | Allowed only for `auth` and `access` events (security-log source address). Never sent to metrics or analytics. See open question 1 |
| `source` | object | yes | `service` (label), `version`, `environment` |

**Other rules** (enforced by model validators; JSON Schema can't express them):

- `outcome` must be one of the outcomes allowed for the action.
- `actor.type` must be allowed for the action (`anonymous` only for `login.failure` and `token.refresh.failure`).
- `subject_pseudonym` is required for `login.failure` and not allowed anywhere else. `auth_method` is required for `login.success`, `login.failure` and `signup`, and not allowed anywhere else.
- `client` is only allowed in `auth`/`access` events.
- The serialized event must be ≤ **16 KiB**. Field bounds (≤ 100 IDs per list, ≤ 200 keys per list) keep the largest valid events below about 14 KiB, so the byte check is only a backstop.
- Token counts are `null` when the provider didn't report usage. `0` means a measured zero.

**Versioning.** `MAJOR.MINOR`. A minor version may add optional fields, actions or enum values. Consumers must ignore unknown fields and actions of the same major version. A major version is needed to remove or rename anything, or to make an optional field required. Every version change goes through the same Security review as this document. The outbox stores `schema_version` per row, and the worker delivers each row unchanged.

## 3. Action catalogue

Fail modes: **C** = closed under every policy, **O** = open under `block_privileged` and closed under `block_all`, **N** = never block (§5).

| Category | Action | Target | Details (all closed) | Outcomes | Fail | Emitted from |
|---|---|---|---|---|---|---|
| auth | `login.success` | user | none | success | O | `issue_tokens_for_user` (signin, ldap, oauth, signup, trusted header) |
| auth | `login.failure` | user, only if the identifier resolves to an account | `reason`: `invalid_credentials`, `invalid_trusted_header`, `ldap_error`, `rate_limited`, `internal_error` | failure | N | `/signin`, `/ldap`, oauth callback |
| auth | `logout` | none | none | success | N | `/signout` |
| auth | `token.refresh.failure` | none | `reason`: `missing_refresh_token`, `invalid_refresh_token`, `session_conflict` | failure | N | `/refresh` |
| auth | `signup` | user | `role` | success | C | `/signup`, ldap/oauth auto-create |
| auth | `password.change` | user | `initiated_by`: `self`, `admin` | success | C | `/update/password`, admin edit |
| auth | `api_key.create`, `api_key.delete` | user (owner) | none | success | C | `/api_key` |
| admin | `user.create` | user | `role` | success | C | `/auths/add` |
| admin | `user.update` | user | `changed_fields` ⊆ {`name`, `email`, `profile_image_url`, `password`}: names only, never values | success | C | `users/{id}/update` |
| admin | `user.role_change` | user | `from_role`, `to_role`, `source`: `manual`, `oauth_sync` | success | C | `/users/update/role`, oauth role sync |
| admin | `user.delete` | user | none | success | C | `DELETE /users/{id}` |
| admin | `user.oauth_link` | user | `oauth_provider` (label) | success | C | `utils/oauth.py` |
| admin | `group.create`, `group.update` | group | `source`, `member_count`, `member_ids_added`/`removed` (≤ 100 each), `ids_truncated`, `permissions_changed` | success | C | `routers/groups.py`, oauth group sync |
| admin | `group.delete` | group | `member_count` | success | C | `routers/groups.py` |
| admin | `permissions.default_update` | permissions | `changed_keys` (≤ 200, `^[a-z][a-z0-9_.]{0,63}$`) | success | C | `/users/default/permissions` |
| admin | `config.update`, `config.import` | config | `section` (router label), `keys` (≤ 200 `UPPER_SNAKE` names, never values) | success | C | configs, auths, retrieval, images, audio, tasks, openai, ollama, users, evaluations routers |
| admin | `domain.create`, `domain.update`, `domain.delete` | domain | none | success | C | `routers/domains.py` |
| access | `model.denied` | model | `reason`: `no_access`, `model_not_found` | denied | N | `check_model_access` |
| resource | `file.upload` | file | `mime_group` (8 values), `size_bucket` (4 values), optional `knowledge_id` | success | C | `POST /files/` |
| resource | `file.update`, `file.delete` | file | none | success | C | `/files/{id}/data/content/update`, `DELETE /files/{id}` |
| resource | `file.delete_all`, `knowledge.delete_all` | none | `scope`: `own`, `all_users`; `count` | success | C | `DELETE /files/all`, retrieval reset |
| resource | `knowledge.create`, `knowledge.update`, `knowledge.delete` | knowledge | none | success | C | `routers/knowledge.py` |
| resource | `knowledge.file_add`, `knowledge.file_remove` | knowledge | `file_ids` (1–100), `file_count`, `ids_truncated` | success | C | single and batch add, remove |
| resource | `knowledge.reset` | knowledge | `file_count` | success | C | `/knowledge/{id}/reset` |
| mcp | `mcp_server.create`, `mcp_server.update` | mcp_server | `server_type`, `transport`, `changed_fields` (field names only; never `env`/`args`/`command`/`url` values) | success | C | `mcp_backend/routers/mcp.py` |
| mcp | `mcp_server.delete`, `.start`, `.stop`, `.restart` | mcp_server | `server_type` | success | C | external CRUD/start/stop/restart, built-in restart |
| mcp | `mcp.config_update` | config | `section`, `keys` | success | C | `/mcp/config/update`, `/mcp/urls/update` |
| export | `metrics.export` | export (the `export_logs` row ID) | `row_count`, `file_size_bytes`, `date_range_start`, `date_range_end` | success | C | `routers/metrics.py` export, same transaction as `ExportLogs.insert_new_export_log` |
| chat | `message` | message | `chat_id`, `model`, `provider`, `path` (`http_background`, `http_stream`, `http_json`, `crewai`), token counts (nullable), `has_files`, `web_search`, `has_knowledge`, `has_tools`, `mcp_tool` | success, error, cancelled | O | `MessageMetrics.insert_new_metrics` (OBS-45) |
| chat | `chat.share`, `chat.unshare` | chat | optional `share_id` | success | C | `/chats/{id}/share` |

Notes:

- **Answers to OBS-02 open question 2:** `domain.*`, `chat.share`/`chat.unshare` and `api_key.*` are included.
- **State-change events are written only when the change commits**, so their only outcome is `success`. Rejected privileged attempts (for example a non-admin calling an admin route) aren't in v1. See open question 3.
- **Supersedes OBS-02 examples:** config keys go in `details.keys` (not `target.keys`), and role changes use `details.from_role`/`to_role`.
- **`user_domain`/`email_domain` are not copied into events.** The domain is a quasi-identifier, and it can be derived from `actor.id` when it's needed. `message_metrics` and `export_logs` keep their existing columns.
- **Deferred:** chat deletion and retention cleanup (records-management design, OBS-61), workspace model/prompt/tool CRUD, MCP tool-call events, and audit access/hold events (records-management design).

## 4. Forbidden fields

These must never appear in an audit event, outbox row, search copy or audit metric label, under any key:

| Class | Examples |
|---|---|
| Credentials and secrets | passwords and hashes, access/refresh/ID tokens, API keys, OAuth client secrets, LDAP bind passwords, `Authorization`/`Cookie` headers, config values, MCP `env`/`args`/`command`/`url` values |
| Direct identifiers | email, user name, first/last/display name, username, LDAP DN, raw login identifier (failed logins use the pseudonym only), email domain |
| Content | prompt, response, message text, chat title, search query, file name, knowledge-base name/description, document text, tool input/output |
| High-entropy client data | user agent, full URL/path with query string, exception message or stack trace |

Enforcement is layered:

1. The schema declares none of these keys (a test walks the generated schema and checks this), and closed objects reject them.
2. The pattern rules in §1 reject such values even when they're placed in an allowed field. Tests cover emails, names, sentences, `KEY=value` strings and markup.
3. Error handling in `emit_audit_event` logs only the action, the validation error type and the field path. It never logs the rejected value.
4. OBS-44 reviewers check that callers pass IDs and enums, not objects that get stringified.

## 5. Failure policy (`AUDIT_FAIL_POLICY`)

This policy covers failure to **build, validate, encrypt or insert** the event locally. A SIEM or Loki outage is *not* an audit failure: the event is already durable in the outbox (§8).

| Mode | `block_privileged` (default) | `block_all` | Actions |
|---|---|---|---|
| **C**: closed | Change rolled back, HTTP 503, nothing applied | same | Every state change: `signup`, `password.change`, `api_key.*`, all `admin`, `resource`, `mcp`, `export`, `chat.share`/`unshare` |
| **O**: open with alert | Request succeeds, failure metric + alert | Closed (see below) | `login.success`, `message` |
| **N**: never block | Normal response (the refusal or logout), failure metric + alert | same | `login.failure`, `token.refresh.failure`, `model.denied`, `logout` |

- **Why N exists:** these requests are already refused, or they end a session. Blocking them adds no protection. Blocking logout would also stop users from revoking sessions while auditing is down.
- **Fail open, as OBS-02 §3.5 describes:** catch errors from build/validate/encrypt only, and skip the insert. An insert failure means the database is failing, so the state change fails too.
- **`block_all` for `message`:** the event is written when the response is finalized, after the user has already seen it, so it can't fail closed afterwards. Instead, a circuit breaker opens for 60 s after any audit emit failure (or when the outbox health check fails). While it's open, new chat requests get a 503 **before** the provider is called. A response already in progress completes and is counted as a failure.
- **`block_all` for `login.success`:** the refresh-session row and the event share one unit of work, so login returns 503.
- **Alerting:** `audit_emit_failures_total{category,action,stage}`, where `stage` is one of `build`, `validate`, `encrypt`, `persist`. Any increase over 5 minutes pages ops and notifies Security. The application logs one ERROR line with action, stage and error type only.
- **Startup:** with `AUDIT_ENABLED=true` in production, a missing pseudonym or outbox key stops startup instead of failing every event at runtime.

## 6. Failed-login pseudonymization

**Scheme (`ps1`)**

```
normalized = casefold(strip(NFKC(identifier)))
pseudonym  = "ps1:" + key_id + ":" + base64url(HMAC-SHA256(key, utf8(normalized))[:16])   # 128 bits, no padding
```

- One identifier always gives the same pseudonym under the same key, across attempts, replicas and restarts. This is what correlation needs. The architecture doc explicitly rejects a fresh random salt per attempt.
- The identifier is the value the user typed: email for password and OAuth, username for LDAP. The pseudonym is computed before any lookup, so failures for unknown accounts can be correlated too.
- If the identifier resolves to an account, `target` also holds that user's ID. This shows attacks against real accounts. See open question 2.
- 128 bits makes accidental collisions negligible. It's not reversible without the key. **With the key, it can be brute-forced against candidate identifiers**, so the key is as sensitive as the identifiers it protects.

**Key management**

| Item | Decision |
|---|---|
| Material | ≥ 256-bit random key from a CSPRNG. Generated and stored in the SSC-approved secret store, never in the repo, image or database. `pseudonymize` rejects keys shorter than 32 bytes |
| Delivery | Mounted file `AUDIT_PSEUDONYM_KEY_FILE` (Kubernetes Secret from the secret store), plus `AUDIT_PSEUDONYM_KEY_ID` (`^[a-z0-9-]{1,32}$`, for example `k2026a`). The key ID is stored in every pseudonym |
| Access | Only the backend workload identity reads the active key. Retired keys are readable only by the investigation role, not the app |
| Rotation | Every 12 months, and right away when compromise is suspected or a holder leaves. Rotation means a new key ID plus a rolling restart. Pseudonyms under different keys don't match by design, so investigations that span a rotation compute both |
| Retired keys | Kept in the secret store for verification only, for as long as any event that names that key ID is retained (SIEM schedule, currently ≥ 2 years). After that they are destroyed, and that destruction is recorded. Destroying the key makes old pseudonyms permanently unlinkable |
| Lookups | An investigator with an identifier computes its pseudonym under the relevant key IDs through a restricted tool, then searches for it. No reverse mapping table exists. The investigation workflow records tool use (records-management design) |
| Compromise | Rotate right away. Treat events under the compromised key ID as linkable to identifiers for anyone holding the key, and notify Security/ATIP under the privacy breach process |

## 7. Metric label cardinality

**Allowed labels**

| Label | Used on | Allowed values | Bounding |
|---|---|---|---|
| `model` | `llm_*`, chat operation metrics | IDs in the server's resolved model list (`app.state.MODELS`) when recorded, lower-cased | Values not in the list become `other`. A per-process cap of 100 distinct values (first seen); after that `other`, plus a `metrics_label_overflow_total{metric,label}` increment |
| `provider` | `llm_*` | `openai`, `ollama`, `arena`, `function`, `crewai`, `other` | Enum (from `owned_by` and the code path) |
| `tool` | `mcp_*`, chat tool metrics | Registered built-in MCP server names; `external` for all user-created servers; `none` | Enum built at startup. User-chosen server names are never used as labels |
| `event` | `socket_*` | `connect`, `disconnect`, `usage`, `crew-mcp-query`, `user-join`, `join-channels`, `channel-events`, `user-list`, `other` | Enum from the registered handlers |
| `outcome` | all domain metrics | `success`, `error`, `cancelled`, `timeout`, `denied`, `rejected` | Enum |
| `type` | `llm_tokens_total` | `prompt`, `completion` | Enum |
| `category`, `action` | `audit_*` | Schema enums (§3) | Enum; 45 actions |
| `stage` | `audit_emit_failures_total` | `build`, `validate`, `encrypt`, `persist` | Enum |
| `destination` | `audit_delivery_*` | `siem`, `loki` | Enum |
| `http.*` | `http.server.request.duration` | Stable semconv from `FastAPIInstrumentor`. `http.route` is the route template | Instrumentor; unmatched routes have no route value |
| existing `web_search_*` | web search | Unchanged in v1. OBS-47 checks them against this table | |

**Never used as metric labels:** user ID, email or domain, role combined with user, session, socket, request, operation, trace, chat, message, file, knowledge, group or MCP server IDs, raw URLs/paths, query strings, exception messages, model names not in the server list, and any free text.

**Budgets and guards**

- At most **1,000 active series per metric per instance**, and **10,000 per instance** in total. `MetricsService.record()` applies the bounding above, so the label set is checked before the SDK sees it. OBS-22 adds a unit test per instrument.
- The SDK view cardinality limit is set where the pinned SDK supports it (to verify in OBS-22). Prometheus scrape configs set `sample_limit: 20000`, `label_limit: 30` and `label_value_length_limit: 128`, so a regression drops the scrape and raises an alert instead of growing without limit.
- **Loki index labels** are limited to `service_name`, `deployment_environment` and `level`. The `audit` tenant also gets `category` (7 values). Everything else, including `action`, `actor.id` and `event_id`, goes into structured metadata or the body.
- Adding a label value outside an enum means changing the enum, this table and the test in the same PR.

## 8. SIEM/archive delivery

**Outbox row (OBS-41/42):** `event_id`, `schema_version`, `category`, `action`, `time`, `key_id`, ciphertext, `payload_sha256`. For each destination (`siem`, `loki`) it also stores `status`, `attempts`, `next_attempt_at`, `lease_until`, `last_error_class`, and the receipt fields.

**Encryption at rest:** the payload is encrypted with AES-256-GCM. The AAD is `event_id|schema_version`, and the key comes from `AUDIT_OUTBOX_KEY_FILE` plus `AUDIT_OUTBOX_KEY_ID`, stored per row. Rotation is annual: new rows use the new key, and old keys stay until no row references them. Delivery uses TLS 1.2+ with service authentication.

**Receipt definitions**

| Destination | Counts as delivered when | Stored receipt |
|---|---|---|
| **SIEM/evidence archive** (authoritative) | The SSC adapter confirms **at the application level that the event is durably committed**. For example: an HTTP 2xx whose body contains the `event_id` and the SIEM's record/ingest ID, or an indexer acknowledgement. **Not enough:** a TCP/TLS syslog send, a load-balancer or collector 2xx before commit, or a fire-and-forget queue | `receipt_id`, SIEM receive time, our ack time, `payload_sha256` |
| **Loki search copy** (non-authoritative) | Collector OTLP 2xx (`forwarded`) | ack time |

**Retries:** exponential backoff with full jitter, 1 s base, 5 min cap, no attempt limit for transient errors (network errors, timeouts, 408, 429, 5xx). Any other 4xx or a schema rejection moves the destination to `dead_letter` right away. Delivery is at-least-once: the destination deduplicates on `event_id`, and consumers order by `time`.

**Concurrency, shutdown and crashes:** on Postgres, workers lease batches with `FOR UPDATE SKIP LOCKED`, `lease_until` = now + 60 s. SQLite (single replica, dev) runs one worker. On shutdown, the worker stops claiming, finishes in-flight sends for up to 10 s, and clears its leases. After a crash, expired leases are reclaimed. The resend is deduplicated by `event_id`.

**Outage behaviour:** requests keep succeeding and keep writing to the outbox. A destination outage never triggers the fail policy. Alerts:

| Condition | Severity |
|---|---|
| Oldest undelivered SIEM event > 15 min | warning |
| Oldest undelivered SIEM event > 1 h, or outbox > 80 % of reserved capacity | critical |
| Any `dead_letter` row | critical |
| Oldest Loki copy > 15 min | warning |
| `AUDIT_DELIVERY_ENABLED=false` with pending rows | warning (backlog alert stays on) |

Reserved outbox capacity covers **7 days of SIEM outage at peak event rate** (≈ 1 KiB per row encrypted). OBS-06 supplies the rate.

**Undelivered-event retention:**

- A row without a SIEM receipt, including `dead_letter`, is **never purged automatically**. Removing it takes an authorized, recorded procedure, and only after the event has been delivered another way with a receipt.
- After a SIEM receipt, the row is kept for `AUDIT_OUTBOX_RETENTION_DAYS` (default **7**) for replay and reconciliation, then deleted. If the Loki copy is still undelivered by then, it is marked `abandoned` and counted. It never holds back purging.
- A daily job compares outbox counts by hour and category against the Loki audit tenant. A mismatch above 0.1 % raises a warning.

## 9. Configuration added to §12

| Variable | Default | Purpose |
|---|---|---|
| `AUDIT_PSEUDONYM_KEY_FILE` | unset | Path to the active pseudonym key (≥ 32 bytes). Required in production when `AUDIT_ENABLED=true` |
| `AUDIT_OUTBOX_KEY_FILE`, `AUDIT_OUTBOX_KEY_ID` | unset | Outbox payload encryption key and its ID |
| `AUDIT_OUTBOX_RETENTION_DAYS` | `7` | How long a row is kept after its SIEM receipt |

`AUDIT_FAIL_POLICY` and `AUDIT_PSEUDONYM_KEY_ID` already exist in §12.

## 10. Open questions and sign-off

1. **`client.address` in `auth`/`access` events:** TBS event logging guidance expects source addresses for security events. Security, please confirm it's required and is covered by the existing collection notice.
2. **`target.user` on failed logins for existing accounts:** this helps detect targeted attacks. It also records that a given person's account was attempted. Keep it?
3. **Rejected privileged attempts** (403 on admin routes): add an `access.admin_denied` action in v1.1?
4. **SSC SIEM interface:** which adapter and protocol give an application-level durable acknowledgement, and can it deduplicate on `event_id`? If it can't deduplicate, queries must deduplicate on `event_id`.
5. **`block_all` circuit breaker window** (60 s) for chat: is it acceptable to Security and the product owner?

| Role | Name | Decision | Date |
|---|---|---|---|
| SSC Security | | | |
| Tech lead | | | |
