"""
Unit tests for OpenTelemetry instrumentation helper utilities.

Tests cover:
- Context managers (sync and async)
- Decorators
- Event and status helpers
- Error handling
- Edge cases
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestTraceSpan:
    """Test trace_span context manager."""
    
    def test_trace_span_success(self):
        """Test that context manager creates span successfully."""
        from open_webui.utils.otel_instrumentation import trace_span
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span") as mock_use_span:
            
            mock_token = MagicMock()
            mock_use_span.return_value = mock_token
            
            with trace_span("test.operation", {"attr1": "value1"}):
                pass
            
            mock_tracer.start_span.assert_called_once()
            mock_span.set_attribute.assert_called()
            mock_span.set_status.assert_called()
            mock_span.end.assert_called_once()
    
    def test_trace_span_error(self):
        """Test that error sets span status to ERROR."""
        from open_webui.utils.otel_instrumentation import trace_span
        from opentelemetry.trace import Status, StatusCode
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span") as mock_use_span:
            
            mock_token = MagicMock()
            mock_use_span.return_value = mock_token
            
            with pytest.raises(ValueError):
                with trace_span("test.operation"):
                    raise ValueError("Test error")
            
            # Verify error status was set
            calls = mock_span.set_status.call_args_list
            assert any(
                call[0][0].status_code == StatusCode.ERROR
                for call in calls
            )
            mock_span.record_exception.assert_called_once()
    
    def test_trace_span_attributes(self):
        """Test that attributes are set correctly."""
        from open_webui.utils.otel_instrumentation import trace_span
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        attributes = {
            "attr1": "value1",
            "attr2": 42,
            "attr3": None,  # Should be skipped
        }
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span"):
            
            with trace_span("test.operation", attributes=attributes):
                pass
            
            # Verify attributes were set (excluding None)
            assert mock_span.set_attribute.call_count == 2
    
    def test_trace_span_no_tracer(self):
        """Test graceful handling when OTEL is not initialized."""
        from open_webui.utils.otel_instrumentation import trace_span
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=None):
            # Should not raise exception
            with trace_span("test.operation"):
                pass
    
    def test_trace_span_parent_link(self):
        """Test that span links to parent correctly."""
        from open_webui.utils.otel_instrumentation import trace_span
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span") as mock_use_span:
            
            mock_token = MagicMock()
            mock_use_span.return_value = mock_token
            
            with trace_span("test.operation"):
                pass
            
            # Verify use_span was called (this links to parent)
            mock_use_span.assert_called_once_with(mock_span, end_on_exit=False)


class TestTraceSpanAsync:
    """Test trace_span_async async context manager."""
    
    @pytest.mark.asyncio
    async def test_trace_span_async_success(self):
        """Test that async context manager creates span successfully."""
        from open_webui.utils.otel_instrumentation import trace_span_async
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span") as mock_use_span:
            
            mock_token = MagicMock()
            mock_use_span.return_value = mock_token
            
            async with trace_span_async("test.operation", {"attr1": "value1"}):
                pass
            
            mock_tracer.start_span.assert_called_once()
            mock_span.set_status.assert_called()
            mock_span.end.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trace_span_async_error(self):
        """Test that error sets span status to ERROR in async context."""
        from open_webui.utils.otel_instrumentation import trace_span_async
        from opentelemetry.trace import StatusCode
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span"):
            
            with pytest.raises(ValueError):
                async with trace_span_async("test.operation"):
                    raise ValueError("Test error")
            
            # Verify error status was set
            calls = mock_span.set_status.call_args_list
            assert any(
                call[0][0].status_code == StatusCode.ERROR
                for call in calls
            )
            mock_span.record_exception.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trace_span_async_no_tracer(self):
        """Test graceful handling when OTEL is not initialized."""
        from open_webui.utils.otel_instrumentation import trace_span_async
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=None):
            # Should not raise exception
            async with trace_span_async("test.operation"):
                pass


class TestTraceFunction:
    """Test trace_function decorator."""
    
    def test_trace_function_decorator_sync(self):
        """Test decorator creates span for sync function."""
        from open_webui.utils.otel_instrumentation import trace_function
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        @trace_function(span_name="test.function")
        def test_func(x, y):
            return x + y
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span"):
            
            result = test_func(1, 2)
            
            assert result == 3
            mock_tracer.start_span.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trace_function_decorator_async(self):
        """Test decorator creates span for async function."""
        from open_webui.utils.otel_instrumentation import trace_function
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        @trace_function(span_name="test.async_function")
        async def test_async_func(x, y):
            await asyncio.sleep(0.01)
            return x + y
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span"):
            
            result = await test_async_func(1, 2)
            
            assert result == 3
            mock_tracer.start_span.assert_called_once()
    
    def test_trace_function_capture_args(self):
        """Test that function arguments are captured as attributes."""
        from open_webui.utils.otel_instrumentation import trace_function
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        @trace_function(span_name="test.function", capture_args=True)
        def test_func(model, messages, api_key="secret"):
            return "response"
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span"):
            
            test_func("gpt-4", ["msg1", "msg2"], api_key="secret123")
            
            # Verify attributes were set (api_key should be skipped as sensitive)
            set_attribute_calls = mock_span.set_attribute.call_args_list
            attr_keys = [call[0][0] for call in set_attribute_calls]
            assert "function.arg.model" in attr_keys
            assert "function.arg.messages" in attr_keys
            # api_key should not be captured
            assert "function.arg.api_key" not in attr_keys
    
    def test_trace_function_error(self):
        """Test that errors in decorated function set span status to ERROR."""
        from open_webui.utils.otel_instrumentation import trace_function
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        
        @trace_function(span_name="test.function")
        def test_func():
            raise ValueError("Test error")
        
        with patch("open_webui.utils.otel_instrumentation._get_tracer", return_value=mock_tracer), \
             patch("opentelemetry.trace.use_span"):
            
            with pytest.raises(ValueError):
                test_func()
            
            # Verify error status was set
            calls = mock_span.set_status.call_args_list
            assert any(
                call[0][0].status_code.value == 2  # ERROR
                for call in calls
            )


class TestAddSpanEvent:
    """Test add_span_event helper."""
    
    def test_add_span_event_success(self):
        """Test that events are added to current span."""
        from open_webui.utils.otel_instrumentation import add_span_event
        
        mock_span = MagicMock()
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=mock_span):
            add_span_event("test.event", {"attr1": "value1"})
            
            mock_span.add_event.assert_called_once_with("test.event", {"attr1": "value1"})
    
    def test_add_span_event_no_span(self):
        """Test graceful handling when no active span."""
        from open_webui.utils.otel_instrumentation import add_span_event
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=None):
            # Should not raise exception
            add_span_event("test.event")
    
    def test_add_span_event_filters_none(self):
        """Test that None values are filtered from event attributes."""
        from open_webui.utils.otel_instrumentation import add_span_event
        
        mock_span = MagicMock()
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=mock_span):
            add_span_event("test.event", {"attr1": "value1", "attr2": None})
            
            # Verify None was filtered out
            call_args = mock_span.add_event.call_args[0]
            assert call_args[0] == "test.event"
            assert "attr2" not in call_args[1]


class TestSetSpanStatus:
    """Test set_span_status helper."""
    
    def test_set_span_status_success(self):
        """Test that span status is set correctly."""
        from open_webui.utils.otel_instrumentation import set_span_status
        from opentelemetry.trace import Status, StatusCode
        
        mock_span = MagicMock()
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=mock_span):
            set_span_status(Status(StatusCode.OK))
            
            mock_span.set_status.assert_called_once()
    
    def test_set_span_status_error(self):
        """Test that error status is set correctly."""
        from open_webui.utils.otel_instrumentation import set_span_status
        from opentelemetry.trace import Status, StatusCode
        
        mock_span = MagicMock()
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=mock_span):
            set_span_status(Status(StatusCode.ERROR, "Test error"))
            
            mock_span.set_status.assert_called_once()
            call_args = mock_span.set_status.call_args[0][0]
            assert call_args.status_code == StatusCode.ERROR
    
    def test_set_span_status_no_span(self):
        """Test graceful handling when no active span."""
        from open_webui.utils.otel_instrumentation import set_span_status
        from opentelemetry.trace import Status, StatusCode
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=None):
            # Should not raise exception
            set_span_status(Status(StatusCode.OK))


class TestSetSpanAttribute:
    """Test set_span_attribute helper."""
    
    def test_set_span_attribute_success(self):
        """Test that span attribute is set correctly."""
        from open_webui.utils.otel_instrumentation import set_span_attribute
        
        mock_span = MagicMock()
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=mock_span):
            set_span_attribute("llm.tokens", 150)
            
            mock_span.set_attribute.assert_called_once_with("llm.tokens", 150)
    
    def test_set_span_attribute_none_value(self):
        """Test that None values are skipped."""
        from open_webui.utils.otel_instrumentation import set_span_attribute
        
        mock_span = MagicMock()
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=mock_span):
            set_span_attribute("llm.tokens", None)
            
            # Should not be called for None
            mock_span.set_attribute.assert_not_called()
    
    def test_set_span_attribute_no_span(self):
        """Test graceful handling when no active span."""
        from open_webui.utils.otel_instrumentation import set_span_attribute
        
        with patch("open_webui.utils.otel_instrumentation._get_current_span", return_value=None):
            # Should not raise exception
            set_span_attribute("llm.tokens", 150)
