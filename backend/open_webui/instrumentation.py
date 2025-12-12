import os
from opentelemetry.metrics import set_meter_provider, get_meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

## Can't import/use open_webui.config here to avoid NoOpMeter issue.
INSTRUMENTATION_SERVICE_NAME = os.environ.get(
    "INSTRUMENTATION_SERVICE_NAME", "canchat-service"
)
INSTRUMENTATION_METER_NAME = os.environ.get(
    "INSTRUMENTATION_METER_NAME", "canchat-meter"
)
INSTRUMENTATION_ENDPOINT = os.environ.get(
    "INSTRUMENTATION_ENDPOINT", "http://localhost:4318/v1/metrics"
)
INSTRUMENTATION_EXPORT_INTERVAL_MS = int(
    os.environ.get("INSTRUMENTATION_EXPORT_INTERVAL_MS", "5000")
)

resource = Resource.create(
    {
        "service.name": INSTRUMENTATION_SERVICE_NAME,
    }
)

readers = [
    PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=INSTRUMENTATION_ENDPOINT),
        export_interval_millis=INSTRUMENTATION_EXPORT_INTERVAL_MS,
    ),
]

meter_provider = MeterProvider(resource=resource, metric_readers=readers)

set_meter_provider(meter_provider)

meter = get_meter(INSTRUMENTATION_METER_NAME)
