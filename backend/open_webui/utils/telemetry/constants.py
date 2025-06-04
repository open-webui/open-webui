from opentelemetry.semconv.trace import SpanAttributes as _SpanAttributes

# Span Tags
SPAN_DB_TYPE = "mysql"
SPAN_REDIS_TYPE = "redis"
SPAN_DURATION = "duration"
SPAN_SQL_STR = "sql"
SPAN_SQL_EXPLAIN = "explain"
SPAN_ERROR_TYPE = "error"


class SpanAttributes(_SpanAttributes):
    """
    Span Attributes
    """

    DB_INSTANCE = "db.instance"
    DB_TYPE = "db.type"
    DB_IP = "db.ip"
    DB_PORT = "db.port"
    ERROR_KIND = "error.kind"
    ERROR_OBJECT = "error.object"
    ERROR_MESSAGE = "error.message"
    RESULT_CODE = "result.code"
    RESULT_MESSAGE = "result.message"
    RESULT_ERRORS = "result.errors"
