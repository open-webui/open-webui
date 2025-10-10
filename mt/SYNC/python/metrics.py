"""
SQLite + Supabase Sync System - Prometheus Metrics
Phase 1: Monitoring and Observability

This module defines all Prometheus metrics for the sync system and provides
instrumentation for the FastAPI application.
"""

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator


# ============================================================================
# SYNC OPERATION METRICS
# ============================================================================

sync_operations_total = Counter(
    'sync_operations_total',
    'Total number of sync operations',
    ['client', 'status']  # status: success, failed, cancelled
)

sync_duration_seconds = Histogram(
    'sync_duration_seconds',
    'Sync operation duration in seconds',
    ['client'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]  # 1s to 1h
)

sync_rows_processed = Counter(
    'sync_rows_processed_total',
    'Total rows synchronized',
    ['client', 'table']
)

sync_rows_failed = Counter(
    'sync_rows_failed_total',
    'Total rows that failed to sync',
    ['client', 'table', 'error_type']
)

sync_bytes_transferred = Counter(
    'sync_bytes_transferred_total',
    'Total bytes transferred during sync operations',
    ['client', 'direction']  # direction: upload, download
)

# ============================================================================
# CONFLICT RESOLUTION METRICS
# ============================================================================

conflicts_detected = Counter(
    'conflicts_detected_total',
    'Total conflicts detected',
    ['client', 'table', 'type']  # type: update_conflict, delete_conflict, etc.
)

conflicts_resolved = Counter(
    'conflicts_resolved_total',
    'Total conflicts resolved',
    ['client', 'strategy']  # strategy: newest_wins, source_wins, target_wins, merge, manual
)

conflicts_unresolved = Gauge(
    'conflicts_unresolved',
    'Number of conflicts requiring manual resolution',
    ['client']
)

conflict_resolution_duration_seconds = Histogram(
    'conflict_resolution_duration_seconds',
    'Time taken to resolve conflicts',
    ['strategy'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10]
)

# ============================================================================
# HIGH AVAILABILITY METRICS
# ============================================================================

leader_elections_total = Counter(
    'leader_elections_total',
    'Total leader elections',
    ['result']  # result: acquired, renewed, lost, failed
)

is_leader = Gauge(
    'sync_container_is_leader',
    'Whether this container is currently the leader (1=yes, 0=no)',
    ['node_id', 'cluster']
)

leader_lease_expires_timestamp = Gauge(
    'leader_lease_expires_timestamp',
    'Unix timestamp when current leader lease expires',
    ['cluster']
)

heartbeat_failures_total = Counter(
    'heartbeat_failures_total',
    'Total heartbeat failures',
    ['node_id']
)

failover_events_total = Counter(
    'failover_events_total',
    'Total failover events',
    ['from_node', 'to_node', 'reason']
)

# ============================================================================
# STATE MANAGEMENT METRICS
# ============================================================================

state_cache_hits_total = Counter(
    'state_cache_hits_total',
    'Total cache hits for state queries'
)

state_cache_misses_total = Counter(
    'state_cache_misses_total',
    'Total cache misses for state queries'
)

state_cache_invalidations_total = Counter(
    'state_cache_invalidations_total',
    'Total cache invalidations',
    ['reason']  # reason: update, expiry, manual
)

state_sync_lag_seconds = Gauge(
    'state_sync_lag_seconds',
    'Time since last state sync with Supabase',
    ['host_id']
)

state_cache_size = Gauge(
    'state_cache_size',
    'Number of items in state cache'
)

# ============================================================================
# DATABASE METRICS
# ============================================================================

db_pool_size = Gauge(
    'db_pool_size',
    'Current database connection pool size',
    ['pool_name']
)

db_pool_available = Gauge(
    'db_pool_available',
    'Available database connections in pool',
    ['pool_name']
)

db_queries_total = Counter(
    'db_queries_total',
    'Total database queries executed',
    ['query_type', 'status']  # query_type: select, insert, update, status: success, error
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

# ============================================================================
# SYNC JOB QUEUE METRICS
# ============================================================================

sync_queue_size = Gauge(
    'sync_queue_size',
    'Number of jobs in sync queue'
)

sync_queue_processing_time_seconds = Histogram(
    'sync_queue_processing_time_seconds',
    'Time jobs spend in queue before processing',
    buckets=[1, 5, 10, 30, 60, 300, 600]
)

sync_jobs_active = Gauge(
    'sync_jobs_active',
    'Number of currently running sync jobs'
)

# ============================================================================
# ERROR METRICS
# ============================================================================

errors_total = Counter(
    'errors_total',
    'Total errors encountered',
    ['component', 'error_type']
)

# ============================================================================
# SYSTEM HEALTH METRICS
# ============================================================================

container_uptime_seconds = Gauge(
    'container_uptime_seconds',
    'Container uptime in seconds',
    ['node_id']
)

last_successful_sync_timestamp = Gauge(
    'last_successful_sync_timestamp',
    'Unix timestamp of last successful sync',
    ['client']
)

# ============================================================================
# INSTRUMENTATION SETUP
# ============================================================================

def setup_metrics(app):
    """
    Set up Prometheus metrics instrumentation for FastAPI app.

    This function:
    1. Instruments all FastAPI endpoints with standard metrics
    2. Exposes /metrics endpoint for Prometheus scraping
    3. Adds custom metrics defined above

    Args:
        app: FastAPI application instance
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=False,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Instrument the app
    instrumentator.instrument(app)

    # Expose metrics endpoint
    instrumentator.expose(app, endpoint="/metrics")

    return instrumentator


def record_sync_operation(client: str, status: str, duration: float, rows: int, table: str):
    """
    Record metrics for a sync operation.

    Args:
        client: Client name
        status: Operation status (success, failed, cancelled)
        duration: Operation duration in seconds
        rows: Number of rows processed
        table: Table name
    """
    sync_operations_total.labels(client=client, status=status).inc()
    sync_duration_seconds.labels(client=client).observe(duration)

    if status == "success":
        sync_rows_processed.labels(client=client, table=table).inc(rows)
        last_successful_sync_timestamp.labels(client=client).set_to_current_time()


def record_conflict(client: str, table: str, conflict_type: str, strategy: str, resolution_time: float):
    """
    Record metrics for a conflict resolution.

    Args:
        client: Client name
        table: Table name
        conflict_type: Type of conflict
        strategy: Resolution strategy used
        resolution_time: Time taken to resolve in seconds
    """
    conflicts_detected.labels(client=client, table=table, type=conflict_type).inc()
    conflicts_resolved.labels(client=client, strategy=strategy).inc()
    conflict_resolution_duration_seconds.labels(strategy=strategy).observe(resolution_time)


def record_leader_election(node_id: str, cluster: str, result: str, is_leader_now: bool):
    """
    Record metrics for leader election.

    Args:
        node_id: Node identifier
        cluster: Cluster name
        result: Election result (acquired, renewed, lost, failed)
        is_leader_now: Whether this node is now the leader
    """
    leader_elections_total.labels(result=result).inc()
    is_leader.labels(node_id=node_id, cluster=cluster).set(1 if is_leader_now else 0)


def record_cache_operation(hit: bool):
    """
    Record cache hit or miss.

    Args:
        hit: True if cache hit, False if cache miss
    """
    if hit:
        state_cache_hits_total.inc()
    else:
        state_cache_misses_total.inc()


def update_db_pool_metrics(pool_name: str, size: int, available: int):
    """
    Update database pool metrics.

    Args:
        pool_name: Name of the connection pool
        size: Total pool size
        available: Available connections
    """
    db_pool_size.labels(pool_name=pool_name).set(size)
    db_pool_available.labels(pool_name=pool_name).set(available)


# ============================================================================
# METRIC COLLECTION HELPERS
# ============================================================================

class MetricsContext:
    """
    Context manager for collecting metrics around operations.

    Usage:
        with MetricsContext('sync_operation', client='acme-corp'):
            # perform sync operation
            pass
    """

    def __init__(self, operation_type: str, **labels):
        self.operation_type = operation_type
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time

        if self.operation_type == 'sync':
            status = 'success' if exc_type is None else 'failed'
            client = self.labels.get('client', 'unknown')
            sync_operations_total.labels(client=client, status=status).inc()
            sync_duration_seconds.labels(client=client).observe(duration)

        elif self.operation_type == 'db_query':
            query_type = self.labels.get('query_type', 'unknown')
            status = 'success' if exc_type is None else 'error'
            db_queries_total.labels(query_type=query_type, status=status).inc()
            db_query_duration_seconds.labels(query_type=query_type).observe(duration)

        return False  # Don't suppress exceptions
