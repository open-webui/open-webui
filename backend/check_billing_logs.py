#!/usr/bin/env python3
"""检查最近的计费记录，诊断重复扣费问题"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "open_webui"))

from internal.db import get_db
from models.billing import BillingLog
from sqlalchemy import desc

def check_recent_logs(limit=10):
    """查询最近的计费记录"""
    with get_db() as db:
        logs = (
            db.query(BillingLog)
            .order_by(desc(BillingLog.created_at))
            .limit(limit)
            .all()
        )

        print(f"最近 {len(logs)} 条计费记录：\n")
        print("=" * 150)

        for i, log in enumerate(logs, 1):
            # 转换时间戳（纳秒 → 秒）
            import datetime
            created_time = datetime.datetime.fromtimestamp(log.created_at / 1000000000)

            print(f"{i}. ID: {log.id[:8]}...")
            print(f"   用户: {log.user_id}")
            print(f"   模型: {log.model_id}")
            print(f"   类型: {log.log_type}")
            print(f"   状态: {log.status}")
            print(f"   Tokens: {log.prompt_tokens}+{log.completion_tokens}")
            print(f"   费用: {log.total_cost / 10000:.4f} 元")
            print(f"   余额: {log.balance_after / 10000:.4f} 元" if log.balance_after else "   余额: None")
            print(f"   预扣费ID: {log.precharge_id[:8] if log.precharge_id else 'None'}...")
            print(f"   时间: {created_time}")
            print("-" * 150)

if __name__ == "__main__":
    check_recent_logs(15)
