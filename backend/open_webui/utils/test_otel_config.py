"""
Unit tests for OpenTelemetry configuration module.

Tests cover:
- Configuration retrieval
- Environment variable handling
- Initialization logic
- Error handling
- Idempotency
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestOTELConfig:
    """Test OpenTelemetry configuration functions."""
    
    def test_otel_disabled_by_default(self):
        """Test that OTEL is disabled when env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Reload module to pick up new env vars
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            assert otel_config.is_otel_enabled() is False
    
    def test_otel_enabled_when_env_set(self):
        """Test that OTEL is enabled when OTEL_ENABLED=true."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}, clear=False):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            assert otel_config.is_otel_enabled() is True
    
    def test_otel_enabled_case_insensitive(self):
        """Test that OTEL_ENABLED is case-insensitive."""
        for value in ["TRUE", "True", "true", "tRuE"]:
            with patch.dict(os.environ, {"OTEL_ENABLED": value}, clear=False):
                import importlib
                import open_webui.utils.otel_config as otel_config
                importlib.reload(otel_config)
                
                assert otel_config.is_otel_enabled() is True
    
    def test_get_otel_config_defaults(self):
        """Test that get_otel_config returns correct defaults."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            config = otel_config.get_otel_config()
            
            assert config["enabled"] is False
            assert config["service_name"] == "open-webui"
            assert config["otlp_endpoint"] == "http://localhost:4317"
            assert config["otlp_protocol"] == "grpc"
            assert config["sampling_ratio"] == 1.0
            assert config["sampler"] == "parentbased_traceidratio"
            assert "resource_attributes" in config
    
    def test_get_otel_config_custom(self):
        """Test that custom environment variables are respected."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_SERVICE_NAME": "custom-service",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://custom:4318",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
                "OTEL_TRACES_SAMPLER_ARG": "0.5",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            config = otel_config.get_otel_config()
            
            assert config["enabled"] is True
            assert config["service_name"] == "custom-service"
            assert config["otlp_endpoint"] == "http://custom:4318"
            assert config["otlp_protocol"] == "http/protobuf"
            assert config["sampling_ratio"] == 0.5
    
    def test_get_resource_attributes(self):
        """Test that resource attributes are correctly generated."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            attributes = otel_config.get_resource_attributes()
            
            assert "service.name" in attributes
            assert "service.version" in attributes
            assert "deployment.environment" in attributes
            assert attributes["service.name"] == "open-webui"
    
    def test_get_resource_attributes_k8s(self):
        """Test that Kubernetes attributes are detected when available."""
        with patch.dict(
            os.environ,
            {
                "HOSTNAME": "test-pod-123",
                "K8S_NAMESPACE": "test-namespace",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            attributes = otel_config.get_resource_attributes()
            
            assert "k8s.pod.name" in attributes
            assert "k8s.namespace.name" in attributes
            assert attributes["k8s.pod.name"] == "test-pod-123"
            assert attributes["k8s.namespace.name"] == "test-namespace"
    
    def test_initialize_otel_disabled(self):
        """Test that initialization is skipped when OTEL is disabled."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}, clear=False):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset initialization flag
            otel_config._otel_initialized = False
            
            result = otel_config.initialize_otel()
            
            assert result is False
            assert otel_config._otel_initialized is False
    
    def test_initialize_otel_import_error(self):
        """Test graceful handling of missing OTEL packages."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}, clear=False):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset initialization flag
            otel_config._otel_initialized = False
            
            # Mock ImportError
            with patch("builtins.__import__", side_effect=ImportError("No module named 'opentelemetry'")):
                result = otel_config.initialize_otel()
                
                assert result is False
                assert otel_config._otel_initialized is False
    
    @patch("opentelemetry.trace.set_tracer_provider")
    @patch("opentelemetry.metrics.set_meter_provider")
    @patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter")
    @patch("opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter")
    @patch("opentelemetry.sdk.trace.TracerProvider")
    @patch("opentelemetry.sdk.metrics.MeterProvider")
    def test_initialize_otel_success(self, mock_meter_provider, mock_tracer_provider, 
                                     mock_metric_exporter, mock_span_exporter,
                                     mock_set_meter, mock_set_tracer):
        """Test successful OTEL initialization."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}, clear=False):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset initialization flag
            otel_config._otel_initialized = False
            
            # Mock OTEL SDK components
            mock_tracer_provider_instance = MagicMock()
            mock_tracer_provider.return_value = mock_tracer_provider_instance
            mock_meter_provider_instance = MagicMock()
            mock_meter_provider.return_value = mock_meter_provider_instance
            
            result = otel_config.initialize_otel()
            
            assert result is True
            assert otel_config._otel_initialized is True
            mock_set_tracer.assert_called_once()
            mock_set_meter.assert_called_once()
    
    def test_initialize_otel_idempotent(self):
        """Test that multiple initialization calls are safe (idempotent)."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}, clear=False):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset initialization flag
            otel_config._otel_initialized = False
            
            # Mock successful initialization
            with patch("opentelemetry.trace.set_tracer_provider"), \
                 patch("opentelemetry.metrics.set_meter_provider"), \
                 patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"), \
                 patch("opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter"), \
                 patch("opentelemetry.sdk.trace.TracerProvider"), \
                 patch("opentelemetry.sdk.metrics.MeterProvider"):
                
                # First call
                result1 = otel_config.initialize_otel()
                assert result1 is True
                
                # Second call (should be idempotent)
                result2 = otel_config.initialize_otel()
                assert result2 is True
                
                # Should only initialize once
                assert otel_config._otel_initialized is True
    
    def test_initialize_otel_invalid_sampler(self):
        """Test graceful handling of invalid sampler configuration."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_TRACES_SAMPLER": "invalid_sampler",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset initialization flag
            otel_config._otel_initialized = False
            
            # Mock OTEL SDK components
            with patch("opentelemetry.trace.set_tracer_provider"), \
                 patch("opentelemetry.metrics.set_meter_provider"), \
                 patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"), \
                 patch("opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter"), \
                 patch("opentelemetry.sdk.trace.TracerProvider") as mock_tracer_provider, \
                 patch("opentelemetry.sdk.metrics.MeterProvider"):
                
                mock_tracer_provider_instance = MagicMock()
                mock_tracer_provider.return_value = mock_tracer_provider_instance
                
                # Should still succeed with default sampler
                result = otel_config.initialize_otel()
                assert result is True
    
    def test_initialize_otel_invalid_protocol(self):
        """Test graceful handling of invalid protocol configuration."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "invalid",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset initialization flag
            otel_config._otel_initialized = False
            
            # Mock OTEL SDK components
            with patch("opentelemetry.trace.set_tracer_provider"), \
                 patch("opentelemetry.metrics.set_meter_provider"), \
                 patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"), \
                 patch("opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter"), \
                 patch("opentelemetry.sdk.trace.TracerProvider"), \
                 patch("opentelemetry.sdk.metrics.MeterProvider"):
                
                # Should still succeed with default protocol (grpc)
                result = otel_config.initialize_otel()
                assert result is True
    
    def test_shutdown_otel_not_initialized(self):
        """Test that shutdown is safe when OTEL is not initialized."""
        import importlib
        import open_webui.utils.otel_config as otel_config
        importlib.reload(otel_config)
        
        # Reset initialization flag
        otel_config._otel_initialized = False
        
        # Should not raise exception
        otel_config.shutdown_otel()
    
    @patch("opentelemetry.trace.get_tracer_provider")
    @patch("opentelemetry.metrics.get_meter_provider")
    def test_shutdown_otel_success(self, mock_get_meter, mock_get_tracer):
        """Test successful OTEL shutdown."""
        import importlib
        import open_webui.utils.otel_config as otel_config
        importlib.reload(otel_config)
        
        # Set initialization flag
        otel_config._otel_initialized = True
        
        # Mock providers with shutdown method
        mock_tracer_provider = MagicMock()
        mock_tracer_provider.shutdown = MagicMock()
        mock_get_tracer.return_value = mock_tracer_provider
        
        mock_meter_provider = MagicMock()
        mock_meter_provider.shutdown = MagicMock()
        mock_get_meter.return_value = mock_meter_provider
        
        otel_config.shutdown_otel()
        
        mock_tracer_provider.shutdown.assert_called_once()
        mock_meter_provider.shutdown.assert_called_once()
        assert otel_config._otel_initialized is False


class TestOTELInstrumentation:
    """Test OpenTelemetry instrumentation functions."""
    
    def test_instrument_fastapi_disabled_when_otel_disabled(self):
        """Test that FastAPI instrumentation is skipped when OTEL is disabled."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}, clear=False):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._fastapi_instrumented = False
            
            # Mock FastAPI app
            mock_app = MagicMock()
            
            result = otel_config.instrument_fastapi(mock_app)
            
            assert result is False
            assert otel_config._fastapi_instrumented is False
    
    def test_instrument_fastapi_disabled_when_config_disabled(self):
        """Test that FastAPI instrumentation is skipped when explicitly disabled."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_FASTAPI_ENABLED": "false",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._fastapi_instrumented = False
            
            mock_app = MagicMock()
            
            result = otel_config.instrument_fastapi(mock_app)
            
            assert result is False
    
    @patch("opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument_app")
    def test_instrument_fastapi_success(self, mock_instrument):
        """Test successful FastAPI instrumentation."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_FASTAPI_ENABLED": "true",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._fastapi_instrumented = False
            
            mock_app = MagicMock()
            
            result = otel_config.instrument_fastapi(mock_app)
            
            assert result is True
            assert otel_config._fastapi_instrumented is True
            mock_instrument.assert_called_once()
    
    def test_instrument_fastapi_idempotent(self):
        """Test that FastAPI instrumentation is idempotent."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_FASTAPI_ENABLED": "true",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._fastapi_instrumented = False
            
            mock_app = MagicMock()
            
            with patch("opentelemetry.instrumentation.fastapi.FastAPIInstrumentor.instrument_app"):
                # First call
                result1 = otel_config.instrument_fastapi(mock_app)
                assert result1 is True
                
                # Second call (should be idempotent)
                result2 = otel_config.instrument_fastapi(mock_app)
                assert result2 is True
                
                # Should only instrument once
                assert otel_config._fastapi_instrumented is True
    
    def test_instrument_fastapi_import_error(self):
        """Test graceful handling of missing FastAPI instrumentation package."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_FASTAPI_ENABLED": "true",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._fastapi_instrumented = False
            
            mock_app = MagicMock()
            
            # Mock ImportError
            with patch("builtins.__import__", side_effect=ImportError("No module named 'opentelemetry.instrumentation.fastapi'")):
                result = otel_config.instrument_fastapi(mock_app)
                
                assert result is False
                assert otel_config._fastapi_instrumented is False
    
    def test_instrument_requests_disabled_when_otel_disabled(self):
        """Test that requests instrumentation is skipped when OTEL is disabled."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}, clear=False):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._requests_instrumented = False
            
            result = otel_config.instrument_requests()
            
            assert result is False
            assert otel_config._requests_instrumented is False
    
    def test_instrument_requests_disabled_when_config_disabled(self):
        """Test that requests instrumentation is skipped when explicitly disabled."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_REQUESTS_ENABLED": "false",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._requests_instrumented = False
            
            result = otel_config.instrument_requests()
            
            assert result is False
    
    @patch("opentelemetry.instrumentation.requests.RequestsInstrumentor")
    def test_instrument_requests_success(self, mock_instrumentor_class):
        """Test successful requests instrumentation."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_REQUESTS_ENABLED": "true",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._requests_instrumented = False
            
            mock_instrumentor = MagicMock()
            mock_instrumentor_class.return_value = mock_instrumentor
            
            result = otel_config.instrument_requests()
            
            assert result is True
            assert otel_config._requests_instrumented is True
            mock_instrumentor.instrument.assert_called_once()
    
    def test_instrument_requests_idempotent(self):
        """Test that requests instrumentation is idempotent."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_REQUESTS_ENABLED": "true",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._requests_instrumented = False
            
            with patch("opentelemetry.instrumentation.requests.RequestsInstrumentor") as mock_instrumentor_class:
                mock_instrumentor = MagicMock()
                mock_instrumentor_class.return_value = mock_instrumentor
                
                # First call
                result1 = otel_config.instrument_requests()
                assert result1 is True
                
                # Second call (should be idempotent)
                result2 = otel_config.instrument_requests()
                assert result2 is True
                
                # Should only instrument once
                assert otel_config._requests_instrumented is True
    
    def test_instrument_requests_import_error(self):
        """Test graceful handling of missing requests instrumentation package."""
        with patch.dict(
            os.environ,
            {
                "OTEL_ENABLED": "true",
                "OTEL_INSTRUMENTATION_REQUESTS_ENABLED": "true",
            },
            clear=False,
        ):
            import importlib
            import open_webui.utils.otel_config as otel_config
            importlib.reload(otel_config)
            
            # Reset instrumentation flag
            otel_config._requests_instrumented = False
            
            # Mock ImportError
            with patch("builtins.__import__", side_effect=ImportError("No module named 'opentelemetry.instrumentation.requests'")):
                result = otel_config.instrument_requests()
                
                assert result is False
                assert otel_config._requests_instrumented is False
