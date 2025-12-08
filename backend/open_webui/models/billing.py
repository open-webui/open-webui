"""
计费模块数据模型

包含模型定价、计费日志、充值日志的 ORM 模型和数据访问层
"""

import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, String, Integer, BigInteger, Text

from open_webui.internal.db import Base, get_db


####################
# ModelPricing DB Schema
####################


class ModelPricing(Base):
    """模型定价表"""

    __tablename__ = "model_pricing"

    id = Column(String, primary_key=True)
    model_id = Column(String, unique=True, nullable=False)  # 模型标识，如 "gpt-4o"
    input_price = Column(Integer, nullable=False)  # 输入价格（毫/1k token，1元=10000毫）
    output_price = Column(Integer, nullable=False)  # 输出价格（毫/1k token，1元=10000毫）
    enabled = Column(Boolean, default=True, nullable=False)  # 是否启用
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class BillingLog(Base):
    """计费日志表"""

    __tablename__ = "billing_log"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    model_id = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_cost = Column(Integer, nullable=False)  # 本次费用（毫，1元=10000毫）
    balance_after = Column(Integer)  # 扣费后余额（毫，1元=10000毫）
    log_type = Column(String(20), default="deduct")  # deduct/refund/precharge/settle
    created_at = Column(BigInteger, nullable=False, index=True)

    # 预扣费相关字段
    precharge_id = Column(String, nullable=True, index=True)  # 预扣费事务ID
    status = Column(String(20), nullable=True, default="settled")  # precharge | settled | refunded
    estimated_tokens = Column(Integer, nullable=True)  # 预估tokens总数
    refund_amount = Column(Integer, nullable=True)  # 退款金额（毫，1元=10000毫）


class RechargeLog(Base):
    """充值日志表"""

    __tablename__ = "recharge_log"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # 充值金额（毫，1元=10000毫）
    operator_id = Column(String, nullable=False)  # 操作员ID
    remark = Column(Text)  # 备注
    created_at = Column(BigInteger, nullable=False)


class PaymentOrder(Base):
    """支付订单表"""

    __tablename__ = "payment_order"

    id = Column(String, primary_key=True)  # 内部订单号
    user_id = Column(String, nullable=False, index=True)
    out_trade_no = Column(String(64), unique=True, nullable=False)  # 商户订单号
    trade_no = Column(String(64), nullable=True)  # 支付宝交易号
    amount = Column(Integer, nullable=False)  # 金额（毫，1元=10000毫）
    status = Column(String(20), default="pending")  # pending/paid/closed/refunded
    payment_method = Column(String(20), default="alipay")  # alipay
    qr_code = Column(Text, nullable=True)  # 支付二维码内容
    paid_at = Column(BigInteger, nullable=True)  # 支付时间
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    expired_at = Column(BigInteger, nullable=False)  # 订单过期时间


####################
# Pydantic Models
####################


class ModelPricingModel(BaseModel):
    """模型定价 Pydantic 模型（以毫为单位，1元=10000毫）"""

    id: str
    model_id: str
    input_price: int  # 毫/1k tokens
    output_price: int  # 毫/1k tokens
    enabled: bool
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class BillingLogModel(BaseModel):
    """计费日志 Pydantic 模型（以毫为单位，1元=10000毫）"""

    id: str
    user_id: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    total_cost: int  # 毫
    balance_after: Optional[int]  # 毫
    log_type: str
    created_at: int

    # 预扣费相关字段
    precharge_id: Optional[str] = None
    status: Optional[str] = "settled"
    estimated_tokens: Optional[int] = None
    refund_amount: Optional[int] = None  # 毫

    model_config = ConfigDict(from_attributes=True)


class RechargeLogModel(BaseModel):
    """充值日志 Pydantic 模型（以毫为单位，1元=10000毫）"""

    id: str
    user_id: str
    amount: int  # 毫
    operator_id: str
    remark: Optional[str]
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class PaymentOrderModel(BaseModel):
    """支付订单 Pydantic 模型（以毫为单位，1元=10000毫）"""

    id: str
    user_id: str
    out_trade_no: str
    trade_no: Optional[str] = None
    amount: int  # 毫
    status: str
    payment_method: str
    qr_code: Optional[str] = None
    paid_at: Optional[int] = None
    created_at: int
    updated_at: int
    expired_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Data Access Layer
####################


class ModelPricingTable:
    """模型定价数据访问层"""

    def get_by_model_id(self, model_id: str) -> Optional[ModelPricingModel]:
        """根据模型ID获取定价"""
        try:
            with get_db() as db:
                pricing = (
                    db.query(ModelPricing)
                    .filter_by(model_id=model_id, enabled=True)
                    .first()
                )
                return ModelPricingModel.model_validate(pricing) if pricing else None
        except Exception:
            return None

    def get_all(self) -> list[ModelPricingModel]:
        """获取所有定价"""
        with get_db() as db:
            pricings = db.query(ModelPricing).filter_by(enabled=True).all()
            return [ModelPricingModel.model_validate(p) for p in pricings]

    def upsert(
        self, model_id: str, input_price: int, output_price: int
    ) -> ModelPricingModel:
        """创建或更新定价"""
        with get_db() as db:
            existing = db.query(ModelPricing).filter_by(model_id=model_id).first()
            now = int(time.time())

            if existing:
                # 更新
                existing.input_price = input_price
                existing.output_price = output_price
                existing.updated_at = now
                db.commit()
                db.refresh(existing)
                return ModelPricingModel.model_validate(existing)
            else:
                # 创建
                new_pricing = ModelPricing(
                    id=str(uuid.uuid4()),
                    model_id=model_id,
                    input_price=input_price,
                    output_price=output_price,
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_pricing)
                db.commit()
                db.refresh(new_pricing)
                return ModelPricingModel.model_validate(new_pricing)

    def delete_by_model_id(self, model_id: str) -> bool:
        """删除定价（软删除，设置 enabled=False）"""
        try:
            with get_db() as db:
                result = (
                    db.query(ModelPricing)
                    .filter_by(model_id=model_id)
                    .update({"enabled": False})
                )
                db.commit()
                return result > 0
        except Exception:
            return False


class BillingLogTable:
    """计费日志数据访问层"""

    def get_by_user_id(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[BillingLogModel]:
        """获取用户计费日志"""
        with get_db() as db:
            logs = (
                db.query(BillingLog)
                .filter_by(user_id=user_id)
                .order_by(BillingLog.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [BillingLogModel.model_validate(log) for log in logs]

    def count_by_user_id(self, user_id: str) -> int:
        """统计用户日志数量"""
        with get_db() as db:
            return db.query(BillingLog).filter_by(user_id=user_id).count()


class RechargeLogTable:
    """充值日志数据访问层"""

    def get_by_user_id(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[RechargeLogModel]:
        """获取用户充值日志"""
        with get_db() as db:
            logs = (
                db.query(RechargeLog)
                .filter_by(user_id=user_id)
                .order_by(RechargeLog.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [RechargeLogModel.model_validate(log) for log in logs]

    def get_by_user_id_with_operator_name(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        """获取用户充值日志,包含操作员姓名"""
        from open_webui.models.users import User

        with get_db() as db:
            logs = (
                db.query(RechargeLog, User.name.label("operator_name"))
                .join(User, RechargeLog.operator_id == User.id)
                .filter(RechargeLog.user_id == user_id)
                .order_by(RechargeLog.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            # 转换为字典格式
            return [
                {
                    "id": log.RechargeLog.id,
                    "user_id": log.RechargeLog.user_id,
                    "amount": log.RechargeLog.amount,  # 整数（分）
                    "operator_id": log.RechargeLog.operator_id,
                    "operator_name": log.operator_name,
                    "remark": log.RechargeLog.remark,
                    "created_at": log.RechargeLog.created_at,
                }
                for log in logs
            ]


class PaymentOrderTable:
    """支付订单数据访问层"""

    def create(
        self,
        user_id: str,
        out_trade_no: str,
        amount: int,
        qr_code: str,
        expired_at: int,
        payment_method: str = "alipay",
    ) -> PaymentOrderModel:
        """创建支付订单"""
        now = int(time.time())
        with get_db() as db:
            order = PaymentOrder(
                id=str(uuid.uuid4()),
                user_id=user_id,
                out_trade_no=out_trade_no,
                amount=amount,
                status="pending",
                payment_method=payment_method,
                qr_code=qr_code,
                created_at=now,
                updated_at=now,
                expired_at=expired_at,
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            return PaymentOrderModel.model_validate(order)

    def get_by_id(self, order_id: str) -> Optional[PaymentOrderModel]:
        """根据ID获取订单"""
        with get_db() as db:
            order = db.query(PaymentOrder).filter_by(id=order_id).first()
            return PaymentOrderModel.model_validate(order) if order else None

    def get_by_out_trade_no(self, out_trade_no: str) -> Optional[PaymentOrderModel]:
        """根据商户订单号获取订单"""
        with get_db() as db:
            order = db.query(PaymentOrder).filter_by(out_trade_no=out_trade_no).first()
            return PaymentOrderModel.model_validate(order) if order else None

    def get_by_user_id(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[PaymentOrderModel]:
        """获取用户支付订单"""
        with get_db() as db:
            orders = (
                db.query(PaymentOrder)
                .filter_by(user_id=user_id)
                .order_by(PaymentOrder.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return [PaymentOrderModel.model_validate(o) for o in orders]

    def update_status(
        self,
        out_trade_no: str,
        status: str,
        trade_no: Optional[str] = None,
        paid_at: Optional[int] = None,
    ) -> bool:
        """更新订单状态"""
        with get_db() as db:
            order = db.query(PaymentOrder).filter_by(out_trade_no=out_trade_no).first()
            if not order:
                return False

            order.status = status
            order.updated_at = int(time.time())
            if trade_no:
                order.trade_no = trade_no
            if paid_at:
                order.paid_at = paid_at

            db.commit()
            return True

    def close_expired_orders(self) -> int:
        """关闭过期订单"""
        now = int(time.time())
        with get_db() as db:
            result = (
                db.query(PaymentOrder)
                .filter(
                    PaymentOrder.status == "pending",
                    PaymentOrder.expired_at < now,
                )
                .update({"status": "closed", "updated_at": now})
            )
            db.commit()
            return result


# 单例实例
ModelPricings = ModelPricingTable()
BillingLogs = BillingLogTable()
RechargeLogs = RechargeLogTable()
PaymentOrders = PaymentOrderTable()
