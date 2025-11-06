import contextvars
import logging
import sys
import time


from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.logging import AccessFormatter

from open_webui.utils.auth import get_current_user

ACCESS_LOG_NAME: str = "uvicorn.access"
DATE_FORMAT: str = "%Y/%m/%d %H:%M:%S %Z"
LOG_FORMAT: str = (
    '%(name)s: %(remote_address)s - %(request_id)s - %(user)s [%(asctime)s] %(host)s "%(http_method)s %(http_path)s HTTP/%(http_version)s" "%(user_agent)s" %(http_status)d %(content_length)dB %(request_duration)fs'
)

_request_duration_context = contextvars.ContextVar(
    "access_log_process_time", default=-1.0
)
_user_context = contextvars.ContextVar("access_log_user", default="unauthenticated")
_request_id_context = contextvars.ContextVar("access_log_request_id", default="N/A")
_context_length_context = contextvars.ContextVar(
    "access_log_content_length", default=-1
)
_user_agent_context = contextvars.ContextVar("access_log_user_agent", default="N/A")
_host_context = contextvars.ContextVar("access_log_host", default="N/A")


class UvicornAccessFieldsFilter(logging.Filter):
    """
    This filter assigns the args passed to the uvicorn.access logger to named variables
    for simpler access within the formatter.

    Log line and argument order: https://github.com/Kludex/uvicorn/blob/9b1c6c45ed7fe8bd485ddad475f0feff03971af7/uvicorn/protocols/http/h11_impl.py#L473
    """

    def filter(self, record: logging.LogRecord) -> bool:

        record.remote_address = record.args[0]
        record.http_method = record.args[1]
        record.http_path = record.args[2]
        record.http_version = record.args[3]
        record.http_status = record.args[4]

        return True


class EndpointFilter(logging.Filter):
    """
    Log filter which removes calls to the health checks from the access logs.

    Log line and argument order: https://github.com/Kludex/uvicorn/blob/9b1c6c45ed7fe8bd485ddad475f0feff03971af7/uvicorn/protocols/http/h11_impl.py#L473
    """

    def filter(self, record: logging.LogRecord) -> bool:

        return not str(record.args[2]).startswith("/health")


class ContextFilter(logging.Filter):
    """
    Logging filter which adds request, response, and identity information into the access logs.
    """

    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        record.user = _user_context.get()
        record.request_duration = _request_duration_context.get()
        record.request_id = _request_id_context.get()
        record.content_length = _context_length_context.get()
        record.user_agent = _user_agent_context.get()
        record.host = _host_context.get()
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to update the context with the appropriate
    """

    async def dispatch(self, request: Request, call_next):

        start_time = time.perf_counter()

        response = await call_next(request)

        try:
            _user_context.set(get_current_user(request=request, auth_token=None).email)
        except Exception:
            pass

        _request_duration_context.set(time.perf_counter() - start_time)

        if request_id := request.headers.get("X-Request-Id"):
            _request_id_context.set(request_id)

        if context_length := response.headers.get("Content-Length"):
            _context_length_context.set(int(context_length))

        if user_agent := request.headers.get("User-Agent"):
            _user_agent_context.set(user_agent)

        if host := request.headers.get("Host"):
            _host_context.set(host)

        return response


def _remove_handlers() -> None:
    """
    Removes the default handlers set up for the uvicorn.access logger, removing the default configurations.
    """
    logger = logging.getLogger(ACCESS_LOG_NAME)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)


def reconfigure_access_log():
    """
    Reconfigures the uvicorn.access logger to provide more robust access logging.
    """

    _remove_handlers()

    logger = logging.getLogger(ACCESS_LOG_NAME)

    handler_stdout = logging.StreamHandler(sys.stdout)

    handler_stdout.setFormatter(
        AccessFormatter(
            fmt=LOG_FORMAT,
            datefmt=DATE_FORMAT,
        )
    )

    for filter in (EndpointFilter(), UvicornAccessFieldsFilter(), ContextFilter()):
        logger.addFilter(filter)

    logger.addHandler(handler_stdout)
    # Must be INFO or lower to be seen.
    logger.setLevel(logging.INFO)
