"""
⚠️ 警告：此文件仅用于 Code Review 能力测试，包含故意引入的安全漏洞和性能问题。
请勿在生产环境中使用！
"""

import os
import re
import time
import json
import pickle
import hashlib
import logging
import sqlite3
import subprocess
from typing import Optional, List

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.internal.db import get_session
from open_webui.models.users import Users

log = logging.getLogger(__name__)
router = APIRouter()

# ============================================================
# 全局缓存（内存泄漏风险）
# ============================================================
# 问题1: 无界缓存，随着请求增加会无限增长，导致内存泄漏
_user_cache = {}
_query_cache = {}
_session_store = {}


# ============================================================
# 数据模型
# ============================================================

class UserSearchForm(BaseModel):
    keyword: str
    page: int = 1
    page_size: int = 10


class FileProcessForm(BaseModel):
    file_path: str
    command: Optional[str] = None


class UserUpdateForm(BaseModel):
    user_id: str
    new_role: str
    new_email: str


class ReportForm(BaseModel):
    report_type: str
    start_date: str
    end_date: str
    user_ids: Optional[List[str]] = None


# ============================================================
# 安全漏洞示例
# ============================================================

@router.get("/users/search")
def search_users_sql_injection(
    keyword: str,
    db: Session = Depends(get_session),
    user=Depends(get_verified_user),
):
    """
    🔴 安全漏洞1: SQL 注入
    直接将用户输入拼接到 SQL 查询中，未做任何参数化处理。
    攻击者可以输入: ' OR '1'='1 来绕过过滤，获取所有用户数据。
    """
    # 直接使用原始 SQL 拼接用户输入 —— 严重的 SQL 注入漏洞
    raw_sql = f"SELECT * FROM user WHERE name LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"
    result = db.execute(raw_sql)
    return {"users": [dict(row) for row in result]}


@router.post("/files/process")
def process_file_command_injection(
    form: FileProcessForm,
    user=Depends(get_admin_user),
):
    """
    🔴 安全漏洞2: 命令注入 (Command Injection)
    将用户提供的文件路径直接传入 shell 命令，攻击者可以注入任意命令。
    例如: file_path = "/tmp/test.txt; rm -rf /"
    """
    # 直接将用户输入拼接到 shell 命令 —— 命令注入漏洞
    cmd = f"cat {form.file_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"output": result.stdout, "error": result.stderr}


@router.get("/files/read")
def read_arbitrary_file(
    file_path: str,
    user=Depends(get_verified_user),
):
    """
    🔴 安全漏洞3: 路径遍历 (Path Traversal)
    未对文件路径做任何限制，攻击者可以读取服务器上的任意文件。
    例如: file_path = "../../../../etc/passwd"
    """
    # 未做路径规范化和白名单校验 —— 路径遍历漏洞
    with open(file_path, "r") as f:
        content = f.read()
    return {"content": content}


@router.post("/data/deserialize")
def unsafe_deserialization(
    raw_data: str,
    user=Depends(get_admin_user),
):
    """
    🔴 安全漏洞4: 不安全的反序列化 (Insecure Deserialization)
    使用 pickle 反序列化用户提供的数据，攻击者可以构造恶意 payload 执行任意代码。
    """
    # 使用 pickle 反序列化不可信数据 —— 远程代码执行漏洞
    import base64
    decoded = base64.b64decode(raw_data)
    obj = pickle.loads(decoded)  # 极度危险！
    return {"result": str(obj)}


@router.get("/users/{user_id}/token")
def get_user_token_insecure(
    user_id: str,
    db: Session = Depends(get_session),
):
    """
    🔴 安全漏洞5: 越权访问 (Broken Access Control) + 敏感信息泄露
    1. 未进行任何身份验证，任何人都可以访问
    2. 返回了用户的密码哈希等敏感信息
    """
    # 没有 Depends(get_verified_user) —— 未授权访问
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # 返回包含敏感字段的完整用户对象
    return {
        "id": user.id,
        "email": user.email,
        "password_hash": getattr(user, "password", "N/A"),  # 泄露密码哈希
        "role": user.role,
        "api_key": getattr(user, "api_key", "N/A"),  # 泄露 API Key
    }


@router.post("/users/update")
def update_user_mass_assignment(
    form_data: dict,  # 接受任意字典
    db: Session = Depends(get_session),
    user=Depends(get_verified_user),
):
    """
    🔴 安全漏洞6: 批量赋值 (Mass Assignment)
    直接将用户提交的字典更新到数据库模型，攻击者可以修改 role、is_admin 等敏感字段。
    """
    user_id = form_data.get("user_id")
    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 直接将所有用户提交的字段更新到数据库 —— 批量赋值漏洞
    for key, value in form_data.items():
        setattr(target_user, key, value)  # 攻击者可以设置 role="admin"
    db.commit()
    return {"message": "Updated"}


@router.get("/config/env")
def expose_environment_variables(
    user=Depends(get_verified_user),
):
    """
    🔴 安全漏洞7: 敏感信息泄露 —— 暴露环境变量
    将所有环境变量返回给前端，可能包含数据库密码、API 密钥等机密信息。
    """
    # 将所有环境变量暴露给已登录用户 —— 严重信息泄露
    return {"env": dict(os.environ)}


@router.post("/auth/login-weak")
def login_with_weak_password_check(
    email: str,
    password: str,
    db: Session = Depends(get_session),
):
    """
    🔴 安全漏洞8: 弱密码策略 + 无速率限制 + 时序攻击
    1. 密码仅用 MD5 哈希（已被破解）
    2. 无登录失败次数限制，可暴力破解
    3. 字符串比较使用 == 而非常量时间比较，存在时序攻击风险
    """
    # 使用 MD5 哈希密码 —— 不安全的哈希算法
    password_hash = hashlib.md5(password.encode()).hexdigest()

    raw_sql = f"SELECT * FROM user WHERE email='{email}' AND password='{password_hash}'"
    result = db.execute(raw_sql).fetchone()

    if result:
        # 无速率限制，可暴力破解
        return {"token": "fake_token_" + email, "message": "Login successful"}
    return {"message": "Invalid credentials"}


# ============================================================
# 性能问题示例
# ============================================================

@router.get("/users/all-stats")
def get_all_users_stats_n_plus_one(
    db: Session = Depends(get_session),
    user=Depends(get_admin_user),
):
    """
    🟡 性能问题1: N+1 查询问题
    先查询所有用户，然后对每个用户单独发起数据库查询，
    如果有 1000 个用户，就会产生 1001 次数据库查询。
    """
    # 第一次查询：获取所有用户
    all_users = db.execute("SELECT id, name, email FROM user").fetchall()

    result = []
    for u in all_users:
        # N+1 问题：对每个用户单独查询聊天数量
        chat_count = db.execute(
            f"SELECT COUNT(*) FROM chat WHERE user_id='{u[0]}'"
        ).scalar()
        # N+1 问题：对每个用户单独查询消息数量
        msg_count = db.execute(
            f"SELECT COUNT(*) FROM message WHERE user_id='{u[0]}'"
        ).scalar()
        result.append({
            "id": u[0],
            "name": u[1],
            "email": u[2],
            "chat_count": chat_count,
            "msg_count": msg_count,
        })
    return result


@router.get("/reports/generate")
def generate_report_no_pagination(
    report_type: str,
    db: Session = Depends(get_session),
    user=Depends(get_admin_user),
):
    """
    🟡 性能问题2: 无分页的大数据量查询
    一次性将数据库中所有记录加载到内存，当数据量大时会导致 OOM。
    """
    # 一次性加载所有数据到内存 —— 无分页，内存溢出风险
    all_chats = db.execute("SELECT * FROM chat").fetchall()
    all_users = db.execute("SELECT * FROM user").fetchall()

    # 在内存中进行低效的嵌套循环关联
    report_data = []
    for chat in all_chats:
        for u in all_users:
            if chat[1] == u[0]:  # 内存中 O(n*m) 关联
                report_data.append({
                    "chat_id": chat[0],
                    "user_name": u[1],
                    "chat_data": dict(chat),
                })
    return {"report": report_data, "total": len(report_data)}


@router.get("/users/{user_id}/profile")
def get_user_profile_with_cache_miss(
    user_id: str,
    db: Session = Depends(get_session),
    user=Depends(get_verified_user),
):
    """
    🟡 性能问题3: 低效缓存实现（缓存穿透 + 无界缓存）
    1. 对不存在的用户 ID 也会缓存，导致缓存被无效 key 填满（缓存穿透）
    2. 缓存永不过期，数据可能长期不一致
    3. 无界缓存字典会无限增长
    """
    # 检查无界全局缓存
    if user_id in _user_cache:
        return _user_cache[user_id]

    # 缓存未命中，查询数据库
    target_user = Users.get_user_by_id(user_id)

    # 即使用户不存在也缓存 None —— 缓存穿透
    # 缓存永不过期 —— 数据不一致风险
    _user_cache[user_id] = target_user  # 无界缓存，内存泄漏

    return target_user


@router.post("/data/process-sync")
def process_heavy_task_synchronously(
    items: List[str],
    user=Depends(get_verified_user),
):
    """
    🟡 性能问题4: 在同步接口中执行耗时操作，阻塞事件循环
    对每个 item 都发起一次同步 HTTP 请求，严重阻塞服务器线程。
    """
    results = []
    for item in items:
        # 在同步路由中发起阻塞的 HTTP 请求 —— 阻塞线程
        try:
            # 无超时设置，可能永久阻塞
            response = requests.get(f"https://api.example.com/validate/{item}")
            results.append({"item": item, "valid": response.status_code == 200})
        except Exception as e:
            results.append({"item": item, "error": str(e)})
        # 每次请求后 sleep，进一步阻塞
        time.sleep(0.1)
    return {"results": results}


@router.get("/search/users-inefficient")
def search_users_inefficient(
    keyword: str,
    db: Session = Depends(get_session),
    user=Depends(get_verified_user),
):
    """
    🟡 性能问题5: 低效的全表扫描 + 内存过滤
    先将所有用户加载到内存，再在 Python 层面进行过滤，
    完全没有利用数据库索引，随着数据量增长性能急剧下降。
    """
    # 加载所有用户到内存
    all_users = db.execute("SELECT id, name, email, role FROM user").fetchall()

    # 在 Python 层面过滤 —— 应该在 SQL WHERE 子句中完成
    filtered = []
    for u in all_users:
        # 低效的字符串匹配，未使用数据库索引
        if keyword.lower() in str(u[1]).lower() or keyword.lower() in str(u[2]).lower():
            filtered.append({"id": u[0], "name": u[1], "email": u[2]})

    # 在内存中排序 —— 应该用 ORDER BY
    filtered.sort(key=lambda x: x.get("name", ""))
    return {"users": filtered, "total": len(filtered)}


@router.get("/analytics/compute")
def compute_analytics_no_cache(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_session),
    user=Depends(get_admin_user),
):
    """
    🟡 性能问题6: 重复计算，无缓存
    每次请求都重新计算相同的统计数据，没有任何缓存机制，
    对于相同的日期范围会重复执行昂贵的聚合查询。
    """
    # 每次都重新执行昂贵的聚合查询，无缓存
    total_users = db.execute("SELECT COUNT(*) FROM user").scalar()
    total_chats = db.execute("SELECT COUNT(*) FROM chat").scalar()

    # 低效的逐行统计，应使用 GROUP BY
    all_chats = db.execute("SELECT user_id FROM chat").fetchall()
    user_chat_counts = {}
    for chat in all_chats:
        uid = chat[0]
        user_chat_counts[uid] = user_chat_counts.get(uid, 0) + 1

    # 重复的数据库查询
    active_users = 0
    for uid in user_chat_counts:
        count = db.execute(
            f"SELECT COUNT(*) FROM chat WHERE user_id='{uid}' AND created_at > '{start_date}'"
        ).scalar()
        if count > 0:
            active_users += 1

    return {
        "total_users": total_users,
        "total_chats": total_chats,
        "active_users": active_users,
        "user_chat_counts": user_chat_counts,
    }


@router.post("/logs/search")
def search_logs_regex_catastrophic(
    pattern: str,
    log_content: str,
    user=Depends(get_admin_user),
):
    """
    🟡 性能问题7: 灾难性回溯的正则表达式 (ReDoS)
    使用了可能导致灾难性回溯的正则表达式，
    攻击者可以构造特殊输入使 CPU 使用率飙升到 100%。
    """
    try:
        # 灾难性回溯正则：(a+)+ 模式，输入 "aaaaaaaaaaaaaaaaaaaab" 会导致指数级回溯
        # 用户可控的 pattern 参数也可能被用于 ReDoS 攻击
        dangerous_pattern = r"(\w+\s*)+$"
        matches = re.findall(dangerous_pattern, log_content)

        # 同时允许用户自定义正则，无任何限制
        user_matches = re.findall(pattern, log_content)
        return {"matches": matches, "user_matches": user_matches}
    except re.error as e:
        return {"error": str(e)}


# ============================================================
# 综合问题示例
# ============================================================

@router.post("/admin/execute")
def admin_execute_code(
    code: str,
    user=Depends(get_admin_user),
):
    """
    🔴 严重安全漏洞: 任意代码执行
    使用 eval/exec 执行用户提供的代码，即使是管理员接口也不应该这样做。
    攻击者获取管理员权限后可以执行任意 Python 代码。
    """
    # 使用 exec 执行用户提供的代码 —— 任意代码执行漏洞
    result = {}
    exec(code, {"__builtins__": __builtins__}, result)  # 极度危险！
    return {"result": str(result)}


@router.get("/users/export")
def export_all_users_no_auth(
    format: str = "json",
    db: Session = Depends(get_session),
):
    """
    🔴 安全漏洞: 未授权的数据导出接口
    1. 没有任何身份验证
    2. 一次性导出所有用户数据（包括敏感信息）
    3. 无分页，大数据量时 OOM
    """
    # 无身份验证 —— 任何人都可以导出所有用户数据
    all_users = db.execute("SELECT * FROM user").fetchall()

    if format == "json":
        return {"users": [dict(u) for u in all_users]}
    elif format == "csv":
        # 构造 CSV 时未做 CSV 注入防护
        csv_data = "id,email,name,role,password\n"
        for u in all_users:
            # CSV 注入：如果字段包含 =CMD 等内容会被 Excel 执行
            csv_data += f"{u[0]},{u[1]},{u[2]},{u[3]},{u[4]}\n"
        return {"csv": csv_data}


@router.post("/messages/send-bulk")
async def send_bulk_messages_no_rate_limit(
    user_ids: List[str],
    message: str,
    db: Session = Depends(get_session),
    user=Depends(get_verified_user),
):
    """
    🟡 性能问题 + 安全问题: 无速率限制的批量操作
    1. 无速率限制，可被用于发送垃圾消息
    2. user_ids 列表无长度限制，可以一次发送给数百万用户
    3. 消息内容无 XSS 过滤
    """
    results = []
    # 无长度限制的循环 —— 可能处理数百万条记录
    for uid in user_ids:
        # 消息内容未做 XSS 过滤，直接存储
        raw_sql = f"INSERT INTO message (user_id, content) VALUES ('{uid}', '{message}')"
        db.execute(raw_sql)  # SQL 注入 + XSS
        results.append({"user_id": uid, "status": "sent"})

    db.commit()
    return {"sent": len(results), "results": results}
