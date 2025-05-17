from typing import Optional


class TelemetryMetrics:
    def __init__(self, meter):
        self.login_counter = meter.create_counter(
            "user_login_total", description="Total number of user logins"
        )
        self.user_request_counter = meter.create_counter(
            "user_request_total", description="Total number of user requests"
        )

    def track_user_login(self, user_id: str, email: str):
        self.login_counter.add(
            1, {"method": "regular", "user_id": user_id, "email": email}
        )

    def track_user_request(self, user_id: str):
        self.user_request_counter.add(1, {"user_id": user_id})


telemetry_metrics: Optional[TelemetryMetrics] = None


def initialize_telemetry_metrics(meter):
    global telemetry_metrics
    telemetry_metrics = TelemetryMetrics(meter)
