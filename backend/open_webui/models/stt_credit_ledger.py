import logging
import time
import uuid
from typing import Any

from sqlalchemy import BigInteger, Column, Integer, JSON, Text

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("DB", logging.INFO))


class SttCreditLedger(Base):
    __tablename__ = "stt_credit_ledger"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, nullable=False)

    # E.g. "stt_realtime_committed" or "stripe_webhook".
    source = Column(Text, nullable=False)

    # Signed deltas. Usage is negative, purchases are positive.
    credits_delta = Column(Integer, nullable=False)
    free_delta = Column(Integer, nullable=False, default=0)
    paid_delta = Column(Integer, nullable=False, default=0)

    # Provider event id (Stripe) or transcript signature (STT).
    reference_id = Column(Text, nullable=True)

    meta = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)


def _now_ts() -> int:
    return int(time.time())


def record_stt_credit_ledger_entry(
    *,
    user_id: str,
    source: str,
    credits_delta: int,
    free_delta: int = 0,
    paid_delta: int = 0,
    reference_id: str | None = None,
    meta: dict[str, Any] | None = None,
    now_ts: int | None = None,
) -> None:
    if not user_id or not source:
        return

    now_ts = int(now_ts or _now_ts())

    try:
        with get_db() as db:
            entry = SttCreditLedger(
                id=str(uuid.uuid4()),
                user_id=str(user_id),
                source=str(source),
                credits_delta=int(credits_delta),
                free_delta=int(free_delta),
                paid_delta=int(paid_delta),
                reference_id=str(reference_id) if reference_id else None,
                meta=meta,
                created_at=now_ts,
            )
            db.add(entry)
            db.commit()
    except Exception:
        log.exception(
            "Failed to write STT credit ledger entry user_id=%s source=%s", user_id, source
        )


def record_stt_credits_charge(
    *,
    user_id: str,
    signature: str,
    credits: int,
    free_credits: int,
    paid_credits: int,
    now_ts: int | None = None,
) -> None:
    record_stt_credit_ledger_entry(
        user_id=user_id,
        source="stt_realtime_committed",
        credits_delta=-int(credits),
        free_delta=-int(free_credits),
        paid_delta=-int(paid_credits),
        reference_id=signature,
        now_ts=now_ts,
    )


def record_tts_credits_charge(
    *,
    user_id: str,
    reference_id: str,
    credits: int,
    free_credits: int,
    paid_credits: int,
    meta: dict[str, Any] | None = None,
    now_ts: int | None = None,
) -> None:
    record_stt_credit_ledger_entry(
        user_id=user_id,
        source="tts_download",
        credits_delta=-int(credits),
        free_delta=-int(free_credits),
        paid_delta=-int(paid_credits),
        reference_id=reference_id,
        meta=meta,
        now_ts=now_ts,
    )


def record_stt_credits_purchase(
    *,
    user_id: str,
    stripe_event_id: str,
    package_code: str,
    credits: int,
    meta: dict[str, Any] | None = None,
    now_ts: int | None = None,
) -> None:
    purchase_meta = {"package_code": package_code}
    if isinstance(meta, dict):
        purchase_meta.update(meta)

    record_stt_credit_ledger_entry(
        user_id=user_id,
        source="stripe_webhook",
        credits_delta=int(credits),
        free_delta=0,
        paid_delta=int(credits),
        reference_id=stripe_event_id,
        meta=purchase_meta,
        now_ts=now_ts,
    )
