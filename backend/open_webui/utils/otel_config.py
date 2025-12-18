"""
OpenTelemetry Configuration and Initialization Module

This module provides configuration and initialization for OpenTelemetry integration
with OpenShift Observe. It is designed to be:
- Non-intrusive: Can be completely disabled via environment variable
- Scalable: Thread-safe and async-safe for high concurrency
- Distributed-ready: Works across multiple pods/replicas
- Zero-impact: No performance degradation when enabled
- Production-ready: Proper error handling and graceful degradation
"""

import logging
import os
import threading
from typing import Dict, Optional

log = logging.getLogger(__name__)

# Thread-safe initialization flag
_otel_initialized = False
_otel_init_lock = threading.Lock()


def is_otel_enabled() -> bool:
    """
    Check if OpenTelemetry is enabled via environment variable.
    
    Returns:
        bool: True if OTEL_ENABLED=true, False otherwise
    """
    from open_webui.env import OTEL_ENABLED
    return OTEL_ENABLED


def get_otel_config() -> Dict:
    """
    Get OpenTelemetry configuration from environment variables.
    
    Returns:
        dict: Configuration dictionary with:
            - enabled: bool
            - service_name: str
            - service_version: str
            - otlp_endpoint: str
            - otlp_protocol: str ("grpc" or "http/protobuf")
            - sampling_ratio: float (0.0-1.0)
            - resource_attributes: dict
    """
    from open_webui.env import (
        OTEL_ENABLED,
        OTEL_SERVICE_NAME,
        OTEL_SERVICE_VERSION,
        OTEL_EXPORTER_OTLP_ENDPOINT,
        OTEL_EXPORTER_OTLP_PROTOCOL,
        OTEL_TRACES_SAMPLER,
        OTEL_TRACES_SAMPLER_ARG,
        OTEL_LOGS_EXPORTER,
        OTEL_METRICS_EXPORTER,
        ENV,
    )
    
    return {
        "enabled": OTEL_ENABLED,
        "service_name": OTEL_SERVICE_NAME,
        "service_version": OTEL_SERVICE_VERSION,
        "otlp_endpoint": OTEL_EXPORTER_OTLP_ENDPOINT,
        "otlp_protocol": OTEL_EXPORTER_OTLP_PROTOCOL,
        "sampling_ratio": OTEL_TRACES_SAMPLER_ARG,
        "sampler": OTEL_TRACES_SAMPLER,
        "logs_exporter": OTEL_LOGS_EXPORTER,
        "metrics_exporter": OTEL_METRICS_EXPORTER,
        "environment": ENV,
        "resource_attributes": get_resource_attributes(),
    }


def get_resource_attributes() -> Dict[str, str]:
    """
    Get resource attributes for OpenTelemetry resource.
    
    Automatically detects Kubernetes pod and namespace information if available.
    
    Returns:
        dict: Resource attributes including:
            - service.name
            - service.version
            - deployment.environment (dev/test/prod)
            - k8s.pod.name (if available)
            - k8s.namespace.name (if available)
    """
    from open_webui.env import (
        OTEL_SERVICE_NAME,
        OTEL_SERVICE_VERSION,
        ENV,
    )
    
    attributes = {
        "service.name": OTEL_SERVICE_NAME,
        "service.version": OTEL_SERVICE_VERSION,
        "deployment.environment": ENV,
    }
    
    # Detect Kubernetes pod name (from downward API or env var)
    pod_name = os.environ.get("HOSTNAME") or os.environ.get("K8S_POD_NAME")
    if pod_name:
        attributes["k8s.pod.name"] = pod_name
    
    # Detect Kubernetes namespace (from env var or downward API)
    namespace = os.environ.get("K8S_NAMESPACE") or os.environ.get("POD_NAMESPACE")
    if namespace:
        attributes["k8s.namespace.name"] = namespace
    
    return attributes


def initialize_otel() -> bool:
    """
    Initialize OpenTelemetry SDK.
    
    This function:
    1. Checks if OTEL is enabled (early return if disabled)
    2. Imports OTEL SDK (handles ImportError gracefully)
    3. Creates Resource with attributes
    4. Configures OTLP exporter (BatchSpanProcessor for async, non-blocking)
    5. Sets TracerProvider and MeterProvider
    6. Returns success status
    
    The initialization is idempotent - calling it multiple times is safe.
    
    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    global _otel_initialized
    
    # Early return if disabled
    if not is_otel_enabled():
        log.debug("OpenTelemetry is disabled via OTEL_ENABLED environment variable")
        return False
    
    # Thread-safe check for already initialized
    with _otel_init_lock:
        if _otel_initialized:
            log.debug("OpenTelemetry already initialized, skipping")
            return True
        
        try:
            # Import OTEL SDK components (handle ImportError gracefully)
            from opentelemetry import trace, metrics
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            
            log.info("Initializing OpenTelemetry SDK...")
            
            # Get configuration
            config = get_otel_config()
            
            # Create resource with attributes
            resource = Resource.create(config["resource_attributes"])
            
            # Configure OTLP exporter based on protocol
            if config["otlp_protocol"] == "grpc":
                # gRPC exporter (default, recommended for sidecar pattern)
                span_exporter = OTLPSpanExporter(
                    endpoint=config["otlp_endpoint"],
                    insecure=True,  # Sidecar is localhost, no TLS needed
                )
                metric_exporter = OTLPMetricExporter(
                    endpoint=config["otlp_endpoint"],
                    insecure=True,
                )
            elif config["otlp_protocol"] in ("http/protobuf", "http"):
                # HTTP/protobuf exporter
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
                
                span_exporter = HTTPSpanExporter(
                    endpoint=config["otlp_endpoint"],
                )
                metric_exporter = HTTPMetricExporter(
                    endpoint=config["otlp_endpoint"],
                )
            else:
                log.warning(
                    f"Unsupported OTEL_EXPORTER_OTLP_PROTOCOL: {config['otlp_protocol']}. "
                    f"Using 'grpc' as default."
                )
                span_exporter = OTLPSpanExporter(
                    endpoint=config["otlp_endpoint"],
                    insecure=True,
                )
                metric_exporter = OTLPMetricExporter(
                    endpoint=config["otlp_endpoint"],
                    insecure=True,
                )
            
            # Configure sampling
            # Use parent-based trace ID ratio sampler for distributed tracing
            if config["sampler"] == "parentbased_traceidratio":
                from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
            
                sampler = ParentBasedTraceIdRatio(config["sampling_ratio"])
            elif config["sampler"] == "traceidratio":
                from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
            
                sampler = TraceIdRatioBased(config["sampling_ratio"])
            elif config["sampler"] == "always_on":
                from opentelemetry.sdk.trace.sampling import ALWAYS_ON
            
                sampler = ALWAYS_ON
            elif config["sampler"] == "always_off":
                from opentelemetry.sdk.trace.sampling import ALWAYS_OFF
            
                sampler = ALWAYS_OFF
            else:
                log.warning(
                    f"Unknown OTEL_TRACES_SAMPLER: {config['sampler']}. "
                    f"Using 'parentbased_traceidratio' as default."
                )
                from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
            
                sampler = ParentBasedTraceIdRatio(config["sampling_ratio"])
            
            # Create TracerProvider with resource and sampler
            tracer_provider = TracerProvider(
                resource=resource,
                sampler=sampler,
            )
            
            # Add BatchSpanProcessor (async-safe, non-blocking)
            # BatchSpanProcessor batches spans and exports them in background
            # This ensures zero blocking of the main application thread
            span_processor = BatchSpanProcessor(
                span_exporter=span_exporter,
                # Default batch settings are good for high-throughput scenarios
                # max_queue_size: 2048 (default)
                # export_timeout_millis: 30000 (default)
                # schedule_delay_millis: 5000 (default)
            )
            tracer_provider.add_span_processor(span_processor)
            
            # Set global TracerProvider
            trace.set_tracer_provider(tracer_provider)
            
            # Create MeterProvider for metrics
            # Note: PeriodicExportingMetricReader takes 'exporter' as keyword argument
            metric_reader = PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=60000,  # Export metrics every 60 seconds
            )
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )
            
            # Set global MeterProvider
            metrics.set_meter_provider(meter_provider)
            
            _otel_initialized = True
            log.info(
                f"OpenTelemetry initialized successfully: "
                f"service={config['service_name']}, "
                f"version={config['service_version']}, "
                f"endpoint={config['otlp_endpoint']}, "
                f"protocol={config['otlp_protocol']}, "
                f"sampling={config['sampling_ratio']}"
            )
            return True
            
        except ImportError as e:
            log.warning(
                f"OpenTelemetry packages not available: {e}. "
                f"Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc"
            )
            return False
        except Exception as e:
            log.warning(
                f"OpenTelemetry initialization failed: {e}",
                exc_info=True,
            )
            return False


def shutdown_otel() -> None:
    """
    Shutdown OpenTelemetry SDK and flush remaining spans/metrics.
    
    This should be called during application shutdown to ensure
    all pending telemetry data is exported.
    """
    global _otel_initialized
    
    if not _otel_initialized:
        return
    
    try:
        from opentelemetry import trace, metrics
        
        # Flush and shutdown TracerProvider
        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, "shutdown"):
            tracer_provider.shutdown()
        
        # Shutdown MeterProvider
        meter_provider = metrics.get_meter_provider()
        if hasattr(meter_provider, "shutdown"):
            meter_provider.shutdown()
        
        log.info("OpenTelemetry SDK shutdown completed")
        _otel_initialized = False
        
    except Exception as e:
        log.warning(f"Error during OpenTelemetry shutdown: {e}", exc_info=True)


# Thread-safe instrumentation flags
_fastapi_instrumented = False
_fastapi_instrument_lock = threading.Lock()
_requests_instrumented = False
_requests_instrument_lock = threading.Lock()


def instrument_fastapi(app) -> bool:
    """
    Instrument FastAPI application for automatic tracing.
    
    This function automatically creates spans for all HTTP requests to FastAPI endpoints.
    It captures request method, path, status code, and duration.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        bool: True if instrumentation succeeded, False otherwise
    """
    global _fastapi_instrumented
    
    # Early return if OTEL is disabled
    if not is_otel_enabled():
        log.debug("FastAPI instrumentation skipped (OTEL disabled)")
        return False
    
    # Check if instrumentation is explicitly disabled
    from open_webui.env import OTEL_INSTRUMENTATION_FASTAPI_ENABLED
    if not OTEL_INSTRUMENTATION_FASTAPI_ENABLED:
        log.debug("FastAPI instrumentation disabled via OTEL_INSTRUMENTATION_FASTAPI_ENABLED")
        return False
    
    # Thread-safe check for already instrumented
    with _fastapi_instrument_lock:
        if _fastapi_instrumented:
            log.debug("FastAPI already instrumented, skipping")
            return True
        
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from open_webui.env import (
                OTEL_INSTRUMENTATION_FASTAPI_EXCLUDED_PATHS,
                OTEL_INSTRUMENTATION_FASTAPI_CAPTURE_HEADERS,
            )
            
            log.info("Instrumenting FastAPI application...")
            
            # Configure excluded paths
            # OpenTelemetry expects a comma-separated string, not a list
            excluded_urls = OTEL_INSTRUMENTATION_FASTAPI_EXCLUDED_PATHS
            if excluded_urls:
                if isinstance(excluded_urls, list):
                    excluded_urls = ",".join(excluded_urls)
                elif not isinstance(excluded_urls, str):
                    excluded_urls = str(excluded_urls)
            
            # Instrument FastAPI app
            # FastAPIInstrumentor.instrument() is idempotent by default
            FastAPIInstrumentor.instrument_app(
                app,
                excluded_urls=excluded_urls if excluded_urls else None,
                # Don't capture headers by default (sensitive data)
                # Can be configured via OTEL_INSTRUMENTATION_FASTAPI_CAPTURE_HEADERS if needed
            )
            
            _fastapi_instrumented = True
            log.info(
                f"FastAPI auto-instrumentation enabled "
                f"(excluded paths: {excluded_urls if excluded_urls else 'none'})"
            )
            return True
            
        except ImportError as e:
            log.warning(
                f"FastAPI instrumentation package not available: {e}. "
                f"Install with: pip install opentelemetry-instrumentation-fastapi"
            )
            return False
        except Exception as e:
            log.warning(
                f"FastAPI instrumentation failed: {e}",
                exc_info=True,
            )
            return False


def instrument_requests() -> bool:
    """
    Instrument requests library for automatic HTTP tracing.
    
    This function automatically creates spans for all HTTP calls made using
    the requests library. Spans are linked as children of parent FastAPI spans.
    
    Returns:
        bool: True if instrumentation succeeded, False otherwise
    """
    global _requests_instrumented
    
    # Early return if OTEL is disabled
    if not is_otel_enabled():
        log.debug("Requests instrumentation skipped (OTEL disabled)")
        return False
    
    # Check if instrumentation is explicitly disabled
    from open_webui.env import OTEL_INSTRUMENTATION_REQUESTS_ENABLED
    if not OTEL_INSTRUMENTATION_REQUESTS_ENABLED:
        log.debug("Requests instrumentation disabled via OTEL_INSTRUMENTATION_REQUESTS_ENABLED")
        return False
    
    # Thread-safe check for already instrumented
    with _requests_instrument_lock:
        if _requests_instrumented:
            log.debug("Requests library already instrumented, skipping")
            return True
        
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            
            log.info("Instrumenting requests library...")
            
            # Instrument requests library
            # RequestsInstrumentor.instrument() is idempotent by default
            RequestsInstrumentor().instrument()
            
            _requests_instrumented = True
            log.info("Requests library auto-instrumentation enabled")
            return True
            
        except ImportError as e:
            log.warning(
                f"Requests instrumentation package not available: {e}. "
                f"Install with: pip install opentelemetry-instrumentation-requests"
            )
            return False
        except Exception as e:
            log.warning(
                f"Requests instrumentation failed: {e}",
                exc_info=True,
            )
            return False
