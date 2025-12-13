import asyncio
import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import case, func, or_

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import get_db
from open_webui.models.stt_credit_ledger import SttCreditLedger
from open_webui.models.users import User
from open_webui.utils.auth import get_current_user
from open_webui.utils.domain_credits import get_domain_status
from open_webui.utils.stt_credits import DEFAULT_FREE_CREDITS_LIMIT, get_credits_status

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ROUTERS", logging.INFO))

router = APIRouter()


def get_admin_user_403(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return user


class AdminDomainCredits(BaseModel):
    unit: str
    cost: Optional[int] = None

    free_used: int = 0
    free_limit: int = 0
    free_remaining: int = 0

    paid_balance: int = 0
    paid_remaining: int = 0

    total_remaining: int = 0


class AdminCreditsUserRow(BaseModel):
    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None

    domains: dict[str, AdminDomainCredits] = {}

    total_purchased_credits_audio: int = 0
    total_used_credits_audio: int = 0
    last_credit_activity_audio: Optional[int] = None


class AdminCreditsUsersResponse(BaseModel):
    redis_available: bool
    users: list[AdminCreditsUserRow]
    total: int


class AdminCreditsDomainStats(BaseModel):
    unit: str
    cost: Optional[int] = None
    total_free_remaining: Optional[int] = None
    total_paid_balance: Optional[int] = None
    total_remaining: Optional[int] = None


class AdminCreditsStatsResponse(BaseModel):
    redis_available: bool
    total_users: int
    domains: dict[str, AdminCreditsDomainStats]

    total_purchased_credits_audio: int = 0
    total_used_credits_audio: int = 0
    total_credits_issued_audio: Optional[int] = None
    total_revenue_by_currency_minor: Optional[dict[str, int]] = None


class AdminCreditsPurchase(BaseModel):
    purchase_id: str
    credits: int
    price_minor: Optional[int] = None
    currency: Optional[str] = None
    payment_provider: Optional[str] = None
    purchase_date: int
    status: Optional[str] = None
    package_code: Optional[str] = None


class AdminCreditsUserDetailResponse(BaseModel):
    redis_available: bool
    user: dict[str, Any]
    domains: dict[str, AdminDomainCredits] = {}

    total_purchased_credits_audio: int = 0
    total_used_credits_audio: int = 0
    last_credit_activity_audio: Optional[int] = None
    purchases_audio: list[AdminCreditsPurchase] = []


def _now_ts() -> int:
    return int(time.time())


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _peek_user_domains(
    request: Request,
    *,
    redis,
    user_id: str,
    now_ts: int,
) -> dict[str, AdminDomainCredits]:
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

    audio_status = await get_credits_status(
        redis, user_id=user_id, now_ts=now_ts, free_limit=audio_free_limit
    )

    photo_status = await get_domain_status(
        redis, domain="photo", subject_id=user_id, free_limit=photo_free_limit
    )
    video_status = await get_domain_status(
        redis, domain="video", subject_id=user_id, free_limit=video_free_limit
    )
    music_status = await get_domain_status(
        redis, domain="music", subject_id=user_id, free_limit=music_free_limit
    )

    photo_paid_remaining = int(photo_status.paid_balance) // photo_cost if photo_cost > 0 else int(photo_status.paid_balance)
    video_paid_remaining = int(video_status.paid_balance) // video_cost if video_cost > 0 else int(video_status.paid_balance)
    music_paid_remaining = int(music_status.paid_balance) // music_cost if music_cost > 0 else int(music_status.paid_balance)

    return {
        "audio": AdminDomainCredits(
            unit="credits",
            cost=1,
            free_used=int(audio_status.free_used),
            free_limit=int(audio_status.free_limit),
            free_remaining=int(audio_status.free_remaining),
            paid_balance=int(audio_status.paid_balance),
            paid_remaining=int(audio_status.paid_balance),
            total_remaining=int(audio_status.total_remaining),
        ),
        "photo": AdminDomainCredits(
            unit="generations",
            cost=photo_cost if photo_cost > 0 else None,
            free_used=int(photo_status.free_used),
            free_limit=int(photo_status.free_limit),
            free_remaining=int(photo_status.free_remaining),
            paid_balance=int(photo_status.paid_balance),
            paid_remaining=int(photo_paid_remaining),
            total_remaining=int(photo_status.free_remaining) + int(photo_paid_remaining),
        ),
        "video": AdminDomainCredits(
            unit="generations",
            cost=video_cost if video_cost > 0 else None,
            free_used=int(video_status.free_used),
            free_limit=int(video_status.free_limit),
            free_remaining=int(video_status.free_remaining),
            paid_balance=int(video_status.paid_balance),
            paid_remaining=int(video_paid_remaining),
            total_remaining=int(video_status.free_remaining) + int(video_paid_remaining),
        ),
        "music": AdminDomainCredits(
            unit="generations",
            cost=music_cost if music_cost > 0 else None,
            free_used=int(music_status.free_used),
            free_limit=int(music_status.free_limit),
            free_remaining=int(music_status.free_remaining),
            paid_balance=int(music_status.paid_balance),
            paid_remaining=int(music_paid_remaining),
            total_remaining=int(music_status.free_remaining) + int(music_paid_remaining),
        ),
    }


def _ledger_aggregate_audio_by_user(user_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not user_ids:
        return {}

    aggregated: dict[str, dict[str, Any]] = {}

    try:
        with get_db() as db:
            rows = (
                db.query(
                    SttCreditLedger.user_id,
                    func.sum(
                        case(
                            (SttCreditLedger.credits_delta > 0, SttCreditLedger.credits_delta),
                            else_=0,
                        )
                    ).label("purchased"),
                    func.sum(
                        case(
                            (SttCreditLedger.credits_delta < 0, -SttCreditLedger.credits_delta),
                            else_=0,
                        )
                    ).label("used"),
                    func.max(SttCreditLedger.created_at).label("last_activity"),
                )
                .filter(SttCreditLedger.user_id.in_(user_ids))
                .group_by(SttCreditLedger.user_id)
                .all()
            )

            for r in rows:
                aggregated[str(r.user_id)] = {
                    "total_purchased_credits_audio": int(r.purchased or 0),
                    "total_used_credits_audio": int(r.used or 0),
                    "last_credit_activity_audio": int(r.last_activity) if r.last_activity else None,
                }
    except Exception:
        log.exception("Failed to aggregate admin credits ledger data")

    return aggregated


def _ledger_audio_totals() -> dict[str, Any]:
    totals: dict[str, Any] = {
        "total_purchased_credits_audio": 0,
        "total_used_credits_audio": 0,
        "total_revenue_by_currency_minor": None,
    }

    try:
        with get_db() as db:
            purchased = (
                db.query(
                    func.sum(
                        case(
                            (SttCreditLedger.credits_delta > 0, SttCreditLedger.credits_delta),
                            else_=0,
                        )
                    )
                ).scalar()
                or 0
            )
            used = (
                db.query(
                    func.sum(
                        case(
                            (SttCreditLedger.credits_delta < 0, -SttCreditLedger.credits_delta),
                            else_=0,
                        )
                    )
                ).scalar()
                or 0
            )

            totals["total_purchased_credits_audio"] = int(purchased or 0)
            totals["total_used_credits_audio"] = int(used or 0)

            # Revenue is stored in Stripe webhook meta (amount_total + currency).
            rows = (
                db.query(SttCreditLedger.meta, SttCreditLedger.credits_delta)
                .filter(SttCreditLedger.credits_delta > 0)
                .all()
            )
            revenue: dict[str, int] = {}
            for meta, delta in rows:
                if not meta or not isinstance(meta, dict):
                    continue
                currency = meta.get("currency")
                amount_total = meta.get("amount_total")
                if not currency or amount_total is None:
                    continue
                try:
                    revenue[str(currency)] = revenue.get(str(currency), 0) + int(amount_total)
                except Exception:
                    continue

            totals["total_revenue_by_currency_minor"] = revenue or None
    except Exception:
        log.exception("Failed to compute admin credits totals")

    return totals


def _purchase_rows_audio(user_id: str) -> list[AdminCreditsPurchase]:
    purchases: list[AdminCreditsPurchase] = []
    try:
        with get_db() as db:
            entries = (
                db.query(
                    SttCreditLedger.credits_delta,
                    SttCreditLedger.reference_id,
                    SttCreditLedger.meta,
                    SttCreditLedger.created_at,
                )
                .filter(SttCreditLedger.user_id == str(user_id))
                .filter(SttCreditLedger.credits_delta > 0)
                .order_by(SttCreditLedger.created_at.desc())
                .limit(100)
                .all()
            )
            for credits_delta, reference_id, meta, created_at in entries:
                try:
                    credits = int(credits_delta or 0)
                except Exception:
                    credits = 0
                if credits <= 0:
                    continue

                meta = meta if isinstance(meta, dict) else {}
                purchases.append(
                    AdminCreditsPurchase(
                        purchase_id=str(reference_id or ""),
                        credits=int(credits),
                        price_minor=meta.get("amount_total"),
                        currency=meta.get("currency"),
                        payment_provider=meta.get("provider"),
                        purchase_date=int(created_at or 0),
                        status=meta.get("status"),
                        package_code=meta.get("package_code"),
                    )
                )
    except Exception:
        log.exception("Failed to load purchases for admin credits user_id=%s", user_id)

    return purchases


@router.get("/stats", response_model=AdminCreditsStatsResponse)
async def get_admin_credits_stats(request: Request, user=Depends(get_admin_user_403)):
    redis_available = request.app.state.redis is not None

    total_users = 0
    try:
        with get_db() as db:
            total_users = int(db.query(func.count(User.id)).scalar() or 0)
    except Exception:
        log.exception("Failed to compute total users for admin credits dashboard")

    domains: dict[str, AdminCreditsDomainStats] = {
        "audio": AdminCreditsDomainStats(unit="credits", cost=1),
        "photo": AdminCreditsDomainStats(
            unit="generations",
            cost=int(getattr(request.app.state.config, "PHOTO_CREDITS_COST", 0) or 0) or None,
        ),
        "video": AdminCreditsDomainStats(
            unit="generations",
            cost=int(getattr(request.app.state.config, "VIDEO_CREDITS_COST", 0) or 0) or None,
        ),
        "music": AdminCreditsDomainStats(
            unit="generations",
            cost=int(getattr(request.app.state.config, "MUSIC_CREDITS_COST", 0) or 0) or None,
        ),
    }

    if redis_available:
        try:
            # For speed, only sum paid balances across users (free remaining depends on per-user usage).
            # Free remaining totals are still computed, but may be expensive on large instances.
            now_ts = _now_ts()
            with get_db() as db:
                user_ids = [str(u.id) for u in db.query(User.id).all()]

            async def peek(uid: str):
                return uid, await _peek_user_domains(
                    request, redis=request.app.state.redis, user_id=uid, now_ts=now_ts
                )

            results: list[tuple[str, dict[str, AdminDomainCredits]]] = []
            for chunk in _chunk(user_ids, 50):
                results.extend(await asyncio.gather(*[peek(uid) for uid in chunk]))

            totals_free: dict[str, int] = {"audio": 0, "photo": 0, "video": 0, "music": 0}
            totals_paid: dict[str, int] = {"audio": 0, "photo": 0, "video": 0, "music": 0}
            totals_remaining: dict[str, int] = {"audio": 0, "photo": 0, "video": 0, "music": 0}

            for _uid, dmap in results:
                for domain, d in dmap.items():
                    totals_free[domain] += int(d.free_remaining or 0)
                    totals_paid[domain] += int(d.paid_balance or 0)
                    totals_remaining[domain] += int(d.total_remaining or 0)

            for domain in domains.keys():
                domains[domain].total_free_remaining = totals_free.get(domain)
                domains[domain].total_paid_balance = totals_paid.get(domain)
                domains[domain].total_remaining = totals_remaining.get(domain)
        except Exception:
            log.exception("Failed to compute per-domain Redis totals for admin credits stats")

    ledger_totals = _ledger_audio_totals()
    issued = None
    try:
        if ledger_totals.get("total_purchased_credits_audio") is not None and ledger_totals.get(
            "total_used_credits_audio"
        ) is not None:
            issued = int(ledger_totals["total_purchased_credits_audio"]) + int(
                ledger_totals["total_used_credits_audio"]
            )
    except Exception:
        issued = None

    return AdminCreditsStatsResponse(
        redis_available=redis_available,
        total_users=int(total_users),
        domains=domains,
        total_purchased_credits_audio=int(ledger_totals.get("total_purchased_credits_audio", 0) or 0),
        total_used_credits_audio=int(ledger_totals.get("total_used_credits_audio", 0) or 0),
        total_credits_issued_audio=issued,
        total_revenue_by_currency_minor=ledger_totals.get("total_revenue_by_currency_minor"),
    )


@router.get("/users", response_model=AdminCreditsUsersResponse)
async def get_admin_credits_users(
    request: Request,
    user=Depends(get_admin_user_403),
    query: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    redis_available = request.app.state.redis is not None
    now_ts = _now_ts()

    users: list[User] = []
    total = 0

    try:
        with get_db() as db:
            q = db.query(User)
            if query:
                like = f"%{query}%"
                q = q.filter(or_(User.email.ilike(like), User.name.ilike(like)))
            total = int(q.count())
            users = (
                q.order_by(User.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
                .all()
            )
    except Exception:
        log.exception("Failed to list users for admin credits dashboard")
        users = []
        total = 0

    user_ids = [str(u.id) for u in users]
    ledger_by_user = _ledger_aggregate_audio_by_user(user_ids)

    credits_by_user: dict[str, dict[str, AdminDomainCredits]] = {}
    if redis_available and user_ids:
        async def peek(uid: str):
            return uid, await _peek_user_domains(
                request, redis=request.app.state.redis, user_id=uid, now_ts=now_ts
            )

        for chunk in _chunk(user_ids, 50):
            for uid, dmap in await asyncio.gather(*[peek(uid) for uid in chunk]):
                credits_by_user[uid] = dmap

    rows: list[AdminCreditsUserRow] = []
    for u in users:
        uid = str(u.id)
        ledger = ledger_by_user.get(uid, {})
        rows.append(
            AdminCreditsUserRow(
                user_id=uid,
                email=u.email,
                username=getattr(u, "name", None),
                role=getattr(u, "role", None),
                domains=credits_by_user.get(uid, {}),
                total_purchased_credits_audio=int(ledger.get("total_purchased_credits_audio", 0) or 0),
                total_used_credits_audio=int(ledger.get("total_used_credits_audio", 0) or 0),
                last_credit_activity_audio=ledger.get("last_credit_activity_audio"),
            )
        )

    return AdminCreditsUsersResponse(redis_available=redis_available, users=rows, total=total)


@router.get("/users/{user_id}", response_model=AdminCreditsUserDetailResponse)
async def get_admin_credits_user(
    request: Request,
    user_id: str,
    user=Depends(get_admin_user_403),
):
    redis_available = request.app.state.redis is not None
    now_ts = _now_ts()

    user_obj: User | None = None
    try:
        with get_db() as db:
            user_obj = db.query(User).filter(User.id == str(user_id)).first()
    except Exception:
        log.exception("Failed to load user %s for admin credits dashboard", user_id)

    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    domains: dict[str, AdminDomainCredits] = {}
    if redis_available:
        try:
            domains = await _peek_user_domains(
                request, redis=request.app.state.redis, user_id=str(user_id), now_ts=now_ts
            )
        except Exception:
            domains = {}

    ledger = _ledger_aggregate_audio_by_user([str(user_id)]).get(str(user_id), {})
    purchases = _purchase_rows_audio(str(user_id))

    return AdminCreditsUserDetailResponse(
        redis_available=redis_available,
        user={
            "id": str(user_obj.id),
            "email": user_obj.email,
            "username": getattr(user_obj, "name", None),
            "name": getattr(user_obj, "name", None),
            "role": getattr(user_obj, "role", None),
        },
        domains=domains,
        total_purchased_credits_audio=int(ledger.get("total_purchased_credits_audio", 0) or 0),
        total_used_credits_audio=int(ledger.get("total_used_credits_audio", 0) or 0),
        last_credit_activity_audio=ledger.get("last_credit_activity_audio"),
        purchases_audio=purchases,
    )

