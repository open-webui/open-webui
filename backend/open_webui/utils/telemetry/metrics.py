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
from base64 import b64encode

from fastapi import FastAPI, Request
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)

from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as OTLPHttpMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

from open_webui.env import (
    OTEL_SERVICE_NAME,
    OTEL_METRICS_EXPORTER_OTLP_ENDPOINT,
    OTEL_METRICS_BASIC_AUTH_USERNAME,
    OTEL_METRICS_BASIC_AUTH_PASSWORD,
    OTEL_METRICS_OTLP_SPAN_EXPORTER,
    OTEL_METRICS_EXPORTER_OTLP_INSECURE,
)
from open_webui.socket.main import get_active_user_ids
from open_webui.models.users import Users

_EXPORT_INTERVAL_MILLIS = 10_000  # 10 seconds


def _build_meter_provider(resource: Resource) -> MeterProvider:
    """Return a configured MeterProvider."""
    headers = []
    if OTEL_METRICS_BASIC_AUTH_USERNAME and OTEL_METRICS_BASIC_AUTH_PASSWORD:
        auth_string = (
            f"{OTEL_METRICS_BASIC_AUTH_USERNAME}:{OTEL_METRICS_BASIC_AUTH_PASSWORD}"
        )
        auth_header = b64encode(auth_string.encode()).decode()
        headers = [("authorization", f"Basic {auth_header}")]

    # Periodic reader pushes metrics over OTLP/gRPC to collector
    if OTEL_METRICS_OTLP_SPAN_EXPORTER == "http":
        readers: List[PeriodicExportingMetricReader] = [
            PeriodicExportingMetricReader(
                OTLPHttpMetricExporter(
                    endpoint=OTEL_METRICS_EXPORTER_OTLP_ENDPOINT, headers=headers
                ),
                export_interval_millis=_EXPORT_INTERVAL_MILLIS,
            )
        ]
    else:
        readers: List[PeriodicExportingMetricReader] = [
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=OTEL_METRICS_EXPORTER_OTLP_ENDPOINT,
                    insecure=OTEL_METRICS_EXPORTER_OTLP_INSECURE,
                    headers=headers,
                ),
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
        View(
            instrument_name="webui.users.total",
        ),
        View(
            instrument_name="webui.users.active",
        ),
    ]

    provider = MeterProvider(
        resource=resource,
        metric_readers=list(readers),
        views=views,
    )
    return provider


def setup_metrics(app: FastAPI, resource: Resource) -> None:
    """Attach OTel metrics middleware to *app* and initialise provider."""

    metrics.set_meter_provider(_build_meter_provider(resource))
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

    def observe_active_users(
        options: metrics.CallbackOptions,
    ) -> Sequence[metrics.Observation]:
        return [
            metrics.Observation(
                value=len(get_active_user_ids()),
            )
        ]

    def observe_total_registered_users(
        options: metrics.CallbackOptions,
    ) -> Sequence[metrics.Observation]:
        return [
            metrics.Observation(
                value=len(Users.get_users()["users"]),
            )
        ]

    meter.create_observable_gauge(
        name="webui.users.total",
        description="Total number of registered users",
        unit="users",
        callbacks=[observe_total_registered_users],
    )

    meter.create_observable_gauge(
        name="webui.users.active",
        description="Number of currently active users",
        unit="users",
        callbacks=[observe_active_users],
    )

    # FastAPI middleware
    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next):
        start_time = time.perf_counter()

        status_code = None
        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", 500)
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Route template e.g. "/items/{item_id}" instead of real path.
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)

            attrs: Dict[str, str | int] = {
                "http.method": request.method,
                "http.route": route_path,
                "http.status_code": status_code,
            }

            request_counter.add(1, attrs)
            duration_histogram.record(elapsed_ms, attrs)
