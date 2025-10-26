# Utils/Telemetry Directory

This directory contains OpenTelemetry instrumentation for observability, providing distributed tracing, metrics, and logging integration. It enables monitoring of Open WebUI's performance, request flows, database queries, external API calls, and custom business metrics across the entire application stack.

## Files in This Directory

### setup.py
**Purpose:** Initialize OpenTelemetry tracing and metrics infrastructure, configure exporters, and instrument the application.

**Key Functions:**
- `setup(app, db_engine)` - Main setup function called at application startup

**Configuration Flow:**
```python
1. Set up TracerProvider with service name
2. Configure OTLP exporter (HTTP or gRPC)
3. Add basic auth headers if configured
4. Add span processor for trace export
5. Instrument FastAPI, SQLAlchemy, HTTP clients
6. Optionally set up metrics (if ENABLE_OTEL_METRICS=true)
```

**Used by:**
- `main.py` - Called during FastAPI app initialization

**Uses:**
- `utils/telemetry/exporters.py` - LazyBatchSpanProcessor
- `utils/telemetry/instrumentors.py` - Instrumentor class
- `utils/telemetry/metrics.py` - setup_metrics()
- `env.py` - OTEL_* environment variables

**Environment Variables:**
- `OTEL_SERVICE_NAME` - Service identifier (default: "open-webui")
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OTLP collector endpoint
- `OTEL_EXPORTER_OTLP_INSECURE` - Use insecure connection (true/false)
- `OTEL_BASIC_AUTH_USERNAME` - Basic auth username for collector
- `OTEL_BASIC_AUTH_PASSWORD` - Basic auth password for collector
- `OTEL_OTLP_SPAN_EXPORTER` - Exporter protocol ("http" or "grpc")
- `ENABLE_OTEL_METRICS` - Enable metrics collection (true/false)

### instrumentors.py
**Purpose:** Automatic instrumentation for FastAPI, SQLAlchemy, Redis, HTTP clients, and custom span enrichment.

**Key Components:**

#### Instrumentor Class
Main instrumentation orchestrator:
```python
class Instrumentor:
    def __init__(self, app: FastAPI, db_engine: Engine):
        self.app = app
        self.db_engine = db_engine

    def instrument(self):
        # Instrument all components
        pass
```

**Instrumentations Applied:**
- **FastAPI**: Automatic endpoint tracing
- **SQLAlchemy**: Database query tracing
- **Redis**: Cache operation tracing
- **HTTPX**: HTTP client request tracing (for async requests)
- **Requests**: HTTP client request tracing (for sync requests)
- **AioHttp**: Async HTTP client tracing
- **Logging**: Correlate logs with trace IDs

#### Hook Functions
Custom span enrichment hooks:

- `requests_hook(span, request)` - Enrich HTTP request spans
- `response_hook(span, request, response)` - Enrich HTTP response spans
- `redis_hook(span)` - Enrich Redis operation spans
- `aiohttp_request_start_hook(span, params)` - Enrich aiohttp request start
- `aiohttp_request_end_hook(span, params)` - Enrich aiohttp request end
- `aiohttp_request_exception_hook(span, params)` - Handle aiohttp errors

**Span Attributes Added:**
- `http.url` - Request URL
- `http.method` - HTTP method
- `http.status_code` - Response status code
- `redis.type` - Redis operation type
- `db.statement` - SQL query (sanitized)
- `error.type` - Exception type
- `error.message` - Exception message

**Used by:**
- `utils/telemetry/setup.py` - Instantiated and called during setup

**Uses:**
- OpenTelemetry instrumentation libraries
- `utils/telemetry/constants.py` - Span attribute constants

### exporters.py
**Purpose:** Custom span exporters and processors for efficient trace export.

**Key Components:**

#### LazyBatchSpanProcessor
Custom span processor that batches spans before export:

**Features:**
- Batches spans to reduce network overhead
- Configurable batch size and timeout
- Lazy initialization to reduce startup time
- Handles backpressure from slow collectors

**Configuration:**
- `max_queue_size` - Maximum spans in memory (default: 2048)
- `schedule_delay_millis` - Export interval in ms (default: 5000)
- `max_export_batch_size` - Spans per batch (default: 512)
- `export_timeout_millis` - Export timeout in ms (default: 30000)

**Used by:**
- `utils/telemetry/setup.py` - Added to TracerProvider

**Uses:**
- `opentelemetry.sdk.trace.export` - Base BatchSpanProcessor

### metrics.py
**Purpose:** Custom application metrics for business and performance monitoring.

**Key Functions:**
- `setup_metrics(app)` - Initialize metrics collection
- `record_request_metrics(request, response, duration)` - Record HTTP metrics
- `record_token_usage(user_id, tokens)` - Track LLM token consumption
- `record_chat_metrics(chat_id, message_count)` - Track chat activity

**Metrics Defined:**

#### HTTP Metrics
- `http_request_duration_seconds` (Histogram) - Request latency distribution
- `http_requests_total` (Counter) - Total requests by method, path, status
- `http_requests_in_progress` (Gauge) - Active requests

#### LLM Metrics
- `llm_tokens_total` (Counter) - Total tokens consumed by user, model
- `llm_completion_duration_seconds` (Histogram) - Completion latency
- `llm_errors_total` (Counter) - LLM errors by type

#### Chat Metrics
- `chats_total` (Counter) - Total chats created
- `messages_total` (Counter) - Total messages sent
- `active_users` (Gauge) - Current active users

#### RAG Metrics
- `rag_queries_total` (Counter) - RAG queries executed
- `rag_query_duration_seconds` (Histogram) - RAG query latency
- `vector_db_operations_total` (Counter) - Vector DB operations

#### System Metrics
- `file_uploads_total` (Counter) - Files uploaded
- `file_upload_size_bytes` (Histogram) - Upload size distribution
- `cache_hits_total` (Counter) - Cache hits
- `cache_misses_total` (Counter) - Cache misses

**Used by:**
- `utils/telemetry/setup.py` - Called if ENABLE_OTEL_METRICS=true
- `utils/middleware.py` - Records metrics during request processing
- `routers/*` - Individual routers record domain-specific metrics

**Uses:**
- `opentelemetry.metrics` - Metric instruments
- `prometheus_client` (optional) - Prometheus exporter

### constants.py
**Purpose:** Centralized constants for span attributes and semantic conventions.

**Constants Defined:**

```python
class SpanAttributes:
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_TARGET = "http.target"

    DB_SYSTEM = "db.system"
    DB_STATEMENT = "db.statement"
    DB_OPERATION = "db.operation"

    LLM_MODEL = "llm.model"
    LLM_TOKENS_PROMPT = "llm.tokens.prompt"
    LLM_TOKENS_COMPLETION = "llm.tokens.completion"
    LLM_TEMPERATURE = "llm.temperature"

    RAG_QUERY = "rag.query"
    RAG_DOCUMENTS_COUNT = "rag.documents.count"
    RAG_SOURCES = "rag.sources"

    USER_ID = "user.id"
    CHAT_ID = "chat.id"
    MESSAGE_ID = "message.id"

SPAN_REDIS_TYPE = "redis.type"
```

**Used by:**
- `utils/telemetry/instrumentors.py` - Span attribute keys
- `utils/middleware.py` - Custom span attributes
- All modules that create custom spans

## Architecture & Patterns

### OpenTelemetry Architecture
```
Application Code
  ↓
TracerProvider (creates spans)
  ↓
SpanProcessor (batches spans)
  ↓
Exporter (sends to collector)
  ↓
OTLP Collector (Jaeger, Zipkin, etc.)
```

### Automatic Instrumentation Pattern
OpenTelemetry libraries automatically wrap frameworks:
```python
# FastAPI routes automatically traced
@app.get("/api/chats")
async def get_chats():
    # Span automatically created: "GET /api/chats"
    # DB queries automatically traced as child spans
    chats = Chats.get_chats_by_user_id(user_id)
    return chats
```

No manual span creation needed for basic tracing.

### Custom Span Pattern
For custom operations, create manual spans:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("rag_query") as span:
    span.set_attribute("rag.query", query_text)
    span.set_attribute("rag.documents.count", len(docs))

    results = query_vector_db(query_text)

    span.set_attribute("rag.results.count", len(results))
```

### Span Context Propagation
Trace context propagates across service boundaries:
```python
# Request to external service
headers = {}
inject(headers)  # Inject trace context into headers

response = requests.get(external_url, headers=headers)
# External service can continue the trace
```

### Metrics Collection Pattern
Metrics recorded during request processing:
```python
# In middleware
start_time = time.time()

response = await call_next(request)

duration = time.time() - start_time
record_request_metrics(request, response, duration)
```

## Integration Points

### utils/telemetry/ → main.py
Application startup initializes telemetry:
```python
# In main.py
from open_webui.utils.telemetry.setup import setup

app = FastAPI()

# After app and DB initialized
setup(app, db_engine)
```

### utils/middleware.py → utils/telemetry/
Middleware records custom metrics and spans:
```python
# In middleware.py
from opentelemetry import trace
from open_webui.utils.telemetry.metrics import record_token_usage

tracer = trace.get_tracer(__name__)

async def chat_completion(body, user):
    with tracer.start_as_current_span("chat_completion") as span:
        span.set_attribute("user.id", user.id)
        span.set_attribute("llm.model", body.model)

        # ... completion logic ...

        record_token_usage(user.id, tokens)
```

### routers/ → utils/telemetry/
Routers automatically instrumented, can add custom metrics:
```python
# In routers/chats.py
from open_webui.utils.telemetry.metrics import record_chat_metrics

@app.post("/api/chats/new")
async def create_chat(chat: ChatForm):
    new_chat = Chats.insert_new_chat(chat)

    record_chat_metrics(new_chat.id, len(chat.messages))

    return new_chat
```

### Telemetry → OTLP Collector
Traces and metrics exported to observability backends:
- **Jaeger**: Distributed tracing visualization
- **Zipkin**: Trace analysis
- **Grafana Tempo**: Scalable trace storage
- **Prometheus**: Metrics scraping (if using Prometheus exporter)
- **Grafana**: Visualization dashboards

## Key Workflows

### Request Tracing Workflow
```
1. Request arrives at FastAPI
2. FastAPI instrumentation creates root span
3. Router handler executes
4. SQLAlchemy instrumentation creates DB span (child)
5. HTTP request to LLM provider creates HTTP span (child)
6. Middleware adds custom attributes (user_id, model, etc.)
7. Response returned
8. Span marked complete with status
9. Span processor batches span
10. Exporter sends to OTLP collector
11. Collector forwards to Jaeger/Zipkin
12. Trace viewable in UI
```

### Metrics Recording Workflow
```
1. Request starts (metrics middleware)
2. http_requests_in_progress.inc()
3. Request processed
4. Token usage recorded: llm_tokens_total.inc(tokens)
5. Response returned
6. Duration calculated
7. http_request_duration_seconds.observe(duration)
8. http_requests_total.inc(method, path, status)
9. http_requests_in_progress.dec()
10. Metrics periodically scraped by Prometheus
11. Metrics visualized in Grafana
```

### Distributed Trace Workflow
```
1. User sends chat message (frontend)
2. POST /api/chat/completions (trace starts)
3. Middleware: inject_user_memory() (child span)
4. Retrieval: query_vector_db() (child span)
5. HTTP: POST to OpenAI API (child span, context injected)
6. OpenAI: Processes request (separate service, continues trace)
7. Middleware: generate_title() background task (linked span)
8. All spans connected by trace ID
9. View full flow in Jaeger UI
```

### Error Tracking Workflow
```
1. Exception occurs during request
2. Span marked with error status
3. Exception details added to span attributes
4. llm_errors_total.inc(error_type)
5. Span exported with error flag
6. Collector alerts on high error rate
7. Developer views trace to debug
```

## Important Notes

### Critical Dependencies
- `opentelemetry-api` - Core API
- `opentelemetry-sdk` - SDK implementation
- `opentelemetry-instrumentation-*` - Auto-instrumentation libraries
- `opentelemetry-exporter-otlp` - OTLP exporter
- OTLP collector running (Jaeger, Grafana Tempo, etc.)

### Configuration
All configuration via environment variables:
- **OTEL_SERVICE_NAME**: Identifies service in traces
- **OTEL_EXPORTER_OTLP_ENDPOINT**: Collector URL (e.g., `http://localhost:4317`)
- **OTEL_EXPORTER_OTLP_INSECURE**: Set to `true` for non-TLS endpoints
- **ENABLE_OTEL_METRICS**: Enable metrics collection (default: false)

### Performance Considerations
- Tracing adds ~1-5ms latency per request
- Span batching reduces network overhead
- High-cardinality attributes (IDs) can explode storage
- Consider sampling for high-traffic endpoints
- Metrics add negligible overhead (<1ms)

### Security Considerations
- Traces may contain sensitive data (sanitize DB queries)
- Basic auth credentials in environment variables
- Use TLS for production OTLP endpoints
- Rotate basic auth credentials regularly
- Filter PII from span attributes

### Sampling Strategies
For high-traffic deployments:
- **Head Sampling**: Sample at trace creation (e.g., 10% of traces)
- **Tail Sampling**: Sample after trace completes (keep errors, slow requests)
- **Adaptive Sampling**: Adjust sampling rate based on traffic

Configure in `setup.py`:
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

sampler = TraceIdRatioBased(0.1)  # 10% sampling
TracerProvider(sampler=sampler, ...)
```

### Custom Metrics Best Practices
- Use labels sparingly (high cardinality increases storage)
- Prefer Histograms for latency (not Gauges)
- Use Counters for event counts (not Gauges)
- Add metric descriptions for documentation
- Consider metric aggregation in collector

### Debugging Telemetry
Enable debug logging:
```python
import logging
logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
```

Verify exporter connectivity:
```bash
# Check OTLP endpoint
curl http://localhost:4317

# View exported traces
docker logs jaeger
```

### Testing Considerations
- Disable telemetry in unit tests (set `ENABLE_OTEL_METRICS=false`)
- Use in-memory span exporter for integration tests
- Verify custom spans created with mock exporter
- Test metric values with test exporter
