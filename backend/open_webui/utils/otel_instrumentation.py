"""
OpenTelemetry Manual Instrumentation Helper Utilities

This module provides reusable utilities for manual instrumentation:
- Context managers for creating spans (sync and async)
- Decorators for automatic function tracing
- Helpers for adding events and setting span status

All utilities are designed to be:
- Thread-safe and async-safe
- Context-aware (automatically link to parent spans)
- Production-ready (proper error handling)
- High-performance (minimal overhead)
"""

import functools
import inspect
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Dict, Optional

log = logging.getLogger(__name__)


def _get_tracer():
    """
    Get the current OTEL tracer.
    
    Returns:
        Tracer: OpenTelemetry tracer instance or None if OTEL is not initialized
    """
    try:
        from opentelemetry import trace
        return trace.get_tracer(__name__)
    except Exception:
        return None


def _get_current_span():
    """
    Get the current active span from context.
    
    Returns:
        Span: Current active span or None if no active span
    """
    try:
        from opentelemetry import trace
        return trace.get_current_span()
    except Exception:
        return None


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: Optional[Any] = None,
):
    """
    Context manager for creating OpenTelemetry spans in synchronous code.
    
    Automatically links to parent span from context, handles errors, and sets status.
    Works in both sync and async contexts (though async code should use trace_span_async).
    
    Args:
        name: Span name (e.g., "llm.chat_completion")
        attributes: Dictionary of span attributes (e.g., {"llm.model": "gpt-4"})
        kind: SpanKind (SERVER, CLIENT, INTERNAL, etc.) - optional
    
    Yields:
        Span: OpenTelemetry span object (can be used to set additional attributes)
    
    Example:
        with trace_span("file.upload", {"file.name": "doc.pdf"}) as span:
            # Your code here
            span.set_attribute("file.size", 1024)
    """
    # Get tracer - wrap in try/except to handle tracer creation failures
    try:
        tracer = _get_tracer()
    except Exception as tracer_error:
        # If tracer creation fails, fall back to no-op mode
        log.warning(f"[trace_span] Failed to get tracer: {type(tracer_error).__name__}: {tracer_error}")
        try:
            log.debug(f"[trace_span] Generator entering (fallback mode - tracer failed) for span '{name}'")
            yield None
            log.debug(f"[trace_span] Generator exiting normally (fallback mode - tracer failed) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span] GeneratorExit caught (fallback mode - tracer failed) for span '{name}': {ge}")
            raise
        except Exception as gen_exc:
            log.warning(f"[trace_span] Exception thrown into generator (fallback mode - tracer failed) for span '{name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
            raise
        return
    
    if not tracer:
        # OTEL not initialized, yield None and continue
        log.debug(f"[trace_span] OTEL not initialized, using no-op for span '{name}'")
        try:
            log.debug(f"[trace_span] Generator entering (no-op mode) for span '{name}'")
            yield None
            log.debug(f"[trace_span] Generator exiting normally (no-op mode) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span] GeneratorExit caught (no-op mode) for span '{name}': {ge}")
            raise
        except Exception as e:
            log.warning(f"[trace_span] Exception thrown into generator (no-op mode) for span '{name}': {type(e).__name__}: {e}", exc_info=True)
            raise
        return
    
    # Import OTEL modules - if this fails, we'll catch it below
    try:
        from opentelemetry.trace import SpanKind, Status, StatusCode
        from opentelemetry import trace
    except Exception as import_error:
        # If imports fail, fall back to no-op mode
        log.warning(f"[trace_span] Failed to import OTEL modules: {import_error}")
        try:
            log.debug(f"[trace_span] Generator entering (fallback mode - import failed) for span '{name}'")
            yield None
            log.debug(f"[trace_span] Generator exiting normally (fallback mode - import failed) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span] GeneratorExit caught (fallback mode - import failed) for span '{name}': {ge}")
            raise
        except Exception as gen_exc:
            log.warning(f"[trace_span] Exception thrown into generator (fallback mode - import failed) for span '{name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
            raise
        return
    
    # Determine span kind
    span_kind = kind if kind is not None else SpanKind.INTERNAL
        
    # Start span as current span (automatically links to parent from context)
    # CRITICAL: We wrap only the span creation in try/except, not the entire span context
    # Exceptions from within the span context should propagate naturally
    try:
        span_context = tracer.start_as_current_span(name, kind=span_kind, end_on_exit=False)
    except Exception as span_creation_error:
        # If span creation fails, fall back to no-op mode
        log.warning(f"[trace_span] Failed to create span '{name}': {type(span_creation_error).__name__}: {span_creation_error}")
        try:
            log.debug(f"[trace_span] Generator entering (fallback mode - creation failed) for span '{name}'")
            yield None
            log.debug(f"[trace_span] Generator exiting normally (fallback mode - creation failed) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span] GeneratorExit caught (fallback mode - creation failed) for span '{name}': {ge}")
            raise
        except Exception as gen_exc:
            log.warning(f"[trace_span] Exception thrown into generator (fallback mode - creation failed) for span '{name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
            raise
        return
    
    # Now enter the span context - exceptions from here should propagate naturally
    with span_context as span:
        # Set attributes if provided (filter None values first for performance)
        if attributes:
            filtered_attrs = {k: v for k, v in attributes.items() if v is not None}
            for key, value in filtered_attrs.items():
                try:
                    span.set_attribute(key, value)
                except Exception as e:
                    log.debug(f"Failed to set span attribute {key}: {e}")
        
        try:
            # Get span_id from SpanContext (not a dict, so access attributes directly)
            try:
                span_context = span.get_span_context()
                span_id = format(span_context.span_id, "016x") if span_context.is_valid else 'unknown'
            except (AttributeError, Exception):
                span_id = 'unknown'
            log.debug(f"[trace_span] Generator entering (OTEL active) for span '{name}', span_id={span_id}")
            yield span
            # Set status to OK if no exception
            span.set_status(Status(StatusCode.OK))
            log.debug(f"[trace_span] Generator exiting normally (OTEL active) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span] GeneratorExit caught (OTEL active) for span '{name}': {ge}")
            # Set status before exiting
            try:
                span.set_status(Status(StatusCode.ERROR, "GeneratorExit"))
            except Exception:
                pass
            # Re-raise GeneratorExit - let finally block handle span.end()
            raise
        except Exception as e:
            # Set status to ERROR on exception
            log.warning(f"[trace_span] Exception in span context (OTEL active) for span '{name}': {type(e).__name__}: {e}", exc_info=True)
            try:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                # Record exception
                span.record_exception(e)
            except Exception as span_error:
                log.debug(f"[trace_span] Failed to set span error status for '{name}': {span_error}")
            # Re-raise exception - let finally block handle span.end()
            # This ensures generator exits properly and contextlib can handle the exception
            raise
        finally:
            # ALWAYS end span here, even on exception
            # This ensures cleanup happens and generator exits properly
            # Note: end_on_exit=False means we must call end() manually
            try:
                span.end()
                log.debug(f"[trace_span] Span ended (OTEL active) for span '{name}'")
            except Exception as end_error:
                log.debug(f"[trace_span] Error ending span '{name}': {end_error}")


@asynccontextmanager
async def trace_span_async(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: Optional[Any] = None,
):
    """
    Async context manager for creating OpenTelemetry spans in asynchronous code.
    
    Same as trace_span but async-compatible. Use this for async functions.
    
    Args:
        name: Span name (e.g., "llm.chat_completion")
        attributes: Dictionary of span attributes
        kind: SpanKind (optional)
    
    Yields:
        Span: OpenTelemetry span object
    
    Example:
        async with trace_span_async("llm.call", {"llm.model": "gpt-4"}) as span:
            response = await make_llm_call()
            span.set_attribute("llm.tokens", response.tokens)
    """
    # Get tracer - wrap in try/except to handle tracer creation failures
    try:
        tracer = _get_tracer()
    except Exception as tracer_error:
        # If tracer creation fails, fall back to no-op mode
        log.warning(f"[trace_span_async] Failed to get tracer: {type(tracer_error).__name__}: {tracer_error}")
        try:
            log.debug(f"[trace_span_async] Generator entering (fallback mode - tracer failed) for span '{name}'")
            yield None
            log.debug(f"[trace_span_async] Generator exiting normally (fallback mode - tracer failed) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span_async] GeneratorExit caught (fallback mode - tracer failed) for span '{name}': {ge}")
            raise
        except Exception as gen_exc:
            log.warning(f"[trace_span_async] Exception thrown into generator (fallback mode - tracer failed) for span '{name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
            raise
        return
    
    if not tracer:
        # OTEL not initialized, yield None and continue
        log.debug(f"[trace_span_async] OTEL not initialized, using no-op for span '{name}'")
        try:
            log.debug(f"[trace_span_async] Generator entering (no-op mode) for span '{name}'")
            yield None
            log.debug(f"[trace_span_async] Generator exiting normally (no-op mode) for span '{name}'")
        except GeneratorExit as ge:
            # Properly handle generator exit
            log.debug(f"[trace_span_async] GeneratorExit caught (no-op mode) for span '{name}': {ge}")
            raise
        except Exception as e:
            # If exception is thrown into generator, re-raise to propagate
            log.warning(f"[trace_span_async] Exception thrown into generator (no-op mode) for span '{name}': {type(e).__name__}: {e}", exc_info=True)
            raise
        return
    
    # Import OTEL modules - if this fails, we'll catch it below
    try:
        from opentelemetry.trace import SpanKind, Status, StatusCode
        from opentelemetry import trace
    except Exception as import_error:
        # If imports fail, fall back to no-op mode
        log.warning(f"[trace_span_async] Failed to import OTEL modules: {import_error}")
        try:
            log.debug(f"[trace_span_async] Generator entering (fallback mode - import failed) for span '{name}'")
            yield None
            log.debug(f"[trace_span_async] Generator exiting normally (fallback mode - import failed) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span_async] GeneratorExit caught (fallback mode - import failed) for span '{name}': {ge}")
            raise
        except Exception as gen_exc:
            log.warning(f"[trace_span_async] Exception thrown into generator (fallback mode - import failed) for span '{name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
            raise
        return
    
    # Determine span kind
    span_kind = kind if kind is not None else SpanKind.INTERNAL
        
    # Start span as current span (automatically links to parent from context)
    # CRITICAL: We wrap only the span creation in try/except, not the entire span context
    # Exceptions from within the span context should propagate naturally
    try:
        span_context = tracer.start_as_current_span(name, kind=span_kind, end_on_exit=False)
    except Exception as span_creation_error:
        # If span creation fails, fall back to no-op mode
        log.warning(f"[trace_span_async] Failed to create span '{name}': {type(span_creation_error).__name__}: {span_creation_error}")
        try:
            log.debug(f"[trace_span_async] Generator entering (fallback mode - creation failed) for span '{name}'")
            yield None
            log.debug(f"[trace_span_async] Generator exiting normally (fallback mode - creation failed) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span_async] GeneratorExit caught (fallback mode - creation failed) for span '{name}': {ge}")
            raise
        except Exception as gen_exc:
            log.warning(f"[trace_span_async] Exception thrown into generator (fallback mode - creation failed) for span '{name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
            raise
        return
    
    # Now enter the span context - exceptions from here should propagate naturally
    with span_context as span:
        # Set attributes if provided (filter None values first for performance)
        if attributes:
            filtered_attrs = {k: v for k, v in attributes.items() if v is not None}
            for key, value in filtered_attrs.items():
                try:
                    span.set_attribute(key, value)
                except Exception as e:
                    log.debug(f"Failed to set span attribute {key}: {e}")
        
        try:
            # Get span_id from SpanContext (not a dict, so access attributes directly)
            try:
                span_context = span.get_span_context()
                span_id = format(span_context.span_id, "016x") if span_context.is_valid else 'unknown'
            except (AttributeError, Exception):
                span_id = 'unknown'
            log.debug(f"[trace_span_async] Generator entering (OTEL active) for span '{name}', span_id={span_id}")
            yield span
            # Set status to OK if no exception
            span.set_status(Status(StatusCode.OK))
            log.debug(f"[trace_span_async] Generator exiting normally (OTEL active) for span '{name}'")
        except GeneratorExit as ge:
            log.debug(f"[trace_span_async] GeneratorExit caught (OTEL active) for span '{name}': {ge}")
            # Set status before exiting
            try:
                span.set_status(Status(StatusCode.ERROR, "GeneratorExit"))
            except Exception:
                pass
            # Re-raise GeneratorExit - let finally block handle span.end()
            raise
        except Exception as e:
            # Set status to ERROR on exception
            log.warning(f"[trace_span_async] Exception in span context (OTEL active) for span '{name}': {type(e).__name__}: {e}", exc_info=True)
            try:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                # Record exception
                span.record_exception(e)
            except Exception as span_error:
                log.debug(f"[trace_span_async] Failed to set span error status for '{name}': {span_error}")
            # Re-raise exception - let finally block handle span.end()
            # This ensures generator exits properly and contextlib can handle the exception
            raise
        finally:
            # ALWAYS end span here, even on exception
            # This ensures cleanup happens and generator exits properly
            # Note: end_on_exit=False means we must call end() manually
            try:
                span.end()
                log.debug(f"[trace_span_async] Span ended (OTEL active) for span '{name}'")
            except Exception as end_error:
                log.debug(f"[trace_span_async] Error ending span '{name}': {end_error}")


def trace_function(
    span_name: Optional[str] = None,
    capture_args: bool = False,
    capture_result: bool = False,
):
    """
    Decorator to automatically trace function execution.
    
    Creates a span for the function, optionally capturing arguments and return value.
    Works for both sync and async functions.
    
    Args:
        span_name: Custom span name (defaults to function name)
        capture_args: Whether to capture function arguments as span attributes
        capture_result: Whether to capture return value as span event (not recommended for large objects)
    
    Returns:
        Decorated function
    
    Example:
        @trace_function(span_name="llm.call", capture_args=True)
        async def generate_chat_completion(model, messages):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Determine if function is async
        is_async = inspect.iscoroutinefunction(func)
        
        # Determine span name
        name = span_name or f"{func.__module__}.{func.__name__}"
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Build attributes
                attributes = {}
                if capture_args:
                    # Capture function arguments (be careful with sensitive data)
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    for param_name, param_value in bound_args.arguments.items():
                        # Skip sensitive parameters
                        if param_name in ("password", "api_key", "token", "secret"):
                            continue
                        # Convert to string, truncate if too long
                        try:
                            value_str = str(param_value)
                            if len(value_str) > 200:
                                value_str = value_str[:200] + "..."
                            attributes[f"function.arg.{param_name}"] = value_str
                        except Exception:
                            pass
                
                # Create span - use try/except to ensure OTEL failures don't break the function
                try:
                    async with trace_span_async(name, attributes=attributes) as span:
                        try:
                            result = await func(*args, **kwargs)
                            
                            if capture_result and span:
                                # Add result as event (not attribute, to avoid large payloads)
                                try:
                                    result_str = str(result)
                                    if len(result_str) > 200:
                                        result_str = result_str[:200] + "..."
                                    span.add_event("function.result", {"result": result_str})
                                except Exception:
                                    pass
                            
                            return result
                        except Exception as e:
                            # Error handling is done in trace_span_async
                            raise
                except Exception as otel_error:
                    # If OTEL fails, log but don't break the function
                    log.debug(f"OTEL span creation failed in decorator (non-critical): {otel_error}")
                    # Execute function without tracing
                    return await func(*args, **kwargs)
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Build attributes
                attributes = {}
                if capture_args:
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    for param_name, param_value in bound_args.arguments.items():
                        if param_name in ("password", "api_key", "token", "secret"):
                            continue
                        try:
                            value_str = str(param_value)
                            if len(value_str) > 200:
                                value_str = value_str[:200] + "..."
                            attributes[f"function.arg.{param_name}"] = value_str
                        except Exception:
                            pass
                
                # Create span - use try/except to ensure OTEL failures don't break the function
                try:
                    with trace_span(name, attributes=attributes) as span:
                        try:
                            result = func(*args, **kwargs)
                            
                            if capture_result and span:
                                try:
                                    result_str = str(result)
                                    if len(result_str) > 200:
                                        result_str = result_str[:200] + "..."
                                    span.add_event("function.result", {"result": result_str})
                                except Exception:
                                    pass
                            
                            return result
                        except Exception as e:
                            # Error handling is done in trace_span
                            raise
                except Exception as otel_error:
                    # If OTEL fails, log but don't break the function
                    log.debug(f"OTEL span creation failed in decorator (non-critical): {otel_error}")
                    # Execute function without tracing
                    return func(*args, **kwargs)
        
        return async_wrapper if is_async else sync_wrapper
    
    return decorator


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current active span.
    
    Events are lightweight and useful for marking milestones in span execution.
    
    Args:
        name: Event name (e.g., "llm.request", "file.uploaded")
        attributes: Optional dictionary of event attributes
    
    Example:
        add_span_event("llm.request", {"model": "gpt-4", "message_count": 5})
    """
    span = _get_current_span()
    if not span:
        # No active span, silently skip
        return
    
    try:
        if attributes:
            # Filter out None values
            filtered_attrs = {k: v for k, v in attributes.items() if v is not None}
            if filtered_attrs:
                span.add_event(name, attributes=filtered_attrs)
            else:
                # No valid attributes after filtering, add event without attributes
                span.add_event(name)
        else:
            span.add_event(name)
    except Exception as e:
        log.debug(f"Failed to add span event '{name}': {e}")


def set_span_status(status: Any, description: Optional[str] = None):
    """
    Set status on the current active span.
    
    Args:
        status: Status object (Status(StatusCode.OK) or Status(StatusCode.ERROR, description))
        description: Optional status description (if status is StatusCode enum, not Status object)
    
    Example:
        from opentelemetry.trace import Status, StatusCode
        set_span_status(Status(StatusCode.OK))
        set_span_status(Status(StatusCode.ERROR, "API call failed"))
    """
    span = _get_current_span()
    if not span:
        # No active span, silently skip
        return
    
    try:
        # Handle both Status object and StatusCode enum
        from opentelemetry.trace import Status, StatusCode
        
        if isinstance(status, Status):
            span.set_status(status)
        elif isinstance(status, StatusCode):
            span.set_status(Status(status, description))
        else:
            log.warning(f"Invalid status type: {type(status)}")
    except Exception as e:
        log.debug(f"Failed to set span status: {e}")


def set_span_attribute(key: str, value: Any):
    """
    Set an attribute on the current active span.
    
    Args:
        key: Attribute key (e.g., "llm.tokens", "file.size")
        value: Attribute value (must be a primitive type: str, int, float, bool, or list of these)
    
    Example:
        set_span_attribute("llm.usage.total_tokens", 150)
    """
    span = _get_current_span()
    if not span:
        # No active span, silently skip
        return
    
    try:
        if value is not None:
            span.set_attribute(key, value)
    except Exception as e:
        log.debug(f"Failed to set span attribute '{key}': {e}")
