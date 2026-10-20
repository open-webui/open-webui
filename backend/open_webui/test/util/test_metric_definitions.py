import json
import traceback
from unittest.mock import Mock

import pytest

from open_webui.config import _load_metric_definitions
from open_webui.metrics.service import MetricsService


def test_unset_uses_builtin_defaults(monkeypatch):
    monkeypatch.delenv("METRIC_DEFINITIONS", raising=False)

    assert _load_metric_definitions() == [
        {
            "name": "http_requests_total",
            "type": "counter",
            "description": "Total HTTP requests",
            "unit": "",
        },
        {
            "name": "http_request_duration_ms",
            "type": "histogram",
            "description": "Duration of HTTP requests in milliseconds",
            "unit": "ms",
        },
        {
            "name": "task_queue_size",
            "type": "gauge",
            "description": "Number of tasks in background queue",
            "unit": "",
        },
    ]


@pytest.mark.parametrize("metric_type", ["counter", "histogram", "gauge", "COUNTER"])
def test_valid_json_creates_instrument(monkeypatch, metric_type):
    definitions = [
        {
            "name": "custom_metric",
            "type": metric_type,
            "description": "Custom metric",
            "unit": "",
        }
    ]
    monkeypatch.setenv("METRIC_DEFINITIONS", json.dumps(definitions))

    parsed = _load_metric_definitions()
    assert parsed == definitions
    meter = Mock()
    service = MetricsService(meter, parsed)
    assert service.list_instruments() == ["custom_metric"]
    method = {
        "counter": meter.create_counter,
        "histogram": meter.create_histogram,
        "gauge": meter.create_observable_gauge,
    }[metric_type.lower()]
    kwargs: dict[str, object] = {
        "name": "custom_metric",
        "description": "Custom metric",
        "unit": "",
    }
    if metric_type == "gauge":
        kwargs["callbacks"] = []
    method.assert_called_once_with(**kwargs)


def test_empty_array_is_allowed(monkeypatch):
    monkeypatch.setenv("METRIC_DEFINITIONS", "[]")
    assert _load_metric_definitions() == []


@pytest.mark.parametrize("value", ["", "not json", "[{", '[{"name": "test",}]'])
def test_invalid_json_has_clear_error(monkeypatch, value):
    monkeypatch.setenv("METRIC_DEFINITIONS", value)
    with pytest.raises(ValueError, match="METRIC_DEFINITIONS must be valid JSON"):
        _load_metric_definitions()


@pytest.mark.parametrize("value", [None, {}, "counter", 1, True])
def test_non_array_json_is_rejected(monkeypatch, value):
    monkeypatch.setenv("METRIC_DEFINITIONS", json.dumps(value))
    with pytest.raises(ValueError, match="METRIC_DEFINITIONS must be a JSON array"):
        _load_metric_definitions()


@pytest.mark.parametrize("value", [None, {}, "counter", [], 1])
def test_non_definition_array_entry_is_rejected(monkeypatch, value):
    monkeypatch.setenv("METRIC_DEFINITIONS", json.dumps([value]))
    with pytest.raises(ValueError, match=r"Invalid METRIC_DEFINITIONS\[0\]"):
        _load_metric_definitions()


@pytest.mark.parametrize("field", ["name", "type", "description", "unit"])
@pytest.mark.parametrize("bad_value", [None, 1, True, [], {}])
def test_non_string_field_is_rejected(monkeypatch, field, bad_value):
    definition = {"name": "test", "type": "counter", "description": "", "unit": ""}
    definition[field] = bad_value
    monkeypatch.setenv("METRIC_DEFINITIONS", json.dumps([definition]))
    with pytest.raises(ValueError, match=rf"METRIC_DEFINITIONS\[0\].*{field}"):
        _load_metric_definitions()


@pytest.mark.parametrize("field", ["name", "type", "description", "unit"])
def test_missing_field_is_rejected(monkeypatch, field):
    definition = {"name": "test", "type": "counter", "description": "", "unit": ""}
    del definition[field]
    monkeypatch.setenv("METRIC_DEFINITIONS", json.dumps([definition]))
    with pytest.raises(ValueError, match=rf"METRIC_DEFINITIONS\[0\].*{field}"):
        _load_metric_definitions()


def test_unsupported_type_reports_definition_index(monkeypatch):
    definition = {"name": "test", "type": "counter", "description": "", "unit": ""}
    monkeypatch.setenv(
        "METRIC_DEFINITIONS",
        json.dumps([definition, {**definition, "type": "unsupported"}]),
    )
    with pytest.raises(ValueError, match=r"METRIC_DEFINITIONS\[1\].type: expected"):
        _load_metric_definitions()


def test_error_does_not_echo_definition_values(monkeypatch):
    sensitive_value = "sensitive-configuration-value"
    monkeypatch.setenv("METRIC_DEFINITIONS", json.dumps([{"name": sensitive_value}]))
    with pytest.raises(ValueError) as error:
        _load_metric_definitions()
    assert sensitive_value not in "".join(traceback.format_exception(error.value))
