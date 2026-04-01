import os, json, base64, datetime as dt
import requests
from typing import Dict, Any, List, Tuple, Optional
from dotenv import load_dotenv

# ---------- env & auth ----------

def load_env() -> Tuple[str, str, str]:
    load_dotenv()
    pk = os.getenv("LANGFUSE_PK", os.getenv("PK", ""))
    sk = os.getenv("LANGFUSE_SK", os.getenv("SK", ""))
    host = os.getenv("LANGFUSE_HOST", os.getenv("HOST", "https://cloud.langfuse.com"))
    return pk, sk, host


def auth_header(pk: str, sk: str) -> Dict[str, str]:
    token = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


# ---------- fixed calendar windows (no rolling) ----------

def _isoformat_utc(dt_obj: dt.datetime) -> str:
    return dt_obj.strftime("%Y-%m-%dT%H:%M:%SZ")


def last_day_fixed_window() -> Tuple[str, str]:
    now = dt.datetime.utcnow().replace(microsecond=0)
    start_today = now.replace(hour=0, minute=0, second=0)
    start_yesterday = start_today - dt.timedelta(days=1)
    end_yesterday = start_today - dt.timedelta(seconds=1)
    return _isoformat_utc(start_yesterday), _isoformat_utc(end_yesterday)


def last_week_fixed_window() -> Tuple[str, str]:
    now = dt.datetime.utcnow().replace(microsecond=0)
    start_this_week = (now - dt.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
    start_prev_week = start_this_week - dt.timedelta(days=7)
    end_prev_week = start_this_week - dt.timedelta(seconds=1)
    return _isoformat_utc(start_prev_week), _isoformat_utc(end_prev_week)


def last_month_fixed_window() -> Tuple[str, str]:
    now = dt.datetime.utcnow().replace(microsecond=0)
    first_this_month = now.replace(day=1, hour=0, minute=0, second=0)
    end_prev_month = first_this_month - dt.timedelta(seconds=1)
    first_prev_month = end_prev_month.replace(day=1, hour=0, minute=0, second=0)
    return _isoformat_utc(first_prev_month), _isoformat_utc(end_prev_month)


def custom_days_fixed_window(days: int) -> Tuple[str, str]:
    if days <= 0:
        raise ValueError("days must be a positive integer")
    now = dt.datetime.utcnow().replace(microsecond=0)
    start_today = now.replace(hour=0, minute=0, second=0)
    start = start_today - dt.timedelta(days=days)
    end = start_today - dt.timedelta(seconds=1)
    return _isoformat_utc(start), _isoformat_utc(end)


def today_utc_window_now() -> Tuple[str, str]:
    now = dt.datetime.utcnow().replace(microsecond=0)
    start_today = now.replace(hour=0, minute=0, second=0)
    return _isoformat_utc(start_today), _isoformat_utc(now)


# ---------- query & fetch ----------

def current_month_window() -> Tuple[str, str]:
    now = dt.datetime.utcnow().replace(microsecond=0)
    start = now.replace(day=1, hour=0, minute=0, second=0)
    return _isoformat_utc(start), _isoformat_utc(now)


def build_metrics_query(from_ts: str, to_ts: str) -> Dict[str, Any]:
    return {
        "view": "observations",
        "metrics": [
            {"measure": "totalTokens", "aggregation": "sum"},
            {"measure": "totalCost", "aggregation": "sum"},
        ],
        "dimensions": [
            {"field": "userId"},
            {"field": "providedModelName"},
        ],
        "fromTimestamp": from_ts,
        "toTimestamp": to_ts,
    }


def fetch_metrics(host: str, headers: Dict[str, str], query: Dict[str, Any], timeout: int = 30) -> List[Dict[str, Any]]:
    resp = requests.get(
        f"{host}/api/public/metrics",
        headers=headers,
        params={"query": json.dumps(query)},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def parse_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        out.append({
            "user": row.get("userId") or "(unknown)",
            "model": row.get("providedModelName") or "Unknown Model",
            "tokens": int(row.get("sum_totalTokens", 0) or 0),
            "cost": float(row.get("sum_totalCost", 0) or 0),
        })
    return out


# ---------- period helpers ----------

def get_today_so_far() -> List[Dict[str, Any]]:
    pk, sk, host = load_env()
    headers = auth_header(pk, sk)
    from_ts, to_ts = today_utc_window_now()
    return parse_rows(fetch_metrics(host, headers, build_metrics_query(from_ts, to_ts)))


def get_last_day() -> List[Dict[str, Any]]:
    pk, sk, host = load_env()
    headers = auth_header(pk, sk)
    from_ts, to_ts = last_day_fixed_window()
    return parse_rows(fetch_metrics(host, headers, build_metrics_query(from_ts, to_ts)))


def get_last_week() -> List[Dict[str, Any]]:
    pk, sk, host = load_env()
    headers = auth_header(pk, sk)
    from_ts, to_ts = last_week_fixed_window()
    return parse_rows(fetch_metrics(host, headers, build_metrics_query(from_ts, to_ts)))


def get_last_month() -> List[Dict[str, Any]]:
    pk, sk, host = load_env()
    headers = auth_header(pk, sk)
    from_ts, to_ts = last_month_fixed_window()
    return parse_rows(fetch_metrics(host, headers, build_metrics_query(from_ts, to_ts)))


def get_custom_days(days: int) -> List[Dict[str, Any]]:
    pk, sk, host = load_env()
    headers = auth_header(pk, sk)
    from_ts, to_ts = custom_days_fixed_window(days)
    return parse_rows(fetch_metrics(host, headers, build_metrics_query(from_ts, to_ts)))


def get_current_month() -> List[Dict[str, Any]]:
    pk, sk, host = load_env()
    headers = auth_header(pk, sk)
    from_ts, to_ts = current_month_window()
    return parse_rows(fetch_metrics(host, headers, build_metrics_query(from_ts, to_ts)))


def read_custom_days_env() -> Optional[int]:
    raw = os.getenv("CUSTOM_DAYS", "").strip()
    if not raw:
        return None
    try:
        val = int(raw)
        return val if val > 0 else None
    except ValueError:
        return None
