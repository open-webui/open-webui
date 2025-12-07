"""
计费管理 API 路由

提供余额查询、充值、消费记录、统计报表、模型定价等管理接口
"""

import time
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from open_webui.models.users import Users, User
from open_webui.models.billing import ModelPricings, BillingLogs, RechargeLogs, BillingLog
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.billing import recharge_user
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)

router = APIRouter()


####################
# Request/Response Models
####################


class BalanceResponse(BaseModel):
    """余额响应"""

    balance: float = Field(..., description="当前余额（元）")
    total_consumed: float = Field(..., description="累计消费（元）")
    billing_status: str = Field(..., description="账户状态: active/frozen")


class RechargeRequest(BaseModel):
    """充值请求"""

    user_id: str = Field(..., description="用户ID")
    amount: int = Field(..., ne=0, description="充值/扣费金额（毫），1元 = 10000毫，正数充值，负数扣费")
    remark: str = Field(default="", description="备注")


class RechargeResponse(BaseModel):
    """充值响应"""

    balance: float = Field(..., description="充值后余额（毫），1元 = 10000毫")
    status: str = Field(..., description="账户状态")


class BillingLogResponse(BaseModel):
    """计费日志响应"""

    id: str
    model_id: str
    cost: float
    balance_after: Optional[float]
    type: str
    prompt_tokens: int
    completion_tokens: int
    created_at: int
    precharge_id: Optional[str] = None  # 预扣费事务ID，用于关联 precharge 和 settle


class PricingRequest(BaseModel):
    """定价请求"""

    model_id: str = Field(..., description="模型标识")
    input_price: Decimal = Field(..., ge=0, description="输入价格（元/百万token）")
    output_price: Decimal = Field(..., ge=0, description="输出价格（元/百万token）")


class PricingResponse(BaseModel):
    """定价响应"""

    model_id: str
    input_price: float
    output_price: float
    source: str = Field(..., description="来源: database/default")


class DailyStats(BaseModel):
    """每日统计"""

    date: str
    cost: float


class ModelStats(BaseModel):
    """模型统计"""

    model: str
    cost: float
    count: int


class StatsResponse(BaseModel):
    """统计报表响应"""

    daily: list[DailyStats]
    by_model: list[ModelStats]


####################
# API Endpoints
####################


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user=Depends(get_verified_user)):
    """
    查询当前用户余额

    需要登录
    """
    user_data = Users.get_user_by_id(user.id)
    if not user_data:
        raise HTTPException(status_code=404, detail="用户不存在")

    return BalanceResponse(
        balance=float(user_data.balance or 0),
        total_consumed=float(user_data.total_consumed or 0),
        billing_status=user_data.billing_status or "active",
    )


@router.post("/recharge", response_model=RechargeResponse)
async def recharge(req: RechargeRequest, admin=Depends(get_admin_user)):
    """
    管理员充值

    需要管理员权限
    """
    try:
        balance = recharge_user(
            user_id=req.user_id,
            amount=req.amount,
            operator_id=admin.id,
            remark=req.remark,
        )

        # 获取用户状态
        user_data = Users.get_user_by_id(req.user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="用户不存在")

        return RechargeResponse(
            balance=float(balance), status=user_data.billing_status or "active"
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"充值失败: {e}")
        raise HTTPException(status_code=500, detail=f"充值失败: {str(e)}")


@router.get("/logs", response_model=list[BillingLogResponse])
async def get_logs(
    user=Depends(get_verified_user), limit: int = 50, offset: int = 0
):
    """
    查询当前用户消费记录

    需要登录
    """
    try:
        logs = BillingLogs.get_by_user_id(user.id, limit=limit, offset=offset)

        return [
            BillingLogResponse(
                id=log.id,
                model_id=log.model_id,
                cost=float(log.total_cost),
                balance_after=float(log.balance_after) if log.balance_after else None,
                type=log.log_type,
                prompt_tokens=log.prompt_tokens,
                completion_tokens=log.completion_tokens,
                created_at=log.created_at,
                precharge_id=log.precharge_id,  # 添加预扣费事务ID
            )
            for log in logs
        ]
    except Exception as e:
        log.error(f"查询日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询日志失败: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user=Depends(get_verified_user), days: int = 7):
    """
    查询统计报表

    按日统计和按模型统计

    需要登录
    """
    try:
        from sqlalchemy import func

        with get_db() as db:
            # cutoff: 纳秒级时间戳
            cutoff = int((time.time() - days * 86400) * 1000000000)

            # 按日统计
            daily_query = (
                db.query(
                    func.date_trunc(
                        "day",
                        # created_at 是纳秒级，需要除以 1000000000 转换为秒级
                        func.to_timestamp(BillingLog.created_at / 1000000000)
                    ).label("date"),
                    func.sum(BillingLog.total_cost).label("total"),
                )
                .filter(
                    BillingLog.user_id == user.id,
                    BillingLog.created_at >= cutoff,
                    BillingLog.log_type == "deduct",
                )
                .group_by("date")
                .order_by("date")
                .all()
            )

            # 按模型统计
            by_model_query = (
                db.query(
                    BillingLog.model_id,
                    func.sum(BillingLog.total_cost).label("total"),
                    func.count().label("count"),
                )
                .filter(
                    BillingLog.user_id == user.id,
                    BillingLog.created_at >= cutoff,
                    BillingLog.log_type == "deduct",
                )
                .group_by(BillingLog.model_id)
                .order_by(func.sum(BillingLog.total_cost).desc())
                .all()
            )

            # cost 单位转换：毫 → 元（除以 10000）
            return StatsResponse(
                daily=[
                    DailyStats(date=str(d[0].date()), cost=d[1] / 10000 if d[1] else 0)
                    for d in daily_query
                ],
                by_model=[
                    ModelStats(model=m[0], cost=m[1] / 10000 if m[1] else 0, count=m[2])
                    for m in by_model_query
                ],
            )
    except Exception as e:
        log.error(f"查询统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询统计失败: {str(e)}")


@router.post("/pricing", response_model=PricingResponse)
async def set_pricing(req: PricingRequest, admin=Depends(get_admin_user)):
    """
    设置模型定价

    需要管理员权限
    """
    try:
        pricing = ModelPricings.upsert(
            model_id=req.model_id,
            input_price=req.input_price,
            output_price=req.output_price,
        )

        return PricingResponse(
            model_id=pricing.model_id,
            input_price=float(pricing.input_price),
            output_price=float(pricing.output_price),
            source="database",
        )
    except Exception as e:
        log.error(f"设置定价失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置定价失败: {str(e)}")


@router.get("/pricing/{model_id}", response_model=PricingResponse)
async def get_pricing(model_id: str):
    """
    查询模型定价

    公开接口，无需登录
    """
    try:
        pricing = ModelPricings.get_by_model_id(model_id)

        if pricing:
            return PricingResponse(
                model_id=pricing.model_id,
                input_price=float(pricing.input_price),
                output_price=float(pricing.output_price),
                source="database",
            )
        else:
            # 返回默认价格
            from open_webui.utils.billing import DEFAULT_PRICING

            default = DEFAULT_PRICING.get(model_id, DEFAULT_PRICING["default"])
            return PricingResponse(
                model_id=model_id,
                input_price=float(default["input"]),
                output_price=float(default["output"]),
                source="default",
            )
    except Exception as e:
        log.error(f"查询定价失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询定价失败: {str(e)}")


@router.get("/pricing", response_model=list[PricingResponse])
async def list_pricing():
    """
    列出所有模型定价

    公开接口，无需登录
    """
    try:
        pricings = ModelPricings.get_all()

        return [
            PricingResponse(
                model_id=p.model_id,
                input_price=float(p.input_price),
                output_price=float(p.output_price),
                source="database",
            )
            for p in pricings
        ]
    except Exception as e:
        log.error(f"列出定价失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出定价失败: {str(e)}")


@router.get("/recharge/logs/{user_id}")
async def get_recharge_logs(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    admin=Depends(get_admin_user)
):
    """
    查询用户充值记录 (仅管理员)

    需要管理员权限
    """
    try:
        logs = RechargeLogs.get_by_user_id_with_operator_name(
            user_id, limit=limit, offset=offset
        )
        return logs
    except Exception as e:
        log.error(f"查询充值记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询充值记录失败: {str(e)}")
