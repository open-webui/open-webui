from fastapi import Request
from open_webui.metrics.service import MetricsService


# For Dependency Injection
def get_metrics(request: Request) -> MetricsService:
    return request.app.state.metrics_service
