import time
from dataclasses import dataclass
from typing import Optional

from open_webui.env import REDIS_KEY_PREFIX, SRC_LOG_LEVELS

import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("AUDIO", logging.INFO))


@dataclass(frozen=True)
class DomainCreditsStatus:
    free_used: int
    free_limit: int
    paid_balance: int

    @property
    def free_remaining(self) -> int:
        return max(0, int(self.free_limit) - int(self.free_used))

    @property
    def total_remaining(self) -> int:
        return int(self.free_remaining) + max(0, int(self.paid_balance))


@dataclass(frozen=True)
class DomainGenerationPreflight:
    mode: str  # "free" | "paid"
    status: DomainCreditsStatus



def domain_free_key(*, domain: str, subject_id: str, prefix: str | None = None) -> str:
    prefix = prefix or REDIS_KEY_PREFIX
    return f"{prefix}:credits:{domain}:free:subject:{subject_id}"


def domain_paid_key(*, domain: str, subject_id: str, prefix: str | None = None) -> str:
    prefix = prefix or REDIS_KEY_PREFIX
    return f"{prefix}:credits:{domain}:paid:subject:{subject_id}"


async def get_domain_status(
    redis,
    *,
    domain: str,
    subject_id: str,
    free_limit: int,
) -> DomainCreditsStatus:
    free_key = domain_free_key(domain=domain, subject_id=subject_id)
    paid_key = domain_paid_key(domain=domain, subject_id=subject_id)

    try:
        raw_free_used = await redis.hget(free_key, "used")
    except Exception:
        raw_free_used = None

    try:
        raw_paid_balance = await redis.hget(paid_key, "balance")
    except Exception:
        raw_paid_balance = None

    try:
        free_used = max(0, int(raw_free_used or 0))
    except Exception:
        free_used = 0

    try:
        paid_balance = max(0, int(raw_paid_balance or 0))
    except Exception:
        paid_balance = 0

    return DomainCreditsStatus(
        free_used=free_used,
        free_limit=max(0, int(free_limit or 0)),
        paid_balance=paid_balance,
    )


async def increment_free_used(
    redis,
    *,
    domain: str,
    subject_id: str,
    amount: int,
    now_ts: int | None = None,
) -> int:
    amount = int(amount or 0)
    if amount <= 0:
        status = await get_domain_status(redis, domain=domain, subject_id=subject_id, free_limit=0)
        return status.free_used

    now_ts = int(now_ts or int(time.time()))
    key = domain_free_key(domain=domain, subject_id=subject_id)
    pipe = redis.pipeline()
    pipe.hincrby(key, "used", amount)
    pipe.hset(key, mapping={"updated_at": now_ts})
    res = await pipe.execute()
    try:
        return max(0, int(res[0] or 0))
    except Exception:
        return amount


async def deduct_paid_credits(
    redis,
    *,
    domain: str,
    subject_id: str,
    amount: int,
    now_ts: int | None = None,
) -> int:
    amount = int(amount or 0)
    if amount <= 0:
        status = await get_domain_status(redis, domain=domain, subject_id=subject_id, free_limit=0)
        return status.paid_balance

    now_ts = int(now_ts or int(time.time()))
    key = domain_paid_key(domain=domain, subject_id=subject_id)
    pipe = redis.pipeline()
    pipe.hincrby(key, "balance", -amount)
    pipe.hset(key, mapping={"updated_at": now_ts})
    res = await pipe.execute()
    try:
        return max(0, int(res[0] or 0))
    except Exception:
        return 0


async def add_paid_credits(
    redis,
    *,
    domain: str,
    subject_id: str,
    amount: int,
    now_ts: int | None = None,
) -> int:
    amount = int(amount or 0)
    if amount <= 0:
        status = await get_domain_status(redis, domain=domain, subject_id=subject_id, free_limit=0)
        return status.paid_balance

    now_ts = int(now_ts or int(time.time()))
    key = domain_paid_key(domain=domain, subject_id=subject_id)
    pipe = redis.pipeline()
    pipe.hincrby(key, "balance", amount)
    pipe.hset(key, mapping={"updated_at": now_ts})
    res = await pipe.execute()
    try:
        return max(0, int(res[0] or 0))
    except Exception:
        return amount


async def charge_generation(
    redis,
    *,
    domain: str,
    subject_id: str,
    free_limit: int,
    cost_credits: int,
    require_auth_after_free: bool,
    is_authenticated: bool,
    now_ts: int | None = None,
) -> tuple[DomainCreditsStatus, bool]:
    """
    Charges one generation:
    - uses free quota first (increments free_used by 1)
    - otherwise deducts paid credits

    Returns: (status_after, charged_paid)
    """
    now_ts = int(now_ts or int(time.time()))
    status_before = await get_domain_status(
        redis, domain=domain, subject_id=subject_id, free_limit=free_limit
    )

    if status_before.free_used < int(free_limit or 0):
        await increment_free_used(
            redis, domain=domain, subject_id=subject_id, amount=1, now_ts=now_ts
        )
        status_after = await get_domain_status(
            redis, domain=domain, subject_id=subject_id, free_limit=free_limit
        )
        return status_after, False

    if require_auth_after_free and not is_authenticated:
        raise PermissionError("AUTH_REQUIRED")

    cost_credits = int(cost_credits or 0)
    if cost_credits <= 0:
        return status_before, False

    if status_before.paid_balance < cost_credits:
        raise ValueError("INSUFFICIENT_CREDITS")

    await deduct_paid_credits(
        redis, domain=domain, subject_id=subject_id, amount=cost_credits, now_ts=now_ts
    )
    status_after = await get_domain_status(
        redis, domain=domain, subject_id=subject_id, free_limit=free_limit
    )
    return status_after, True


async def preflight_generation(
    redis,
    *,
    domain: str,
    subject_id: str,
    free_limit: int,
    cost_credits: int,
    require_auth_after_free: bool,
    is_authenticated: bool,
) -> DomainGenerationPreflight:
    status_before = await get_domain_status(
        redis, domain=domain, subject_id=subject_id, free_limit=free_limit
    )

    if status_before.free_used < int(free_limit or 0):
        return DomainGenerationPreflight(mode="free", status=status_before)

    if require_auth_after_free and not is_authenticated:
        raise PermissionError("AUTH_REQUIRED")

    cost_credits = int(cost_credits or 0)
    if cost_credits <= 0:
        return DomainGenerationPreflight(mode="free", status=status_before)

    if status_before.paid_balance < cost_credits:
        raise ValueError("INSUFFICIENT_CREDITS")

    return DomainGenerationPreflight(mode="paid", status=status_before)


async def commit_generation(
    redis,
    *,
    domain: str,
    subject_id: str,
    free_limit: int,
    mode: str,
    cost_credits: int,
    now_ts: int | None = None,
) -> tuple[DomainCreditsStatus, bool]:
    now_ts = int(now_ts or int(time.time()))

    if mode == "free":
        await increment_free_used(
            redis, domain=domain, subject_id=subject_id, amount=1, now_ts=now_ts
        )
        status_after = await get_domain_status(
            redis, domain=domain, subject_id=subject_id, free_limit=free_limit
        )
        return status_after, False

    if mode != "paid":
        raise ValueError("INVALID_MODE")

    cost_credits = int(cost_credits or 0)
    if cost_credits > 0:
        await deduct_paid_credits(
            redis, domain=domain, subject_id=subject_id, amount=cost_credits, now_ts=now_ts
        )

    status_after = await get_domain_status(
        redis, domain=domain, subject_id=subject_id, free_limit=free_limit
    )
    return status_after, True
