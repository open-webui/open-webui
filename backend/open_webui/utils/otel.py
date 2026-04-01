try:
    from opentelemetry import trace as trace  # noqa: F401
except Exception:
    class _SpanContext:
        is_valid = False
        trace_id = 0
        span_id = 0

    class _Span:
        def get_span_context(self):
            return _SpanContext()

        def set_attribute(self, key, value):
            return None

    class _TraceModule:
        @staticmethod
        def get_current_span():
            return _Span()

        @staticmethod
        def format_trace_id(trace_id):
            return ""

        @staticmethod
        def format_span_id(span_id):
            return ""

    trace = _TraceModule()
