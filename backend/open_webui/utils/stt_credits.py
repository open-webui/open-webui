import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from open_webui.env import REDIS_KEY_PREFIX, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("AUDIO", logging.INFO))


DEFAULT_FREE_CREDITS_LIMIT = 500

# Legacy fields retained for API compatibility. Free credits are enforced as a simple
# monotonic allowance (no automatic reset window) to support strict anonymous limits.
WEEKLY_FREE_CREDITS_PERIOD_SECONDS = 0
WEEKLY_FREE_CREDITS_TTL_GRACE_SECONDS = 0

# Used for reconnect deduplication. We store recent committed segment signatures for a short
# time to avoid double-charging when a WS reconnect replays the same committed transcript.
DEDUP_WINDOW_SECONDS = 10 * 60
DEDUP_TTL_SECONDS = DEDUP_WINDOW_SECONDS + 60

# One active realtime STT session per user.
SESSION_LOCK_TTL_SECONDS = 60
SESSION_LOCK_REFRESH_SECONDS = 15


AUTH_REQUIRED_MESSAGE_KA = "ხმოვანი რეჟიმით სარგებლობისთვის გთხოვთ გაიაროთ ავტორიზაცია."
LIMIT_EXHAUSTED_MESSAGE_KA = (
    "თქვენი ხმოვანი ლიმიტი ამოიწურა. დამატებითი კრედიტების შესაძენად გახსენით პროფილი და აირჩიეთ პაკეტი."
)


def _now_ts() -> int:
    return int(time.time())


def _redis_prefix(prefix: str | None = None) -> str:
    return prefix or REDIS_KEY_PREFIX


def free_credits_key(*, user_id: str, prefix: str | None = None) -> str:
    return f"{_redis_prefix(prefix)}:stt:credits:free:user:{user_id}"


def paid_credits_key(*, user_id: str, prefix: str | None = None) -> str:
    return f"{_redis_prefix(prefix)}:stt:credits:paid:user:{user_id}"


def dedup_key(*, user_id: str, prefix: str | None = None) -> str:
    return f"{_redis_prefix(prefix)}:stt:dedup:user:{user_id}"


def session_lock_key(*, user_id: str, prefix: str | None = None) -> str:
    return f"{_redis_prefix(prefix)}:stt:session:user:{user_id}"


def stripe_event_key(*, event_id: str, prefix: str | None = None) -> str:
    return f"{_redis_prefix(prefix)}:stripe:event:{event_id}"


_STRIPE_APPLY_PAID_CREDITS_LUA = """
local event_key = KEYS[1]
local paid_key = KEYS[2]
local credits = tonumber(ARGV[1])
local now_ts = tonumber(ARGV[2]) or 0

if not credits or credits <= 0 then
  local bal = redis.call('HGET', paid_key, 'credits_balance') or '0'
  return {0, bal}
end

if redis.call('EXISTS', event_key) == 1 then
  local bal = redis.call('HGET', paid_key, 'credits_balance') or '0'
  return {0, bal}
end

redis.call('SET', event_key, '1')

local current = redis.call('HGET', paid_key, 'credits_balance')
if current and tonumber(current) == nil then
  redis.call('HSET', paid_key, 'credits_balance', 0)
end

local new_balance = redis.call('HINCRBY', paid_key, 'credits_balance', credits)
if now_ts > 0 then
  redis.call('HSET', paid_key, 'updated_at', now_ts)
end

return {1, new_balance}
"""


def normalize_text_for_credits(text: str) -> str:
    return " ".join((text or "").split()).strip()


def count_credits(text: str) -> int:
    normalized = normalize_text_for_credits(text)
    return len(normalized)


def committed_segment_signature(text: str, *, words: Any | None = None) -> str:
    normalized = normalize_text_for_credits(text)
    if not normalized:
        return ""

    start: Optional[float] = None
    end: Optional[float] = None

    if isinstance(words, list):
        for w in words:
            if not isinstance(w, dict):
                continue
            if w.get("type") not in {"word", "spacing"}:
                continue
            try:
                s = float(w.get("start")) if w.get("start") is not None else None
                e = float(w.get("end")) if w.get("end") is not None else None
            except Exception:
                s = None
                e = None

            if s is not None:
                start = s if start is None else min(start, s)
            if e is not None:
                end = e if end is None else max(end, e)

    signature_source = (
        f"{normalized}|{start:.3f}|{end:.3f}" if start is not None and end is not None else normalized
    )
    return hashlib.sha256(signature_source.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CreditsStatus:
    free_used: int
    free_limit: int
    period_start: int
    reset_at: int
    paid_balance: int

    @property
    def free_remaining(self) -> int:
        return max(0, self.free_limit - self.free_used)

    @property
    def total_remaining(self) -> int:
        return self.free_remaining + self.paid_balance


async def _get_or_init_weekly_free_credits(redis, *, user_id: str, now_ts: int) -> CreditsStatus:
    key = free_credits_key(user_id=user_id)
    raw = await redis.hgetall(key)

    if not raw:
        await redis.hset(
            key,
            mapping={
                "credits_used": 0,
                "credits_limit": DEFAULT_FREE_CREDITS_LIMIT,
                "period_start": now_ts,
                "reset_at": 0,
            },
        )
        return CreditsStatus(
            free_used=0,
            free_limit=DEFAULT_FREE_CREDITS_LIMIT,
            period_start=now_ts,
            reset_at=0,
            paid_balance=0,
        )

    try:
        free_used = int(raw.get("credits_used", 0))
    except Exception:
        free_used = 0
    try:
        free_limit = int(raw.get("credits_limit", DEFAULT_FREE_CREDITS_LIMIT))
    except Exception:
        free_limit = DEFAULT_FREE_CREDITS_LIMIT
    try:
        period_start = int(raw.get("period_start", now_ts))
    except Exception:
        period_start = now_ts
    try:
        reset_at = int(raw.get("reset_at", 0))
    except Exception:
        reset_at = 0

    # Legacy window fields are no longer enforced. Keep reset_at == 0.
    if reset_at != 0:
        reset_at = 0
        await redis.hset(key, mapping={"reset_at": 0})

    return CreditsStatus(
        free_used=max(0, free_used),
        free_limit=max(0, free_limit),
        period_start=period_start,
        reset_at=0,
        paid_balance=0,
    )


async def _get_paid_balance(redis, *, user_id: str) -> int:
    key = paid_credits_key(user_id=user_id)
    raw = await redis.hget(key, "credits_balance")
    try:
        return max(0, int(raw or 0))
    except Exception:
        return 0


async def get_credits_status(
    redis,
    *,
    user_id: str,
    now_ts: int | None = None,
    free_limit: int | None = None,
) -> CreditsStatus:
    now_ts = now_ts or _now_ts()
    free_status = await _get_or_init_weekly_free_credits(redis, user_id=user_id, now_ts=now_ts)

    # Override persisted limit to match the configured free_limit when provided.
    if free_limit is not None:
        free_limit = max(0, int(free_limit))
        if free_status.free_limit != free_limit:
            try:
                await redis.hset(free_credits_key(user_id=user_id), mapping={"credits_limit": free_limit})
            except Exception:
                pass
            free_status = CreditsStatus(
                free_used=free_status.free_used,
                free_limit=free_limit,
                period_start=free_status.period_start,
                reset_at=0,
                paid_balance=0,
            )
    paid_balance = await _get_paid_balance(redis, user_id=user_id)
    return CreditsStatus(
        free_used=free_status.free_used,
        free_limit=free_status.free_limit,
        period_start=free_status.period_start,
        reset_at=0,
        paid_balance=paid_balance,
    )


async def add_paid_credits(
    redis,
    *,
    user_id: str,
    credits: int,
    now_ts: int | None = None,
) -> int:
    if credits <= 0:
        return await _get_paid_balance(redis, user_id=user_id)

    now_ts = now_ts or _now_ts()
    key = paid_credits_key(user_id=user_id)
    pipe = redis.pipeline()
    pipe.hincrby(key, "credits_balance", int(credits))
    pipe.hset(key, mapping={"updated_at": int(now_ts)})
    results = await pipe.execute()
    try:
        return max(0, int(results[0] or 0))
    except Exception:
        return await _get_paid_balance(redis, user_id=user_id)


async def mark_stripe_event_processed(redis, *, event_id: str) -> bool:
    key = stripe_event_key(event_id=event_id)
    # SET NX without TTL (idempotency ledger).
    return bool(await redis.set(key, "1", nx=True))


async def apply_stripe_paid_credits(
    redis,
    *,
    event_id: str,
    user_id: str,
    credits: int,
    now_ts: int | None = None,
) -> tuple[bool, int]:
    """
    Atomically grants paid credits exactly once per Stripe event id.

    Returns: (applied, paid_balance_after)
    """
    if not user_id:
        return False, 0

    now_ts = now_ts or _now_ts()

    try:
        result = await redis.eval(
            _STRIPE_APPLY_PAID_CREDITS_LUA,
            2,
            stripe_event_key(event_id=event_id),
            paid_credits_key(user_id=user_id),
            int(credits),
            int(now_ts),
        )
    except Exception:
        # Let the webhook fail so Stripe retries (at-least-once delivery).
        raise

    applied = False
    balance = 0

    if isinstance(result, (list, tuple)) and len(result) >= 2:
        try:
            applied = bool(int(result[0]))
        except Exception:
            applied = False
        try:
            balance = max(0, int(result[1]))
        except Exception:
            balance = 0

    return applied, balance


async def acquire_session_lock(redis, *, user_id: str, value: str) -> bool:
    key = session_lock_key(user_id=user_id)
    return bool(
        await redis.set(
            key,
            value,
            nx=True,
            ex=SESSION_LOCK_TTL_SECONDS,
        )
    )


async def refresh_session_lock(redis, *, user_id: str, value: str) -> None:
    key = session_lock_key(user_id=user_id)
    try:
        current = await redis.get(key)
        if current == value:
            await redis.expire(key, SESSION_LOCK_TTL_SECONDS)
    except Exception:
        pass


async def release_session_lock(redis, *, user_id: str, value: str) -> None:
    key = session_lock_key(user_id=user_id)
    try:
        current = await redis.get(key)
        if current == value:
            await redis.delete(key)
    except Exception:
        pass


async def should_charge_committed_segment(
    redis,
    *,
    user_id: str,
    signature: str,
    now_ts: int,
) -> bool:
    if not signature:
        return False
    key = dedup_key(user_id=user_id)
    added = await redis.set(f"{key}:{signature}", "1", nx=True, ex=DEDUP_WINDOW_SECONDS)
    return bool(added)


async def charge_committed_transcript(
    redis,
    *,
    user_id: str,
    credits_needed: int,
    signature: str,
    now_ts: int,
    free_limit: int | None = None,
) -> tuple[CreditsStatus, bool, bool]:
    """
    Returns: (status, charged, exhausted_after)
    - charged: False if duplicate or credits_needed == 0
    - exhausted_after: True if total remaining == 0 after successful charge
    """
    status_before = await get_credits_status(
        redis, user_id=user_id, now_ts=now_ts, free_limit=free_limit
    )

    if credits_needed <= 0 or not signature:
        return status_before, False, status_before.total_remaining <= 0

    if status_before.total_remaining < credits_needed:
        return status_before, False, True

    should_charge = await should_charge_committed_segment(
        redis, user_id=user_id, signature=signature, now_ts=now_ts
    )
    if not should_charge:
        return status_before, False, status_before.total_remaining <= 0

    free_to_use = min(status_before.free_remaining, credits_needed)
    paid_to_use = credits_needed - free_to_use

    pipe = redis.pipeline()

    free_key = free_credits_key(user_id=user_id)
    if free_to_use > 0:
        pipe.hincrby(free_key, "credits_used", int(free_to_use))

    paid_key = paid_credits_key(user_id=user_id)
    if paid_to_use > 0:
        pipe.hincrby(paid_key, "credits_balance", -int(paid_to_use))
        pipe.hset(paid_key, mapping={"updated_at": int(now_ts)})

    await pipe.execute()

    status_after = await get_credits_status(
        redis, user_id=user_id, now_ts=now_ts, free_limit=free_limit
    )
    return status_after, True, status_after.total_remaining <= 0
