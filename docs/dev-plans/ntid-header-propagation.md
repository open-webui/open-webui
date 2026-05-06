# NTID `user` Header Propagation — Dev Plan

| Field | Value |
|---|---|
| **Status** | Draft — pending sign-off on **Plan A vs Plan B** (see §12) |
| **Owner** | TBD |
| **IT Deadline** | 2026-05-02 (already past — P0) |
| **Source of Truth** | [Confluence: User Header Modification](https://amd.atlassian.net/wiki/spaces/SI/pages/1655519770/User+Header+Modification) |
| **Repos Affected** | Plan A: `open-webui` + `pipeline`. Plan B: `pipeline` only |
| **Created** | 2026-05-06 |

> **Two viable approaches.** §1–§10 describe **Plan A** (capture NTID at OIDC login, store on `user.ntid` — a new dedicated column — propagate via body). **Plan B** (§12) does the email→NTID lookup inside the pipeline at request time — single-repo change, no IT dependency, no backfill, but adds a runtime DB hop. Pick before implementation starts.

> **Storage decision (Plan A):** NTID lives in a **new dedicated `ntid` column** on the `user` table — not in the `info` JSONField. Rationale: this is a fork of Open WebUI (the team already maintains schema divergence — see `Datar-Tech/open-webui` history); NTID is a first-class business identifier (compliance, billing attribution, IT audit); a real column gives type safety, B-tree indexability for reverse lookups, UNIQUE constraint, and clean ORM access (`user.ntid` instead of `(user.info or {}).get("ntid")`).

---

## 1. Background

AMD IT mandates that **every** outbound request to `https://llm-api.amd.com/*` made with a **shared application API key** must carry a `user: <NTID>` HTTP header. The header value is the human user's AMD network login ID (e.g. `jdoe1`); for CI/automation it is the service account's NTID.

Our Open WebUI deployment authenticates users via Microsoft OIDC (Entra ID) and proxies chat completions through an external pipeline (`llamaindex_pipeline_v6.1_SPA_Chief_Planner_modularized.py`) that finally calls `https://llm-api.amd.com/*`. The NTID currently does **not** flow end-to-end. This plan closes that gap.

**Out of scope** (per IT, SLAI/IT-managed tools are exempt):
- NABU / TIP calls — uses `intelligence.amd.com/nabu/prod`, not the LLM Gateway
- Personal API key users (Claude Code, Codex CLI) — handled separately

---

## 2. End-to-End Flow (Target State)

```
┌──────────────┐    OIDC    ┌──────────────┐    HTTP    ┌────────────────┐    HTTPS    ┌──────────────┐
│  Microsoft   │ ─────────► │  Open WebUI  │ ─────────► │   Pipeline     │ ──────────► │  LLM Gateway │
│  Entra ID    │   claims   │   backend    │  body.user │   server       │  user:NTID  │  llm-api.amd │
└──────────────┘            └──────────────┘            └────────────────┘             └──────────────┘
                                  │                            │
                              user.ntid                   ntid_context (ContextVar)
                          (dedicated column)              (per-request propagation)
```

**Three handoffs**, each requires code change:
1. **Entra ID → Open WebUI**: capture NTID claim during OIDC callback; persist to `user.ntid` (new dedicated column)
2. **Open WebUI → Pipeline**: inject `payload["user"]["ntid"]` when calling the pipeline (registered as OpenAI-compatible URL)
3. **Pipeline → LLM Gateway**: read `body["user"]["ntid"]` in `pipe()`, propagate via `ContextVar` to `CustomHTTPLLM._get_headers()`, emit `user: <NTID>` header

---

## 3. Architectural Decision: Why ContextVar (not instance attr)

`CustomHTTPLLM` is instantiated **once** in `Pipeline.__init__()` (entrypoint line 170) and registered as the global `Settings.llm`. All agents (`orchestrator`, `react`, `powerbi`, etc.) share this singleton.

NTID is **per-request** data. Three options were considered:

| Approach | Verdict | Why |
|---|---|---|
| Instance attribute (`self.ntid = ntid`) | ❌ Reject | Cross-user leak under concurrent requests |
| Thread through every call's `kwargs` | ❌ Reject | Touches ~10 call sites, breaks LlamaIndex's `LLM` interface |
| **`ContextVar`** | ✅ **Adopt** | Per-request isolation, codebase already uses this pattern (`user_id_context` in `orchestrator_agent_workflow.py:782`), single choke point at `_get_headers()` |

---

## 4. Change Inventory

### 4.1 `open-webui` repo (this repo) — 1 manual DDL + 3 code files

#### Step 0 (Deployment DDL — run once on prod SQL Server, BEFORE deploying code)

> No migration file is created. This deployment runs against a single SQL Server instance with no fresh-install requirement, so the column is added directly via DDL.

```sql
-- Run as DB admin on [openwebui]
ALTER TABLE [openwebui].[dbo].[user]
    ADD [ntid] NVARCHAR(64) NULL;

-- Optional but recommended for fast reverse lookup (NTID → user)
CREATE INDEX [IX_user_ntid] ON [openwebui].[dbo].[user]([ntid])
    WHERE [ntid] IS NOT NULL;
```

**Caveats**:
- DDL must run **before** the new code deploys, otherwise the SQLAlchemy model declaration will fail on first read with `column user.ntid does not exist`
- No UNIQUE constraint — defer until backfill confirms there are no duplicate NTIDs in AD (rare but possible: contractor rejoin, account merge)
- A future re-deploy from scratch (e.g., new env, DR rebuild) requires re-running this DDL — keep it in your runbook / infra-as-code repo

#### File A: `backend/open_webui/models/users.py`

| Location | Current | Change |
|---|---|---|
| Line 36 (after `oauth_sub = Column(Text, unique=True)` in `User`) | No `ntid` column declared | Add `ntid = Column(String(64), nullable=True, index=True)` |
| Line 60 (after `oauth_sub: Optional[str] = None` in `UserModel`) | No `ntid` field | Add `ntid: Optional[str] = None` |
| Lines 98–128 (`insert_new_user`) | Doesn't accept/persist `ntid` | Add optional `ntid: Optional[str] = None` parameter; include `"ntid": ntid` in the dict that builds `UserModel` |

#### File B: `backend/open_webui/utils/oauth.py`

| Location | Current | Change |
|---|---|---|
| ~line 380, before `Auths.insert_new_auth(...)` and the analogous update branch | NTID claim is dropped | Read claim via new env var `OAUTH_NTID_CLAIM` (default `onpremisessamaccountname`); after user creation/update, persist via `Users.update_user_by_id(user.id, {"ntid": ntid})` |

**Notes:**
- Add `OAUTH_NTID_CLAIM` to `backend/open_webui/config.py` and `env.py`, mirroring the `OAUTH_USERNAME_CLAIM` / `OAUTH_EMAIL_CLAIM` env var pattern

#### File C: `backend/open_webui/routers/openai.py`

| Location | Current | Change |
|---|---|---|
| Lines 658–665 (the `if "pipeline" in model and model.get("pipeline"):` block) | `payload["user"]` carries `name/id/email/role` only | Add `"ntid": user.ntid or ""` to the dict |

**Why body channel, not the header block at 705–726:**
The header block is gated by `ENABLE_FORWARD_USER_INFO_HEADERS` and applies to **all** OpenAI-compatible URLs (Azure OpenAI, OpenAI direct, etc.). Putting NTID there would leak our internal identifier to non-AMD endpoints. The body channel (line 658) only fires when the model is flagged as `pipeline=True` — exactly the right scope.

---

### 4.2 `pipeline` repo (`C:\Github\pipeline`) — 3 files

#### File C: `llamaindex_pipeline_v6.1_SPA_Chief_Planner_modularized.py`

| Location | Current | Change |
|---|---|---|
| Lines 225–231, `pipe()` | Extracts `user.role` only | Also extract `user_ntid = user.get("ntid", "")`; pass to `_async_pipe_logic` |
| Lines 202–223, `_async_pipe_logic()` | Signature takes `user_role` | Add `user_ntid: str = ""` param; pass through to `run_orchestrator_workflow` |

#### File D: `pipeline_modules/agents/orchestrator_agent_workflow.py`

| Location | Current | Change |
|---|---|---|
| Lines 714–723, `run_orchestrator_workflow` signature | Last kwarg is `user_role: str = ""` | Add `user_ntid: str = ""` |
| ~line 772, after `user_info = body.get("user", {})` | Only reads email/id | Resolve `ntid = user_info.get("ntid", "") or user_ntid` (kwarg as fallback) |
| ~line 782, alongside `user_id_token = user_id_context.set(user_id_to_use)` | Has `user_id_context` pattern | Add `ntid_token = ntid_context.set(ntid)` (import `ntid_context` from `llm_clients`) |
| `finally:` block (search for `user_id_context.reset`) | Resets `user_id_context` | Also `ntid_context.reset(ntid_token)` to prevent leak across requests |

#### File E: `pipeline_modules/llm_clients.py` ⭐ **Core choke point**

| Location | Current | Change |
|---|---|---|
| Top of file (imports) | `ContextVar` may not be imported | Add `from contextvars import ContextVar`; declare module-level `ntid_context: ContextVar[str] = ContextVar("ntid", default="")` (export it) |
| Lines 118–123, `_get_headers()` | Returns `Ocp-Apim-Subscription-Key + Content-Type` | Read `ntid = ntid_context.get(""); if ntid: headers["user"] = ntid` |
| Line 338 and any streaming call sites | All use `headers=self._get_headers()` | **No change** — single choke point covers all outbound HTTP |

> ⚠️ **Header name is the literal lowercase string `user`** — IT specified this verbatim in their cURL example. Do NOT use `X-NTID`, `X-User-NTID`, or any variant.

---

### 4.3 Files explicitly NOT changing

| File | Why skip |
|---|---|
| `pipeline_modules/nabu_client.py` | NABU is SLAI/IT-managed (per IT FAQ); not in NTID enforcement scope |
| `pipeline_modules/azure_search_client.py` | Azure Search is not the LLM Gateway |
| `react_agent_workflow.py`, `powerbi_agent_workflow.py`, etc. | All consume `Settings.llm` → routed through `CustomHTTPLLM._get_headers()`, automatically covered |
| `agent_registry.py` | No outbound HTTP |

---

## 5. Prerequisites (External Owners)

| Action | Owner | Blocking? |
|---|---|---|
| Add `onpremisessamaccountname` to ID token's optional claims in **Azure Entra ID** app registration | IT / Azure admin | ✅ Blocks all 3 handoffs — without this, `user_data` in OIDC callback won't contain NTID |
| Confirm `OAUTH_NTID_CLAIM` value (`onpremisessamaccountname` vs `employeeid` vs custom extension claim) | IT | ✅ Determines env var default |
| Deployment env vars: `OAUTH_NTID_CLAIM=<claim_name>` set in production Open WebUI | DevOps | ✅ Required at runtime |

---

## 6. Backfill Strategy (Existing Users) — **Dual Track**

Existing users' `user.info["ntid"]` is empty until they re-login. We adopt **both** approaches in sequence:

| Order | Track | Purpose |
|---|---|---|
| 1 | **B. One-shot SQL backfill** (run on deployment day) | Cover ~all current users immediately by joining `[user]` to AD; eliminates the empty-header window |
| 2 | **A. Lazy backfill on OIDC callback** (continuous) | Cover new users + correct any AD-stale entries on next re-login; self-healing forever |

### 6.1 Backfill SQL (Track B)

**Backend confirmed**: SQL Server. Target column is the new dedicated `[ntid]` column added in §4.1 Step 0 — plain `UPDATE`, no JSON path required.

**AD source**: `PKG_ENG.[dbo].[ACTIVEDIRECTORY_USERS]` — `mail` column joins to `[user].email`; `NTName` column carries the identifier in `DOMAIN\username` format (e.g. `amd\agriffin`).

#### Step 1 — Sanity check (run first, fix issues before UPDATE)

```sql
-- 6.1.a Match rate
SELECT
    SUM(CASE WHEN ad.[NTName] IS NOT NULL THEN 1 ELSE 0 END) AS matched,
    SUM(CASE WHEN ad.[NTName] IS NULL     THEN 1 ELSE 0 END) AS unmatched,
    COUNT(*) AS total
FROM [openwebui].[dbo].[user] u
LEFT JOIN PKG_ENG.[dbo].[ACTIVEDIRECTORY_USERS] ad
    ON u.[email] COLLATE Latin1_General_100_CI_AS_SC_UTF8 = ad.[mail];

-- 6.1.b Duplicate-email check (must be empty before UPDATE; otherwise pick a tiebreaker)
SELECT u.[email], COUNT(*) AS ad_match_count
FROM [openwebui].[dbo].[user] u
JOIN PKG_ENG.[dbo].[ACTIVEDIRECTORY_USERS] ad
    ON u.[email] COLLATE Latin1_General_100_CI_AS_SC_UTF8 = ad.[mail]
GROUP BY u.[email]
HAVING COUNT(*) > 1;
```

#### Step 2 — Backfill UPDATE (transactional, idempotent)

```sql
BEGIN TRAN;

UPDATE u
SET u.[ntid] =
    -- Strip "amd\" (or any DOMAIN\) prefix; IT requires bare NTID, e.g. "agriffin" not "amd\agriffin"
    CASE
        WHEN ad.[NTName] LIKE '%\%'
            THEN RIGHT(ad.[NTName], LEN(ad.[NTName]) - CHARINDEX('\', ad.[NTName]))
        ELSE ad.[NTName]
    END
FROM [openwebui].[dbo].[user] u
INNER JOIN PKG_ENG.[dbo].[ACTIVEDIRECTORY_USERS] ad
    ON u.[email] COLLATE Latin1_General_100_CI_AS_SC_UTF8 = ad.[mail]
WHERE ad.[NTName] IS NOT NULL
  AND u.[oauth_sub] IS NOT NULL    -- only OIDC-provisioned users; excludes bootstrap admin / local-auth accounts
  AND (u.[ntid] IS NULL OR u.[ntid] = '');   -- idempotent: skip rows already backfilled

-- Verify before commit
SELECT TOP 20 u.[email], u.[ntid] AS backfilled_ntid
FROM [openwebui].[dbo].[user] u
WHERE u.[ntid] IS NOT NULL;

-- COMMIT;   -- uncomment after sanity check
-- ROLLBACK; -- if numbers look wrong
```

#### Critical correctness gotchas (do not skip)

| # | Gotcha | Mitigation |
|---|---|---|
| 1 | **`NTName` is `DOMAIN\username` format** (e.g. `amd\agriffin`). Loading the raw string sends `user: amd\agriffin` to gateway, which is invalid NTID — calls misattributed or rejected | The `RIGHT(... CHARINDEX('\\', ...))` slice in the UPDATE strips the prefix |
| 2 | **Email-side `COLLATE` defeats index** — query plan goes to scan. OK for one-shot; document as known cost | If `[user]` is large (>50k rows), pre-stage to a temp table or add a persisted computed column on the AD side |
| 3 | **Duplicate AD rows per email** (contractor offboarding lag, test accounts) → `UPDATE` may pick a non-canonical NTID | Run 6.1.b first; if duplicates exist, refine join with `WHERE ad.[active] = 1` or `MAX(ad.[lastLogon])` tiebreaker |
| 4 | **Idempotency** — re-running must not regress users who logged-in post-backfill and got fresher data | `WHERE u.[ntid] IS NULL OR u.[ntid] = ''` skips already-set rows |
| 5 | **Non-OIDC users** (bootstrap admin, local-auth accounts) have `oauth_sub IS NULL` and may not have a valid AD email match; populating their `ntid` would send a wrong/stale NTID to the gateway | `AND u.[oauth_sub] IS NOT NULL` guard limits backfill to users provisioned through OIDC. Non-OIDC accounts must be handled separately (typically via a service-account NTID per IT FAQ). |

### 6.2 Lazy backfill (Track A)

Already covered by §4.1 File B (`oauth.py`) — OIDC callback writes `user.ntid` on every login (insert and update branches). This is the long-term mechanism; SQL backfill is a one-shot warm-up.

---

## 7. Test Plan

### 7.1 Unit / Component
- [ ] `oauth.py`: mock OIDC callback with `onpremisessamaccountname` in `userinfo`; assert `user.ntid` is persisted on both insert and update branches
- [ ] `openai.py`: mock pipeline-flagged model; assert `payload["user"]["ntid"]` matches `user.ntid`
- [ ] `llm_clients.py`: set `ntid_context`; assert `_get_headers()` returns `{"user": "<ntid>", ...}`
- [ ] `llm_clients.py`: empty `ntid_context`; assert `user` header is **omitted** (not empty string — per IT, only required when shared app key in use)
- [ ] `orchestrator_agent_workflow.py`: `ContextVar` reset is reached even when workflow raises

### 7.2 Integration
- [ ] End-to-end via local Open WebUI + local pipeline + LLM Gateway dev endpoint. Capture egress traffic (`mitmproxy` or pipeline log) and confirm `user: <ntid>` header on `/v1/chat/completions`
- [ ] Concurrent user test: 2 users login simultaneously, fire chats in parallel, verify each request carries the correct NTID (no cross-contamination)
- [ ] Empty-NTID path: user who hasn't re-logged-in; verify request shape (header omitted) and gateway response

### 7.3 Manual Acceptance
- [ ] Re-login → check user row `ntid` column
- [ ] Send chat → grep pipeline log for `user:` header
- [ ] Hit gateway with valid NTID → 200; with empty NTID → expect 401/403 (per IT enforcement)

---

## 8. Rollout Sequence

> **Critical constraint**: PRs cross repos. If pipeline ships without Open WebUI, NTID is never set in body → gateway 401. If Open WebUI ships without pipeline, body field is added but ignored → silent miss. Also: DDL must precede the open-webui code deploy or the SQLAlchemy model will fail to query the user table.

```
Day 0:  IT/Azure adds onpremisessamaccountname optional claim          [external dependency]
Day 1:  PR-1 (pipeline) + PR-2 (open-webui) opened, both reviewed     [parallel review]
Day 2:  Run §4.1 Step 0 DDL on prod SQL Server (ALTER TABLE + index)  [must precede code deploy]
Day 2:  Merge PR-2 (open-webui) first — backward compatible (extra body field)
Day 2:  Deploy open-webui to staging; verify body carries ntid via pipeline log
Day 3:  Merge PR-1 (pipeline); deploy pipeline to staging
Day 3:  E2E verify in staging
Day 4:  Promote both to prod in same deployment window
Day 4:  Run §6.1 Step 1 sanity SQL → review match rate + duplicates
Day 4:  Run §6.1 Step 2 backfill UPDATE inside transaction → verify → COMMIT
Day 5:  Force session expiry on edge users without AD match; monitor gateway 401 rate
```

---

## 9. Rollback

| PR | Rollback impact |
|---|---|
| PR-1 (pipeline) | `user` header stops being sent → gateway 401 (after enforcement date). Revert to skip enforcement temporarily — coordinate with `dl.LLM-Gateway-Ops@amd.com` |
| PR-2 (open-webui) | Body field disappears; pipeline reads `""` → header omitted → gateway 401 same as above |

Both PRs are **additive** (new field / new header), no destructive schema changes. Revert is straightforward git revert.

---

## 10. Open Questions (Need Sign-Off)

| # | Question | Recommendation |
|---|---|---|
| 1 | Body field name in `payload["user"]` (Open WebUI ↔ Pipeline) | `ntid` (lowercase) — decoupled from IT's header name `user` to avoid confusing `payload["user"]["user"]` |
| 2 | Behavior on missing NTID | **Omit the `user` header entirely** (don't send empty string). Per IT FAQ, gateway team monitors for non-compliance. Empty header may be treated as malformed. |
| 3 | Logging: should we emit a WARNING when NTID is empty for a pipeline-flagged request? | Yes — log once per session at INFO level to aid debugging during backfill window |
| 4 | Service account NTID for batch/test scenarios | Need IT to allocate a dedicated service account NTID; track separately |

---

## 11. References

- [Confluence: User Header Modification](https://amd.atlassian.net/wiki/spaces/SI/pages/1655519770/User+Header+Modification)
- [Confluence: Mandatory User Identification Policy and Enforcement Strategy](https://amd.atlassian.net/wiki/spaces/SI/pages/1655519770) (deadline 2026-05-02)
- IT contacts:
  - Gateway implementation: `dl.LLM-Gateway-Ops@amd.com`
  - SLAI Suite / personal keys: `dl.SLAI-Suite-Ops@amd.com`
- Code references:
  - Open WebUI OIDC callback: `backend/open_webui/utils/oauth.py:233`
  - Open WebUI pipeline body injection: `backend/open_webui/routers/openai.py:658`
  - Pipeline entrypoint: `C:\Github\pipeline\llamaindex_pipeline_v6.1_SPA_Chief_Planner_modularized.py:225`
  - Pipeline LLM headers (choke point): `C:\Github\pipeline\pipeline_modules\llm_clients.py:118`

---

## 12. Alternative: Plan B — Pipeline-Side AD Lookup

### 12.1 Idea

Instead of teaching Open WebUI to capture and store NTID, let the **pipeline** look it up itself at request time. The pipeline already receives `body["user"]["email"]` (Open WebUI sends this today, no code change). The pipeline queries `PKG_ENG.[dbo].[ACTIVEDIRECTORY_USERS]` directly to translate `email → NTID`, caches the result, and emits the `user: <NTID>` header.

### 12.2 Why Plan B exists

The user table already has `email`. AD has `email → NTID`. Plan A serializes that mapping into `user.ntid` ahead of time; Plan B resolves it on demand. **Same data flow, different cache point.**

### 12.3 Comparison

| Dimension | Plan A (current §1–§10) | Plan B |
|---|---|---|
| Repos changed | `open-webui` + `pipeline` (1 DDL + 6 files) | `pipeline` only (4 files: 3 from §4.2 + 1 new `ad_client.py`) |
| Open WebUI schema | Adds dedicated `ntid` column (manual DDL) | Untouched |
| Open WebUI DB writes | Yes (`user.ntid` updated on OIDC login) | None |
| Backfill SQL needed | Yes (§6) | No |
| External blocker | Azure Entra ID optional claim config (IT) | None |
| Runtime cost per request | Zero (NTID already in body) | One DB lookup (cached LRU; ~0ms warm, ~10–50ms cold) |
| Pipeline infra needs | Existing | New: network access from pipeline host → `PKG_ENG` DB + read-only credential |
| Failure mode if AD is down | Pipeline still works (uses cached `user.info`) | Pipeline degrades — must decide: 503, fall back to cached, or send empty header |
| AD identity drift (rename/rejoin) | Stale until user re-logs in | Stale until cache TTL expires (configurable, e.g. 1h) |
| Schema coupling | Pipeline ignorant of AD schema | Pipeline directly depends on `ACTIVEDIRECTORY_USERS` table shape |

### 12.4 What Plan B keeps from Plan A

The entire **pipeline-side** half is unchanged:

- §4.2 File C (`llamaindex_pipeline_v6.1_..._modularized.py`) — same `pipe()` change, but reads `body["user"]["email"]` instead of `body["user"]["ntid"]`
- §4.2 File D (`orchestrator_agent_workflow.py`) — same `ContextVar` plumbing
- §4.2 File E (`pipeline_modules/llm_clients.py`) — same `_get_headers()` injection of `user: <NTID>`

### 12.5 New code Plan B requires

#### `pipeline_modules/ad_client.py` (new file)

Responsibilities:
1. Hold a connection (or pool) to MSSQL `PKG_ENG`
2. Expose `lookup_ntid(email: str) -> str | None`
3. In-memory LRU cache with TTL (recommend `cachetools.TTLCache(maxsize=10000, ttl=3600)`)
4. Strip `DOMAIN\` prefix from `NTName` (same gotcha as Plan A §6.1)
5. Log cache hit/miss metrics for ops visibility

Pseudocode skeleton:

```python
# pipeline_modules/ad_client.py
import pyodbc
from cachetools import TTLCache
from threading import Lock

_cache: TTLCache[str, str] = TTLCache(maxsize=10000, ttl=3600)
_lock = Lock()

def lookup_ntid(email: str) -> str | None:
    if not email:
        return None
    if email in _cache:
        return _cache[email]
    with _lock:  # avoid stampede on cold key
        if email in _cache:
            return _cache[email]
        with pyodbc.connect(AD_CONN_STR, readonly=True) as conn:
            row = conn.execute(
                "SELECT TOP 1 NTName FROM PKG_ENG.dbo.ACTIVEDIRECTORY_USERS "
                "WHERE mail COLLATE Latin1_General_100_CI_AS_SC_UTF8 = ? "
                "ORDER BY <tiebreaker>",
                email,
            ).fetchone()
        if not row:
            _cache[email] = ""        # negative cache, prevents repeated lookups
            return None
        ntid = row.NTName.split("\\")[-1]   # strip "amd\"
        _cache[email] = ntid
        return ntid
```

#### Changes to existing pipeline files (replace email-keyed flow for NTID)

- `llamaindex_pipeline_v6.1_..._modularized.py:228-230`: read `email = user.get("email", "")`; immediately call `ad_client.lookup_ntid(email)`; pass result down as `user_ntid`
- `orchestrator_agent_workflow.py` and `llm_clients.py`: identical to Plan A §4.2 D & E

### 12.6 New configuration (Pipeline `.env` / Valves)

| Var | Purpose |
|---|---|
| `AD_DB_CONN_STR` | MSSQL connection string for `PKG_ENG` (read-only credential) |
| `AD_CACHE_TTL_SEC` | Default 3600 |
| `AD_CACHE_MAX` | Default 10000 |

### 12.7 Test Plan delta vs §7

Add:
- [ ] `ad_client.lookup_ntid` returns correct stripped NTID for sample emails
- [ ] Cache hit on second call (no second DB query) — verify via mock or query counter
- [ ] Negative cache: missing email returns `None` and doesn't re-query within TTL
- [ ] Stampede: 100 concurrent calls for a cold key result in 1 DB query (lock works)
- [ ] AD unreachable: failure mode behaves per chosen policy (503 / empty header / cached)

### 12.8 Rollout delta vs §8

```
Day 0:  DBA grants pipeline service account read on PKG_ENG.dbo.ACTIVEDIRECTORY_USERS
Day 0:  Pipeline host network: confirm reachability to PKG_ENG
Day 1:  PR-1 (pipeline only, includes ad_client.py)
Day 2:  Stage; load test (verify cache effectiveness, p99 latency unchanged)
Day 3:  Prod
```

No Open WebUI deployment, no SQL backfill, no IT/Azure claim work.

### 12.9 When to choose Plan B

✅ Choose Plan B if:
- Pipeline host has network + credentials to read `PKG_ENG`
- You want to ship faster (single repo, no external blocker)
- You're OK with one-time per-user DB hop (~10–50ms cold, 0ms warm)

❌ Choose Plan A if:
- Pipeline cannot reach `PKG_ENG` (network policy, infra cost)
- You want zero runtime DB dependency (AD outage = pipeline still works)
- You already plan to expose NTID elsewhere in the Open WebUI UI / API surface (then storing it makes sense)

### 12.10 Sections to delete if Plan B is chosen

| Section | Action |
|---|---|
| §4.1 entire (DDL Step 0 + Files A/B/C) | Delete |
| §5 row 1 (Azure optional claim) | Delete |
| §5 row 2 (`OAUTH_NTID_CLAIM`) | Delete |
| §6 entire backfill strategy | Delete |
| §8 Day 2 DDL + Day 4 SQL backfill steps | Delete |
| §10 Q1 (body field name) | Delete |
