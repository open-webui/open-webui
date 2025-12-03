"""
公告系统数据模型模块

本模块定义了公告系统的数据库模型和数据访问层。

==============================================================================
数据库表结构说明（SQLite DDL）
==============================================================================

本模块对应的数据库表如下（本项目使用 SQLite）：

1. 公告主表 (announcement)
---------------------------
CREATE TABLE announcement (
    id TEXT PRIMARY KEY,                     -- 公告 UUID
    title TEXT NOT NULL,                     -- 公告标题
    content TEXT NOT NULL,                   -- 公告内容（支持 Markdown）
    status VARCHAR(32) NOT NULL DEFAULT 'active',  -- 状态：active(激活) / archived(已归档)
    created_by TEXT NOT NULL,                -- 创建者用户 ID
    created_at BIGINT NOT NULL,              -- 创建时间（纳秒时间戳）
    updated_at BIGINT NOT NULL,              -- 更新时间（纳秒时间戳）
    meta JSON DEFAULT NULL                   -- 扩展元数据（JSON 格式）
);

-- 索引建议
CREATE INDEX idx_announcement_status ON announcement(status);
CREATE INDEX idx_announcement_created_at ON announcement(created_at DESC);


2. 公告阅读记录表 (announcement_read)
--------------------------------------
CREATE TABLE announcement_read (
    id TEXT PRIMARY KEY,                     -- 记录 UUID
    user_id TEXT NOT NULL,                   -- 用户 ID
    announcement_id TEXT NOT NULL,           -- 公告 ID（关联 announcement.id）
    read_at BIGINT NOT NULL                  -- 阅读时间（纳秒时间戳）
);

-- 索引建议（关键性能优化）
CREATE INDEX idx_announcement_read_user ON announcement_read(user_id);
CREATE INDEX idx_announcement_read_announcement ON announcement_read(announcement_id);
CREATE UNIQUE INDEX idx_announcement_read_unique ON announcement_read(user_id, announcement_id);


==============================================================================
数据库表建立流程（实际操作）
==============================================================================

直接在 SQLite 中执行 DDL（手动建表）
--------------------------------------------

sqlite3 backend/data/webui.db

sqlite> -- 执行上述两个 CREATE TABLE 语句
sqlite> -- 执行索引创建语句（可选但强烈推荐）

-- 常用 SQLite 命令：
sqlite> .tables                    -- 显示所有表
sqlite> .schema announcement       -- 查看表结构
sqlite> SELECT * FROM announcement LIMIT 10;  -- 查询数据

==============================================================================
SQLAlchemy 类型映射说明（SQLite）
==============================================================================
Column(Text)       → SQLite: TEXT
Column(String(32)) → SQLite: TEXT (SQLite 不强制长度限制)
Column(BigInteger) → SQLite: INTEGER
Column(JSON)       → SQLite: TEXT (以 JSON 字符串存储)

注意事项：
- 时间戳使用 BigInteger 存储纳秒级时间戳（int(time.time_ns())）
- UUID 使用 Text 存储字符串形式（str(uuid.uuid4())）
- JSON 字段存储扩展元数据，便于未来功能扩展
- 索引设计遵循查询模式：status 过滤、created_at 排序、user_id 查询
"""

import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON

from open_webui.internal.db import Base, get_db


##############################################################################
# SQLAlchemy 数据库模型 (ORM Models)
##############################################################################

class Announcement(Base):
    """
    公告主表 - 存储系统公告内容

    对应数据库表：announcement

    字段说明：
    - id: 公告唯一标识 (UUID)
    - title: 公告标题
    - content: 公告内容（支持 Markdown）
    - status: 公告状态（active: 激活, archived: 已归档）
    - created_by: 创建者用户 ID
    - created_at: 创建时间（纳秒时间戳）
    - updated_at: 更新时间（纳秒时间戳）
    - meta: 扩展元数据（JSON 格式，用于存储额外配置）
    """
    __tablename__ = "announcement"

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="active")
    created_by = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    meta = Column(JSON, nullable=True)


class AnnouncementRead(Base):
    """
    公告阅读状态表 - 记录用户的公告阅读记录

    对应数据库表：announcement_read

    字段说明：
    - id: 记录唯一标识 (UUID)
    - user_id: 用户 ID
    - announcement_id: 公告 ID（外键关联 announcement.id）
    - read_at: 阅读时间（纳秒时间戳）

    用途：
    - 追踪每个用户对每条公告的阅读状态
    - 支持"未读公告"提醒功能
    - (user_id, announcement_id) 组合应唯一
    """
    __tablename__ = "announcement_read"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    announcement_id = Column(Text, nullable=False)
    read_at = Column(BigInteger, nullable=False)


##############################################################################
# Pydantic 数据模型 (Data Transfer Objects)
##############################################################################

class AnnouncementModel(BaseModel):
    """
    公告完整数据模型 - 用于 API 响应

    用途：将 ORM 对象转换为 JSON 可序列化的 Pydantic 模型
    配置：from_attributes=True 允许从 SQLAlchemy 模型自动转换
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    status: str
    created_by: str
    created_at: int
    updated_at: int
    meta: Optional[dict] = None


class AnnouncementReadModel(BaseModel):
    """
    公告阅读记录数据模型 - 用于 API 响应

    用途：表示单个用户对单条公告的阅读记录
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    announcement_id: str
    read_at: int


class AnnouncementForm(BaseModel):
    """
    创建公告请求模型 - 用于 POST /api/announcements

    必填字段：title, content
    可选字段：status（默认 active）, meta
    """
    title: str
    content: str
    status: Optional[str] = "active"
    meta: Optional[dict] = None


class AnnouncementUpdateForm(BaseModel):
    """
    更新公告请求模型 - 用于 PUT /api/announcements/{id}

    所有字段均可选，仅更新提供的字段
    """
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    meta: Optional[dict] = None


class AnnouncementUserView(AnnouncementModel):
    """
    用户视角的公告模型 - 包含阅读状态

    继承自 AnnouncementModel，额外添加：
    - is_read: 当前用户是否已读
    - read_at: 当前用户的阅读时间（如果已读）

    用途：GET /api/announcements/latest 返回给前端
    """
    is_read: bool = False
    read_at: Optional[int] = None


##############################################################################
# 数据访问层 (Data Access Layer)
##############################################################################

class AnnouncementReadsTable:
    """
    公告阅读记录数据访问层

    职责：管理用户的公告阅读状态
    """

    def bulk_mark_read(self, user_id: str, announcement_ids: list[str]) -> list[AnnouncementReadModel]:
        """
        批量标记公告为已读

        参数：
        - user_id: 用户 ID
        - announcement_ids: 公告 ID 列表

        返回：
        - 阅读记录列表（包括新创建和已存在的记录）

        逻辑：
        1. 查询已存在的阅读记录
        2. 对于未读的公告，创建新的阅读记录
        3. 返回完整的阅读记录列表

        注意：幂等操作，重复调用不会创建重复记录
        """
        now = int(time.time_ns())
        results: list[AnnouncementReadModel] = []

        with get_db() as db:
            # 查询已存在的阅读记录
            existing = (
                db.query(AnnouncementRead)
                .filter(
                    AnnouncementRead.user_id == user_id,
                    AnnouncementRead.announcement_id.in_(announcement_ids),
                )
                .all()
            )
            existing_map = {
                read.announcement_id: AnnouncementReadModel.model_validate(read) for read in existing
            }

            # 对于未读的公告，创建新的阅读记录
            for announcement_id in announcement_ids:
                if announcement_id in existing_map:
                    results.append(existing_map[announcement_id])
                    continue

                read = AnnouncementReadModel(
                    **{
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "announcement_id": announcement_id,
                        "read_at": now,
                    }
                )
                db.add(AnnouncementRead(**read.model_dump()))
                results.append(read)

            db.commit()

        return results

    def get_read_map(self, user_id: str, announcement_ids: list[str]) -> dict[str, AnnouncementReadModel]:
        """
        获取用户的阅读记录映射

        参数：
        - user_id: 用户 ID
        - announcement_ids: 公告 ID 列表

        返回：
        - 字典 {announcement_id: AnnouncementReadModel}

        用途：快速查询多个公告的阅读状态，用于前端显示"已读/未读"标识
        """
        with get_db() as db:
            reads = (
                db.query(AnnouncementRead)
                .filter(
                    AnnouncementRead.user_id == user_id,
                    AnnouncementRead.announcement_id.in_(announcement_ids),
                )
                .all()
            )
            return {read.announcement_id: AnnouncementReadModel.model_validate(read) for read in reads}


class AnnouncementsTable:
    """
    公告数据访问层

    职责：提供公告的 CRUD 操作（创建、读取、更新、删除）
    """

    def insert(self, form_data: AnnouncementForm, user_id: str) -> AnnouncementModel:
        """
        创建新公告

        参数：
        - form_data: 公告表单数据（标题、内容、状态、元数据）
        - user_id: 创建者用户 ID

        返回：
        - 创建的公告完整数据

        注意：自动生成 UUID、时间戳，默认状态为 active
        """
        now = int(time.time_ns())
        data = AnnouncementModel(
            **{
                "id": str(uuid.uuid4()),
                "title": form_data.title,
                "content": form_data.content,
                "status": form_data.status or "active",
                "meta": form_data.meta,
                "created_by": user_id,
                "created_at": now,
                "updated_at": now,
            }
        )

        with get_db() as db:
            db.add(Announcement(**data.model_dump()))
            db.commit()

        return data

    def get_by_id(self, id: str) -> Optional[AnnouncementModel]:
        """
        根据 ID 查询单个公告

        参数：
        - id: 公告 ID

        返回：
        - 公告数据（如果存在），否则返回 None
        """
        with get_db() as db:
            announcement = db.query(Announcement).filter(Announcement.id == id).first()
            return AnnouncementModel.model_validate(announcement) if announcement else None

    def list(
        self,
        status: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[AnnouncementModel]:
        """
        查询公告列表

        参数：
        - status: 过滤状态（如 "active", "archived"），None 表示不过滤
        - since: 仅返回创建时间晚于此时间戳的公告（纳秒），用于增量拉取
        - limit: 限制返回数量

        返回：
        - 公告列表，按创建时间倒序排列（最新的在前）

        用途：
        - 管理员查看所有公告：不传参数
        - 用户查看最新公告：status="active", limit=20
        - 增量拉取：status="active", since=上次拉取时间
        """
        with get_db() as db:
            query = db.query(Announcement)
            if status:
                query = query.filter(Announcement.status == status)
            if since:
                query = query.filter(Announcement.created_at > since)

            query = query.order_by(Announcement.created_at.desc())
            if limit:
                query = query.limit(limit)

            announcements = query.all()
            return [AnnouncementModel.model_validate(item) for item in announcements]

    def update(self, id: str, form_data: AnnouncementUpdateForm) -> Optional[AnnouncementModel]:
        """
        更新公告

        参数：
        - id: 公告 ID
        - form_data: 更新表单数据（仅包含需要更新的字段）

        返回：
        - 更新后的公告数据，如果公告不存在则返回 None

        注意：
        - 仅更新提供的字段，未提供的字段保持不变
        - 自动更新 updated_at 时间戳
        """
        with get_db() as db:
            announcement = db.query(Announcement).filter(Announcement.id == id).first()
            if not announcement:
                return None

            payload = form_data.model_dump(exclude_unset=True)
            if "title" in payload:
                announcement.title = payload["title"]
            if "content" in payload:
                announcement.content = payload["content"]
            if "status" in payload and payload["status"]:
                announcement.status = payload["status"]
            if "meta" in payload:
                announcement.meta = payload["meta"]

            announcement.updated_at = int(time.time_ns())
            db.commit()
            db.refresh(announcement)
            return AnnouncementModel.model_validate(announcement)

    def archive(self, id: str) -> Optional[AnnouncementModel]:
        """
        归档公告（软删除）

        参数：
        - id: 公告 ID

        返回：
        - 归档后的公告数据，如果公告不存在则返回 None

        注意：
        - 不物理删除数据，仅将状态设置为 "archived"
        - 归档后的公告不会在用户端显示，但管理员仍可查看
        """
        with get_db() as db:
            announcement = db.query(Announcement).filter(Announcement.id == id).first()
            if not announcement:
                return None

            announcement.status = "archived"
            announcement.updated_at = int(time.time_ns())
            db.commit()
            db.refresh(announcement)
            return AnnouncementModel.model_validate(announcement)

    def delete(self, id: str) -> bool:
        """
        硬删除公告及其所有阅读记录

        参数：
        - id: 公告 ID

        返回：
        - True 表示删除成功，False 表示公告不存在
        """
        with get_db() as db:
            # 先删除阅读记录，避免外键/数据残留
            db.query(AnnouncementRead).filter(
                AnnouncementRead.announcement_id == id
            ).delete()

            deleted = db.query(Announcement).filter(Announcement.id == id).delete()
            db.commit()

            return bool(deleted)


##############################################################################
# 单例实例 (Singleton Instances)
##############################################################################

# 全局单例，供路由层直接导入使用
Announcements = AnnouncementsTable()
AnnouncementReads = AnnouncementReadsTable()
