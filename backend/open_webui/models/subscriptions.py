import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    Integer,
    String,
    Text,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


####################
# DB Schemas
####################


class SubscriptionTier(Base):
    __tablename__ = 'subscription_tier'

    id = Column(String, primary_key=True)  # slug: 'free' | 'pro' | 'max' | 'ultra'
    name = Column(String, nullable=False)  # display name
    description = Column(Text, nullable=True)
    price_usd = Column(Float, nullable=False, default=0.0)  # monthly price, in USDT
    duration_days = Column(Integer, nullable=False, default=30)
    daily_message_limit = Column(Integer, nullable=True)  # NULL = unlimited
    allowed_model_ids = Column(JSONField, nullable=True)  # [] / NULL = all models allowed
    enabled = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class UserSubscription(Base):
    __tablename__ = 'user_subscription'

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    tier_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default='active')  # active | expired | cancelled
    started_at = Column(BigInteger, nullable=False)
    expires_at = Column(BigInteger, nullable=False, index=True)
    order_id = Column(String, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class SubscriptionOrder(Base):
    __tablename__ = 'subscription_order'

    # id = the composite order id returned by the payment service ("<sent id>_<chainId>")
    id = Column(String, primary_key=True)
    logical_order_id = Column(String, index=True, nullable=False)  # the id we generated and sent
    user_id = Column(String, index=True, nullable=False)
    tier_id = Column(String, nullable=False)
    chain_id = Column(String, nullable=False)
    amount = Column(String, nullable=False)  # stored as string to avoid float drift
    address = Column(String, nullable=True)
    status = Column(String, nullable=False, default='PENDING')  # PENDING|PAID|EXPIRED|FAILED
    tx_hash = Column(String, nullable=True)
    activated = Column(Boolean, nullable=False, default=False)  # subscription granted for this paid order
    expires_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class SubscriptionUsageDaily(Base):
    __tablename__ = 'subscription_usage_daily'

    id = Column(String, primary_key=True)  # f"{user_id}:{date}"
    user_id = Column(String, index=True, nullable=False)
    date = Column(String, nullable=False)  # 'YYYY-MM-DD' (UTC)
    count = Column(Integer, nullable=False, default=0)
    updated_at = Column(BigInteger, nullable=False)


####################
# Pydantic models
####################


class SubscriptionTierModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    price_usd: float = 0.0
    duration_days: int = 30
    daily_message_limit: Optional[int] = None
    allowed_model_ids: Optional[list[str]] = None
    enabled: bool = True
    sort_order: int = 0
    created_at: int
    updated_at: int


class SubscriptionTierForm(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price_usd: float = 0.0
    duration_days: int = 30
    daily_message_limit: Optional[int] = None
    allowed_model_ids: Optional[list[str]] = None
    enabled: bool = True
    sort_order: int = 0


class UserSubscriptionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    tier_id: str
    status: str
    started_at: int
    expires_at: int
    order_id: Optional[str] = None
    created_at: int
    updated_at: int


class SubscriptionOrderModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    logical_order_id: str
    user_id: str
    tier_id: str
    chain_id: str
    amount: str
    address: Optional[str] = None
    status: str
    tx_hash: Optional[str] = None
    activated: bool
    expires_at: Optional[int] = None
    created_at: int
    updated_at: int


####################
# Table operations
####################


class SubscriptionTiersTable:
    async def list_tiers(
        self, enabled_only: bool = False, db: Optional[AsyncSession] = None
    ) -> list[SubscriptionTierModel]:
        async with get_async_db_context(db) as db:
            stmt = select(SubscriptionTier)
            if enabled_only:
                stmt = stmt.filter_by(enabled=True)
            stmt = stmt.order_by(SubscriptionTier.sort_order, SubscriptionTier.price_usd)
            result = await db.execute(stmt)
            return [SubscriptionTierModel.model_validate(t) for t in result.scalars().all()]

    async def get_tier(self, tier_id: str, db: Optional[AsyncSession] = None) -> Optional[SubscriptionTierModel]:
        async with get_async_db_context(db) as db:
            tier = await db.get(SubscriptionTier, tier_id)
            return SubscriptionTierModel.model_validate(tier) if tier else None

    async def count(self, db: Optional[AsyncSession] = None) -> int:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(SubscriptionTier.id))
            return len(result.scalars().all())

    async def upsert_tier(
        self, form: SubscriptionTierForm, db: Optional[AsyncSession] = None
    ) -> Optional[SubscriptionTierModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            tier = await db.get(SubscriptionTier, form.id)
            if tier is None:
                tier = SubscriptionTier(
                    id=form.id,
                    name=form.name,
                    description=form.description,
                    price_usd=form.price_usd,
                    duration_days=form.duration_days,
                    daily_message_limit=form.daily_message_limit,
                    allowed_model_ids=form.allowed_model_ids,
                    enabled=form.enabled,
                    sort_order=form.sort_order,
                    created_at=now,
                    updated_at=now,
                )
                db.add(tier)
            else:
                tier.name = form.name
                tier.description = form.description
                tier.price_usd = form.price_usd
                tier.duration_days = form.duration_days
                tier.daily_message_limit = form.daily_message_limit
                tier.allowed_model_ids = form.allowed_model_ids
                tier.enabled = form.enabled
                tier.sort_order = form.sort_order
                tier.updated_at = now
            await db.commit()
            await db.refresh(tier)
            return SubscriptionTierModel.model_validate(tier)

    async def delete_tier(self, tier_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(delete(SubscriptionTier).filter_by(id=tier_id))
            await db.commit()
            return result.rowcount > 0


class UserSubscriptionsTable:
    async def get_active_for_user(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[UserSubscriptionModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            result = await db.execute(
                select(UserSubscription)
                .filter(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == 'active',
                    UserSubscription.expires_at > now,
                )
                .order_by(UserSubscription.expires_at.desc())
                .limit(1)
            )
            sub = result.scalars().first()
            return UserSubscriptionModel.model_validate(sub) if sub else None

    async def list_for_user(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[UserSubscriptionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(UserSubscription)
                .filter_by(user_id=user_id)
                .order_by(UserSubscription.created_at.desc())
            )
            return [UserSubscriptionModel.model_validate(s) for s in result.scalars().all()]

    async def list_all(self, db: Optional[AsyncSession] = None) -> list[UserSubscriptionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(UserSubscription).order_by(UserSubscription.created_at.desc())
            )
            return [UserSubscriptionModel.model_validate(s) for s in result.scalars().all()]

    async def create_or_extend(
        self,
        user_id: str,
        tier_id: str,
        duration_days: int,
        order_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[UserSubscriptionModel]:
        """Grant `tier_id` to the user. If they already hold an active subscription on the
        same tier, extend its expiry; otherwise mark existing active subs of other tiers
        expired and create a fresh subscription."""
        async with get_async_db_context(db) as db:
            now = int(time.time())
            duration_secs = duration_days * 86400

            result = await db.execute(
                select(UserSubscription)
                .filter(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == 'active',
                    UserSubscription.expires_at > now,
                )
                .order_by(UserSubscription.expires_at.desc())
            )
            active = result.scalars().all()

            same_tier = next((s for s in active if s.tier_id == tier_id), None)
            if same_tier is not None:
                # extend from current expiry
                base = max(same_tier.expires_at, now)
                same_tier.expires_at = base + duration_secs
                same_tier.updated_at = now
                if order_id:
                    same_tier.order_id = order_id
                target = same_tier
            else:
                # supersede any other active tier
                for s in active:
                    s.status = 'expired'
                    s.updated_at = now
                target = UserSubscription(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    tier_id=tier_id,
                    status='active',
                    started_at=now,
                    expires_at=now + duration_secs,
                    order_id=order_id,
                    created_at=now,
                    updated_at=now,
                )
                db.add(target)

            await db.commit()
            await db.refresh(target)
            return UserSubscriptionModel.model_validate(target)


class SubscriptionOrdersTable:
    async def insert(
        self,
        order_id: str,
        logical_order_id: str,
        user_id: str,
        tier_id: str,
        chain_id: str,
        amount: str,
        address: Optional[str],
        status: str,
        expires_at: Optional[int],
        db: Optional[AsyncSession] = None,
    ) -> Optional[SubscriptionOrderModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            order = SubscriptionOrder(
                id=order_id,
                logical_order_id=logical_order_id,
                user_id=user_id,
                tier_id=tier_id,
                chain_id=chain_id,
                amount=amount,
                address=address,
                status=status,
                activated=False,
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )
            db.add(order)
            await db.commit()
            await db.refresh(order)
            return SubscriptionOrderModel.model_validate(order)

    async def get(self, order_id: str, db: Optional[AsyncSession] = None) -> Optional[SubscriptionOrderModel]:
        async with get_async_db_context(db) as db:
            order = await db.get(SubscriptionOrder, order_id)
            return SubscriptionOrderModel.model_validate(order) if order else None

    async def list_for_user(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[SubscriptionOrderModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(SubscriptionOrder)
                .filter_by(user_id=user_id)
                .order_by(SubscriptionOrder.created_at.desc())
            )
            return [SubscriptionOrderModel.model_validate(o) for o in result.scalars().all()]

    async def update_status(
        self,
        order_id: str,
        status: str,
        tx_hash: Optional[str] = None,
        activated: Optional[bool] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[SubscriptionOrderModel]:
        async with get_async_db_context(db) as db:
            order = await db.get(SubscriptionOrder, order_id)
            if order is None:
                return None
            order.status = status
            if tx_hash is not None:
                order.tx_hash = tx_hash
            if activated is not None:
                order.activated = activated
            order.updated_at = int(time.time())
            await db.commit()
            await db.refresh(order)
            return SubscriptionOrderModel.model_validate(order)


class SubscriptionUsageTable:
    @staticmethod
    def _id(user_id: str, date: str) -> str:
        return f'{user_id}:{date}'

    async def get_count(self, user_id: str, date: str, db: Optional[AsyncSession] = None) -> int:
        async with get_async_db_context(db) as db:
            row = await db.get(SubscriptionUsageDaily, self._id(user_id, date))
            return row.count if row else 0

    async def increment(self, user_id: str, date: str, db: Optional[AsyncSession] = None) -> int:
        async with get_async_db_context(db) as db:
            _id = self._id(user_id, date)
            row = await db.get(SubscriptionUsageDaily, _id)
            now = int(time.time())
            if row is None:
                row = SubscriptionUsageDaily(id=_id, user_id=user_id, date=date, count=1, updated_at=now)
                db.add(row)
                new_count = 1
            else:
                row.count = row.count + 1
                row.updated_at = now
                new_count = row.count
            await db.commit()
            return new_count


SubscriptionTiers = SubscriptionTiersTable()
UserSubscriptions = UserSubscriptionsTable()
SubscriptionOrders = SubscriptionOrdersTable()
SubscriptionUsage = SubscriptionUsageTable()
