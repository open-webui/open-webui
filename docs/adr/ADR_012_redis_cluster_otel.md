# ADR 012: Distributed Cache and Observability Infrastructure

> **Status:** Accepted
> **Date:** 2026-01 (commit: 654172d)
> **Deciders:** Open WebUI contributors

## Context

Production deployments of Open WebUI require:
- **Horizontal scaling:** Multiple instances behind load balancer
- **Shared state:** WebSocket connections, session data, cache
- **Observability:** Distributed tracing, metrics, logging

Single-instance deployments use in-memory state, but multi-instance deployments need:
- Redis for shared WebSocket state (Socket.IO adapter)
- Redis for caching (model lists, configuration)
- OpenTelemetry for tracing across instances

## Decision

Implement **Redis cluster support with OpenTelemetry instrumentation**:

1. **Redis integration:** Socket.IO Redis adapter, cache storage
2. **Cluster mode:** Support Redis Cluster for high availability
3. **OpenTelemetry:** Instrument Redis operations for tracing
4. **Graceful fallback:** Work without Redis for simple deployments

## Consequences

### Positive
- **Scalability:** Horizontal scaling with shared state
- **Reliability:** Redis Cluster provides HA
- **Observability:** Full request tracing across services
- **Flexibility:** Optional infrastructure for those who need it

### Negative
- **Complexity:** Additional infrastructure to manage
- **Cost:** Redis Cluster requires multiple nodes
- **Configuration:** More environment variables to set
- **Debugging:** Distributed systems harder to debug

### Neutral
- Redis is well-understood infrastructure
- OpenTelemetry is becoming industry standard

## Implementation

**Redis configuration:**

```python
# env.py
REDIS_URL = os.environ.get("REDIS_URL", "")  # redis://localhost:6379
REDIS_CLUSTER_MODE = os.environ.get("REDIS_CLUSTER_MODE", "false").lower() == "true"
WEBSOCKET_MANAGER = os.environ.get("WEBSOCKET_MANAGER", "")  # "redis" for distributed
WEBSOCKET_REDIS_URL = os.environ.get("WEBSOCKET_REDIS_URL", REDIS_URL)
```

**Socket.IO with Redis adapter:**

```python
# socket/main.py
import socketio
from socketio import AsyncRedisManager

def get_client_manager():
    if WEBSOCKET_MANAGER == "redis" and WEBSOCKET_REDIS_URL:
        return AsyncRedisManager(WEBSOCKET_REDIS_URL)
    return None  # In-memory manager

sio = socketio.AsyncServer(
    async_mode="asgi",
    client_manager=get_client_manager(),
)
```

**Redis Cluster instrumentation:**

```python
# utils/telemetry/instrumentors.py
from opentelemetry.instrumentation.redis import RedisInstrumentor

def instrument_redis():
    """Instrument Redis for OpenTelemetry tracing."""
    RedisInstrumentor().instrument()

# For cluster mode, ensure proper instrumentation
def get_redis_client():
    if REDIS_CLUSTER_MODE:
        from redis.cluster import RedisCluster
        return RedisCluster.from_url(REDIS_URL)
    else:
        import redis
        return redis.from_url(REDIS_URL)
```

**OpenTelemetry setup:**

```python
# main.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def setup_telemetry():
    if not OTEL_EXPORTER_OTLP_ENDPOINT:
        return

    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument libraries
    instrument_redis()
    instrument_fastapi()
    instrument_sqlalchemy()
```

**Docker Compose for observability:**

```yaml
# docker-compose.otel.yaml
services:
  open-webui:
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
      - REDIS_URL=redis://redis:6379

  redis:
    image: redis:7-alpine

  otel-collector:
    image: otel/opentelemetry-collector-contrib
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml

  jaeger:
    image: jaegertracing/all-in-one
    ports:
      - "16686:16686"  # Jaeger UI
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Load Balancer                                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   Instance 1  │       │   Instance 2  │       │   Instance 3  │
│   Open WebUI  │       │   Open WebUI  │       │   Open WebUI  │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        │  WebSocket + Cache    │                       │
        └───────────────────────┼───────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌───────────────┐       ┌───────────────┐
            │ Redis Cluster │       │    OTEL       │
            │ (HA State)    │       │  Collector    │
            └───────────────┘       └───────┬───────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │    Jaeger/    │
                                    │   Zipkin/etc  │
                                    └───────────────┘
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `""` | Redis connection URL |
| `REDIS_CLUSTER_MODE` | `false` | Enable Redis Cluster |
| `WEBSOCKET_MANAGER` | `""` | Set to `redis` for distributed |
| `WEBSOCKET_REDIS_URL` | `REDIS_URL` | Redis URL for Socket.IO |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `""` | OTLP collector endpoint |
| `OTEL_SERVICE_NAME` | `open-webui` | Service name in traces |

## Alternatives Considered

### Memcached for caching
- Simpler than Redis
- No pub/sub for Socket.IO
- Rejected for Socket.IO requirements

### Custom WebSocket clustering
- Build custom pub/sub
- More control
- Significant implementation effort
- Rejected for Socket.IO Redis adapter maturity

### Prometheus instead of OpenTelemetry
- Well-established for metrics
- Less suited for distributed tracing
- Rejected for tracing requirements (OTel does both)

## Related Documents

- `ADR_005_socketio_realtime.md` — WebSocket architecture
- `SYSTEM_TOPOLOGY.md` — Runtime data flows
- `docker-compose.otel.yaml` — Observability deployment

---

*Last updated: 2026-02-03*
