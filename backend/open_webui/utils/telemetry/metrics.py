"""OpenTelemetry metrics bootstrap for Open WebUI.

This module initialises a MeterProvider that sends metrics to an OTLP
collector. The collector is responsible for exposing a Prometheus
`/metrics` endpoint – WebUI does **not** expose it directly.

Metrics collected:

* http.server.requests (counter)
* http.server.duration (histogram, milliseconds)

Attributes used: http.method, http.route, http.status_code

If you wish to add more attributes (e.g. user-agent) you can, but beware of
high-cardinality label sets.
"""

from __future__ import annotations

import time
from typing import Dict, List, Sequence, Any

from fastapi import FastAPI, Request
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from open_webui.env import OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT


_EXPORT_INTERVAL_MILLIS = 10_000  # 10 seconds


def _build_meter_provider() -> MeterProvider:
    """Return a configured MeterProvider."""

    # Periodic reader pushes metrics over OTLP/gRPC to collector
    readers: List[PeriodicExportingMetricReader] = [
        PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT),
            export_interval_millis=_EXPORT_INTERVAL_MILLIS,
        )
    ]

    # Optional view to limit cardinality: drop user-agent etc.
    views: List[View] = [
        View(
            instrument_name="http.server.duration",
            attribute_keys=["http.method", "http.route", "http.status_code"],
        ),
        View(
            instrument_name="http.server.requests",
            attribute_keys=["http.method", "http.route", "http.status_code"],
        ),
    ]

    provider = MeterProvider(
        resource=Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME}),
        metric_readers=list(readers),
        views=views,
    )
    return provider


def setup_metrics(app: FastAPI) -> None:
    """Attach OTel metrics middleware to *app* and initialise provider."""

    metrics.set_meter_provider(_build_meter_provider())
    meter = metrics.get_meter(__name__)

    # Instruments
    request_counter = meter.create_counter(
        name="http.server.requests",
        description="Total HTTP requests",
        unit="1",
    )
    duration_histogram = meter.create_histogram(
        name="http.server.duration",
        description="HTTP request duration",
        unit="ms",
    )

    # FastAPI middleware
    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Route template e.g. "/items/{item_id}" instead of real path.
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)

        attrs: Dict[str, str | int] = {
            "http.method": request.method,
            "http.route": route_path,
            "http.status_code": response.status_code,
        }

        request_counter.add(1, attrs)
        duration_histogram.record(elapsed_ms, attrs)

        return response
