"""
用户私有模型凭据管理 - 数据模型层

功能：
1. 允许用户保存自己的 LLM API 凭据（OpenAI/Claude/自建等）
2. 提供凭据的增删改查操作
3. 自动掩码 API Key 防止泄露
4. 支持多 Provider（OpenAI/Ollama/兼容接口等）

核心设计：
- 每个用户可以添加多个私有模型配置
- 存储 base_url、api_key 等信息
- 返回给前端时自动掩码 API Key（仅显示前 4 位和后 4 位）
- 所有操作都强制用户隔离（通过 user_id 校验）

建表参考（SQLite 默认路径 backend/data/webui.db）：
cd /home/gaofeng/open-webui-next/backend
    source .venv/bin/activate
    sqlite3 data/webui.db "
        CREATE TABLE IF NOT EXISTS user_model_credential (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        name TEXT,
        model_id TEXT NOT NULL,
        base_url TEXT,
        api_key TEXT NOT NULL,
        config TEXT,
        created_at INTEGER,
        updated_at INTEGER
        );
        CREATE INDEX IF NOT EXISTS ix_user_model_credential_user_id ON user_model_credential (user_id);
    "
"""

import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text

####################
# DB Schema - 数据库表定义
####################


class UserModelCredential(Base):
    """
    用户私有模型凭据表 - 存储每个用户自己配置的 LLM API 凭据

    字段说明：
    - id: 凭据唯一标识（纳秒时间戳）
    - user_id: 所属用户 ID（外键，索引）
    - name: 用户可读名称（如 "我的 GPT-4"）
    - model_id: 上游模型名称/ID（如 "gpt-4", "claude-3-opus"）
    - base_url: API 基础地址（如 "https://api.openai.com/v1"）
    - api_key: API 密钥（明文存储，返回时掩码）
    - config: 扩展配置（JSON，可存 organization、headers 等）
    - created_at/updated_at: 创建/更新时间戳
    """
    __tablename__ = "user_model_credential"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)

    name = Column(String, nullable=True)  # 用户可读名称
    model_id = Column(String, nullable=False)  # 上游模型名/ID
    base_url = Column(Text, nullable=True)
    api_key = Column(Text, nullable=False)

    config = Column(JSONField, nullable=True)  # 预留自定义字段，如org、headers等

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class UserModelCredentialModel(BaseModel):
    """
    用户私有模型凭据数据模型 - 内部使用的完整数据模型

    用途：数据库操作和内部逻辑使用的完整模型（包含明文 api_key）
    注意：不应直接返回给前端，应使用 UserModelCredentialResponse
    """
    id: str
    user_id: str
    name: Optional[str] = None
    model_id: str
    base_url: Optional[str] = None
    api_key: str  # 明文 API Key，仅内部使用
    config: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class UserModelCredentialResponse(BaseModel):
    """
    用户私有模型凭据响应模型 - 返回给前端的安全模型

    用途：API 响应时使用，将 api_key 替换为掩码后的 api_key_masked
    安全设计：前端永远看不到完整的 API Key，只能看到前 4 位和后 4 位
    """
    id: str
    user_id: str
    name: Optional[str] = None
    model_id: str
    base_url: Optional[str] = None
    api_key_masked: str  # 掩码后的 API Key（如 "sk-1***5678"）
    config: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class UserModelCredentialForm(BaseModel):
    """
    用户私有模型凭据表单模型 - 前端提交的数据格式

    用途：创建/更新凭据时前端提交的数据
    字段：不包含 id、user_id、时间戳（由后端自动生成）
    """
    name: Optional[str] = None
    model_id: str
    base_url: Optional[str] = None
    api_key: str  # 前端提交时是明文，后端直接存储
    config: Optional[dict] = None


def mask_api_key(key: str) -> str:
    """
    掩码 API Key - 保护敏感信息

    规则：
    - 空字符串：返回空
    - 长度 ≤ 8：全部替换为 *
    - 长度 > 8：保留前 4 位和后 4 位，中间用 * 填充

    示例：
    - "sk-1234567890abcdef" → "sk-1**********cdef"
    - "short" → "*****"
    - "" → ""
    """
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


class UserModelCredentialsTable:
    """
    用户私有模型凭据数据访问层 - CRUD 操作

    功能：
    1. 增：insert_new_credential - 创建新凭据
    2. 删：delete_credential_by_id_and_user_id - 删除凭据（用户隔离）
    3. 改：update_credential_by_id_and_user_id - 更新凭据（用户隔离）
    4. 查：get_credentials_by_user_id - 获取用户的所有凭据
         get_credential_by_id_and_user_id - 获取单个凭据（用户隔离）

    安全设计：
    - 所有操作都强制校验 user_id，防止跨用户访问
    - 更新/删除/查询单条时，必须同时匹配 id 和 user_id
    """
    def insert_new_credential(
        self, user_id: str, form: UserModelCredentialForm
    ) -> Optional[UserModelCredentialModel]:
        """
        创建新的用户私有模型凭据

        流程：
        1. 生成唯一 ID（纳秒时间戳，确保唯一性）
        2. 关联当前用户 ID
        3. 保存表单数据（model_id、base_url、api_key 等）
        4. 设置创建时间和更新时间
        5. 持久化到数据库

        Args:
            user_id: 当前用户 ID
            form: 前端提交的凭据表单数据

        Returns:
            UserModelCredentialModel: 创建成功的凭据对象
        """
        with get_db() as db:
            now = int(time.time())
            # 使用纳秒时间戳生成唯一 ID
            cred = UserModelCredential(
                **{
                    "id": str(time.time_ns()),
                    "user_id": user_id,
                    "name": form.name,
                    "model_id": form.model_id,
                    "base_url": form.base_url,
                    "api_key": form.api_key,  # 明文存储
                    "config": form.config,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            db.add(cred)
            db.commit()
            db.refresh(cred)
            return UserModelCredentialModel.model_validate(cred)

    def update_credential_by_id_and_user_id(
        self, cred_id: str, user_id: str, form: UserModelCredentialForm
    ) -> Optional[UserModelCredentialModel]:
        """
        更新用户私有模型凭据

        安全校验：
        - 凭据必须存在
        - 凭据必须属于当前用户（user_id 匹配）
        - 不满足条件返回 None

        更新策略：
        - 仅更新前端提交的字段（exclude_none=True）
        - 自动更新 updated_at 时间戳
        - created_at 不会被修改

        Args:
            cred_id: 凭据 ID
            user_id: 当前用户 ID
            form: 更新的数据

        Returns:
            UserModelCredentialModel: 更新后的凭据对象，权限不足返回 None
        """
        with get_db() as db:
            # === 1. 权限校验：凭据必须存在且属于当前用户 ===
            cred = db.get(UserModelCredential, cred_id)
            if not cred or cred.user_id != user_id:
                return None

            # === 2. 更新字段：仅更新提交的非空字段 ===
            for field, value in form.model_dump(exclude_none=True).items():
                setattr(cred, field, value)
            cred.updated_at = int(time.time())

            # === 3. 持久化 ===
            db.commit()
            db.refresh(cred)
            return UserModelCredentialModel.model_validate(cred)

    def delete_credential_by_id_and_user_id(
        self, cred_id: str, user_id: str
    ) -> bool:
        """
        删除用户私有模型凭据

        安全校验：
        - 凭据必须存在
        - 凭据必须属于当前用户（user_id 匹配）
        - 不满足条件返回 False

        Args:
            cred_id: 凭据 ID
            user_id: 当前用户 ID

        Returns:
            bool: 删除成功返回 True，权限不足或不存在返回 False
        """
        with get_db() as db:
            # === 1. 权限校验：凭据必须存在且属于当前用户 ===
            cred = db.get(UserModelCredential, cred_id)
            if not cred or cred.user_id != user_id:
                return False

            # === 2. 删除凭据 ===
            db.delete(cred)
            db.commit()
            return True

    def get_credentials_by_user_id(
        self, user_id: str
    ) -> list[UserModelCredentialModel]:
        """
        获取用户的所有私有模型凭据

        用途：前端模型选择器展示用户的所有私有模型
        返回：用户创建的所有凭据列表（包含明文 api_key）

        Args:
            user_id: 用户 ID

        Returns:
            list[UserModelCredentialModel]: 用户的所有凭据列表，无数据返回空列表
        """
        with get_db() as db:
            # 查询该用户的所有凭据
            creds = (
                db.query(UserModelCredential).filter_by(user_id=user_id).all()
            )
            return (
                [UserModelCredentialModel.model_validate(c) for c in creds]
                if creds
                else []
            )

    def get_credential_by_id_and_user_id(
        self, cred_id: str, user_id: str
    ) -> Optional[UserModelCredentialModel]:
        """
        获取单个用户私有模型凭据

        安全校验：
        - 凭据必须存在
        - 凭据必须属于当前用户（user_id 匹配）
        - 不满足条件返回 None

        用途：查看/编辑凭据详情时使用

        Args:
            cred_id: 凭据 ID
            user_id: 当前用户 ID

        Returns:
            UserModelCredentialModel: 凭据对象，权限不足返回 None
        """
        with get_db() as db:
            # === 1. 权限校验：凭据必须存在且属于当前用户 ===
            cred = db.get(UserModelCredential, cred_id)
            if not cred or cred.user_id != user_id:
                return None
            return UserModelCredentialModel.model_validate(cred)


UserModelCredentials = UserModelCredentialsTable()
