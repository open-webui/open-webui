"""Cost tracking and budget enforcement for TracexGPT.

Per-user monthly spending limits with IST timezone billing cycles.
Integrates with Open WebUI's existing chat_message.usage tracking.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status

log = logging.getLogger(__name__)

# IST = UTC+5:30
IST_OFFSET_SECONDS = 5 * 3600 + 30 * 60

# Default monthly limit in USD
DEFAULT_MONTHLY_LIMIT_USD = 5.0

# Model pricing: per 1M tokens (input / output)
# Loaded from static JSON, overridden by env var
_MODEL_PRICES: dict[str, dict] = {}


def _load_model_prices() -> dict[str, dict]:
    """Load model prices from bundled JSON."""
    global _MODEL_PRICES
    if _MODEL_PRICES:
        return _MODEL_PRICES

    paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'model-prices.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'open_webui', 'static', 'model-prices.json'),
        '/app/backend/static/model-prices.json',
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    data = json.load(f)
                    _MODEL_PRICES = data.get('models', {})
                    log.info(f'Loaded {len(_MODEL_PRICES)} model prices from {p}')
                    return _MODEL_PRICES
            except Exception as e:
                log.warning(f'Failed to load prices from {p}: {e}')
                continue

    # Fallback hardcoded prices (OpenAI as of June 2026)
    _MODEL_PRICES = {
        'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
        'gpt-3.5-turbo-16k': {'input': 3.00, 'output': 4.00},
        'gpt-4-0613': {'input': 30.00, 'output': 60.00},
        'gpt-4': {'input': 30.00, 'output': 60.00},
        'gpt-3.5-turbo-instruct': {'input': 1.50, 'output': 2.00},
        'gpt-3.5-turbo-instruct-0914': {'input': 1.50, 'output': 2.00},
        'gpt-3.5-turbo-1106': {'input': 1.00, 'output': 2.00},
        'gpt-3.5-turbo-0125': {'input': 0.50, 'output': 1.50},
        'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
        'gpt-4-turbo-2024-04-09': {'input': 10.00, 'output': 30.00},
        'gpt-4o': {'input': 2.50, 'output': 10.00},
        'gpt-4o-2024-05-13': {'input': 5.00, 'output': 15.00},
        'gpt-4o-mini-2024-07-18': {'input': 0.15, 'output': 0.60},
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
        'gpt-4o-2024-08-06': {'input': 2.50, 'output': 10.00},
        'gpt-4o-2024-11-20': {'input': 2.50, 'output': 10.00},
        'omni-moderation-latest': {'input': 0.10, 'output': 0.10},
        'omni-moderation-2024-09-26': {'input': 0.10, 'output': 0.10},
        'o1-2024-12-17': {'input': 15.00, 'output': 60.00},
        'o1': {'input': 15.00, 'output': 60.00},
        'o3-mini': {'input': 1.10, 'output': 4.40},
        'o3-mini-2025-01-31': {'input': 1.10, 'output': 4.40},
        'gpt-4o-mini-search-preview-2025-03-11': {'input': 0.20, 'output': 0.80},
        'gpt-4o-mini-search-preview': {'input': 0.20, 'output': 0.80},
        'gpt-4o-transcribe': {'stt_per_minute': 0.01},
        'gpt-4o-mini-transcribe': {'stt_per_minute': 0.005},
        'o1-pro-2025-03-19': {'input': 20.00, 'output': 80.00},
        'o1-pro': {'input': 20.00, 'output': 80.00},
        'o3-2025-04-16': {'input': 2.00, 'output': 8.00},
        'o4-mini-2025-04-16': {'input': 1.10, 'output': 4.40},
        'o3': {'input': 2.00, 'output': 8.00},
        'o4-mini': {'input': 1.10, 'output': 4.40},
        'gpt-4.1-2025-04-14': {'input': 2.00, 'output': 8.00},
        'gpt-4.1': {'input': 2.00, 'output': 8.00},
        'gpt-4.1-mini-2025-04-14': {'input': 0.40, 'output': 1.60},
        'gpt-4.1-mini': {'input': 0.40, 'output': 1.60},
        'gpt-4.1-nano-2025-04-14': {'input': 0.10, 'output': 0.40},
        'gpt-4.1-nano': {'input': 0.10, 'output': 0.40},
        'gpt-image-1': {'image_per_1024x1024': 0.40},
        'o4-mini-deep-research': {'input': 2.00, 'output': 8.00},
        'gpt-4o-transcribe-diarize': {'stt_per_minute': 0.015},
        'o4-mini-deep-research-2025-06-26': {'input': 2.00, 'output': 8.00},
        'gpt-5-chat-latest': {'input': 5.00, 'output': 20.00},
        'gpt-5-2025-08-07': {'input': 5.00, 'output': 20.00},
        'gpt-5': {'input': 5.00, 'output': 20.00},
        'gpt-5-mini-2025-08-07': {'input': 0.50, 'output': 2.00},
        'gpt-5-mini': {'input': 0.50, 'output': 2.00},
        'gpt-5-nano-2025-08-07': {'input': 0.15, 'output': 0.60},
        'gpt-5-nano': {'input': 0.15, 'output': 0.60},
        'gpt-audio-2025-08-28': {'tts_per_1m_chars': 20.00},
        'gpt-realtime': {'stt_per_minute': 0.02},
        'gpt-realtime-2025-08-28': {'stt_per_minute': 0.02},
        'gpt-audio': {'tts_per_1m_chars': 20.00},
        'gpt-5-codex': {'input': 10.00, 'output': 40.00},
        'gpt-image-1-mini': {'image_per_1024x1024': 0.10},
        'gpt-5-pro-2025-10-06': {'input': 10.00, 'output': 40.00},
        'gpt-5-pro': {'input': 10.00, 'output': 40.00},
        'gpt-audio-mini': {'tts_per_1m_chars': 10.00},
        'gpt-audio-mini-2025-10-06': {'tts_per_1m_chars': 10.00},
        'gpt-5-search-api': {'input': 7.50, 'output': 30.00},
        'gpt-realtime-mini': {'stt_per_minute': 0.01},
        'gpt-realtime-mini-2025-10-06': {'stt_per_minute': 0.01},
        'sora-2': {'image_per_1024x1024': 1.00},
        'sora-2-pro': {'image_per_1024x1024': 2.00},
        'gpt-5-search-api-2025-10-14': {'input': 7.50, 'output': 30.00},
        'gpt-5.1-chat-latest': {'input': 5.00, 'output': 20.00},
        'gpt-5.1-2025-11-13': {'input': 5.00, 'output': 20.00},
        'gpt-5.1': {'input': 5.00, 'output': 20.00},
        'gpt-5.1-codex': {'input': 10.00, 'output': 40.00},
        'gpt-5.1-codex-mini': {'input': 2.00, 'output': 8.00},
        'gpt-5.1-codex-max': {'input': 15.00, 'output': 60.00},
        'gpt-image-1.5': {'image_per_1024x1024': 0.50},
        'gpt-5.2-2025-12-11': {'input': 5.00, 'output': 20.00},
        'gpt-5.2': {'input': 5.00, 'output': 20.00},
        'gpt-5.2-pro-2025-12-11': {'input': 10.00, 'output': 40.00},
        'gpt-5.2-pro': {'input': 10.00, 'output': 40.00},
        'gpt-5.2-chat-latest': {'input': 5.00, 'output': 20.00},
        'gpt-4o-mini-transcribe-2025-12-15': {'stt_per_minute': 0.005},
        'gpt-4o-mini-transcribe-2025-03-20': {'stt_per_minute': 0.005},
        'gpt-realtime-mini-2025-12-15': {'stt_per_minute': 0.01},
        'gpt-audio-mini-2025-12-15': {'tts_per_1m_chars': 10.00},
        'chatgpt-image-latest': {'image_per_1024x1024': 0.50},
        'gpt-5.2-codex': {'input': 10.00, 'output': 40.00},
        'gpt-5.3-codex': {'input': 10.00, 'output': 40.00},
        'gpt-realtime-1.5': {'stt_per_minute': 0.02},
        'gpt-audio-1.5': {'tts_per_1m_chars': 20.00},
        'gpt-4o-search-preview': {'input': 3.00, 'output': 12.00},
        'gpt-4o-search-preview-2025-03-11': {'input': 3.00, 'output': 12.00},
        'gpt-5.3-chat-latest': {'input': 5.00, 'output': 20.00},
        'gpt-5.4-2026-03-05': {'input': 2.50, 'output': 15.00},
        'gpt-5.4-pro': {'input': 5.00, 'output': 30.00},
        'gpt-5.4-pro-2026-03-05': {'input': 5.00, 'output': 30.00},
        'gpt-5.4': {'input': 2.50, 'output': 15.00},
        'gpt-5.4-nano-2026-03-17': {'input': 0.75, 'output': 4.50},
        'gpt-5.4-nano': {'input': 0.75, 'output': 4.50},
        'gpt-5.4-mini-2026-03-17': {'input': 0.75, 'output': 4.50},
        'gpt-5.4-mini': {'input': 0.75, 'output': 4.50},
        'gpt-image-2': {'image_per_1024x1024': 0.60},
        'gpt-image-2-2026-04-21': {'image_per_1024x1024': 0.60},
        'gpt-5.5': {'input': 5.00, 'output': 30.00},
        'gpt-5.5-2026-04-23': {'input': 5.00, 'output': 30.00},
        'gpt-5.5-pro': {'input': 10.00, 'output': 50.00},
        'gpt-5.5-pro-2026-04-23': {'input': 10.00, 'output': 50.00},
        'chat-latest': {'input': 5.00, 'output': 20.00},
        'gpt-realtime-translate': {'stt_per_minute': 0.02},
        'gpt-realtime-2': {'stt_per_minute': 0.02},
    }
    log.warning('Using fallback hardcoded model prices')
    return _MODEL_PRICES


def get_model_price(model_id: str) -> Optional[dict]:
    """Get pricing for a model ID. Handles aliases and prefixes."""
    prices = _load_model_prices()

    # Exact match
    if model_id in prices:
        return prices[model_id]

    # Strip provider prefixes (e.g., openai.gpt-4o -> gpt-4o)
    if '.' in model_id:
        bare = model_id.split('.')[-1]
        if bare in prices:
            return prices[bare]

    # Common aliases
    aliases = {
        'gpt-4o-2024-08-06': 'gpt-4o',
        'gpt-4o-2024-11-20': 'gpt-4o',
        'gpt-4o-mini-2024-07-18': 'gpt-4o-mini',
        'chatgpt-4o-latest': 'gpt-4o',
        'o1-preview': 'o1',
        'o1-mini': 'o4-mini',
        'o3-mini': 'o4-mini',
    }
    if model_id in aliases and aliases[model_id] in prices:
        return prices[aliases[model_id]]

    return None


def calculate_cost(model_id: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
    """Calculate cost in USD for a chat completion."""
    price = get_model_price(model_id)
    if not price:
        log.warning(f'Unknown model pricing for {model_id}, assuming $0')
        return 0.0

    input_price = price.get('input', 0.0)  # per 1M tokens
    output_price = price.get('output', 0.0)

    cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
    return round(cost, 6)


def calculate_image_cost(model_id: str, count: int = 1, size: str = '1024x1024') -> float:
    """Calculate cost for image generation/editing (per image)."""
    price = get_model_price(model_id)
    if not price:
        return 0.0

    # Try size-specific pricing first
    size_key = f'image_per_{size}'
    if size_key in price:
        return round(count * price[size_key], 6)

    # Fallback to generic per-unit pricing
    per_unit = price.get('image_per_unit', price.get('image_per_1024x1024', 0.0))
    return round(count * per_unit, 6)


def calculate_tts_cost(model_id: str, char_count: int) -> float:
    """Calculate cost for text-to-speech (per 1M characters)."""
    price = get_model_price(model_id)
    if not price:
        return 0.0

    rate = price.get('tts_per_1m_chars', 0.0)
    return round((char_count / 1_000_000) * rate, 6)


def calculate_stt_cost(model_id: str, minutes: float) -> float:
    """Calculate cost for speech-to-text (per minute of audio)."""
    price = get_model_price(model_id)
    if not price:
        return 0.0

    rate = price.get('stt_per_minute', 0.0)
    return round(minutes * rate, 6)


def get_current_ist_month() -> str:
    """Return current billing month as YYYY-MM in IST."""
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(timezone(offset=timedelta(seconds=IST_OFFSET_SECONDS)))
    return now_ist.strftime('%Y-%m')


def get_month_start_end_ist(month_str: str) -> tuple[int, int]:
    """Return epoch timestamps for start and end of a month in IST."""
    year, month = map(int, month_str.split('-'))
    tz = timezone(offset=timedelta(seconds=IST_OFFSET_SECONDS))
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=tz)
    return int(start.timestamp()), int(end.timestamp())


# ---------------------------------------------------------------------------
# User spending DB helpers (async — import inside functions to avoid
# circular imports at module load time)
# ---------------------------------------------------------------------------

async def _get_user_info(user_id: str) -> Optional[dict]:
    """Fetch user info JSON from DB."""
    from open_webui.models.users import Users
    user = await Users.get_user_by_id(user_id)
    return (user.info or {}) if user else {}


async def _set_user_info(user_id: str, info: dict):
    """Update user info JSON in DB."""
    from open_webui.models.users import Users
    await Users.update_user_by_id(user_id, {'info': info})


async def _get_or_create_spending_row(user_id: str, month: str) -> dict:
    """Get or initialize spending record for user+month.

    Stored inside user.info['spending'] to avoid schema migration.
    Structure: { "spending": { "2025-06": {"spent": 1.23, "limit": 5.0} } }
    """
    info = await _get_user_info(user_id) or {}
    spending = info.setdefault('spending', {})
    row = spending.setdefault(month, {'spent': 0.0, 'limit': None})
    if row.get('limit') is None:
        row['limit'] = info.get('monthly_limit_usd', DEFAULT_MONTHLY_LIMIT_USD)
    return row


async def _save_spending_row(user_id: str, month: str, row: dict):
    """Persist spending record back to user info."""
    info = await _get_user_info(user_id) or {}
    info.setdefault('spending', {})[month] = row
    await _set_user_info(user_id, info)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_user_spending(user_id: str, month: Optional[str] = None) -> dict:
    """Get current spending for a user. Returns {"spent": float, "limit": float, "remaining": float}."""
    month = month or get_current_ist_month()
    row = await _get_or_create_spending_row(user_id, month)
    return {
        'month': month,
        'spent': round(row['spent'], 4),
        'limit': round(row['limit'], 2),
        'remaining': round(max(0, row['limit'] - row['spent']), 4),
    }


async def set_user_limit(user_id: str, limit_usd: float) -> dict:
    """Set monthly spending limit for a user (admin only)."""
    info = await _get_user_info(user_id) or {}
    info['monthly_limit_usd'] = round(limit_usd, 2)
    await _set_user_info(user_id, info)

    # Update current month row too
    month = get_current_ist_month()
    row = await _get_or_create_spending_row(user_id, month)
    row['limit'] = round(limit_usd, 2)
    await _save_spending_row(user_id, month, row)

    return {'user_id': user_id, 'monthly_limit_usd': round(limit_usd, 2)}


async def check_budget_before_request(user_id: str, model_id: str) -> None:
    """Raise HTTPException if user has exceeded their monthly budget.

    Call this *before* sending the request to the LLM.
    """
    # Allow unlimited for admins
    from open_webui.models.users import Users
    user = await Users.get_user_by_id(user_id)
    if user and user.role == 'admin':
        return

    month = get_current_ist_month()
    row = await _get_or_create_spending_row(user_id, month)
    spent = row['spent']
    limit = row['limit']

    # Hard block when over limit
    if spent >= limit:
        log.warning(f'User {user_id} blocked: spent ${spent:.2f} / limit ${limit:.2f}')
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f'Monthly budget exceeded. Spent ${spent:.2f} of ${limit:.2f}. '
                   f'Contact admin to increase your limit.',
        )

    # Warn when over 80%
    if spent >= limit * 0.8:
        log.info(f'User {user_id} at {spent/limit*100:.0f}% of budget')


async def record_spend(user_id: str, model_id: str, input_tokens: int, output_tokens: int) -> dict:
    """Record actual spend after a chat completion completes.

    Returns {"cost": float, "new_spent": float, "limit": float}.
    """
    cost = calculate_cost(model_id, input_tokens, output_tokens)
    if cost <= 0:
        return {'cost': 0.0, 'new_spent': 0.0, 'limit': 0.0}

    month = get_current_ist_month()
    row = await _get_or_create_spending_row(user_id, month)
    row['spent'] = round(row['spent'] + cost, 6)
    await _save_spending_row(user_id, month, row)

    log.info(f'User {user_id} spent ${cost:.4f} on {model_id} (month total: ${row["spent"]:.2f})')

    return {
        'cost': cost,
        'new_spent': row['spent'],
        'limit': row['limit'],
        'remaining': max(0, row['limit'] - row['spent']),
    }


async def record_non_token_spend(user_id: str, model_id: str, cost: float) -> dict:
    """Record spend for non-token operations (image gen, TTS, STT).

    Callers compute cost via calculate_image_cost, calculate_tts_cost, etc.
    """
    if cost <= 0:
        return {'cost': 0.0, 'new_spent': 0.0, 'limit': 0.0}

    month = get_current_ist_month()
    row = await _get_or_create_spending_row(user_id, month)
    row['spent'] = round(row['spent'] + cost, 6)
    await _save_spending_row(user_id, month, row)

    log.info(f'User {user_id} spent ${cost:.4f} on {model_id} (non-token) (month total: ${row["spent"]:.2f})')

    return {
        'cost': cost,
        'new_spent': row['spent'],
        'limit': row['limit'],
        'remaining': max(0, row['limit'] - row['spent']),
    }


async def get_all_user_spending(month: Optional[str] = None) -> list[dict]:
    """Get spending summary for all users (admin)."""
    from open_webui.models.users import Users
    month = month or get_current_ist_month()
    all_users = await Users.get_users()
    results = []
    for u in all_users.get('users', []):
        info = u.info or {}
        spending = info.get('spending', {}).get(month, {'spent': 0.0, 'limit': info.get('monthly_limit_usd', DEFAULT_MONTHLY_LIMIT_USD)})
        results.append({
            'user_id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'month': month,
            'spent': round(spending.get('spent', 0.0), 4),
            'limit': round(spending.get('limit', DEFAULT_MONTHLY_LIMIT_USD), 2),
            'remaining': round(max(0, spending.get('limit', DEFAULT_MONTHLY_LIMIT_USD) - spending.get('spent', 0.0)), 4),
        })
    return results
