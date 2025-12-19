## OpenTelemetry & Observability – 7 Phases Deployment Guide

This guide explains, in simple terms, the **7 OpenTelemetry phases** implemented in this branch and **what must be done next** to fully deploy and use them on OpenShift / Observe.

It is written so that even someone new to OTEL, tracing, or OpenShift can follow it end-to-end.

---

## Phase 1 – Dependencies & Environment Configuration

**Goal:** Add OpenTelemetry (OTEL) packages and environment variables so the backend *can* produce telemetry (traces + metrics).

### What was implemented

- **Dependencies** added to `pyproject.toml`:
  - `opentelemetry-api`
  - `opentelemetry-sdk`
  - `opentelemetry-exporter-otlp-proto-grpc`
  - `opentelemetry-instrumentation-fastapi`
  - `opentelemetry-instrumentation-requests`
  - `opentelemetry-instrumentation-redis`
  - `opentelemetry-instrumentation-sqlalchemy`
- **Environment variables** added in `backend/open_webui/env.py`, for example:
  - `OTEL_ENABLED`
  - `OTEL_SERVICE_NAME`
  - `OTEL_EXPORTER_OTLP_ENDPOINT`
  - `OTEL_EXPORTER_OTLP_PROTOCOL`
  - `OTEL_TRACES_SAMPLER`
  - `OTEL_TRACES_SAMPLER_ARG`
  - `OTEL_METRICS_EXPORTER`
  - `OTEL_LOGS_EXPORTER`

### What you need to do

For most people, **nothing extra is required** for this phase.

- Ensure the application is built and deployed with the updated `pyproject.toml`.
- At runtime (in OpenShift), configure these variables as needed. Common values:
  - `OTEL_ENABLED=true`
  - `OTEL_SERVICE_NAME=open-webui`
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` (sidecar collector)
  - `OTEL_EXPORTER_OTLP_PROTOCOL=grpc`
  - `OTEL_TRACES_SAMPLER=parentbased_traceidratio`
  - `OTEL_TRACES_SAMPLER_ARG=0.1` (10% sampling)

Once this is set, the app has everything it needs to use OTEL.

---

## Phase 2 – OTEL SDK Initialization in FastAPI

**Goal:** Properly initialize the OTEL SDK when the FastAPI app starts, and shut it down cleanly when the app stops.

### What was implemented

- A centralized module (e.g. `backend/open_webui/utils/otel_config.py`) that:
  - Reads OTEL env vars.
  - Creates a `TracerProvider` and `MeterProvider`.
  - Attaches a `BatchSpanProcessor` and metric reader.
  - Handles errors gracefully (no crashes if OTEL is misconfigured).
- In `backend/open_webui/main.py`:
  - On startup (`lifespan` function), the app calls `initialize_otel()`.
  - On shutdown, it calls `shutdown_otel()` to flush remaining spans/metrics.

### What you need to do

- Ensure the backend is running the updated `main.py`.
- OTEL can be **turned on/off by env vars**:
  - Set `OTEL_ENABLED=true` to enable tracing/metrics.
  - Set `OTEL_ENABLED=false` to disable OTEL entirely.

No extra deployment steps are needed beyond setting these env vars.

---

## Phase 3 – Auto-Instrumentation for FastAPI & HTTP

**Goal:** Get **automatic tracing** for HTTP endpoints and outgoing HTTP calls without hand-writing manual spans everywhere.

### What was implemented

- **FastAPI instrumentation**:
  - Each request to the backend (e.g. `/api/chat/completions`) is automatically wrapped in a span.
- **`requests` instrumentation**:
  - Outgoing HTTP calls (to LLM APIs, gateways, etc.) are also traced automatically.

### What you need to do

- Nothing extra beyond Phases 1 and 2.
- Once the collector is deployed (Phase 6) and OTEL is enabled, you will automatically see basic traces:
  - One span per HTTP request.
  - Child spans for outgoing HTTP calls.

---

## Phase 4 – Manual Instrumentation for Business Logic

This phase adds **rich, business-aware spans** in critical parts of the system: LLM calls, file embeddings, and RQ jobs.

### 4A–4B – LLM Calls

**Goal:** Trace LLM interactions with detailed metadata.

#### What was implemented

- Helper utilities in `backend/open_webui/utils/otel_instrumentation.py`:
  - `trace_span`, `trace_span_async`
  - `add_span_event`, `set_span_attribute`, etc.
- Instrumented core LLM call sites:
  - `backend/open_webui/utils/chat.py` – `generate_chat_completion()`, `generate_direct_chat_completion()`.
  - `backend/open_webui/routers/openai.py` – OpenAI-compatible chat completions.
  - `backend/open_webui/routers/ollama.py` – Ollama chat completions.
  - `backend/open_webui/functions.py` – function/pipe-based completions.

Each of these functions now creates spans such as:

- `llm.chat_completion`
- `llm.openai.chat_completion`
- `llm.ollama.chat_completion`
- `llm.function.chat_completion`

with attributes like:

- `llm.provider`
- `llm.model`
- `llm.stream`
- Token usage (input, output, total), where available.

#### What you need to do

- Nothing special; these spans will show up automatically once OTEL and the collector are live.
- When debugging or analyzing performance, you can filter traces by these span names.

---

### 4C – File Processing (Uploads & Embeddings)

**Goal:** Trace the full lifecycle of file uploads and embedding generation.

#### What was implemented

- In `backend/open_webui/routers/knowledge.py`:
  - `add_file_to_knowledge_by_id()` is wrapped in a `file.upload` span.
  - Attributes recorded: `file.id`, `file.name`, `file.size`, `file.content_type`, `knowledge.id`, `user.id`.
  - Events:
    - `file.upload.started`
    - `file.upload.stored`
    - `file.upload.queued`
    - `file.upload.completed`
    - `file.upload.error` (with error details)

- In `backend/open_webui/routers/retrieval.py`:
  - `save_docs_to_vector_db()` – span `file.embedding.save`:
    - Attributes: `collection.name`, `document.count`, `chunk.count`, `embedding.engine`, `embedding.model`.
    - Events: `embedding.split.completed`, `embedding.generation.started`, `embedding.generation.completed`, `vector_db.insert.started`, `vector_db.insert.completed`, `vector_db.insert.failed`.
  - `get_embeddings_with_fallback()` – span `file.embedding.generate`:
    - Attributes: `embedding.engine`, `embedding.model`, `text.count`, `embedding.batch_size`, `embedding.fallback_used`.
    - Events: `embedding.api.request`, `embedding.api.response`, `embedding.api.fallback`, `embedding.api.fallback_failed`.

#### What you need to do

- Again, nothing extra beyond deploying the updated backend and collector.
- You will be able to see, for a single knowledge file:
  - Upload → splitting → embedding → vector DB insert.

---

### 4D – RQ Background Jobs (Distributed Tracing Across Workers)

**Goal:** Maintain **trace continuity across process boundaries**, from the web app to Redis Queue (RQ) worker processes.

#### What was implemented

- In `backend/open_webui/utils/job_queue.py` (`enqueue_file_processing_job()`):
  - Extracts current OTEL trace context using `TraceContextTextMapPropagator`.
  - Stores it in job kwargs as `_otel_trace_context`.
  - Creates a `job.enqueue` span with attributes such as:
    - `job.id`
    - `job.file_id`
    - `job.queue_name`
    - `job.timeout`

- In `backend/open_webui/workers/file_processor.py` (`process_file_job()`):
  - Accepts `_otel_trace_context` as an argument.
  - Restores the trace context using `context.attach()/detach()`.
  - Wraps the entire job with a `job.process` span.
  - Adds events:
    - `job.started`
    - `job.file.extracted`
    - `job.embedding.completed`
    - `job.completed`
    - `job.failed`
  - Records `job.duration_ms` attribute.

#### What you need to do

- Make sure the **worker deployments** also:
  - Have OTEL env vars set.
  - Include the OTEL collector sidecar (Phase 6).
- Then, a single trace will span:
  - HTTP request → file upload → job enqueue → worker job processing → embeddings saved.

---

## Phase 5 – Loguru Trace Correlation

**Goal:** Make logs and traces **correlatable** using `trace_id` and `span_id`.

### What was implemented

- `backend/open_webui/utils/logger.py`:
  - `stdout_format()` now:
    - Extracts `trace_id` and `span_id` from the current OTEL context (if any).
    - Adds them to `record["extra"]`.
    - Renders them in the log line, e.g.:
      - `trace_id=... span_id=...`.

- `backend/open_webui/utils/audit.py`:
  - `AuditLogger.write()` now:
    - Extracts `trace_id` from OTEL.
    - Adds it into the audit log `extra` dict.

### What you need to do

- Ensure Loguru logs are being collected by your log system (e.g., OpenShift / Loki).
- When investigating issues:
  - Start from a trace: copy its `trace_id` and search logs.
  - Or start from a log line: use its `trace_id` to find the corresponding trace.

This is especially useful for production debugging.

---

## Phase 6 – OTEL Collector Sidecar Deployment

**Goal:** Run an OTEL Collector as a **sidecar container** next to each app pod so:

- The app sends telemetry to `localhost:4317`.
- The sidecar forwards telemetry to OpenShift Observe (once configured).

### What was implemented

- `kubernetes/manifest/base/otel-collector-config.yaml`:
  - Defines a `ConfigMap` with OTEL Collector configuration:
    - Receivers: OTLP (gRPC 4317, HTTP 4318).
    - Processor: `batch` (timeout 5s, batch size 512).
    - Exporters:
      - `otlp` – endpoint is `${OTEL_EXPORTER_OTLP_ENDPOINT}` (needs to be set for Observe).
      - `logging` – for debugging.
    - Service pipelines: `traces`, `metrics`, `logs`.

- `kubernetes/manifest/base/webui-deployment.yaml`:
  - Main `open-webui` container unchanged **plus** OTEL env vars:
    - `OTEL_ENABLED=true`, `OTEL_SERVICE_NAME=open-webui`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`, etc.
  - Added `otel-collector` sidecar container with:
    - Image: `otel/opentelemetry-collector:latest`.
    - Command: `--config=/etc/otel-collector-config/otel-collector-config.yaml`.
    - Volume mount from ConfigMap.
    - Liveness/readiness probes on port 8888.

- `kubernetes/manifest/base/rq-worker-deployment.yaml`:
  - Similar OTEL env vars and `otel-collector` sidecar for worker pods.

### What you must do to deploy this

1. **Apply the OTEL Collector ConfigMap**:

   ```bash
   oc apply -f kubernetes/manifest/base/otel-collector-config.yaml
   ```

2. **Apply the updated deployments**:

   ```bash
   oc apply -f kubernetes/manifest/base/webui-deployment.yaml
   oc apply -f kubernetes/manifest/base/rq-worker-deployment.yaml
   ```

3. **Verify that the sidecars are running**:

   ```bash
   oc get pods -n <namespace> | grep open-webui
   oc describe pod <one-open-webui-pod> | grep -A3 "Containers:"
   # You should see both 'open-webui' and 'otel-collector' containers listed.
   ```

At this point, **telemetry is flowing from your app to the sidecars**, but the sidecars may not yet be pointing at a real Observe endpoint.

---

## Phase 7 – Testing, Validation, Optimization

**Goal:** Verify the full pipeline and tune it for production readiness.

### 7.1 – Wire OTEL Collector to OpenShift Observe (when ready)

Once the platform team provides:

- The OTLP endpoint for Observe (e.g. Tempo distributor service DNS).
- TLS/auth details (whether you need mTLS, Bearer token, or plain gRPC).

Then update the **exporter** section in `otel-collector-config.yaml`:

```yaml
exporters:
  otlp:
    endpoint: <YOUR_OBSERVE_OTLP_ENDPOINT>
    tls:
      insecure: false        # likely for production
      # ca_file: /path/to/ca.crt   (if needed)
      # cert_file: /path/to/tls.crt
      # key_file: /path/to/tls.key
    headers:
      # Authorization: "Bearer ${OTEL_AUTH_TOKEN}"  # if Observe requires a token
``

Then **re-apply** the ConfigMap and roll deployments:

```bash
oc apply -f kubernetes/manifest/base/otel-collector-config.yaml
oc rollout restart deployment/open-webui-deployment -n <namespace>
oc rollout restart deployment/open-webui-rq-worker-deployment -n <namespace>
```

### 7.2 – End-to-End Functional Testing

1. **Trigger real workflows**:
   - Open WebUI, create chats, use LLMs.
   - Upload files to knowledge bases.

2. **Check traces in Observe**:
   - Look for service `open-webui` and `open-webui-rq-worker`.
   - Confirm you can see:
     - HTTP spans.
     - LLM spans.
     - File upload + embedding spans.
     - Job enqueue + job processing spans.

### 7.3 – Performance Testing

- Run load tests (e.g. multiple concurrent users doing chat + file upload).
- Measure:
  - Latency before OTEL vs after OTEL.
  - CPU/memory of app pods and OTEL sidecars.
- If overhead is too high:
  - Reduce sampling (`OTEL_TRACES_SAMPLER_ARG`).
  - Tweak batch processor settings in the collector.
  - Adjust sidecar resource limits.

### 7.4 – Fault Tolerance Testing

- Simulate failures:
  - Stop Observe or block the OTLP endpoint.
  - Confirm the app still serves traffic (traces may be buffered/dropped, but no crashes).
  - Examine sidecar logs to ensure errors are logged but not fatal.

### 7.5 – Document & Handover

- Use this markdown plus `OTEL_DEPLOYMENT.md` as the basis for your **runbook**:
  - Where OTEL is configured.
  - How to adjust sampling.
  - How to change exporter endpoints and auth.
  - How to troubleshoot missing traces or sidecar issues.

---

## High-Level Checklist for New Operators

1. **Confirm code is deployed with all phases (1–5) implemented.**
2. **Apply OTEL ConfigMap and deployments** (Phase 6) to get sidecars running.
3. **Obtain Observe OTLP endpoint + TLS/auth requirements** from platform team.
4. **Update `otel-collector-config.yaml` exporter** section and re-apply.
5. **Verify traces and logs** in Observe, using `trace_id` for correlation.
6. **Load test and tune** sampling, batch settings, and resources.
7. **Keep this guide and OTEL_DEPLOYMENT.md with your runbooks** for future operators.
