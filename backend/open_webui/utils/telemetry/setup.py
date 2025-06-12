from fastapi import FastAPI
from open_webui.utils.telemetry.metrics import initialize_telemetry_metrics
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)
from sqlalchemy import Engine

from open_webui.utils.telemetry.exporters import LazyBatchSpanProcessor
from open_webui.utils.telemetry.instrumentors import Instrumentor
from open_webui.env import OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT


def setup(app: FastAPI, db_engine: Engine):
    resource = Resource.create(attributes={SERVICE_NAME: OTEL_SERVICE_NAME})

    # set up trace
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)
    # otlp export
    span_exporter = OTLPSpanExporter(
        endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True
    )
    trace_provider.add_span_processor(LazyBatchSpanProcessor(span_exporter))
    Instrumentor(app=app, db_engine=db_engine).instrument()

    # set up metrics
    metric_exporter = OTLPMetricExporter(
        endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True
    )
    reader = PeriodicExportingMetricReader(
        exporter=metric_exporter, export_interval_millis=5000
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(OTEL_SERVICE_NAME)
    initialize_telemetry_metrics(meter)
