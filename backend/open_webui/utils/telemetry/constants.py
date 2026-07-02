from opentelemetry.semconv._incubating.attributes import (
    db_attributes as _db,
)
from opentelemetry.semconv._incubating.attributes import (
    http_attributes as _http,
)

# Span Tags
SPAN_DB_TYPE = 'mysql'
SPAN_REDIS_TYPE = 'redis'
SPAN_DURATION = 'duration'
SPAN_SQL_STR = 'sql'
SPAN_SQL_EXPLAIN = 'explain'
SPAN_ERROR_TYPE = 'error'


class SpanAttributes:
    """Span attribute keys used by the telemetry instrumentors.

    Legacy semconv keys (http.* and db.*) are sourced from the `_incubating`
    attribute modules, which still define these exact string values.
    `opentelemetry.semconv.trace.SpanAttributes` (previously subclassed here)
    is deprecated since semconv 1.25.0, and the *stable* http module renamed
    the keys (e.g. `http.request.method`), so only the incubating module keeps
    the original `http.method` / `http.url` / `http.status_code` / `db.*` values.
    Sourcing from it keeps emitted span attribute keys unchanged.
    """

    # HTTP — legacy keys retained in the incubating module
    HTTP_URL = _http.HTTP_URL  # 'http.url'
    HTTP_METHOD = _http.HTTP_METHOD  # 'http.method'
    HTTP_STATUS_CODE = _http.HTTP_STATUS_CODE  # 'http.status_code'

    # DB — incubating semconv keys
    DB_NAME = _db.DB_NAME  # 'db.name'
    DB_STATEMENT = _db.DB_STATEMENT  # 'db.statement'
    DB_OPERATION = _db.DB_OPERATION  # 'db.operation'

    # Open WebUI custom keys (not part of semconv)
    DB_INSTANCE = 'db.instance'
    DB_TYPE = 'db.type'
    DB_IP = 'db.ip'
    DB_PORT = 'db.port'
    ERROR_KIND = 'error.kind'
    ERROR_OBJECT = 'error.object'
    ERROR_MESSAGE = 'error.message'
    RESULT_CODE = 'result.code'
    RESULT_MESSAGE = 'result.message'
    RESULT_ERRORS = 'result.errors'
