from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from sqlalchemy import Engine

from open_webui.utils.telemetry.exporters import LazyBatchSpanProcessor
from open_webui.utils.telemetry.instrumentors import Instrumentor
from open_webui.utils.telemetry.metrics import setup_metrics
from open_webui.env import (
    OTEL_SERVICE_NAME,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    ENABLE_OTEL_METRICS,
)


def setup(app: FastAPI, db_engine: Engine):
    # set up trace
    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create(attributes={SERVICE_NAME: OTEL_SERVICE_NAME})
        )
    )
    # otlp export
    exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)
    trace.get_tracer_provider().add_span_processor(LazyBatchSpanProcessor(exporter))
    Instrumentor(app=app, db_engine=db_engine).instrument()

    # set up metrics only if enabled
    if ENABLE_OTEL_METRICS:
        setup_metrics(app)
