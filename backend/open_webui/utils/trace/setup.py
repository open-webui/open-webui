from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

from open_webui.utils.trace.exporters import LazyBatchSpanProcessor
from open_webui.utils.trace.instrumentors import Instrumentor
from open_webui.env import OT_SERVICE_NAME, OT_HOST, OT_TOKEN


def setup(app):
    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create(
                {SERVICE_NAME: OT_SERVICE_NAME, "token": OT_TOKEN}
            ),
            sampler=ALWAYS_ON,
        )
    )
    # otlp
    exporter = OTLPSpanExporter(endpoint=OT_HOST)
    trace.get_tracer_provider().add_span_processor(LazyBatchSpanProcessor(exporter))
    Instrumentor(app=app).instrument()
