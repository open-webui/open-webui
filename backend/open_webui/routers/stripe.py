import hmac
import json
import logging
import os
import time
from hashlib import sha256
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.stt_credit_ledger import record_stt_credits_purchase
from open_webui.utils.stt_credits import apply_stripe_paid_credits

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ROUTERS", logging.INFO))

router = APIRouter()


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> None:
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    parts = {}
    for item in sig_header.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            parts.setdefault(k.strip(), []).append(v.strip())

    try:
        timestamp = int(parts.get("t", ["0"])[0])
    except Exception:
        timestamp = 0

    if not timestamp:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature header")

    tolerance = int(os.environ.get("STRIPE_WEBHOOK_TOLERANCE_SECONDS", "300") or "300")
    if abs(int(time.time()) - timestamp) > tolerance:
        raise HTTPException(status_code=400, detail="Expired Stripe signature header")

    signed_payload = str(timestamp).encode("utf-8") + b"." + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, sha256).hexdigest()

    signatures = parts.get("v1", [])
    if not any(hmac.compare_digest(expected, s) for s in signatures):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured.")

    if request.app.state.redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credits system is not available.",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    _verify_stripe_signature(payload, sig_header, webhook_secret)

    try:
        event = json.loads(payload.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = event.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event id")

    event_type = event.get("type", "")
    if event_type not in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        return {"status": "ignored"}

    session = ((event.get("data") or {}).get("object") or {})
    if not isinstance(session, dict):
        return {"status": "ignored"}

    payment_status = session.get("payment_status")
    if payment_status and payment_status != "paid":
        return {"status": "ignored"}

    user_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("user_id")
    if not user_id:
        log.warning("Stripe checkout completed without user_id. event_id=%s", event_id)
        return {"status": "ignored"}

    metadata = session.get("metadata") or {}
    package_code = metadata.get("package_code")
    if not package_code:
        log.warning("Stripe checkout completed without package_code. event_id=%s", event_id)
        return {"status": "ignored"}

    try:
        from open_webui.routers.credits import STT_CREDIT_PACKAGES

        package = STT_CREDIT_PACKAGES.get(str(package_code))
    except Exception:
        package = None

    if not package:
        log.warning(
            "Stripe checkout completed with unknown package_code=%s event_id=%s",
            package_code,
            event_id,
        )
        return {"status": "ignored"}

    try:
        credits = int(package.get("credits") or 0)
    except Exception:
        credits = 0

    if credits <= 0:
        log.warning("Stripe checkout completed without credits. event_id=%s", event_id)
        return {"status": "ignored"}

    now_ts = int(time.time())
    applied, balance = await apply_stripe_paid_credits(
        request.app.state.redis,
        event_id=event_id,
        user_id=user_id,
        credits=credits,
        now_ts=now_ts,
    )
    if applied:
        purchase_meta: dict[str, Any] = {
            "provider": "stripe",
            "status": "completed",
            "session_id": session.get("id"),
            "amount_total": session.get("amount_total"),
            "currency": session.get("currency"),
        }
        record_stt_credits_purchase(
            user_id=str(user_id),
            stripe_event_id=str(event_id),
            package_code=str(package_code),
            credits=int(credits),
            meta=purchase_meta,
            now_ts=now_ts,
        )
        log.info(
            "Stripe credits applied user_id=%s credits=%s paid_balance=%s event_id=%s",
            user_id,
            credits,
            balance,
            event_id,
        )
    return {"status": "ok"}
