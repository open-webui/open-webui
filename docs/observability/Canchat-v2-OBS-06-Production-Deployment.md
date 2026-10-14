# OBS-06: Production capacity, availability and ownership for the observability stack

Status: **Proposed (2026-10-14).** | Depends on: OBS-03 (done: [Gate 1](Canchat-v2-Logging%20Architecture-v2.md#gate-1-obs-03-dependency-resolution)) | Unblocks: OBS-58 | Ref: [Logging Architecture v2 §9](Canchat-v2-Logging%20Architecture-v2.md#9-infrastructure), Gate 5

Compose shows local integration only. This document defines what production needs: size, replicas, backups and restore, credentials, network flows, egress, ownership and which parts SSC runs. OBS-58 implements it as Kubernetes manifests.

## 1. Decisions

1. **Self-run the telemetry stack; use SSC services for the stateful dependencies.** CANChat runs the collector, Alloy, tenant proxy, Loki, Tempo, both Prometheus instances, Grafana and the audit worker in its own namespace. The SIEM/evidence archive, object storage, Postgres, the secret store and SSO come from SSC (§4).
2. **Use the small deployment modes.** Loki runs monolithic with 3 replicas (replication factor 3), Tempo as a single binary, and Prometheus as 2 identical replicas. The volume in §3 is far below the roughly 20 GB/day where Loki recommends moving off monolithic mode.
3. **The collector pushes metrics to Prometheus** using Prometheus's OTLP receiver. Prometheus does not scrape the collector's `prometheus` exporter. With 2 collector replicas behind one Service, a scraped exporter splits one app pod's counters across two targets. **This changes the "scrape endpoint" arrow in the architecture diagram** (§10).
4. **The audit delivery worker runs as its own Deployment**, not inside the web pods. Only the worker gets egress to the SIEM and holds the SIEM credentials. Web pods set `AUDIT_DELIVERY_ENABLED=false`.
5. **Production requires Postgres.** The outbox lease (`FOR UPDATE SKIP LOCKED`, [OBS-04 §8](Canchat-v2-OBS-04-Audit-Event-Schema.md#8-siemarchive-delivery)), multiple web replicas and the separate worker do not work on SQLite.
6. **Default-deny networking with no internet egress** for every observability component, except the destinations listed in §7.2. Vendor usage reporting is turned off in configuration *and* blocked by policy.
7. **Respond to alerts during service hours.** The audit outbox holds 7 days of SIEM outage, which covers a long weekend. Pages outside service hours are limited to outbox capacity (§9.2).

## 2. Inputs and assumptions

### 2.1 Inputs from earlier tickets

| Source | Input used here |
|---|---|
| OBS-03 Gate 1 | Image pins: collector-contrib `0.162.0`, Loki `3.7.8`, Tempo `3.1.0` (topology to be validated), Prometheus `v3.15.0`, Grafana `13.2.3`. Alloy deferred to OBS-70. HTTPX instrumentation is added for LiteLLM/OpenAI. |
| OBS-04 §7 | ≤ 10,000 active series per app instance. Scrape limits `sample_limit: 20000`, `label_limit: 30`, `label_value_length_limit: 128`. |
| OBS-04 §8 | Outbox row ≈ 1 KiB encrypted. Reserve capacity for **7 days of SIEM outage at peak rate**. Rows are kept 7 days after their SIEM receipt. |
| OBS-05 §3 (provisional) | Loki `app` 184 d, `frontend` 90 d, `audit` 731 d. Tempo 30 d. Both Prometheus instances 397 d. Chat DB backups ≤ 30 d. Noncurrent object versions ≤ 7 d. |

### 2.2 Current state (checked 2026-10-14)

| Finding | Evidence | Effect |
|---|---|---|
| The base manifest runs 1 web replica of the upstream image with 500m/500Mi requests and a single RWO PVC. It has no Postgres, Redis or Qdrant. | [webui-deployment.yaml](../../kubernetes/manifest/base/webui-deployment.yaml) | The production topology lives outside this repo. Platform supplies the real replica count and DB endpoints in OBS-58. |
| Ollama has `nvidia.com/gpu: "0"`, and Ollama and Qdrant use `:latest` images. | [ollama-statefulset.yaml](../../kubernetes/manifest/base/ollama-statefulset.yaml), [docker-compose.qdrant.yaml](../../docker-compose.qdrant.yaml) | GPU metrics apply only where GPU nodes exist. Pin the model server and Qdrant images in OBS-58. |
| The collector has a `debug` exporter with `verbosity: detailed` in the metrics pipeline. | [otel-collector-config.yaml](../../otel-collector-config.yaml) | Must not reach production (OBS-51). |
| No backup configuration exists in the repo. | `kubernetes/` | §5 is new work for platform. |
| `crew_mcp_integration.py` sets `os.environ["OTEL_SDK_DISABLED"] = "true"` at import. `main.py` imports it through the `crew_mcp` router (line 95), after `instrumentation.py` (line 36) and before the lifespan runs. | [crew_mcp_integration.py](../../backend/mcp_backend/integration/crew_mcp_integration.py#L14-L15), [main.py](../../backend/open_webui/main.py#L95) | Today's meter provider is created first, so it survives. Any provider that OBS-14 creates later, in the lifespan, will be **silently disabled** in the whole process. The setting was meant to stop CrewAI's own telemetry to `telemetry.crewai.com:4319`. CrewAI also honours `CREWAI_DISABLE_TELEMETRY` (checked in the installed 1.7.2; re-check on the pinned 1.15.14). See §10. |
| The image already sets `SCARF_NO_ANALYTICS=true`, `DO_NOT_TRACK=true`, `ANONYMIZED_TELEMETRY=false`. | [Dockerfile](../../Dockerfile#L139-L141) | Keep these. ChromaDB's PostHog client (in the resolved set) is covered by `ANONYMIZED_TELEMETRY=false`. |

### 2.3 Load baseline

No production usage figures are in the repo, so the sizing uses the **planning baseline** below. Before OBS-58 merges, platform replaces it with values measured from `message_metrics` (one row per finalized message) and from one day of current access logs:

```sql
-- Postgres: peak day, peak daily users and peak minute over the last 30 days
WITH m AS (
  SELECT to_timestamp(created_at) AT TIME ZONE 'UTC' AS ts, user_id
  FROM message_metrics
  WHERE created_at >= extract(epoch FROM now() - interval '30 days')
)
SELECT
  (SELECT max(c) FROM (SELECT count(*) c FROM m GROUP BY date_trunc('day', ts)) d)                AS peak_messages_per_day,
  (SELECT max(c) FROM (SELECT count(DISTINCT user_id) c FROM m GROUP BY date_trunc('day', ts)) d) AS peak_daily_users,
  (SELECT max(c) FROM (SELECT count(*) c FROM m GROUP BY date_trunc('minute', ts)) d)             AS peak_messages_per_minute;
```

| Quantity | Planning baseline | How to replace it |
|---|---|---|
| Daily active users (peak day) | 6,000 | `peak_daily_users` |
| Chat messages (peak day) | 60,000 | `peak_messages_per_day` |
| Peak message rate | 6 / s | `peak_messages_per_minute / 60` |
| HTTP requests per message (all API calls, page loads, polling) | 30 → 1.8 M requests/day | Access-log lines per day ÷ messages per day |
| Web replicas | 4 | Platform |
| Audit events | 70,000/day (60k `chat.message`, ~10k auth/admin/access) | Messages + logins × 2 |

Storage for Loki and Tempo scales linearly with messages/day. Prometheus storage scales with active series.

## 3. Sizing

### 3.1 Volume and storage

Compression ratios are planning values. Check them against real chunk and block sizes during OBS-50.

| Store | Basis (baseline) | Raw/day | Stored/day | Retention | Storage needed |
|---|---|---|---|---|---|
| Loki `app` | 1.8 M access records × 1 KiB + 0.6 M app records × 0.5 KiB, × 1.5 margin | 3.0 GiB | 0.6 GiB (5:1) | 184 d | 110 GiB |
| Loki `frontend` | 6,000 users × 20 page views × 8 records + 60k × 3 events ≈ 1.1 M × 1 KiB | 1.1 GiB | 0.22 GiB | 90 d | 20 GiB |
| Loki `audit` | 70k events × 1.5 KiB | 0.1 GiB | 0.02 GiB | 731 d | 15 GiB |
| **Loki object storage** | Sum × 1.5 (duplicate chunks from RF 3) × 1.3 headroom | | | | **300 GiB** |
| **Tempo object storage** | 10 % sampling: 180k sampled requests × 8 spans + 6k sampled chat operations × 40 spans, × 0.7 KiB; 3:1; × 2 headroom | 1.2 GiB | 0.4 GiB | 30 d | **25 GiB** |
| **Prometheus ops** (each replica) | 40k app series (4 × 10k budget) at 15 s + 40k infra/exporter series at 30 s ≈ 345 M samples/day × 2 B, × 1.3 headroom | | 0.7 GiB | 397 d | **400 GiB PVC** |
| Prometheus analytics | ≤ 2,000 aggregate series, 1-min evaluation | | 6 MiB | 397 d | 10 GiB PVC |
| Audit outbox (in app Postgres) | 7-day SIEM outage at peak (105k/day × 7 × 1 KiB, × 2 for indexes) + 7 days of receipted rows | | | | **3 GiB reserved** |
| Collector persistent queue | ≈ 3 days of a Loki/Tempo outage at baseline | | | | 10 GiB per pod |

Peak Loki ingest is about 250 KiB/s (5 × the 50 KiB/s average). Ingest rate does not constrain any of these sizes.

**Lower-cost option:** setting `OTEL_METRIC_EXPORT_INTERVAL` to 30 s in production halves the app share of Prometheus storage (about 240 GiB of data instead of 330 GiB per replica, so a 300 GiB PVC). Grafana panels then cannot resolve below 30 s. The §12 default stays 15 s unless platform asks for this.

### 3.2 Compute and storage per component

| Component | Workload / mode | Replicas | CPU request / limit | Memory request / limit | Persistent storage |
|---|---|---|---|---|---|
| OTel Collector (contrib) | StatefulSet, gateway | 2 | 500m / 1 | 512Mi / 1Gi (`memory_limiter` 800 MiB, spike 200 MiB) | 10 GiB PVC per pod (`file_storage` queue) |
| Alloy (`faro.receiver`, phase 6) | Deployment | 2 | 250m / 1 | 256Mi / 512Mi | none |
| Loki tenant proxy | Deployment | 2 | 100m / 500m | 64Mi / 256Mi | none |
| Loki | StatefulSet, monolithic (`-target=all`), RF 3, memberlist | 3 | 500m / 2 | 2Gi / 4Gi | 20 GiB PVC per pod (WAL, index cache, compactor) + object storage 300 GiB |
| Tempo | single binary | 1 | 500m / 2 | 2Gi / 4Gi | 20 GiB PVC (WAL) + object storage 25 GiB |
| Prometheus ops | StatefulSet, OTLP receiver | 2 | 500m / 2 | 2Gi / 4Gi | 400 GiB PVC per pod |
| Prometheus analytics | StatefulSet, remote-write receiver | 1 | 250m / 1 | 512Mi / 1Gi | 10 GiB PVC |
| Grafana | Deployment, unified alerting HA | 2 | 250m / 1 | 512Mi / 1Gi | none (`grafana` DB on Postgres, < 1 GiB) |
| Audit delivery worker | Deployment | 2 | 100m / 500m | 256Mi / 512Mi | none (outbox in app DB) |
| postgres_exporter, redis_exporter, blackbox_exporter | Deployment | 1 each | 50m / 200m | 64Mi / 128Mi | none |
| DCGM exporter | DaemonSet on GPU nodes only | 1 per GPU node | 100m / 500m | 256Mi / 512Mi | none |
| Web pods (existing) | change only | | about +10 % | about +150 MiB (span/log batch queues of 2,048 records each) | none |

**Total for the stack (without web pods, without GPU nodes):** about 6.5 vCPU and 16 GiB of memory requested; about 910 GiB of block storage (PVCs) and 325 GiB of object storage.

The worker figures assume an entrypoint that does not import `open_webui.main` or run migrations (§10).

## 4. Managed SSC services and self-run components

| Capability | Decision | Reason |
|---|---|---|
| SIEM / evidence archive | **SSC-managed** (required) | Authoritative audit record ([OBS-04 §8](Canchat-v2-OBS-04-Audit-Event-Schema.md#8-siemarchive-delivery), OBS-57) |
| Object storage for Loki and Tempo | **SSC-managed, S3-compatible** | Durability and replication outside the cluster. A self-run object store would add a component with its own backup, licensing and on-call needs. |
| Postgres (app DB with outbox, `message_metrics`; `grafana` DB) | **SSC-managed or platform DBA** | Point-in-time recovery is required for the outbox RPO (§5). Grafana gets its own database and user on the same service. |
| Secret store | **SSC-approved store** (already required by OBS-04 keys) | Synced to Kubernetes Secrets. Never in Git or ConfigMaps. |
| SSO for Grafana | **Existing Entra ID** tenant (CANChat already uses Graph tokens) | Group claims map to the three orgs |
| Collector, Alloy, tenant proxy, Loki, Tempo, Prometheus ×2, Grafana, audit worker, exporters | **Self-run** in namespace `canchat-observability` (worker in `canchat`) | The tenant model, three-org isolation and analytics store are specific to CANChat. The architecture rules out public-cloud telemetry services at runtime. The volume fits the small modes. |

**Open option (confirm with platform in OBS-58):** if the SSC platform team already runs a shared Loki/Tempo/Prometheus that enforces tenants and supports retention per tenant, Loki, Tempo and ops Prometheus may be hosted there. The analytics Prometheus, the tenant-proxy rules and the Grafana orgs stay with CANChat in either case.

## 5. Availability, backup and restore

| Store / component | HA approach | Backup | RPO | RTO | Restore test |
|---|---|---|---|---|---|
| App Postgres (outbox, `message_metrics`, chats) | Managed HA (primary + standby) | Daily base backup + continuous WAL archive (PITR). Backups kept ≤ 30 days (OBS-05 R14). | ≤ 5 min | ≤ 4 h | Quarterly, to a scratch instance: compare outbox counts and `payload_sha256`; run chat cleanup before users get access; confirm the worker resumes. Redelivered events are expected (duplicates allowed by OBS-04). |
| SIEM / evidence archive | SSC | SSC | SSC schedule | SSC | SSC (OBS-57 replay test) |
| Loki | 3 replicas, RF 3, spread across nodes/zones, WAL on PVC | Object versioning; noncurrent versions expire ≤ 7 days (R14). No separate copy: the audit tenant is a search copy that can be re-fed from the SIEM. | 0 for one pod; ≤ 15 min for the whole store | ≤ 4 h | Every 6 months: start Loki in a scratch namespace on the bucket and query known canary lines from each tenant |
| Tempo | 1 replica; rescheduled on failure | none | ≤ 1 h (WAL loss, best effort) | 1 business day | none (diagnostic data) |
| Prometheus ops | 2 identical replicas; the collector pushes to both | Daily CSI VolumeSnapshot, keep 7. The admin API stays disabled. | 0 if one replica survives; 24 h if both are lost | ≤ 4 h | Every 6 months, from a snapshot |
| Prometheus analytics | 1 replica | Daily CSI VolumeSnapshot, keep 30 | 24 h. Windows within the last 90 days can be recomputed from Loki `frontend`. | 1 business day | Every 6 months, from a snapshot |
| Grafana | 2 replicas, shared DB, unified alerting HA (`ha_peers`) | Dashboards, data sources and alert rules are provisioned from Git. Users, annotations and alert state are in Postgres (PITR). | 0 for configuration; ≤ 5 min for DB | ≤ 2 h | With the Postgres test |
| Collector | 2 replicas, persistent queue | none | Data still queued on a lost PVC. Audit is not affected because the outbox keeps it. | ≤ 15 min | none |
| Alloy, tenant proxy, audit worker | 2 stateless replicas, `PodDisruptionBudget` `minAvailable: 1` | none | n/a (worker state is the outbox) | ≤ 15 min | none |

Rules for all components:

- Anti-affinity across nodes (and zones where they exist) for every multi-replica component. Use `PodDisruptionBudget`s so node drains never take all replicas. Run as non-root with a read-only root filesystem.
- Grafana queries ops Prometheus through a Service in front of both replicas. After a restart the replicas can differ by a few minutes of data. This is accepted, and avoids running Thanos or Mimir.
- **Monitoring the monitoring:** the platform's existing cluster monitoring probes `/-/healthy` (Prometheus), `/ready` (Loki, Tempo) and `/api/health` (Grafana). A Grafana "watchdog" alert that always fires goes to a dead-man's switch. If Grafana or Prometheus stops, someone still finds out.
- **Restoring the app DB to an earlier time** loses audit events and their state changes together, so they stay consistent. Events that already have a SIEM receipt are safe in the SIEM. The outbox may resend some events with the same `event_id`.

## 6. Credentials

All secrets come from the SSC-approved secret store as mounted files. None are in Git, images or ConfigMaps. Each ingress class and each writer has its own identity, so one stolen credential cannot write into another tenant.

| Credential | Used by → for | Form | Rotation |
|---|---|---|---|
| Backend OTLP identity | web pods → collector backend receiver | Bearer token (`bearertokenauth`) over TLS, or mTLS client certificate if the cluster has cert-manager | 90 days |
| Frontend OTLP identity | Alloy → collector frontend receiver | Same, separate value | 90 days |
| Audit OTLP identity | audit worker → collector audit receiver | Same, separate value | 90 days |
| Loki writer identities (`app`, `frontend`, `audit`) | collector → tenant proxy | Basic auth or mTLS, one identity per tenant | 90 days |
| Loki reader identities (`ops-reader`: app + frontend; `audit-reader`) | Grafana data sources → tenant proxy | Basic auth, stored encrypted in Grafana | 90 days |
| Prometheus web config | collector → ops Prometheus OTLP; aggregation producer → analytics remote write; Grafana → both | Basic auth + TLS (`--web.config.file`) | 90 days |
| Object storage keys | Loki, Tempo | Workload identity if SSC supports it, else access keys scoped to one bucket each | 90 days, or managed by the identity |
| Grafana `secret_key`, admin password, OIDC client secret, DB password | Grafana | Secret files | Admin password and client secret: 90 days. `secret_key` only with re-encryption. |
| SIEM credentials (`AUDIT_SIEM_AUTH_*`) | audit worker only | Per OBS-57 | Per SSC Security |
| `AUDIT_OUTBOX_KEY_FILE`, `AUDIT_PSEUDONYM_KEY_FILE` | web pods + worker (outbox key); web pods (pseudonym key) | 256-bit keys | 12 months ([OBS-04 §6, §8](Canchat-v2-OBS-04-Audit-Event-Schema.md#6-failed-login-pseudonymization)) |

Tempo has no built-in authentication. It accepts traffic only from the collector and Grafana, which NetworkPolicy enforces (§7).

## 7. Network policy and egress

### 7.1 In-cluster flows

Both namespaces start with **default-deny for ingress and egress**. Every pod may reach cluster DNS on port 53. Only the flows below are allowed. Receiver ports 4328/4338 are proposals; OBS-51 fixes them.

| # | From | To | Port | Purpose |
|---|---|---|---|---|
| F1 | Ingress controller | web pods | 8080 | App (existing) |
| F2 | Ingress controller | Alloy | 12347 | `/faro/collect` (phase 6) |
| F3 | Ingress controller, **internal hostname only** | Grafana | 3000 | Operators, auditors, analysts. Not on the public CANChat host. |
| F4 | web pods | Collector backend receiver | 4318 | Logs, traces, metrics (OTLP/HTTP + TLS) |
| F5 | Alloy | Collector frontend receiver | 4328 | Faro logs and traces |
| F6 | Audit worker | Collector audit receiver | 4338 | Loki search copy |
| F7 | web pods, audit worker | Postgres | 5432 | App DB, outbox |
| F8 | Collector | Tenant proxy | 8080 | Writes, one identity per tenant |
| F9 | Tenant proxy | Loki | 3100 | Fixed `X-Scope-OrgID` |
| F10 | Loki ↔ Loki | Loki | 7946, 9095 | Memberlist ring, replication |
| F11 | Collector | Tempo | 4318 | Traces |
| F12 | Collector | Prometheus ops (both) | 9090 `/api/v1/otlp` | Metrics push |
| F13 | Loki ruler / aggregation job | Prometheus analytics | 9090 `/api/v1/write` | Approved aggregates only |
| F14 | Prometheus ops | Collector 8888, Alloy 12345, Loki 3100, Tempo 3200, Grafana 3000, tenant proxy, exporters (9187, 9121, 9115, 9400), Qdrant 6333 | as listed | Scrape own and platform metrics |
| F15 | Grafana | Tenant proxy (read), Tempo 3200, both Prometheus 9090, Postgres 5432 | as listed | Queries, Grafana DB |
| F16 | postgres_exporter → Postgres; redis_exporter → Redis 6379; blackbox_exporter → model server (Ollama 11434) | | as listed | Platform health (§8) |

Nothing outside `canchat-observability` can reach Loki, Tempo or either Prometheus directly. Analytics Prometheus accepts F13 and Grafana only. It has no route to Loki reads, Tempo or ops Prometheus.

### 7.2 Egress allow-list (outside the cluster)

| Component | Allowed destinations |
|---|---|
| Loki, Tempo | SSC object storage endpoint (443) |
| Audit worker | SSC SIEM endpoint(s), port per OBS-57 |
| Grafana | Entra ID OIDC endpoints (`login.microsoftonline.com`; `graph.microsoft.com` only if group overage lookup is needed) on 443 |
| Postgres, object storage | If they run outside the cluster: their endpoints only |
| Web pods | Existing allow-list (LLM providers, web search, Graph, Entra ID). No telemetry vendor hosts are added. |
| Collector, Alloy, tenant proxy, both Prometheus, exporters | **None** |

### 7.3 Vendor usage reporting disabled

| Component | Setting |
|---|---|
| Grafana | `[analytics] reporting_enabled = false`, `check_for_updates = false`, `check_for_plugin_updates = false`, `feedback_links_enabled = false`; `[snapshots] external_enabled = false`; `[news] news_feed_enabled = false`; `[security] disable_gravatar = true`; `[plugins] plugin_admin_enabled = false`, plugin preinstall disabled. Plugins are baked into the image. Check key names against 13.2.3. |
| Loki | `analytics: reporting_enabled: false` |
| Tempo | `usage_report: reporting_enabled: false` |
| Alloy | `--disable-reporting`; `faro.receiver` source-map download disabled (OBS-75) |
| Collector, Prometheus | No phone-home. No `debug` exporter in production. |
| Web pods | Keep `SCARF_NO_ANALYTICS`, `DO_NOT_TRACK`, `ANONYMIZED_TELEMETRY=false`. Add `CREWAI_DISABLE_TELEMETRY=true` and `CREWAI_TRACING_ENABLED=false`. Set `ENABLE_VERSION_UPDATE_CHECK=false`. |

**Check:** during the OBS-58 end-to-end run, egress-deny logs must show no attempts to reach `stats.grafana.org`, `grafana.com`, `telemetry.crewai.com`, `app.crewai.com`, PostHog, Scarf or GitHub release endpoints. The policy is the control. The settings stop the noise.

## 8. Platform health metrics (DB, Redis, GPU, model server)

Client spans show calls *from* CANChat. They do not show the health of the dependency. These sources fill that gap. Prefer the managed service's own metrics where SSC provides them; otherwise use the exporter listed. Exporters use their default collectors only, with per-table stats limited to the outbox and `message_metrics`.

| Target | Source | Signals | Alerts |
|---|---|---|---|
| Postgres | Managed service metrics, else `postgres_exporter` | `up`; connections ÷ `max_connections`; commit/rollback rate; deadlocks; longest transaction age; replication lag; `pg_stat_archiver` failures and age of last archived WAL; free disk; outbox table size | Down, or WAL archiving failing (breaks the RPO): Sev 1. Connections > 80 % or lag > 60 s: Sev 2 |
| App DB pool | SQLAlchemy instrumentation (OBS-20) | Pool usage and wait time | Pool exhausted: Sev 2 |
| Audit outbox | App metrics (OBS-42) | Oldest undelivered age, backlog size, `dead_letter` count | Per [OBS-04 §8](Canchat-v2-OBS-04-Audit-Event-Schema.md#8-siemarchive-delivery) |
| Redis | `redis_exporter` | `up`; `used_memory` ÷ `maxmemory`; evicted keys; rejected connections; connected clients; AOF write status | Down (breaks Socket.IO across replicas): Sev 1. Memory > 80 %: Sev 2 |
| GPU | NVIDIA DCGM exporter | `DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED`/`FB_FREE`, `DCGM_FI_DEV_GPU_TEMP`, `DCGM_FI_DEV_POWER_USAGE`, `DCGM_FI_DEV_XID_ERRORS`, ECC double-bit errors | XID or ECC errors: Sev 1. Framebuffer > 95 % for 10 min, or temperature: Sev 2 |
| Model server (Ollama) | Ollama has no built-in Prometheus endpoint (verify on the pinned version). Use a blackbox probe of `/api/version`, pod restarts from kube-state-metrics, and the app's `llm_requests_total{provider="ollama"}` and TTFT. | Probe success; error ratio; TTFT p95 | Probe failing while Ollama models are enabled: Sev 1. Error ratio or TTFT regression: Sev 2 |
| External LLM providers (Azure OpenAI) | App `llm_*` metrics by `provider` and `outcome`; HTTPX client spans | Error ratio, 429 rate, TTFT | Sev 2 |
| Qdrant | Native `/metrics` | `up`, collection count, request durations | Down: Sev 1 |
| Kubernetes | kube-state-metrics and kubelet/cAdvisor (platform-provided) | Restarts, OOMKilled, PVC usage, pending pods | PVC > 80 % for Prometheus, Loki, Tempo or the collector queue: Sev 2 |

## 9. Ownership and on-call

### 9.1 Ownership per component

Names are SSC's to fill in. Roles: **Dev** = CANChat development team, **Platform** = SSC hosting/infrastructure team, **Security** = SSC Security, **PO** = CANChat product owner.

| Component | Builds and configures (repo) | Runs (capacity, upgrades, backups) | Receives alerts | Approves data access |
|---|---|---|---|---|
| App instrumentation, audit worker | Dev | Platform | Dev; Security for audit Sev 1 | n/a |
| Collector, Alloy, tenant proxy | Dev (config) | Platform | Platform | n/a |
| Loki, Tempo, ops Prometheus | Dev (config, rules, dashboards) | Platform | Platform | Dev lead (Operations org) |
| Analytics Prometheus | Dev | Platform | Platform | PO (which aggregates are allowed) |
| Grafana | Dev (dashboards and alerts as code) | Platform | Platform | Operations org: Dev lead. Audit org: Security. Analytics org: PO. |
| SIEM / evidence archive | Security | Security | Security | Security |
| Postgres, Redis, object storage, secret store | Platform / DBA | Platform / DBA | Platform | n/a |
| GPU nodes, model server, Qdrant | Platform | Platform | Platform; Dev for app-side LLM alerts | n/a |

Image upgrades follow Gate 1: pin by digest, scan, validate config with the new binary, then roll out. Platform schedules them. Dev updates the configuration.

### 9.2 On-call expectations

"Service hours" means CANChat's published support hours. Platform confirms them; the proposal is Monday to Friday, 07:00–19:00 Eastern.

| Severity | Examples | Response |
|---|---|---|
| **Sev 1** | Audit `dead_letter` row; `audit_emit_failures_total` rising; oldest undelivered SIEM event > 1 h; app 5xx or LLM error ratio over threshold; Postgres/Redis/Qdrant down; WAL archiving failing; no ingestion during service hours | Page during service hours, acknowledge within 15 min. Outside service hours: only **outbox > 80 % of reserved capacity** and **Postgres down** page; everything else waits for the next service-hours start. Security is notified for every audit Sev 1. |
| **Sev 2** | Loki/Tempo export failures; collector queue > 50 %; rejected data; TTFT regression; PVC > 80 %; frontend errors by release | Ticket, next business day |
| **Sev 3** | Dashboard gaps, single-replica loss with healthy peers | Backlog |

**Why service hours is enough for audit:** the outbox reserves 7 days of SIEM outage at peak rate. That is longer than a 4-day long weekend. The SIEM backlog alerts at 15 min and 1 h are early warnings well inside that reserve. If CANChat later commits to 24/7 service, these hours move with it.

## 10. Follow-ups for other tickets

| Ticket | Action |
|---|---|
| **OBS-14** (blocker) | Remove the process-wide `os.environ["OTEL_SDK_DISABLED"] = "true"` from [crew_mcp_integration.py](../../backend/mcp_backend/integration/crew_mcp_integration.py#L14-L15). Disable CrewAI telemetry with `CREWAI_DISABLE_TELEMETRY=true` and `CREWAI_TRACING_ENABLED=false` instead. Confirm on CrewAI 1.15.14 that these stop all connections to `telemetry.crewai.com`. Add a test that providers created after importing the `crew_mcp` router are enabled. |
| OBS-42 | Provide a worker-only entrypoint that does not import `open_webui.main` or run migrations at import. Web pods run with `AUDIT_DELIVERY_ENABLED=false`. Export the outbox backlog metrics listed in §8. |
| OBS-50 / OBS-51 | Collector pushes metrics to Prometheus's OTLP receiver (`--web.enable-otlp-receiver`) instead of a scraped `prometheus` exporter; check resource-attribute promotion and out-of-order settings with the pinned binaries. Update the architecture diagram ("scrape endpoint" → "OTLP push"). Remove the `debug` exporter. Confirm Tempo 3.1.0 runs as a single binary without Kafka; if it can't, pin the latest Tempo 2.x for v1 rather than run Kafka for diagnostic traces. |
| OBS-52 | Implement the tenant proxy with the identities in §6. NGINX (unprivileged image, pinned) is enough; no custom code. |
| OBS-56 | Use the severities and recipients in §9.2. Add the watchdog alert. |
| OBS-58 | Implement §3.2, §5, §6 and §7 as manifests. Replace the §2.3 baseline with measured values first. Confirm service hours (§9.2) and the shared-stack option (§4) with platform. Pin Ollama and Qdrant images. Require `DATABASE_URL` to be Postgres in production. Run the restore tests in §5 for Loki and the outbox DB. |
| OBS-60 | Retention values are already in §3.1 (from OBS-05). Size changes follow if SSC changes them. |
