"""
Inbound callback receiver for the Swept Workbench supervision pipeline.

When Workbench finishes evaluating a SupervisionEvent (that this Open WebUI
instance previously sent via the supervision filter plugin), it POSTs to
`/api/v1/supervision/callback` here (router is mounted under `/api/v1` in
`main.py`). The request is HMAC-signed; we verify the signature, persist
the payload, and 200 back.

V1: persistence only. Nothing is surfaced in the chat UI. Read rows from
the `supervision_callback` table for now; UI integration can layer on
later without changing the wire protocol.

Configuration (env vars, read at request time so a redeploy isn't needed
to rotate a secret):
  WORKBENCH_CALLBACK_SECRET   shared HMAC secret matching
                              AgentConfig.config["callback_secret"] in Workbench
  WORKBENCH_CALLBACK_SKEW_SEC max timestamp drift in seconds (default 300);
                              non-integer values fall back to the default
"""

import hashlib
import hmac
import json
import logging
import os
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_session
from open_webui.models.supervision_callbacks import (
    SupervisionCallback,
    SupervisionCallbackModel,
    now_seconds,
)

log = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_SKEW_SECONDS = 300
SIGNATURE_VERSION = 'v1'


def _skew_seconds() -> int:
    raw = os.environ.get('WORKBENCH_CALLBACK_SKEW_SEC')
    if raw is None:
        return DEFAULT_SKEW_SECONDS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning(
            'WORKBENCH_CALLBACK_SKEW_SEC=%r is not an integer; using default %d',
            raw,
            DEFAULT_SKEW_SECONDS,
        )
        return DEFAULT_SKEW_SECONDS
    if value < 0:
        # A negative skew would make abs(now - ts) > skew always true and
        # reject every well-formed callback. Treat misconfiguration as
        # "use the default" rather than silently disabling supervision.
        log.warning(
            'WORKBENCH_CALLBACK_SKEW_SEC=%d is negative; using default %d',
            value,
            DEFAULT_SKEW_SECONDS,
        )
        return DEFAULT_SKEW_SECONDS
    return value


def _verify_signature(
    secret: str,
    timestamp: str | None,
    body: bytes,
    signature_header: str | None,
) -> bool:
    if not (secret and timestamp and signature_header):
        return False
    if '=' not in signature_header:
        return False
    version, sig = signature_header.split('=', 1)
    if version != SIGNATURE_VERSION:
        return False
    try:
        ts_int = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - ts_int) > _skew_seconds():
        return False
    # Concatenate as bytes directly — avoids a decode round-trip that could
    # raise UnicodeDecodeError on a malformed body. Workbench signs the exact
    # bytes it puts on the wire, so this matches its calculation precisely.
    signed_payload = timestamp.encode('utf-8') + b'.' + body
    expected = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


@router.post('/callback', response_model=SupervisionCallbackModel)
async def receive_supervision_callback(
    request: Request,
    x_workbench_timestamp: str | None = Header(default=None, alias='X-Workbench-Timestamp'),
    x_workbench_signature: str | None = Header(default=None, alias='X-Workbench-Signature'),
    db: AsyncSession = Depends(get_async_session),
):
    secret = os.environ.get('WORKBENCH_CALLBACK_SECRET', '').strip()
    if not secret:
        log.error('WORKBENCH_CALLBACK_SECRET is not configured; rejecting supervision callback')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='supervision_disabled')

    body = await request.body()

    if not _verify_signature(secret, x_workbench_timestamp, body, x_workbench_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid_signature')

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invalid_json')

    if not isinstance(payload, dict):
        # JSON arrays / scalars are syntactically valid but useless here —
        # subsequent payload.get() would raise AttributeError. Reject as a
        # client error instead of 500ing.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invalid_payload_shape')

    event_id = payload.get('event_id')
    supervision_session_id = payload.get('supervision_session_id')
    evaluation_status = payload.get('evaluation_status')

    if not (event_id and supervision_session_id and evaluation_status):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='missing_required_field')

    record = SupervisionCallback(
        id=str(uuid.uuid4()),
        event_id=event_id,
        supervision_session_id=supervision_session_id,
        agent_name=payload.get('agent_name') or '',
        evaluation_status=evaluation_status,
        external_message_id=payload.get('external_message_id'),
        external_chat_id=payload.get('external_chat_id'),
        evaluated_at=payload.get('evaluated_at'),
        raw=payload,
        received_at=now_seconds(),
    )

    # Idempotency on event_id: Workbench's retry_on can fire up to 5x per
    # event. We use a plain insert + IntegrityError catch so the route
    # works on Postgres and SQLite without dialect-specific upsert syntax.
    try:
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return SupervisionCallbackModel.model_validate(record)
    except IntegrityError as exc:
        await db.rollback()
        existing_result = await db.execute(select(SupervisionCallback).where(SupervisionCallback.event_id == event_id))
        existing = existing_result.scalar_one_or_none()
        if existing is None:
            # IntegrityError wasn't the event_id uniqueness conflict we
            # expected — surface the real cause instead of masking it as
            # a successful idempotent replay.
            log.exception('Unexpected IntegrityError on supervision callback insert')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='callback_persist_failed',
            ) from exc
        return SupervisionCallbackModel.model_validate(existing)
