"""In-memory progress registry + signed access token for the seeded
`background_agent` Tool (open-webui-seed/tools/agent.py).

The Tool runs the sub-agent loop inside this backend process and pushes
debug-level progress events here; a small `/api/v1/agent/jobs/{id}/view`
iframe (served by routers/agent_jobs.py) streams them live over SSE.

Single-process, in-memory by design — same assumption as `open_webui.tasks`.
A backend restart loses live jobs (the run itself dies too — acceptable).
Tokens are stateless HMACs over the job id (the sandboxed iframe has a null
origin and cannot carry the session cookie, so the token is the credential).
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Optional
from uuid import uuid4

from open_webui.env import WEBUI_SECRET_KEY

try:
    from open_webui.env import DATA_DIR as _DATA_DIR
except Exception:  # pragma: no cover
    _DATA_DIR = os.environ.get("DATA_DIR", "/app/backend/data")

# Persisted run logs survive the in-memory prune so the agent output can be
# retrieved later for debugging (admin endpoint). Kept on the open-webui-data
# volume; aged out by AGENT_LOG_RETENTION_DAYS.
LOG_DIR = os.path.join(_DATA_DIR, "agent_logs")
_LOG_RETENTION_DAYS = int(os.environ.get("AGENT_LOG_RETENTION_DAYS", "14"))
_LOG_MAX_FILES = int(os.environ.get("AGENT_LOG_MAX_FILES", "500"))

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_MAX_EVENTS = 2000
_DEFAULT_PRUNE_TTL = 600  # seconds a terminal job stays viewable
_TERMINAL = {"success", "partial", "error", "cancelled"}


@dataclass
class JobRecord:
    job_id: str
    summary: str
    state: str = "running"  # running | success | partial | error | cancelled
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    _seq: int = 0
    cancel_requested: bool = False
    events: deque = field(default_factory=lambda: deque(maxlen=_MAX_EVENTS))
    subscribers: list[asyncio.Queue] = field(default_factory=list)


JOBS: dict[str, JobRecord] = {}


def request_cancel(job_id: str) -> bool:
    """Flag a running job to stop (the run loop checks this between
    steps and finalizes a partial result)."""
    rec = JOBS.get(job_id)
    if rec is None or rec.state in _TERMINAL:
        return False
    rec.cancel_requested = True
    push(job_id, "state", "⏹ Stop requested by user…")
    return True


def is_cancelled(job_id: str) -> bool:
    rec = JOBS.get(job_id)
    return bool(rec and rec.cancel_requested)


def create_job(summary: str) -> str:
    job_id = uuid4().hex
    JOBS[job_id] = JobRecord(job_id=job_id, summary=(summary or "").strip())
    return job_id


def get(job_id: str) -> Optional[JobRecord]:
    return JOBS.get(job_id)


def push(job_id: str, kind: str, text: str, data: Optional[dict] = None) -> None:
    """Append a progress event and fan it out to live SSE subscribers.

    Never blocks the agent: a full subscriber queue drops its oldest item.
    """
    rec = JOBS.get(job_id)
    if rec is None:
        return
    rec._seq += 1
    ev = {
        "seq": rec._seq,
        "ts": round(time.time() - rec.created_at, 2),
        "kind": kind,
        "text": text if isinstance(text, str) else str(text),
        "data": data or {},
    }
    rec.events.append(ev)
    rec.updated_at = time.time()
    for q in list(rec.subscribers):
        try:
            q.put_nowait(ev)
        except asyncio.QueueFull:
            try:
                q.get_nowait()
                q.put_nowait(ev)
            except Exception:
                pass


def _safe_jid(job_id: str) -> Optional[str]:
    jid = "".join(c for c in (job_id or "") if c.isalnum())
    return jid or None


def _persist(rec: "JobRecord") -> None:
    """Write the full run log to disk so it's retrievable later."""
    jid = _safe_jid(rec.job_id)
    if not jid:
        return
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, f"{jid}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "job_id": rec.job_id,
                    "summary": rec.summary,
                    "state": rec.state,
                    "created_at": rec.created_at,
                    "finished_at": rec.finished_at,
                    "events": list(rec.events),
                },
                f,
                ensure_ascii=False,
                default=str,
            )
        os.replace(tmp, path)
    except Exception:
        pass


def list_persisted() -> list[dict]:
    """Metadata of persisted run logs, newest first (for the admin list)."""
    out: list[dict] = []
    try:
        for fn in os.listdir(LOG_DIR):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(LOG_DIR, fn), encoding="utf-8") as f:
                    d = json.load(f)
                out.append(
                    {
                        "job_id": d.get("job_id"),
                        "summary": d.get("summary"),
                        "state": d.get("state"),
                        "created_at": d.get("created_at"),
                        "finished_at": d.get("finished_at"),
                        "events": len(d.get("events") or []),
                    }
                )
            except Exception:
                continue
    except FileNotFoundError:
        return []
    out.sort(key=lambda x: x.get("finished_at") or 0, reverse=True)
    return out


def read_persisted(job_id: str) -> Optional[dict]:
    jid = _safe_jid(job_id)
    if not jid:
        return None
    try:
        with open(os.path.join(LOG_DIR, f"{jid}.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def finish(job_id: str, state: str) -> None:
    rec = JOBS.get(job_id)
    if rec is None:
        return
    rec.state = state if state in _TERMINAL else "success"
    rec.finished_at = time.time()
    rec.updated_at = rec.finished_at
    push(job_id, "state", f"__done__:{rec.state}", {"state": rec.state})
    _persist(rec)


def subscribe(job_id: str) -> Optional[asyncio.Queue]:
    rec = JOBS.get(job_id)
    if rec is None:
        return None
    q: asyncio.Queue = asyncio.Queue(maxsize=512)
    rec.subscribers.append(q)
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    rec = JOBS.get(job_id)
    if rec is None:
        return
    try:
        rec.subscribers.remove(q)
    except ValueError:
        pass


def prune(ttl: int = _DEFAULT_PRUNE_TTL) -> None:
    """Drop terminal jobs from memory after ttl (the iframe becomes
    discardable). Persisted logs survive separately and are aged out by
    retention days / max-files so old runs stay debuggable for a while."""
    now = time.time()
    for jid in list(JOBS):
        rec = JOBS[jid]
        if (
            rec.state in _TERMINAL
            and rec.finished_at is not None
            and now - rec.finished_at > ttl
        ):
            JOBS.pop(jid, None)
    # Persisted-log retention.
    try:
        files = [
            os.path.join(LOG_DIR, fn)
            for fn in os.listdir(LOG_DIR)
            if fn.endswith(".json")
        ]
    except FileNotFoundError:
        return
    cutoff = now - _LOG_RETENTION_DAYS * 86400
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for i, p in enumerate(files):
        try:
            if i >= _LOG_MAX_FILES or os.path.getmtime(p) < cutoff:
                os.remove(p)
        except Exception:
            pass


def is_terminal(state: str) -> bool:
    return state in _TERMINAL


# ---------------------------------------------------------------------------
# Stateless access token: base64url(job_id).<exp>.<hmac>
# ---------------------------------------------------------------------------

_TOKEN_TTL = 2 * 60 * 60  # >= max run budget


def _sign(job_id: str, exp: int) -> str:
    msg = f"{job_id}.{exp}".encode("utf-8")
    sig = hmac.new(
        (WEBUI_SECRET_KEY or "").encode("utf-8"), msg, sha256
    ).digest()[:16]
    return base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")


def sign_job_token(job_id: str, ttl_seconds: int = _TOKEN_TTL) -> str:
    exp = int(time.time()) + ttl_seconds
    return f"{job_id}.{exp}.{_sign(job_id, exp)}"


def verify_job_token(token: str) -> Optional[str]:
    """Return the job_id if the token is well-formed, unexpired and valid."""
    try:
        job_id, exp_s, sig = token.split(".", 2)
        exp = int(exp_s)
    except (ValueError, AttributeError):
        return None
    if exp < int(time.time()):
        return None
    if not hmac.compare_digest(sig, _sign(job_id, exp)):
        return None
    return job_id
