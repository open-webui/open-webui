import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_async_db_context
from open_webui.utils.response import compute_token_cost, normalize_usage
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Float,
    Index,
    Text,
    case,
    distinct,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

####################
# Helpers
####################


def extract_token_counts(usage: dict) -> tuple[int, int, int, int, int]:
    """Extract (input, output, cached, reasoning, total) token counts from a
    normalized usage dict. Mirrors the key fallbacks used by the frontend
    (getUsageTokens) and the legacy chat_message JSON extraction."""

    def _int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    input_tokens = _int(usage.get('input_tokens') or usage.get('prompt_tokens'))
    output_tokens = _int(usage.get('output_tokens') or usage.get('completion_tokens'))
    cached_tokens = _int(
        (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
        or usage.get('cache_read_input_tokens')
        or (usage.get('input_tokens_details') or {}).get('cached_tokens')
    )
    reasoning_tokens = _int(
        (usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
        or (usage.get('output_tokens_details') or {}).get('reasoning_tokens')
    )
    total_tokens = _int(usage.get('total_tokens')) or (input_tokens + output_tokens)

    return input_tokens, output_tokens, cached_tokens, reasoning_tokens, total_tokens


def derive_usage_source(chat_id: Optional[str]) -> str:
    """Classify a completion by its chat_id shape."""
    if not chat_id:
        return 'api'
    if chat_id.startswith('local:'):
        return 'temporary'
    if chat_id.startswith('channel:'):
        return 'channel'
    return 'chat'


####################
# UsageLog DB Schema
####################


class UsageLog(Base):
    """Append-only ledger: one row per LLM completion, written at generation
    time. Survives chat/user deletion (no foreign keys) and covers usage the
    chat tables never see (temporary chats, API calls, background tasks).
    No message content is stored."""

    __tablename__ = 'usage_log'

    id = Column(Text, primary_key=True)

    # Attribution (plain identifiers, deliberately no FKs)
    user_id = Column(Text, nullable=False, index=True)
    chat_id = Column(Text, nullable=True)
    message_id = Column(Text, nullable=True, index=True)
    session_id = Column(Text, nullable=True)
    model_id = Column(Text, nullable=False, index=True)
    # Underlying model that actually served a workspace/preset model,
    # captured at generation time (base-model changes stay visible in history)
    base_model_id = Column(Text, nullable=True)

    # Classification
    source = Column(Text, nullable=False, default='chat')  # chat, temporary, channel, api, task
    task = Column(Text, nullable=True)  # task name when source == 'task'
    status = Column(Text, nullable=False, default='completed')  # completed, cancelled, error

    # Token counts (first-class columns so aggregation is plain SQL)
    input_tokens = Column(BigInteger, nullable=False, default=0)
    output_tokens = Column(BigInteger, nullable=False, default=0)
    cached_tokens = Column(BigInteger, nullable=False, default=0)
    reasoning_tokens = Column(BigInteger, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)

    # Full normalized usage blob (timings, detail maps, provider extras)
    usage = Column(JSON, nullable=True)

    # Cost snapshot at time of use; None when the model had no pricing then
    # (query-time fallback prices those rows with current pricing).
    pricing = Column(JSON, nullable=True)
    cost = Column(Float, nullable=True)
    currency = Column(Text, nullable=True)

    created_at = Column(BigInteger, nullable=False, index=True)

    __table_args__ = (
        Index('usage_log_user_created_idx', 'user_id', 'created_at'),
        Index('usage_log_model_created_idx', 'model_id', 'created_at'),
    )


####################
# Pydantic Models
####################


class UsageLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    session_id: Optional[str] = None
    model_id: str
    base_model_id: Optional[str] = None
    source: str = 'chat'
    task: Optional[str] = None
    status: str = 'completed'
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    usage: Optional[dict] = None
    pricing: Optional[dict] = None
    cost: Optional[float] = None
    currency: Optional[str] = None
    created_at: int


####################
# Table Operations
####################


def _unpriced_sum(column):
    """SUM(column) over rows without a stored cost snapshot."""
    return func.coalesce(func.sum(case((UsageLog.cost.is_(None), column), else_=0)), 0)


class UsageLogTable:
    async def record(
        self,
        *,
        user_id: Optional[str],
        model_id: Optional[str],
        base_model_id: Optional[str] = None,
        usage: Optional[dict] = None,
        pricing: Optional[dict] = None,
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        task: Optional[str] = None,
        status: str = 'completed',
        db: Optional[AsyncSession] = None,
    ) -> Optional[UsageLogModel]:
        """Append one immutable ledger row. Best-effort: swallows every
        exception (a ledger failure must never break a chat completion)."""
        try:
            if not user_id or not model_id:
                return None

            usage = normalize_usage(usage or {})
            input_tokens, output_tokens, cached_tokens, reasoning_tokens, total_tokens = extract_token_counts(usage)

            cost = compute_token_cost(input_tokens, output_tokens, cached_tokens, pricing)
            currency = pricing.get('currency', 'USD') if pricing and cost is not None else None

            async with get_async_db_context(db) as db:
                entry = UsageLog(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    chat_id=chat_id or None,
                    message_id=message_id,
                    session_id=session_id,
                    model_id=model_id,
                    base_model_id=base_model_id if base_model_id != model_id else None,
                    source=source or derive_usage_source(chat_id),
                    task=task,
                    status=status,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    reasoning_tokens=reasoning_tokens,
                    total_tokens=total_tokens,
                    usage=usage or None,
                    pricing=pricing,
                    cost=cost,
                    currency=currency,
                    created_at=int(time.time()),
                )
                db.add(entry)
                await db.commit()
                await db.refresh(entry)
                return UsageLogModel.model_validate(entry)
        except Exception:
            log.exception('Failed to record usage log entry')
            return None

    def _apply_filters(
        self,
        stmt,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        include_tasks: bool = False,
    ):
        from open_webui.models.groups import GroupMember

        if not include_tasks:
            stmt = stmt.filter(UsageLog.source != 'task')
        if start_date:
            stmt = stmt.filter(UsageLog.created_at >= start_date)
        if end_date:
            stmt = stmt.filter(UsageLog.created_at <= end_date)
        if group_id:
            group_users = select(GroupMember.user_id).filter(GroupMember.group_id == group_id).scalar_subquery()
            stmt = stmt.filter(UsageLog.user_id.in_(group_users))
        return stmt

    # Activity counts (exclude task generations so background title/tag
    # calls don't inflate user-facing message counts)

    async def get_count_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[tuple[str, Optional[str]], int]:
        """Counts keyed by (model_id, base_model_id) — a workspace model whose
        underlying model changed over time yields one entry per base model."""
        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(UsageLog.model_id, UsageLog.base_model_id, func.count(UsageLog.id).label('count')),
                start_date,
                end_date,
                group_id,
            ).group_by(UsageLog.model_id, UsageLog.base_model_id)
            result = await db.execute(stmt)
            return {(row.model_id, row.base_model_id): row.count for row in result.all()}

    async def get_unique_counts_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[tuple[str, Optional[str]], dict]:
        """Count distinct users and chats per (model_id, base_model_id)."""
        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(
                    UsageLog.model_id,
                    UsageLog.base_model_id,
                    func.count(distinct(UsageLog.user_id)).label('unique_users'),
                    func.count(distinct(UsageLog.chat_id)).label('unique_chats'),
                ),
                start_date,
                end_date,
                group_id,
            ).group_by(UsageLog.model_id, UsageLog.base_model_id)
            result = await db.execute(stmt)
            return {
                (row.model_id, row.base_model_id): {
                    'unique_users': row.unique_users,
                    'unique_chats': row.unique_chats,
                }
                for row in result.all()
            }

    async def get_count_by_user(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, int]:
        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(UsageLog.user_id, func.count(UsageLog.id).label('count')),
                start_date,
                end_date,
                group_id,
            ).group_by(UsageLog.user_id)
            result = await db.execute(stmt)
            return {row.user_id: row.count for row in result.all()}

    async def get_count_by_chat(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, int]:
        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(UsageLog.chat_id, func.count(UsageLog.id).label('count')).filter(UsageLog.chat_id.isnot(None)),
                start_date,
                end_date,
                group_id,
            ).group_by(UsageLog.chat_id)
            result = await db.execute(stmt)
            return {row.chat_id: row.count for row in result.all()}

    # Token/cost aggregations (include task generations: billing truth)

    def _token_usage_columns(self):
        return [
            func.coalesce(func.sum(UsageLog.input_tokens), 0).label('input_tokens'),
            func.coalesce(func.sum(UsageLog.output_tokens), 0).label('output_tokens'),
            func.coalesce(func.sum(UsageLog.cached_tokens), 0).label('cached_tokens'),
            func.coalesce(func.sum(UsageLog.reasoning_tokens), 0).label('reasoning_tokens'),
            func.count(UsageLog.id).label('message_count'),
            # SUM ignores NULL costs; stays None when no row had a snapshot
            func.sum(UsageLog.cost).label('stored_cost'),
            _unpriced_sum(UsageLog.input_tokens).label('unpriced_input_tokens'),
            _unpriced_sum(UsageLog.output_tokens).label('unpriced_output_tokens'),
            _unpriced_sum(UsageLog.cached_tokens).label('unpriced_cached_tokens'),
        ]

    @staticmethod
    def _token_usage_entry(row) -> dict:
        return {
            'input_tokens': row.input_tokens,
            'output_tokens': row.output_tokens,
            'cached_tokens': row.cached_tokens,
            'reasoning_tokens': row.reasoning_tokens,
            'total_tokens': row.input_tokens + row.output_tokens,
            'message_count': row.message_count,
            'stored_cost': row.stored_cost,
            'unpriced': {
                'input_tokens': row.unpriced_input_tokens,
                'output_tokens': row.unpriced_output_tokens,
                'cached_tokens': row.unpriced_cached_tokens,
            },
        }

    async def get_token_usage_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[tuple[str, Optional[str]], dict]:
        """Token usage keyed by (model_id, base_model_id)."""
        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(UsageLog.model_id, UsageLog.base_model_id, *self._token_usage_columns()),
                start_date,
                end_date,
                group_id,
                include_tasks=True,
            ).group_by(UsageLog.model_id, UsageLog.base_model_id)
            result = await db.execute(stmt)
            return {(row.model_id, row.base_model_id): self._token_usage_entry(row) for row in result.all()}

    async def get_token_usage_by_user(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Token usage per user, with a per-(model, base_model) breakdown so
        per-model pricing can be applied by the caller."""
        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(
                    UsageLog.user_id,
                    UsageLog.model_id,
                    UsageLog.base_model_id,
                    func.count(distinct(UsageLog.chat_id)).label('unique_chats'),
                    *self._token_usage_columns(),
                ),
                start_date,
                end_date,
                group_id,
                include_tasks=True,
            ).group_by(UsageLog.user_id, UsageLog.model_id, UsageLog.base_model_id)
            result = await db.execute(stmt)

            usage_by_user: dict[str, dict] = {}
            for row in result.all():
                user_usage = usage_by_user.setdefault(
                    row.user_id,
                    {
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'message_count': 0,
                        'models': {},
                    },
                )
                user_usage['input_tokens'] += row.input_tokens
                user_usage['output_tokens'] += row.output_tokens
                user_usage['total_tokens'] += row.input_tokens + row.output_tokens
                user_usage['message_count'] += row.message_count
                model_entry = self._token_usage_entry(row)
                model_entry['unique_chats'] = row.unique_chats
                user_usage['models'][(row.model_id, row.base_model_id)] = model_entry

            return usage_by_user

    async def get_usage_by_source(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict]:
        """Completion counts and token totals per source (chat, temporary,
        channel, api, task), with a per-model breakdown so per-model
        pricing can be applied by the caller."""
        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(UsageLog.source, UsageLog.model_id, *self._token_usage_columns()),
                start_date,
                end_date,
                group_id,
                include_tasks=True,
            ).group_by(UsageLog.source, UsageLog.model_id)
            result = await db.execute(stmt)

            usage_by_source: dict[str, dict] = {}
            for row in result.all():
                source_usage = usage_by_source.setdefault(
                    row.source,
                    {
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'message_count': 0,
                        'models': {},
                    },
                )
                source_usage['input_tokens'] += row.input_tokens
                source_usage['output_tokens'] += row.output_tokens
                source_usage['total_tokens'] += row.input_tokens + row.output_tokens
                source_usage['message_count'] += row.message_count
                source_usage['models'][row.model_id] = self._token_usage_entry(row)

            return usage_by_source

    async def get_timeseries_usage_by_model(
        self,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        group_id: Optional[str] = None,
        granularity: str = 'daily',
        db: Optional[AsyncSession] = None,
    ) -> dict[str, dict[str, dict]]:
        """Per-bucket (day or hour) per-model usage:
        {date_str: {model_id: {count, total_tokens, stored_cost, unpriced}}}.

        Buckets in Python (like the legacy daily counts) to stay
        dialect-agnostic; missing buckets are filled with {}."""
        from datetime import datetime, timedelta

        from open_webui.models.chat_messages import _normalize_timestamp

        async with get_async_db_context(db) as db:
            stmt = self._apply_filters(
                select(
                    UsageLog.created_at,
                    UsageLog.model_id,
                    UsageLog.input_tokens,
                    UsageLog.output_tokens,
                    UsageLog.cached_tokens,
                    UsageLog.cost,
                ),
                start_date,
                end_date,
                group_id,
            )
            result = await db.execute(stmt)
            rows = result.all()

        hourly = granularity == 'hourly'
        fmt = '%Y-%m-%d %H:00' if hourly else '%Y-%m-%d'

        buckets: dict[str, dict[str, dict]] = {}
        for created_at, model_id, input_tokens, output_tokens, cached_tokens, cost in rows:
            bucket = datetime.fromtimestamp(_normalize_timestamp(created_at)).strftime(fmt)
            entry = buckets.setdefault(bucket, {}).setdefault(
                model_id,
                {
                    'count': 0,
                    'total_tokens': 0,
                    'stored_cost': None,
                    'unpriced': {'input_tokens': 0, 'output_tokens': 0, 'cached_tokens': 0},
                },
            )
            entry['count'] += 1
            entry['total_tokens'] += (input_tokens or 0) + (output_tokens or 0)
            if cost is not None:
                entry['stored_cost'] = (entry['stored_cost'] or 0.0) + cost
            else:
                entry['unpriced']['input_tokens'] += input_tokens or 0
                entry['unpriced']['output_tokens'] += output_tokens or 0
                entry['unpriced']['cached_tokens'] += cached_tokens or 0

        # Fill in missing buckets
        if start_date and end_date:
            step = timedelta(hours=1) if hourly else timedelta(days=1)
            current = datetime.fromtimestamp(_normalize_timestamp(start_date))
            if hourly:
                current = current.replace(minute=0, second=0, microsecond=0)
            end_dt = datetime.fromtimestamp(_normalize_timestamp(end_date))
            while current <= end_dt:
                buckets.setdefault(current.strftime(fmt), {})
                current += step

        return buckets


UsageLogs = UsageLogTable()
