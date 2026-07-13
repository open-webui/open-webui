import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from open_webui.internal.db import get_async_session
from open_webui.models.chat_messages import ChatMessageModel, ChatMessages
from open_webui.models.chats import Chats
from open_webui.models.feedbacks import Feedbacks
from open_webui.models.groups import Groups
from open_webui.models.usage_logs import UsageLogs
from open_webui.models.users import Users
from open_webui.utils.auth import get_admin_user
from open_webui.utils.models import get_all_models
from open_webui.utils.response import compute_token_cost, compute_token_cost_breakdown
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


router = APIRouter()


async def _get_pricing_by_model(request: Request, user) -> dict[str, dict]:
    """Resolve the `pricing` vendor extension for every known model.

    Models a provider no longer serves simply have no pricing and are
    reported unpriced rather than priced at zero.
    """
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    pricing_by_model = {}
    for model_id, model in request.app.state.MODELS.items():
        pricing = model.get('pricing') or (model.get('openai') or {}).get('pricing')
        if pricing:
            pricing_by_model[model_id] = pricing
    return pricing_by_model


def _combine_cost(entry: dict, pricing: Optional[dict]) -> Optional[float]:
    """Cost of a ledger aggregation entry: the stored write-time snapshots
    plus a current-pricing fallback for rows recorded without pricing
    (e.g. backfilled history). None when nothing could be priced."""
    stored = entry.get('stored_cost')
    unpriced = entry.get('unpriced') or {}
    fallback = None
    if any(unpriced.values()):
        fallback = compute_token_cost(
            unpriced.get('input_tokens', 0),
            unpriced.get('output_tokens', 0),
            unpriced.get('cached_tokens', 0),
            pricing,
        )
    if stored is None and fallback is None:
        return None
    return (stored or 0.0) + (fallback or 0.0)


####################
# Response Models
####################


class ModelAnalyticsEntry(BaseModel):
    model_id: str
    # Underlying model that served a workspace/preset model at usage time;
    # a base-model change yields a separate entry per base model.
    base_model_id: Optional[str] = None
    count: int
    unique_users: int = 0
    unique_chats: int = 0


class ModelAnalyticsResponse(BaseModel):
    models: list[ModelAnalyticsEntry]


class UserModelUsageEntry(BaseModel):
    model_id: str
    base_model_id: Optional[str] = None
    count: int
    unique_chats: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: Optional[float] = None


class UserAnalyticsEntry(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    count: int
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    # Estimated from current model pricing; covers priced models only
    # (lower-bound estimate). None when no usage could be priced.
    cost: Optional[float] = None
    # Per-model breakdown (message count, tokens, cost), largest cost first
    models: list[UserModelUsageEntry] = []


class UserAnalyticsResponse(BaseModel):
    users: list[UserAnalyticsEntry]


####################
# Endpoints
####################


@router.get('/models', response_model=ModelAnalyticsResponse)
async def get_model_analytics(
    start_date: Optional[int] = Query(None, description='Start timestamp (epoch)'),
    end_date: Optional[int] = Query(None, description='End timestamp (epoch)'),
    group_id: Optional[str] = Query(None, description='Filter by user group ID'),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get completion counts per (model, base model) from the usage ledger."""
    counts = await UsageLogs.get_count_by_model(start_date=start_date, end_date=end_date, group_id=group_id, db=db)
    unique_counts = await UsageLogs.get_unique_counts_by_model(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
    )
    models = [
        ModelAnalyticsEntry(
            model_id=key[0],
            base_model_id=key[1],
            count=count,
            unique_users=unique_counts.get(key, {}).get('unique_users', 0),
            unique_chats=unique_counts.get(key, {}).get('unique_chats', 0),
        )
        for key, count in sorted(counts.items(), key=lambda x: -x[1])
    ]
    return ModelAnalyticsResponse(models=models)


@router.get('/users', response_model=UserAnalyticsResponse)
async def get_user_analytics(
    request: Request,
    start_date: Optional[int] = Query(None, description='Start timestamp (epoch)'),
    end_date: Optional[int] = Query(None, description='End timestamp (epoch)'),
    group_id: Optional[str] = Query(None, description='Filter by user group ID'),
    limit: int = Query(50, description='Max users to return'),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get completion counts and token usage per user from the usage ledger."""
    counts = await UsageLogs.get_count_by_user(start_date=start_date, end_date=end_date, group_id=group_id, db=db)
    token_usage = await UsageLogs.get_token_usage_by_user(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
    )
    pricing_by_model = await _get_pricing_by_model(request, user)

    # Get user info for top users
    top_user_ids = [uid for uid, _ in sorted(counts.items(), key=lambda x: -x[1])[:limit]]
    user_info = {u.id: u for u in await Users.get_users_by_user_ids(top_user_ids, db=db)}

    users = []
    for user_id in top_user_ids:
        u = user_info.get(user_id)
        tokens = token_usage.get(user_id, {})

        cost = None
        model_entries = []
        for (model_id, base_model_id), model_tokens in (tokens.get('models') or {}).items():
            model_cost = _combine_cost(model_tokens, pricing_by_model.get(model_id))
            if model_cost is not None:
                cost = (cost or 0.0) + model_cost
            model_entries.append(
                UserModelUsageEntry(
                    model_id=model_id,
                    base_model_id=base_model_id,
                    count=model_tokens.get('message_count', 0),
                    unique_chats=model_tokens.get('unique_chats', 0),
                    input_tokens=model_tokens.get('input_tokens', 0),
                    cached_tokens=model_tokens.get('cached_tokens', 0),
                    output_tokens=model_tokens.get('output_tokens', 0),
                    total_tokens=model_tokens.get('total_tokens', 0),
                    cost=model_cost,
                )
            )
        model_entries.sort(key=lambda m: (-(m.cost or 0.0), -m.count))

        users.append(
            UserAnalyticsEntry(
                user_id=user_id,
                name=u.name if u else None,
                email=u.email if u else None,
                count=counts[user_id],
                input_tokens=tokens.get('input_tokens', 0),
                output_tokens=tokens.get('output_tokens', 0),
                total_tokens=tokens.get('total_tokens', 0),
                cost=cost,
                models=model_entries,
            )
        )

    return UserAnalyticsResponse(users=users)


@router.get('/messages', response_model=list[ChatMessageModel])
async def get_messages(
    model_id: Optional[str] = Query(None, description='Filter by model ID'),
    user_id: Optional[str] = Query(None, description='Filter by user ID'),
    chat_id: Optional[str] = Query(None, description='Filter by chat ID'),
    start_date: Optional[int] = Query(None, description='Start timestamp (epoch)'),
    end_date: Optional[int] = Query(None, description='End timestamp (epoch)'),
    skip: int = Query(0),
    limit: int = Query(50, le=100),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Query messages with filters."""
    if chat_id:
        return await ChatMessages.get_messages_by_chat_id(chat_id=chat_id, db=db)
    elif model_id:
        return await ChatMessages.get_messages_by_model_id(
            model_id=model_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
            db=db,
        )
    elif user_id:
        return await ChatMessages.get_messages_by_user_id(user_id=user_id, skip=skip, limit=limit, db=db)
    else:
        # Return empty if no filter specified
        return []


class SummaryResponse(BaseModel):
    total_messages: int
    total_chats: int
    total_models: int
    total_users: int


@router.get('/summary', response_model=SummaryResponse)
async def get_summary(
    start_date: Optional[int] = Query(None, description='Start timestamp (epoch)'),
    end_date: Optional[int] = Query(None, description='End timestamp (epoch)'),
    group_id: Optional[str] = Query(None, description='Filter by user group ID'),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get summary statistics for the dashboard from the usage ledger."""
    model_counts = await UsageLogs.get_count_by_model(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
    )
    user_counts = await UsageLogs.get_count_by_user(start_date=start_date, end_date=end_date, group_id=group_id, db=db)
    chat_counts = await UsageLogs.get_count_by_chat(start_date=start_date, end_date=end_date, group_id=group_id, db=db)

    return SummaryResponse(
        total_messages=sum(model_counts.values()),
        total_chats=len(chat_counts),
        total_models=len({key[0] for key in model_counts}),
        total_users=len(user_counts),
    )


class DailyStatsEntry(BaseModel):
    date: str
    models: dict[str, int]
    # Per-model token and cost sums for the same bucket (ledger-backed)
    tokens: dict[str, int] = {}
    costs: dict[str, float] = {}


class DailyStatsResponse(BaseModel):
    data: list[DailyStatsEntry]


@router.get('/daily', response_model=DailyStatsResponse)
async def get_daily_stats(
    request: Request,
    start_date: Optional[int] = Query(None, description='Start timestamp (epoch)'),
    end_date: Optional[int] = Query(None, description='End timestamp (epoch)'),
    group_id: Optional[str] = Query(None, description='Filter by user group ID'),
    granularity: str = Query('daily', description="Granularity: 'hourly' or 'daily'"),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get completion counts, tokens and cost grouped by model for time-series charts."""
    buckets = await UsageLogs.get_timeseries_usage_by_model(
        start_date=start_date,
        end_date=end_date,
        group_id=group_id,
        granularity=granularity,
        db=db,
    )
    pricing_by_model = await _get_pricing_by_model(request, user)

    data = []
    for date, models in sorted(buckets.items()):
        counts = {}
        tokens = {}
        costs = {}
        for model_id, entry in models.items():
            counts[model_id] = entry['count']
            tokens[model_id] = entry['total_tokens']
            cost = _combine_cost(entry, pricing_by_model.get(model_id))
            if cost is not None:
                costs[model_id] = cost
        data.append(DailyStatsEntry(date=date, models=counts, tokens=tokens, costs=costs))

    return DailyStatsResponse(data=data)


class CostBreakdown(BaseModel):
    # Per-component cost estimates from current pricing; 'reasoning' is the
    # reasoning-token subset of 'output' (informational, not additive).
    input: Optional[float] = None
    cached: Optional[float] = None
    output: Optional[float] = None
    reasoning: Optional[float] = None


class TokenUsageEntry(BaseModel):
    model_id: str
    base_model_id: Optional[str] = None
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int
    message_count: int
    # Stored write-time cost snapshots plus a current-pricing fallback for
    # rows recorded without pricing; None when nothing could be priced.
    cost: Optional[float] = None
    # Per-component estimates from current pricing (None when unpriced)
    cost_breakdown: Optional[CostBreakdown] = None


class TokenUsageResponse(BaseModel):
    models: list[TokenUsageEntry]
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int = 0
    total_reasoning_tokens: int = 0
    total_tokens: int
    total_cost: Optional[float] = None
    cost_breakdown: Optional[CostBreakdown] = None
    currency: Optional[str] = None
    unpriced_models: int = 0


@router.get('/tokens', response_model=TokenUsageResponse)
async def get_token_usage(
    request: Request,
    start_date: Optional[int] = Query(None),
    end_date: Optional[int] = Query(None),
    group_id: Optional[str] = Query(None, description='Filter by user group ID'),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get token usage aggregated by model from the usage ledger."""
    usage = await UsageLogs.get_token_usage_by_model(start_date=start_date, end_date=end_date, group_id=group_id, db=db)
    pricing_by_model = await _get_pricing_by_model(request, user)

    models = []
    breakdown_totals: dict[str, float] = {}
    for (model_id, base_model_id), data in sorted(usage.items(), key=lambda x: -x[1]['total_tokens']):
        breakdown = compute_token_cost_breakdown(
            data['input_tokens'],
            data['output_tokens'],
            data.get('cached_tokens', 0),
            data.get('reasoning_tokens', 0),
            pricing_by_model.get(model_id),
        )
        if breakdown:
            for component, amount in breakdown.items():
                breakdown_totals[component] = breakdown_totals.get(component, 0.0) + amount

        models.append(
            TokenUsageEntry(
                model_id=model_id,
                base_model_id=base_model_id,
                input_tokens=data['input_tokens'],
                output_tokens=data['output_tokens'],
                cached_tokens=data.get('cached_tokens', 0),
                reasoning_tokens=data.get('reasoning_tokens', 0),
                total_tokens=data['total_tokens'],
                message_count=data['message_count'],
                cost=_combine_cost(data, pricing_by_model.get(model_id)),
                cost_breakdown=CostBreakdown(**breakdown) if breakdown else None,
            )
        )

    total_input = sum(m.input_tokens for m in models)
    total_output = sum(m.output_tokens for m in models)

    priced_costs = [m.cost for m in models if m.cost is not None]
    currency = None
    for m in models:
        pricing = pricing_by_model.get(m.model_id)
        if pricing:
            currency = pricing.get('currency', 'USD')
            break

    return TokenUsageResponse(
        models=models,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_cached_tokens=sum(m.cached_tokens for m in models),
        total_reasoning_tokens=sum(m.reasoning_tokens for m in models),
        total_tokens=total_input + total_output,
        total_cost=sum(priced_costs) if priced_costs else None,
        cost_breakdown=CostBreakdown(**breakdown_totals) if breakdown_totals else None,
        currency=currency,
        unpriced_models=len(models) - len(priced_costs),
    )


class SourceUsageEntry(BaseModel):
    source: str
    count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: Optional[float] = None


class SourceUsageResponse(BaseModel):
    sources: list[SourceUsageEntry]


@router.get('/sources', response_model=SourceUsageResponse)
async def get_source_usage(
    request: Request,
    start_date: Optional[int] = Query(None),
    end_date: Optional[int] = Query(None),
    group_id: Optional[str] = Query(None, description='Filter by user group ID'),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get usage broken down by source (chat, temporary, channel, api, task)."""
    usage = await UsageLogs.get_usage_by_source(start_date=start_date, end_date=end_date, group_id=group_id, db=db)
    pricing_by_model = await _get_pricing_by_model(request, user)

    sources = []
    for source, data in sorted(usage.items(), key=lambda x: -x[1]['message_count']):
        cost = None
        for model_id, model_tokens in (data.get('models') or {}).items():
            model_cost = _combine_cost(model_tokens, pricing_by_model.get(model_id))
            if model_cost is not None:
                cost = (cost or 0.0) + model_cost

        sources.append(
            SourceUsageEntry(
                source=source,
                count=data['message_count'],
                input_tokens=data['input_tokens'],
                output_tokens=data['output_tokens'],
                total_tokens=data['total_tokens'],
                cost=cost,
            )
        )

    return SourceUsageResponse(sources=sources)


####################
# Model Chats Browser
####################


class ModelChatEntry(BaseModel):
    chat_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    first_message: Optional[str] = None
    updated_at: int


class ModelChatsResponse(BaseModel):
    chats: list[ModelChatEntry]
    total: int


MODEL_CHAT_ORDER_FIELDS = {'title', 'updated_at', 'user_name'}


@router.get('/models/{model_id:path}/chats', response_model=ModelChatsResponse)
async def get_model_chats(
    model_id: str,
    start_date: Optional[int] = Query(None),
    end_date: Optional[int] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50, le=100),
    order_by: str = Query('updated_at'),
    direction: str = Query('desc'),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get chats that used a specific model, with preview and feedback info."""
    filter = {}
    if start_date:
        filter['start_date'] = start_date
    if end_date:
        filter['end_date'] = end_date
    if order_by in MODEL_CHAT_ORDER_FIELDS:
        filter['order_by'] = order_by
    if direction in {'asc', 'desc'}:
        filter['direction'] = direction

    result = await Chats.get_chats_by_model_id(
        model_id=model_id,
        filter=filter,
        skip=skip,
        limit=limit,
        db=db,
    )

    return ModelChatsResponse(
        chats=[ModelChatEntry.model_validate(chat) for chat in result['items']],
        total=result['total'] or 0,
    )


####################
# Model Overview
####################


class HistoryEntry(BaseModel):
    date: str
    won: int = 0
    lost: int = 0


class TagEntry(BaseModel):
    tag: str
    count: int


class ModelOverviewResponse(BaseModel):
    history: list[HistoryEntry]
    tags: list[TagEntry]


@router.get('/models/{model_id:path}/overview', response_model=ModelOverviewResponse)
async def get_model_overview(
    model_id: str,
    days: int = Query(30, description='Number of days of history (0 for all)'),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get model overview with feedback history and chat tags."""

    # Calculate start date for history
    now = datetime.now()
    start_dt = None
    if days > 0:
        start_dt = now - timedelta(days=days)

    # Get chat IDs that used this model
    chat_ids = await ChatMessages.get_chat_ids_by_model_id(
        model_id=model_id,
        start_date=None,
        end_date=None,
        skip=0,
        limit=10000,  # Get all chats
        db=db,
    )

    history_rows = await Feedbacks.get_model_feedback_counts_by_day(
        model_id=model_id,
        start_date=int(start_dt.timestamp()) if start_dt else None,
        db=db,
    )
    history_counts = {
        entry.date: {
            'won': entry.won,
            'lost': entry.lost,
        }
        for entry in history_rows
    }

    # Fill in missing days
    history = []
    if history_counts or days > 0:
        end_dt = now
        if days > 0:
            current = start_dt
        elif history_counts:
            # Find earliest date
            min_date = min(history_counts.keys())
            current = datetime.strptime(min_date, '%Y-%m-%d')
        else:
            current = now

        while current <= end_dt:
            date_str = current.strftime('%Y-%m-%d')
            counts = history_counts.get(date_str, {'won': 0, 'lost': 0})
            history.append(
                HistoryEntry(
                    date=date_str,
                    won=counts['won'],
                    lost=counts['lost'],
                )
            )
            current += timedelta(days=1)

    # Get chat tags
    tag_counts: dict[str, int] = defaultdict(int)
    if chat_ids:
        chat_metas = await Chats.get_chat_metas_by_chat_ids(
            chat_ids,
            include_archived=True,
            db=db,
        )
        for meta in chat_metas:
            for tag in meta.get('tags', []):
                tag_counts[tag] += 1

    # Sort by count and take top 10
    tags = [TagEntry(tag=tag, count=count) for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]]

    return ModelOverviewResponse(history=history, tags=tags)
