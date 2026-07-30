# Database Audit Logging

Open WebUI can persist audit records in its application database in addition to the existing JSON-lines audit file. Database logging is disabled by default and is intended for operational search, retention, and access-controlled review.

## Enable It

Set the following environment variables on the `open-webui` container:

```yaml
environment:
  - AUDIT_LOG_LEVEL=REQUEST
  - AUDIT_EXACT_INCLUDED_PATHS=/api/v1/chat/completions
  - ENABLE_AUDIT_LOGS_DB=true
  - ENABLE_AUDIT_LOGS_FILE=true
  - AUDIT_LOGS_FILE_PATH=/app/backend/data/audit.log
  - MAX_BODY_LOG_SIZE=16384
```

`AUDIT_EXACT_INCLUDED_PATHS` is a comma-separated list of exact request paths. When it is set, it takes precedence over all other include and exclude rules, including the normally always-audited authentication endpoints. The configuration above therefore records only `POST /api/v1/chat/completions`, not WebUI requests to `/api/chat/completions`.

The service creates the `audit_log` table through Alembic migration `c2a4f28d7b1e` at startup. Existing file logging is unchanged; keep `ENABLE_AUDIT_LOGS_FILE=true` during initial rollout to retain a fallback record.

## Stored Record

One row is written after each audited HTTP request completes. Failed database writes are logged by the server but never change the API response.

| Column | Description |
| --- | --- |
| `id` | UUID shared with the file audit entry. |
| `created_at` | Write time in Unix milliseconds. |
| `user_id`, `user_snapshot` | User identifier and a snapshot of `id`, `name`, `email`, and `role`; no foreign key is used so audit history survives user deletion. |
| `audit_level`, `verb` | Effective audit level and HTTP method. |
| `request_path`, `request_uri` | Query-safe path and a URI with sensitive query values redacted. |
| `response_status_code` | HTTP status, captured for every audit level. |
| `source_ip`, `user_agent` | Caller metadata. |
| `request_object`, `response_object` | Captured, redacted request and response body text. |
| `request_truncated`, `response_truncated` | `true` when the respective body reached `MAX_BODY_LOG_SIZE`; `NULL` when that body type was not captured at the selected audit level. |
| `extra` | Reserved JSON object for future audit metadata. |

`METADATA` stores neither body. `REQUEST` stores only `request_object`. `REQUEST_RESPONSE` stores both bodies. A streamed response is stored as the prefix observed before completion or disconnect, up to `MAX_BODY_LOG_SIZE` bytes.

## Querying

Use the application database's normal administrative access. For example:

```sql
SELECT created_at, user_id, verb, request_path, response_status_code, source_ip
FROM audit_log
WHERE request_path = '/api/v1/chat/completions'
ORDER BY created_at DESC
LIMIT 100;
```

The table indexes time, path plus time, user plus time, and status plus time. Do not query or export body columns by default; prompts and model output may contain sensitive business data.

## Security and Retention

Before persistence, JSON fields named `password`, `authorization`, `cookie`, `api_key`, `token`, `secret`, or suffixes such as `_token` and `_secret` are redacted. Sensitive values in opaque strings cannot be reliably identified, so callers should never place credentials in prompt content.

Restrict direct database access and any future audit-log UI to administrators. Database retention is managed externally for now: use a scheduled database job or backup policy to purge rows according to your organization's retention requirements. Do not delete audit rows in the request path.
