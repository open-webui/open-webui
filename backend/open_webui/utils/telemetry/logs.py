import logging
from base64 import b64encode
from opentelemetry.sdk._logs import (
    LoggingHandler,
    LoggerProvider,
)
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HttpOTLPLogExporter,
)
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from open_webui.env import (
    OTEL_SERVICE_NAME,
    OTEL_LOGS_EXPORTER_OTLP_ENDPOINT,
    OTEL_LOGS_EXPORTER_OTLP_INSECURE,
    OTEL_LOGS_BASIC_AUTH_USERNAME,
    OTEL_LOGS_BASIC_AUTH_PASSWORD,
    OTEL_LOGS_OTLP_SPAN_EXPORTER,
)


def setup_logging():
    headers = []
    if OTEL_LOGS_BASIC_AUTH_USERNAME and OTEL_LOGS_BASIC_AUTH_PASSWORD:
        auth_string = f"{OTEL_LOGS_BASIC_AUTH_USERNAME}:{OTEL_LOGS_BASIC_AUTH_PASSWORD}"
        auth_header = b64encode(auth_string.encode()).decode()
        headers = [("authorization", f"Basic {auth_header}")]
    resource = Resource.create(attributes={SERVICE_NAME: OTEL_SERVICE_NAME})

    if OTEL_LOGS_OTLP_SPAN_EXPORTER == "http":
        exporter = HttpOTLPLogExporter(
            endpoint=OTEL_LOGS_EXPORTER_OTLP_ENDPOINT,
            headers=headers,
        )
    else:
        exporter = OTLPLogExporter(
            endpoint=OTEL_LOGS_EXPORTER_OTLP_ENDPOINT,
            insecure=OTEL_LOGS_EXPORTER_OTLP_INSECURE,
            headers=headers,
        )
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    otel_handler = LoggingHandler(logger_provider=logger_provider)

    return otel_handler


otel_handler = setup_logging()
