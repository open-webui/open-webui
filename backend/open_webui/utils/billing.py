"""
计费核心逻辑

提供费用计算、余额扣除、预扣费、结算等核心功能

金额单位说明：
- 存储单位：毫（整数），1元 = 10000毫
- 定价单位：毫/百万tokens
"""

import time
import uuid
import logging
from typing import Tuple, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from open_webui.models.users import User
from open_webui.models.billing import BillingLog, ModelPricings, RechargeLog
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)


def estimate_prompt_tokens(messages: list, model_id: str) -> int:
    """
    使用tiktoken预估prompt tokens

    Args:
        messages: OpenAI格式消息 [{"role": "user", "content": "..."}]
        model_id: 模型ID

    Returns:
        int: 预估的prompt tokens数量
    """
    try:
        import tiktoken

        # 选择encoding（GPT-4/3.5/Claude都用cl100k_base）
        encoding = tiktoken.get_encoding("cl100k_base")

        total_tokens = 0
        for message in messages:
            # 每条消息有4 tokens开销（role + content结构）
            total_tokens += 4
            for key, value in message.items():
                if isinstance(value, str):
                    total_tokens += len(encoding.encode(value))
                elif isinstance(value, list):
                    # 处理多模态消息（如图片）
                    for item in value:
                        if isinstance(item, dict) and item.get("type") == "text":
                            total_tokens += len(encoding.encode(item.get("text", "")))

        # 额外的系统开销
        total_tokens += 2

        return total_tokens

    except Exception as e:
        # tiktoken失败时降级为字符估算
        log.warning(f"tiktoken预估失败，降级为字符估算: {e}")
        char_count = 0
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                char_count += len(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        char_count += len(item.get("text", ""))
        return max(char_count // 4, 10)  # 1 token ≈ 4字符

# 默认定价配置（毫/百万tokens）
# 说明：1元 = 10000毫，精度为 0.0001元
# 原价格（元/百万tokens）* 10000（元转毫）= 毫/百万tokens
DEFAULT_PRICING = {
    "gpt-4o": {"input": 25000, "output": 100000},  # 2.5元/M -> 25000毫/M
    "gpt-4o-mini": {"input": 1500, "output": 6000},  # 0.15元/M -> 1500毫/M
    "gpt-4-turbo": {"input": 100000, "output": 300000},  # 10元/M -> 100000毫/M
    "gpt-3.5-turbo": {"input": 5000, "output": 15000},  # 0.5元/M -> 5000毫/M
    "claude-3.5-sonnet": {"input": 30000, "output": 150000},  # 3元/M -> 30000毫/M
    "claude-3-opus": {"input": 150000, "output": 750000},  # 15元/M -> 150000毫/M
    "claude-3-sonnet": {"input": 30000, "output": 150000},  # 3元/M -> 30000毫/M
    "claude-3-haiku": {"input": 2500, "output": 12500},  # 0.25元/M -> 2500毫/M
    "gemini-1.5-pro": {"input": 35000, "output": 105000},  # 3.5元/M -> 35000毫/M
    "gemini-1.5-flash": {"input": 750, "output": 3000},  # 0.075元/M -> 750毫/M
    "default": {"input": 10000, "output": 20000},  # 1元/M -> 10000毫/M
}


def calculate_cost(
    model_id: str, prompt_tokens: int, completion_tokens: int
) -> int:
    """
    计算费用

    公式: (prompt_tokens / 1,000,000 × input_price) + (completion_tokens / 1,000,000 × output_price)

    Args:
        model_id: 模型标识
        prompt_tokens: 输入token数
        completion_tokens: 输出token数

    Returns:
        int: 费用（毫），1元 = 10000毫，精度为 0.0001元
    """
    # 1. 从数据库获取定价
    pricing = ModelPricings.get_by_model_id(model_id)

    if pricing:
        input_price = pricing.input_price  # 毫/百万tokens
        output_price = pricing.output_price
    else:
        # 使用默认价格
        default = DEFAULT_PRICING.get(model_id, DEFAULT_PRICING["default"])
        input_price = default["input"]  # 毫/百万tokens
        output_price = default["output"]

    # 2. 计算费用（毫）
    # 公式: (tokens * price_per_million) / 1000000
    input_cost = (prompt_tokens * input_price) // 1000000
    output_cost = (completion_tokens * output_price) // 1000000
    total_cost = input_cost + output_cost

    return int(total_cost)


def deduct_balance(
    user_id: str,
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    log_type: str = "deduct",
) -> Tuple[int, int]:
    """
    扣除用户余额（带行锁，防止并发超扣）

    Args:
        user_id: 用户ID
        model_id: 模型标识
        prompt_tokens: 输入token数
        completion_tokens: 输出token数
        log_type: 日志类型（deduct/refund/precharge）

    Returns:
        Tuple[int, int]: (本次费用（毫）, 扣费后余额（毫）)

    Raises:
        HTTPException: 用户不存在、账户冻结、余额不足
    """
    with get_db() as db:
        # 1. 行锁获取用户（防止并发）
        user = db.query(User).filter_by(id=user_id).with_for_update().first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 2. 检查账户状态
        if user.billing_status == "frozen":
            raise HTTPException(status_code=403, detail="账户已冻结，请联系管理员充值")

        # 3. 计算费用（毫）
        cost = calculate_cost(model_id, prompt_tokens, completion_tokens)

        # 4. 检查余额
        balance_before = user.balance or 0
        if balance_before < cost:
            raise HTTPException(
                status_code=402,
                detail=f"余额不足：当前 {balance_before / 10000:.4f} 元，需要 {cost / 10000:.4f} 元",
            )

        # 5. 扣费
        user.balance = balance_before - cost
        user.total_consumed = (user.total_consumed or 0) + cost

        # 6. 余额不足时冻结账户（< 0.01元 = 100毫）
        if user.balance < 100:
            user.billing_status = "frozen"
            log.warning(f"用户 {user_id} 余额不足，账户已冻结")

        # 7. 记录日志
        billing_log = BillingLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost=cost,
            balance_after=user.balance,
            log_type=log_type,
            created_at=int(time.time() * 1000000000),  # 纳秒级时间戳
        )
        db.add(billing_log)

        # 8. 提交事务
        db.commit()

        log.info(
            f"用户 {user_id} 使用模型 {model_id} 扣费 {cost / 10000:.4f} 元，"
            f"余额 {balance_before / 10000:.4f} -> {user.balance / 10000:.4f}"
        )

        return cost, user.balance


def recharge_user(
    user_id: str, amount: int, operator_id: str, remark: str = ""
) -> int:
    """
    用户充值/扣费

    Args:
        user_id: 用户ID
        amount: 充值金额（毫），正数充值，负数扣费，1元 = 10000毫
        operator_id: 操作员ID
        remark: 备注

    Returns:
        int: 充值/扣费后余额（毫）

    Raises:
        HTTPException: 用户不存在、金额无效或余额不足
    """
    if amount == 0:
        raise HTTPException(status_code=400, detail="金额不能为0")

    with get_db() as db:
        # 1. 行锁获取用户
        user = db.query(User).filter_by(id=user_id).with_for_update().first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 2. 扣费时检查余额是否足够
        balance_before = user.balance or 0
        if amount < 0:
            if balance_before + amount < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"余额不足,当前余额 {balance_before / 10000:.2f} 元"
                )

        # 3. 充值/扣费
        user.balance = balance_before + amount

        # 4. 账户状态自动管理（< 0.01元 = 100毫）
        if user.balance < 100:
            user.billing_status = "frozen"
        elif user.balance >= 100:
            user.billing_status = "active"

        # 5. 记录充值日志
        recharge_log = RechargeLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=amount,
            operator_id=operator_id,
            remark=remark,
            created_at=int(time.time() * 1000000000),  # 纳秒级时间戳
        )
        db.add(recharge_log)

        # 6. 提交事务
        db.commit()

        operation_text = "充值" if amount > 0 else "扣费"
        log.info(
            f"用户 {user_id} {operation_text} {abs(amount) / 10000:.2f} 元，"
            f"余额 {balance_before / 10000:.4f} -> {user.balance / 10000:.4f}，"
            f"操作员 {operator_id}"
        )

        return user.balance


def get_user_balance(user_id: str) -> Optional[Tuple[int, int, str]]:
    """
    获取用户余额信息

    Args:
        user_id: 用户ID

    Returns:
        Optional[Tuple[int, int, str]]: (余额（毫）, 累计消费（毫）, 账户状态) 或 None
    """
    try:
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return None

            return (
                user.balance or 0,
                user.total_consumed or 0,
                user.billing_status or "active",
            )
    except Exception as e:
        log.error(f"获取用户余额失败: {e}")
        return None


def precharge_balance(
    user_id: str,
    model_id: str,
    estimated_prompt_tokens: int,
    max_completion_tokens: int = 4096,
) -> Tuple[str, int, int]:
    """
    预扣费（冻结余额）

    Args:
        user_id: 用户ID
        model_id: 模型ID
        estimated_prompt_tokens: 预估的输入tokens
        max_completion_tokens: 最大输出tokens

    Returns:
        Tuple[str, int, int]: (预扣费ID, 预扣金额（毫）, 剩余余额（毫）)

    Raises:
        HTTPException: 余额不足或账户冻结
    """
    with get_db() as db:
        # 1. 行锁获取用户
        user = db.query(User).filter_by(id=user_id).with_for_update().first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if user.billing_status == "frozen":
            raise HTTPException(status_code=403, detail="账户已冻结")

        # 2. 计算最大可能费用
        max_cost = calculate_cost(model_id, estimated_prompt_tokens, max_completion_tokens)

        # 3. 检查余额
        balance_before = user.balance or 0
        if balance_before < max_cost:
            raise HTTPException(
                status_code=402,
                detail=f"余额不足：当前 {balance_before / 10000:.4f} 元，预估需要 {max_cost / 10000:.4f} 元",
            )

        # 4. 预扣费
        user.balance = balance_before - max_cost

        # 5. 创建预扣费记录
        precharge_id = str(uuid.uuid4())
        billing_log = BillingLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            model_id=model_id,
            prompt_tokens=0,  # 实际tokens在settle时更新
            completion_tokens=0,
            total_cost=max_cost,
            balance_after=user.balance,
            log_type="precharge",
            precharge_id=precharge_id,
            status="precharge",
            estimated_tokens=estimated_prompt_tokens + max_completion_tokens,
            created_at=int(time.time() * 1000000000),
        )
        db.add(billing_log)
        db.commit()

        log.info(
            f"预扣费成功: user={user_id} model={model_id} "
            f"estimated={estimated_prompt_tokens}+{max_completion_tokens}tokens "
            f"cost={max_cost / 10000:.4f}元 precharge_id={precharge_id}"
        )

        return precharge_id, max_cost, user.balance


def settle_precharge(
    precharge_id: str, actual_prompt_tokens: int, actual_completion_tokens: int
) -> Tuple[int, int, int]:
    """
    结算预扣费（退还差额或补扣不足）

    Args:
        precharge_id: 预扣费事务ID
        actual_prompt_tokens: 实际消费的prompt tokens
        actual_completion_tokens: 实际消费的completion tokens

    Returns:
        Tuple[int, int, int]: (实际费用（毫）, 退款金额（毫）, 结算后余额（毫）)
    """
    with get_db() as db:
        # 1. 查询预扣费记录
        precharge_log = (
            db.query(BillingLog)
            .filter_by(precharge_id=precharge_id, status="precharge")
            .first()
        )

        if not precharge_log:
            log.warning(f"预扣费记录不存在: precharge_id={precharge_id}")
            # 降级为直接扣费
            if actual_prompt_tokens > 0 or actual_completion_tokens > 0:
                cost, balance_after = deduct_balance(
                    user_id="unknown",
                    model_id="unknown",
                    prompt_tokens=actual_prompt_tokens,
                    completion_tokens=actual_completion_tokens,
                    log_type="deduct",
                )
                return cost, 0, balance_after
            return 0, 0, 0

        # 2. 行锁获取用户
        user = db.query(User).filter_by(id=precharge_log.user_id).with_for_update().first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 3. 计算实际费用
        actual_cost = calculate_cost(
            precharge_log.model_id, actual_prompt_tokens, actual_completion_tokens
        )

        # 4. 计算差额
        precharged_cost = precharge_log.total_cost
        diff = precharged_cost - actual_cost  # 正数=退款，负数=补扣

        # 5. 调整余额
        if diff > 0:
            # 退款
            user.balance += diff
            refund_amount = diff
        elif diff < 0:
            # 补扣
            additional_cost = abs(diff)
            if user.balance < additional_cost:
                # 余额不足以补扣
                log.warning(
                    f"补扣余额不足: user={user.id} need={additional_cost / 10000:.4f}元 "
                    f"balance={user.balance / 10000:.4f}元"
                )
                # 扣除所有余额，标记账户冻结
                user.balance = 0
                user.billing_status = "frozen"
            else:
                user.balance -= additional_cost
            refund_amount = -additional_cost
        else:
            refund_amount = 0

        # 6. 更新累计消费
        user.total_consumed = (user.total_consumed or 0) + actual_cost

        # 7. 更新预扣费记录状态
        precharge_log.status = "settled"

        # 8. 创建结算记录
        settle_log = BillingLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            model_id=precharge_log.model_id,
            prompt_tokens=actual_prompt_tokens,
            completion_tokens=actual_completion_tokens,
            total_cost=actual_cost,
            balance_after=user.balance,
            log_type="settle",
            precharge_id=precharge_id,
            status="settled",
            refund_amount=refund_amount,
            created_at=int(time.time() * 1000000000),
        )
        db.add(settle_log)

        # 9. 提交事务
        db.commit()

        log.info(
            f"结算成功: user={user.id} precharge_id={precharge_id} "
            f"actual={actual_prompt_tokens}+{actual_completion_tokens}tokens "
            f"cost={actual_cost / 10000:.4f}元 refund={refund_amount / 10000:.4f}元 "
            f"balance={user.balance / 10000:.4f}元"
        )

        return actual_cost, refund_amount, user.balance


async def safe_deduct_balance_for_middleware(
    user_id: str,
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    event_emitter: Optional[callable] = None,
    log_prefix: str = "计费"
) -> Tuple[Optional[int], Optional[int]]:
    """
    安全扣费包装器（用于middleware.py）

    统一处理计费逻辑、异常处理、日志记录和事件通知

    Args:
        user_id: 用户ID
        model_id: 模型ID
        prompt_tokens: 输入tokens
        completion_tokens: 输出tokens
        event_emitter: 事件发送器（可选）
        log_prefix: 日志前缀（"计费" or "流式计费"）

    Returns:
        Tuple[Optional[int], Optional[int]]: (cost, balance_after) 或 (None, None)
    """
    # 如果tokens都为0，跳过计费
    if prompt_tokens == 0 and completion_tokens == 0:
        return None, None

    try:
        cost, balance_after = deduct_balance(
            user_id=user_id,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

        # 统一日志格式（单位：毫 → 元）
        log.info(
            f"{log_prefix}成功: 用户={user_id}, 模型={model_id}, "
            f"tokens={prompt_tokens}+{completion_tokens}, "
            f"费用={cost / 10000:.6f}元, 余额={balance_after / 10000:.4f}元"
        )

        return cost, balance_after

    except ImportError:
        log.warning("billing模块不存在，跳过计费")
        return None, None

    except HTTPException as e:
        # 业务异常（如余额不足）
        log.error(f"{log_prefix}失败（业务异常）: {e.detail}")

        if event_emitter:
            try:
                await event_emitter({
                    "type": "billing:error",
                    "data": {"message": str(e.detail)}
                })
            except Exception:
                pass

        return None, None

    except Exception as e:
        # 系统异常
        log.error(f"{log_prefix}失败（系统异常）: {e}", exc_info=True)

        if event_emitter:
            try:
                await event_emitter({
                    "type": "billing:error",
                    "data": {"message": f"计费系统异常: {str(e)}"}
                })
            except Exception:
                pass

        return None, None


def check_user_balance_threshold(
    user_id: str,
    threshold: int = 100  # 默认100毫 = 0.01元
) -> None:
    """
    检查用户余额是否满足阈值要求

    Args:
        user_id: 用户ID
        threshold: 最低余额阈值（毫），默认100毫 = 0.01元

    Raises:
        HTTPException:
            - 402: 余额不足
            - 403: 账户已冻结

    Note:
        - 如果billing模块不存在，静默跳过
        - 如果发生其他异常，静默跳过（记录日志但不阻断请求）
    """
    try:
        balance_info = get_user_balance(user_id)
        if not balance_info:
            return  # 用户不存在或查询失败，跳过检查

        balance, _, status = balance_info

        # 检查账户状态
        if status == "frozen":
            raise HTTPException(
                status_code=403,
                detail="账户已冻结，请联系管理员充值"
            )

        # 检查余额阈值
        if balance < threshold:
            raise HTTPException(
                status_code=402,
                detail=f"余额不足: 当前余额 {balance / 10000:.4f} 元，"
                       f"最低需要 {threshold / 10000:.4f} 元，请前往计费中心充值"
            )

    except ImportError:
        # billing模块不存在，跳过检查
        pass

    except HTTPException:
        # 业务异常（余额不足/账户冻结），向上抛出
        raise

    except Exception as e:
        # 其他异常仅记录日志，不阻断请求
        log.error(f"计费预检查异常: {e}")
