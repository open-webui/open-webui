import json
import logging
import sys
import os
from typing import TYPE_CHECKING
from datetime import timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    from backports.zoneinfo import ZoneInfo

from loguru import logger

# Configure timezone to NYC (America/New_York) - Set as early as possible
NYC_TIMEZONE = ZoneInfo("America/New_York")

# Set TZ environment variable to ensure all time operations use NYC timezone
# This affects Python's datetime operations and logging
os.environ["TZ"] = "America/New_York"

from open_webui.env import (
    AUDIT_LOG_FILE_ROTATION_SIZE,
    AUDIT_LOG_LEVEL,
    AUDIT_LOGS_FILE_PATH,
    GLOBAL_LOG_LEVEL,
)


if TYPE_CHECKING:
    from loguru import Record


def stdout_format(record: "Record") -> str:
    """
    Generates a formatted string for log records that are output to the console. This format includes a timestamp, log level, source location (module, function, and line), the log message, and any extra data (serialized as JSON).
    
    Timestamps are displayed in NYC timezone (America/New_York).
    Includes trace_id and span_id from OpenTelemetry context for log-trace correlation.

    Parameters:
    record (Record): A Loguru record that contains logging details including time, level, name, function, line, message, and any extra context.
    Returns:
    str: A formatted log string intended for stdout.
    """
    # Extract trace context from current OTEL span
    trace_id = None
    span_id = None
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span and current_span.get_span_context().is_valid:
            span_context = current_span.get_span_context()
            trace_id = format(span_context.trace_id, "032x")  # 32 hex chars
            span_id = format(span_context.span_id, "016x")  # 16 hex chars
    except Exception:
        pass  # OTEL not available or no active span
    
    # Add trace_id and span_id to record extra
    if trace_id:
        record["extra"]["trace_id"] = trace_id
    if span_id:
        record["extra"]["span_id"] = span_id
    
    # Convert time to NYC timezone and format it
    nyc_time = record["time"].astimezone(NYC_TIMEZONE)
    time_str = nyc_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    # Determine if EST or EDT based on timezone offset
    tz_abbr = "EST" if nyc_time.utcoffset().total_seconds() == -18000 else "EDT"
    
    record["extra"]["extra_json"] = json.dumps(record["extra"])
    
    # Build trace correlation string
    trace_correlation = ""
    if trace_id:
        trace_correlation = f"<yellow>trace_id={trace_id}</yellow> | "
    if span_id:
        trace_correlation += f"<yellow>span_id={span_id}</yellow> | "
    
    return (
        f"<green>{time_str} {tz_abbr}</green> | "
        "<level>{level: <8}</level> | "
        f"{trace_correlation}"
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level> - {extra[extra_json]}"
        "\n{exception}"
    )


class InterceptHandler(logging.Handler):
    """
    Intercepts log records from Python's standard logging module
    and redirects them to Loguru's logger.
    All timestamps are converted to NYC timezone (America/New_York).
    """

    def emit(self, record):
        """
        Called by the standard logging module for each log event.
        It transforms the standard `LogRecord` into a format compatible with Loguru
        and passes it to Loguru's logger. The timestamp is converted to NYC timezone.
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Convert record time to NYC timezone if available
        # Loguru will handle the timezone conversion in stdout_format
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def file_format(record: "Record"):
    """
    Formats audit log records into a structured JSON string for file output.

    Parameters:
    record (Record): A Loguru record containing extra audit data.
    Returns:
    str: A JSON-formatted string representing the audit data.
    """

    audit_data = {
        "id": record["extra"].get("id", ""),
        "timestamp": int(record["time"].timestamp()),
        "user": record["extra"].get("user", dict()),
        "audit_level": record["extra"].get("audit_level", ""),
        "verb": record["extra"].get("verb", ""),
        "request_uri": record["extra"].get("request_uri", ""),
        "response_status_code": record["extra"].get("response_status_code", 0),
        "source_ip": record["extra"].get("source_ip", ""),
        "user_agent": record["extra"].get("user_agent", ""),
        "request_object": record["extra"].get("request_object", b""),
        "response_object": record["extra"].get("response_object", b""),
        "extra": record["extra"].get("extra", {}),
    }

    record["extra"]["file_extra"] = json.dumps(audit_data, default=str)
    return "{extra[file_extra]}\n"


def start_logger():
    """
    Initializes and configures Loguru's logger with distinct handlers:

    A console (stdout) handler for general log messages (excluding those marked as auditable).
    An optional file handler for audit logs if audit logging is enabled.
    Additionally, this function reconfigures Python's standard logging to route through Loguru and adjusts logging levels for Uvicorn.
    
    All timestamps are displayed in NYC timezone (America/New_York).

    Parameters:
    enable_audit_logging (bool): Determines whether audit-specific log entries should be recorded to file.
    """
    logger.remove()

    logger.add(
        sys.stdout,
        level=GLOBAL_LOG_LEVEL,
        format=stdout_format,
        filter=lambda record: "auditable" not in record["extra"],
    )

    if AUDIT_LOG_LEVEL != "NONE":
        try:
            logger.add(
                AUDIT_LOGS_FILE_PATH,
                level="INFO",
                rotation=AUDIT_LOG_FILE_ROTATION_SIZE,
                compression="zip",
                format=file_format,
                filter=lambda record: record["extra"].get("auditable") is True,
            )
        except Exception as e:
            logger.error(f"Failed to initialize audit log file handler: {str(e)}")

    logging.basicConfig(
        handlers=[InterceptHandler()], level=GLOBAL_LOG_LEVEL, force=True
    )
    for uvicorn_logger_name in ["uvicorn", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.setLevel(GLOBAL_LOG_LEVEL)
        uvicorn_logger.handlers = []
    for uvicorn_logger_name in ["uvicorn.access"]:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.setLevel(GLOBAL_LOG_LEVEL)
        uvicorn_logger.handlers = [InterceptHandler()]

    logger.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")
