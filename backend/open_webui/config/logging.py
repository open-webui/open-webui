import logging


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health") == -1


def setup_logging():
    """
    Setup logging configuration.

    Filter out /health endpoint logs.
    """
    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
