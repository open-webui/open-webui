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
    by_model: dict[str, float] = {}  # 按模型分组的消费


class ModelStats(BaseModel):
    """模型统计"""

    model: str
    cost: float
    count: int


class StatsResponse(BaseModel):
    """统计报表响应"""

    daily: list[DailyStats]
    by_model: list[ModelStats]
    models: list[str] = []  # 所有模型列表（用于前端生成堆叠图系列）


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
async def get_stats(
    user=Depends(get_verified_user),
    days: int = 7,
    granularity: str = "day"
):
    """
    查询统计报表

    Args:
        days: 查询天数
        granularity: 时间粒度 (hour/day/month)

    需要登录
    """
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta

        with get_db() as db:
            now = datetime.now()
            cutoff = int((time.time() - days * 86400) * 1000000000)

            # 根据粒度选择分组方式和生成完整时间序列（包含当前时段）
            if granularity == "hour":
                trunc_unit = "hour"
                date_format = "%H:00"
                # 生成过去24小时的完整序列（包含当前小时）
                all_periods = []
                for i in range(23, -1, -1):
                    dt = now - timedelta(hours=i)
                    all_periods.append(dt.replace(minute=0, second=0, microsecond=0))
            elif granularity == "month":
                trunc_unit = "month"
                date_format = "%Y-%m"
                # 生成过去12个月的完整序列（包含当前月）
                all_periods = []
                for i in range(11, -1, -1):
                    dt = now - relativedelta(months=i)
                    all_periods.append(dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0))
            else:
                # 默认按天分组
                trunc_unit = "day"
                date_format = "%m-%d"
                # 生成过去N天的完整序列（包含今天）
                all_periods = []
                for i in range(days - 1, -1, -1):
                    dt = now - timedelta(days=i)
                    all_periods.append(dt.replace(hour=0, minute=0, second=0, microsecond=0))

            # 按时间+模型分组统计（用于堆叠图）
            daily_by_model_query = (
                db.query(
                    func.date_trunc(
                        trunc_unit,
                        func.to_timestamp(BillingLog.created_at / 1000000000)
                    ).label("date"),
                    BillingLog.model_id,
                    func.sum(BillingLog.total_cost).label("total"),
                )
                .filter(
                    BillingLog.user_id == user.id,
                    BillingLog.created_at >= cutoff,
                    BillingLog.log_type.in_(["deduct", "settle"]),
                )
                .group_by("date", BillingLog.model_id)
                .order_by("date")
                .all()
            )

            # 构建数据结构: {date_key: {model_id: cost, ...}, ...}
            data_dict: dict[str, dict[str, float]] = {}
            all_models: set[str] = set()
            for d in daily_by_model_query:
                if d[0] and d[1]:
                    date_key = d[0].strftime(date_format)
                    model_id = d[1]
                    cost = d[2] / 10000 if d[2] else 0
                    all_models.add(model_id)
                    if date_key not in data_dict:
                        data_dict[date_key] = {}
                    data_dict[date_key][model_id] = cost

            log.debug(f"统计查询: granularity={granularity}, days={days}, 记录数={len(daily_by_model_query)}, 模型数={len(all_models)}")

            # 填充完整时间序列
            daily_stats = []
            for period in all_periods:
                key = period.strftime(date_format)
                by_model = data_dict.get(key, {})
                total_cost = sum(by_model.values())
                daily_stats.append(DailyStats(date=key, cost=total_cost, by_model=by_model))

            log.debug(f"生成时间序列: 数量={len(daily_stats)}, 模型列表={list(all_models)}")

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
                    BillingLog.log_type.in_(["deduct", "settle"]),
                )
                .group_by(BillingLog.model_id)
                .order_by(func.sum(BillingLog.total_cost).desc())
                .all()
            )

            return StatsResponse(
                daily=daily_stats,
                by_model=[
                    ModelStats(model=m[0], cost=m[1] / 10000 if m[1] else 0, count=m[2])
                    for m in by_model_query
                ],
                models=sorted(list(all_models)),  # 按字母排序的模型列表
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


####################
# Payment API (用户自助充值)
####################


class CreateOrderRequest(BaseModel):
    """创建充值订单请求"""

    amount: float = Field(..., gt=0, le=10000, description="充值金额（元），1-10000")


class CreateOrderResponse(BaseModel):
    """创建充值订单响应"""

    order_id: str
    out_trade_no: str
    qr_code: str
    amount: float
    expired_at: int


class OrderStatusResponse(BaseModel):
    """订单状态响应"""

    order_id: str
    status: str
    amount: float
    paid_at: Optional[int] = None


@router.post("/payment/create", response_model=CreateOrderResponse)
async def create_payment_order(req: CreateOrderRequest, user=Depends(get_verified_user)):
    """
    创建充值订单（生成支付二维码）

    需要登录
    """
    import uuid as uuid_module

    from open_webui.utils.alipay import create_qr_payment, is_alipay_configured
    from open_webui.models.billing import PaymentOrders

    # 检查支付宝配置
    if not is_alipay_configured():
        raise HTTPException(status_code=503, detail="支付功能暂未开放，请联系管理员")

    # 验证金额
    if req.amount < 1:
        raise HTTPException(status_code=400, detail="充值金额最低1元")
    if req.amount > 10000:
        raise HTTPException(status_code=400, detail="充值金额最高10000元")

    # 生成订单号: CK + 时间戳 + 随机字符
    out_trade_no = f"CK{int(time.time())}{uuid_module.uuid4().hex[:8].upper()}"

    # 调用支付宝创建订单
    success, msg, qr_code = create_qr_payment(
        out_trade_no=out_trade_no,
        amount_yuan=req.amount,
        subject="Cakumi账户充值",
    )

    if not success:
        log.error(f"创建支付订单失败: {msg}")
        raise HTTPException(status_code=500, detail=f"创建订单失败: {msg}")

    # 保存订单到数据库
    now = int(time.time())
    expired_at = now + 900  # 15分钟后过期

    order = PaymentOrders.create(
        user_id=user.id,
        out_trade_no=out_trade_no,
        amount=int(req.amount * 10000),  # 元 → 毫
        qr_code=qr_code,
        expired_at=expired_at,
        payment_method="alipay",
    )

    log.info(f"创建支付订单成功: {out_trade_no}, 用户={user.id}, 金额={req.amount}元")

    return CreateOrderResponse(
        order_id=order.id,
        out_trade_no=out_trade_no,
        qr_code=qr_code,
        amount=req.amount,
        expired_at=expired_at,
    )


@router.get("/payment/status/{order_id}", response_model=OrderStatusResponse)
async def get_payment_status(order_id: str, user=Depends(get_verified_user)):
    """
    查询订单状态（前端轮询）

    需要登录
    """
    from open_webui.models.billing import PaymentOrders

    order = PaymentOrders.get_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 确保只能查询自己的订单
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权查询该订单")

    return OrderStatusResponse(
        order_id=order.id,
        status=order.status,
        amount=order.amount / 10000,  # 毫 → 元
        paid_at=order.paid_at,
    )


@router.post("/payment/notify")
async def alipay_notify(request):
    """
    支付宝异步通知回调

    注意：此接口无需登录验证
    """
    from fastapi import Request
    from open_webui.utils.alipay import verify_notify_sign
    from open_webui.models.billing import PaymentOrders, RechargeLog
    from open_webui.models.users import Users
    import uuid as uuid_module

    # 获取回调参数
    form_data = await request.form()
    params = dict(form_data)

    log.info(f"收到支付宝回调: {params.get('out_trade_no')}")

    # 验签
    if not verify_notify_sign(params):
        log.error("支付宝回调验签失败")
        return "fail"

    out_trade_no = params.get("out_trade_no")
    trade_no = params.get("trade_no")
    trade_status = params.get("trade_status")

    # 只处理支付成功状态
    if trade_status not in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
        log.info(f"支付宝回调，非成功状态: {trade_status}")
        return "success"

    # 查询订单
    order = PaymentOrders.get_by_out_trade_no(out_trade_no)
    if not order:
        log.error(f"支付宝回调，订单不存在: {out_trade_no}")
        return "success"

    # 幂等检查：已处理的订单直接返回成功
    if order.status == "paid":
        log.info(f"支付宝回调，订单已处理: {out_trade_no}")
        return "success"

    # 更新订单状态
    now = int(time.time())
    PaymentOrders.update_status(
        out_trade_no=out_trade_no,
        status="paid",
        trade_no=trade_no,
        paid_at=now,
    )

    # 增加用户余额
    try:
        from open_webui.models.users import User as UserModel

        with get_db() as db:
            user = db.query(UserModel).filter_by(id=order.user_id).first()
            if user:
                user.balance = (user.balance or 0) + order.amount
                db.commit()

                # 记录充值日志
                recharge_log = RechargeLog(
                    id=str(uuid_module.uuid4()),
                    user_id=order.user_id,
                    amount=order.amount,
                    operator_id="system",  # 系统自动充值
                    remark=f"支付宝充值，订单号: {out_trade_no}",
                    created_at=now,
                )
                db.add(recharge_log)
                db.commit()

                log.info(
                    f"支付成功: 用户={order.user_id}, 金额={order.amount / 10000:.2f}元, "
                    f"订单={out_trade_no}"
                )
    except Exception as e:
        log.error(f"支付回调处理失败: {e}")
        # 即使余额更新失败，也返回 success，避免支付宝重复回调
        # 后续可通过定时任务修复

    return "success"


@router.get("/payment/config")
async def get_payment_config():
    """
    获取支付配置状态

    公开接口，用于前端判断是否显示充值功能
    """
    from open_webui.utils.alipay import is_alipay_configured

    return {
        "alipay_enabled": is_alipay_configured(),
    }
