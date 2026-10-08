"""OBS-03: validate logging bridges and HTTPX coverage without backend startup."""

import asyncio
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind


@pytest.mark.parametrize("bridge", ["sdk", "instrumentation"])
def test_logging_handler_exports_correlated_otlp_logs(monkeypatch, bridge):
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    handler_class = LoggingHandler
    if bridge == "instrumentation":
        handler_class = pytest.importorskip(
            "opentelemetry.instrumentation.logging.handler"
        ).LoggingHandler
    received = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = self.rfile.read(int(self.headers["Content-Length"]))
            received.append(
                (
                    self.path,
                    self.headers["Content-Type"],
                    ExportLogsServiceRequest.FromString(payload),
                )
            )
            self.send_response(200)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Receiver)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    provider = LoggerProvider(resource=Resource.create({"service.name": "obs03-poc"}))
    provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"http://127.0.0.1:{server.server_port}/v1/logs",
                timeout=5,
            )
        )
    )
    handler = handler_class(level=logging.INFO, logger_provider=provider)
    logger = logging.Logger("obs03-poc", level=logging.INFO)
    logger.addHandler(handler)
    traces = TracerProvider()
    try:
        with traces.get_tracer("obs03-poc").start_as_current_span(
            "bridge-check"
        ) as span:
            context = span.get_span_context()
            logger.info("bridge-check", extra={"event": "obs03.bridge"})
        assert provider.force_flush(timeout_millis=5000)
        assert len(received) == 1
        path, content_type, request = received[0]
        assert path == "/v1/logs"
        assert content_type == "application/x-protobuf"
        resource_logs = request.resource_logs[0]
        resource = {
            item.key: item.value.string_value
            for item in resource_logs.resource.attributes
        }
        assert resource["service.name"] == "obs03-poc"
        records = resource_logs.scope_logs[0].log_records
        assert len(records) == 1
        record = records[0]
        assert record.body.string_value == "bridge-check"
        assert record.severity_text == "INFO"
        assert int.from_bytes(record.trace_id, "big") == context.trace_id
        assert int.from_bytes(record.span_id, "big") == context.span_id
        attributes = {item.key: item.value.string_value for item in record.attributes}
        assert attributes["event"] == "obs03.bridge"
    finally:
        logger.removeHandler(handler)
        handler.close()
        provider.shutdown()
        traces.shutdown()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize("is_async", [False, True])
def test_httpx_instrumentor_covers_sync_and_async_clients(monkeypatch, is_async):
    instrumentor = pytest.importorskip("opentelemetry.instrumentation.httpx")
    import httpx

    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"status": True})

    async def call_async():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            instrumentor.HTTPXClientInstrumentor.instrument_client(
                client, tracer_provider=provider
            )
            try:
                response = await client.get("http://127.0.0.1/obs03")
                assert response.status_code == 200
            finally:
                instrumentor.HTTPXClientInstrumentor.uninstrument_client(client)

    try:
        if is_async:
            asyncio.run(call_async())
        else:
            with httpx.Client(transport=httpx.MockTransport(respond)) as client:
                instrumentor.HTTPXClientInstrumentor.instrument_client(
                    client, tracer_provider=provider
                )
                try:
                    assert client.get("http://127.0.0.1/obs03").status_code == 200
                finally:
                    instrumentor.HTTPXClientInstrumentor.uninstrument_client(client)
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].kind == SpanKind.CLIENT
        assert len(requests) == 1
        assert requests[0].headers["traceparent"].split("-")[1] == format(
            spans[0].context.trace_id, "032x"
        )
    finally:
        provider.shutdown()
