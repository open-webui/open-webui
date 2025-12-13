import logging
import os
import time
from typing import Any, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.utils.domain_credits import get_domain_status
from open_webui.utils.stt_credits import DEFAULT_FREE_CREDITS_LIMIT, get_credits_status

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ROUTERS", logging.INFO))

router = APIRouter()


class CreditsPackage(BaseModel):
    package_code: str
    credits: int
    label: str
    price_label: str
    enabled: bool = False


class DomainCreditsStatusResponse(BaseModel):
    enforced: bool = True
    unit: str = "credits"
    cost: Optional[int] = None
    free_used: int
    free_limit: int
    free_remaining: int
    paid_balance: int
    paid_remaining: int
    total_remaining: int
    packages: list[CreditsPackage]


class CreditsStatusResponse(BaseModel):
    redis_available: bool
    domains: dict[str, DomainCreditsStatusResponse]


class CreditsCheckoutForm(BaseModel):
    package_code: str
    domain: Optional[str] = "audio"


STT_CREDIT_PACKAGES: dict[str, dict[str, Any]] = {
    "10000": {
        "credits": 10_000,
        "label": "10,000",
        "price_label": "$5 or ƒ,_15",
        "price_id_env": "STRIPE_PRICE_ID_STT_10000",
    },
    "100000": {
        "credits": 100_000,
        "label": "100,000",
        "price_label": "$40",
        "price_id_env": "STRIPE_PRICE_ID_STT_100000",
    },
    "500000": {
        "credits": 500_000,
        "label": "500,000",
        "price_label": "$500",
        "price_id_env": "STRIPE_PRICE_ID_STT_500000",
    },
    "1000000": {
        "credits": 1_000_000,
        "label": "1,000,000",
        "price_label": "$700",
        "price_id_env": "STRIPE_PRICE_ID_STT_1000000",
    },
}


def _packages_public_audio() -> list[CreditsPackage]:
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    payments_configured = bool(stripe_key and webhook_secret)

    packages: list[CreditsPackage] = []
    for code, pkg in STT_CREDIT_PACKAGES.items():
        price_id = os.environ.get(pkg["price_id_env"], "")
        packages.append(
            CreditsPackage(
                package_code=code,
                credits=int(pkg["credits"]),
                label=str(pkg.get("label", code)),
                price_label=str(pkg.get("price_label", "")),
                enabled=payments_configured and bool(price_id),
            )
        )
    return packages


def _packages_public_from_config(raw: Any) -> list[CreditsPackage]:
    if not isinstance(raw, list):
        return []

    packages: list[CreditsPackage] = []
    for pkg in raw:
        if not isinstance(pkg, dict):
            continue
        try:
            packages.append(
                CreditsPackage(
                    package_code=str(pkg.get("package_code") or ""),
                    credits=int(pkg.get("credits") or 0),
                    label=str(pkg.get("label") or ""),
                    price_label=str(pkg.get("price_label") or ""),
                    enabled=bool(pkg.get("enabled") or False),
                )
            )
        except Exception:
            continue

    return [p for p in packages if p.package_code and p.credits > 0]


@router.get("/status", response_model=CreditsStatusResponse)
async def credits_status(request: Request, user: UserModel = Depends(get_verified_user)):
    redis_available = request.app.state.redis is not None
    is_admin = getattr(user, "role", None) == "admin"

    # Admin bypass: never block.
    if not redis_available and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credits system is not available.",
        )

    enforced = not is_admin

    audio_packages = _packages_public_audio()
    photo_packages = _packages_public_from_config(
        getattr(request.app.state.config, "PHOTO_CREDITS_PACKAGES", []) or []
    )
    video_packages = _packages_public_from_config(
        getattr(request.app.state.config, "VIDEO_CREDITS_PACKAGES", []) or []
    )
    music_packages = _packages_public_from_config(
        getattr(request.app.state.config, "MUSIC_CREDITS_PACKAGES", []) or []
    )

    if is_admin:
        unlimited = 2_147_483_647
        audio_free_limit = int(
            getattr(request.app.state.config, "AUDIO_CREDITS_FREE_AUTH", DEFAULT_FREE_CREDITS_LIMIT)
            or DEFAULT_FREE_CREDITS_LIMIT
        )
        photo_free_limit = int(getattr(request.app.state.config, "PHOTO_CREDITS_FREE_AUTH", 0) or 0)
        video_free_limit = int(getattr(request.app.state.config, "VIDEO_CREDITS_FREE_AUTH", 0) or 0)
        music_free_limit = int(getattr(request.app.state.config, "MUSIC_CREDITS_FREE_AUTH", 0) or 0)

        photo_cost = int(getattr(request.app.state.config, "PHOTO_CREDITS_COST", 0) or 0)
        video_cost = int(getattr(request.app.state.config, "VIDEO_CREDITS_COST", 0) or 0)
        music_cost = int(getattr(request.app.state.config, "MUSIC_CREDITS_COST", 0) or 0)

        return CreditsStatusResponse(
            redis_available=redis_available,
            domains={
                "audio": DomainCreditsStatusResponse(
                    enforced=False,
                    free_used=0,
                    unit="credits",
                    cost=1,
                    free_limit=audio_free_limit,
                    free_remaining=audio_free_limit,
                    paid_balance=unlimited,
                    paid_remaining=unlimited,
                    total_remaining=unlimited,
                    packages=audio_packages,
                ),
                "photo": DomainCreditsStatusResponse(
                    enforced=False,
                    unit="generations",
                    cost=photo_cost if photo_cost > 0 else None,
                    free_used=0,
                    free_limit=photo_free_limit,
                    free_remaining=photo_free_limit,
                    paid_balance=unlimited,
                    paid_remaining=unlimited,
                    total_remaining=unlimited,
                    packages=photo_packages,
                ),
                "video": DomainCreditsStatusResponse(
                    enforced=False,
                    unit="generations",
                    cost=video_cost if video_cost > 0 else None,
                    free_used=0,
                    free_limit=video_free_limit,
                    free_remaining=video_free_limit,
                    paid_balance=unlimited,
                    paid_remaining=unlimited,
                    total_remaining=unlimited,
                    packages=video_packages,
                ),
                "music": DomainCreditsStatusResponse(
                    enforced=False,
                    unit="generations",
                    cost=music_cost if music_cost > 0 else None,
                    free_used=0,
                    free_limit=music_free_limit,
                    free_remaining=music_free_limit,
                    paid_balance=unlimited,
                    paid_remaining=unlimited,
                    total_remaining=unlimited,
                    packages=music_packages,
                ),
            },
        )

    now_ts = int(time.time())

    audio_free_limit = int(getattr(request.app.state.config, "AUDIO_CREDITS_FREE_AUTH", DEFAULT_FREE_CREDITS_LIMIT) or DEFAULT_FREE_CREDITS_LIMIT)
    audio_status = await get_credits_status(
        request.app.state.redis, user_id=user.id, now_ts=now_ts, free_limit=audio_free_limit
    )

    photo_free_limit = int(getattr(request.app.state.config, "PHOTO_CREDITS_FREE_AUTH", 0) or 0)
    photo_status = await get_domain_status(
        request.app.state.redis, domain="photo", subject_id=user.id, free_limit=photo_free_limit
    )

    video_free_limit = int(getattr(request.app.state.config, "VIDEO_CREDITS_FREE_AUTH", 0) or 0)
    video_status = await get_domain_status(
        request.app.state.redis, domain="video", subject_id=user.id, free_limit=video_free_limit
    )

    music_free_limit = int(getattr(request.app.state.config, "MUSIC_CREDITS_FREE_AUTH", 0) or 0)
    music_status = await get_domain_status(
        request.app.state.redis, domain="music", subject_id=user.id, free_limit=music_free_limit
    )

    photo_cost = int(getattr(request.app.state.config, "PHOTO_CREDITS_COST", 0) or 0)
    video_cost = int(getattr(request.app.state.config, "VIDEO_CREDITS_COST", 0) or 0)
    music_cost = int(getattr(request.app.state.config, "MUSIC_CREDITS_COST", 0) or 0)

    photo_paid_remaining = (
        int(photo_status.paid_balance) // photo_cost if photo_cost > 0 else int(photo_status.paid_balance)
    )
    video_paid_remaining = (
        int(video_status.paid_balance) // video_cost if video_cost > 0 else int(video_status.paid_balance)
    )
    music_paid_remaining = (
        int(music_status.paid_balance) // music_cost if music_cost > 0 else int(music_status.paid_balance)
    )

    return CreditsStatusResponse(
        redis_available=redis_available,
        domains={
            "audio": DomainCreditsStatusResponse(
                enforced=enforced,
                unit="credits",
                cost=1,
                free_used=int(audio_status.free_used),
                free_limit=int(audio_status.free_limit),
                free_remaining=int(audio_status.free_remaining),
                paid_balance=int(audio_status.paid_balance),
                paid_remaining=int(audio_status.paid_balance),
                total_remaining=int(audio_status.total_remaining),
                packages=audio_packages,
            ),
            "photo": DomainCreditsStatusResponse(
                enforced=enforced,
                unit="generations",
                cost=photo_cost if photo_cost > 0 else None,
                free_used=int(photo_status.free_used),
                free_limit=int(photo_status.free_limit),
                free_remaining=int(photo_status.free_remaining),
                paid_balance=int(photo_status.paid_balance),
                paid_remaining=int(photo_paid_remaining),
                total_remaining=int(photo_status.free_remaining) + int(photo_paid_remaining),
                packages=photo_packages,
            ),
            "video": DomainCreditsStatusResponse(
                enforced=enforced,
                unit="generations",
                cost=video_cost if video_cost > 0 else None,
                free_used=int(video_status.free_used),
                free_limit=int(video_status.free_limit),
                free_remaining=int(video_status.free_remaining),
                paid_balance=int(video_status.paid_balance),
                paid_remaining=int(video_paid_remaining),
                total_remaining=int(video_status.free_remaining) + int(video_paid_remaining),
                packages=video_packages,
            ),
            "music": DomainCreditsStatusResponse(
                enforced=enforced,
                unit="generations",
                cost=music_cost if music_cost > 0 else None,
                free_used=int(music_status.free_used),
                free_limit=int(music_status.free_limit),
                free_remaining=int(music_status.free_remaining),
                paid_balance=int(music_status.paid_balance),
                paid_remaining=int(music_paid_remaining),
                total_remaining=int(music_status.free_remaining) + int(music_paid_remaining),
                packages=music_packages,
            ),
        },
    )


@router.post("/checkout")
async def create_checkout(
    request: Request, form_data: CreditsCheckoutForm, user: UserModel = Depends(get_verified_user)
):
    domain = (form_data.domain or "audio").strip().lower()
    if domain != "audio":
        raise HTTPException(status_code=400, detail="Checkout is only supported for audio credits.")

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Payments are not configured.")

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured.")

    if request.app.state.redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credits system is not available.",
        )

    package = STT_CREDIT_PACKAGES.get(form_data.package_code)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package_code")

    price_id = os.environ.get(package["price_id_env"], "")
    if not price_id:
        raise HTTPException(status_code=400, detail="This package is not available.")

    webui_url = (request.app.state.config.WEBUI_URL or "").rstrip("/")
    if not webui_url:
        webui_url = str(request.base_url).rstrip("/")

    success_url = os.environ.get("STRIPE_SUCCESS_URL", "") or f"{webui_url}/?credits=success"
    cancel_url = os.environ.get("STRIPE_CANCEL_URL", "") or f"{webui_url}/?credits=cancel"

    credits_amount = int(package["credits"])

    payload = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": user.id,
        "customer_email": user.email,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": 1,
        "metadata[user_id]": user.id,
        "metadata[package_code]": form_data.package_code,
        "metadata[credits]": str(credits_amount),
        "metadata[domain]": "audio",
    }

    try:
        res = requests.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=payload,
            headers={"Authorization": f"Bearer {stripe_key}"},
            timeout=20,
        )
        res.raise_for_status()
        data = res.json()
        url = data.get("url")
        if not url:
            raise HTTPException(status_code=500, detail="Failed to create checkout session.")
        return {"url": url}
    except requests.RequestException as e:
        log.exception("Stripe checkout session failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment provider error.")
