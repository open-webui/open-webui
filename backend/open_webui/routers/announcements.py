"""
公告系统 API 路由模块

本模块提供系统公告的 RESTful API 接口，支持：
- 用户端：查看最新公告、标记已读
- 管理端：公告 CRUD 管理（创建、查询、更新、归档）

路由前缀：/api/announcements
权限控制：
- 用户接口（/latest, /read）：需要 verified 用户身份
- 管理接口（/, POST, PUT, DELETE）：需要 admin 用户身份

数据流：
用户请求 → FastAPI Router → 数据访问层（models/announcements.py）→ 数据库
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.announcements import (
    Announcements,
    AnnouncementReads,
    AnnouncementForm,
    AnnouncementUpdateForm,
    AnnouncementUserView,
    AnnouncementModel,
)
from open_webui.models.users import UserResponse, Users
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


##############################################################################
# 请求/响应模型
##############################################################################

class AnnouncementReadRequest(BaseModel):
    """
    标记已读请求模型

    用于批量标记多个公告为已读
    """
    ids: list[str]


class AnnouncementWithAuthor(AnnouncementModel):
    """
    带作者信息的公告模型

    继承自 AnnouncementModel，额外包含创建者的用户信息
    用于管理端列表接口
    """
    author: Optional[UserResponse] = None


##############################################################################
# 用户端 API（需要登录验证）
##############################################################################

@router.get("/latest", response_model=list[AnnouncementUserView])
async def get_latest_announcements(
    request: Request,
    since: Optional[int] = None,
    limit: Optional[int] = 20,
    user=Depends(get_verified_user),
):
    """
    获取最新公告列表（用户端）

    权限：已验证用户
    方法：GET /api/announcements/latest

    查询参数：
    - since: 可选，纳秒时间戳。仅返回创建时间晚于此值的公告（用于增量拉取）
    - limit: 可选，限制返回数量，默认 20 条

    返回：
    - 公告列表（仅 active 状态），每条公告包含：
      - 公告基本信息（id, title, content, status, created_at 等）
      - is_read: 当前用户是否已读
      - read_at: 当前用户的阅读时间（如果已读）

    用途：
    - 前端首次加载：since=None, limit=20
    - 增量拉取新公告：since=上次拉取的最新公告时间戳

    示例：
    GET /api/announcements/latest?limit=10
    GET /api/announcements/latest?since=1638316800000000000
    """
    # 查询激活状态的公告列表
    announcements = Announcements.list(status="active", since=since, limit=limit)

    # 获取当前用户的阅读记录
    read_map = AnnouncementReads.get_read_map(
        user.id, [announcement.id for announcement in announcements]
    )

    # 为每条公告附加阅读状态
    return [
        AnnouncementUserView(
            **announcement.model_dump(),
            is_read=announcement.id in read_map,
            read_at=read_map.get(announcement.id).read_at if announcement.id in read_map else None,
        )
        for announcement in announcements
    ]


@router.post("/read")
async def mark_read(
    payload: AnnouncementReadRequest,
    user=Depends(get_verified_user),
):
    """
    批量标记公告为已读（用户端）

    权限：已验证用户
    方法：POST /api/announcements/read

    请求体：
    {
      "ids": ["uuid1", "uuid2", ...]
    }

    返回：
    {
      "success": true,
      "updated": 2  // 成功标记的数量
    }

    注意：
    - 幂等操作，重复标记不会报错
    - 仅标记指定用户的阅读记录，不影响其他用户
    - 用于用户点击公告或滚动浏览时标记已读

    示例：
    POST /api/announcements/read
    {"ids": ["123e4567-e89b-12d3-a456-426614174000"]}
    """
    if not payload.ids:
        return {"success": True, "updated": 0}

    AnnouncementReads.bulk_mark_read(user.id, payload.ids)
    return {"success": True, "updated": len(payload.ids)}


##############################################################################
# 管理端 API（需要管理员权限）
##############################################################################

# Support both with and without trailing slash for list/create
@router.get("", response_model=list[AnnouncementWithAuthor])
@router.get("/", response_model=list[AnnouncementWithAuthor])
async def list_announcements(
    status: Optional[str] = None,
    user=Depends(get_admin_user),
):
    """
    获取公告列表（管理端）

    权限：管理员
    方法：GET /api/announcements

    查询参数：
    - status: 可选，过滤状态（"active" 或 "archived"）。不传则返回所有状态

    返回：
    - 公告列表，每条包含作者用户信息（id, name, email, role 等）
    - 按创建时间倒序排列

    用途：
    - 管理员查看所有公告
    - 管理员查看已归档公告：status=archived

    示例：
    GET /api/announcements
    GET /api/announcements?status=active
    GET /api/announcements?status=archived
    """
    announcements = Announcements.list(status=status)

    # 批量查询作者信息（避免 N+1 查询）
    authors = {a.created_by: Users.get_user_by_id(a.created_by) for a in announcements}

    return [
        AnnouncementWithAuthor(
            **a.model_dump(),
            author=UserResponse(**authors[a.created_by].model_dump()) if authors.get(a.created_by) else None,
        )
        for a in announcements
    ]


@router.post("", response_model=AnnouncementModel)
@router.post("/", response_model=AnnouncementModel)
async def create_announcement(
    form_data: AnnouncementForm,
    user=Depends(get_admin_user),
):
    """
    创建新公告（管理端）

    权限：管理员
    方法：POST /api/announcements

    请求体：
    {
      "title": "公告标题",
      "content": "公告内容（支持 Markdown）",
      "status": "active",  // 可选，默认 "active"
      "meta": {}           // 可选，扩展元数据
    }

    返回：
    - 创建的完整公告数据（包含自动生成的 id, created_at, updated_at）

    注意：
    - 自动记录创建者为当前管理员用户
    - 默认状态为 active，创建后立即对用户可见

    示例：
    POST /api/announcements
    {
      "title": "系统维护通知",
      "content": "系统将于明天凌晨 2:00-4:00 进行维护升级",
      "status": "active"
    }
    """
    announcement = Announcements.insert(form_data, user.id)
    return announcement


@router.put("/{announcement_id}", response_model=AnnouncementModel)
async def update_announcement(
    announcement_id: str,
    form_data: AnnouncementUpdateForm,
    user=Depends(get_admin_user),
):
    """
    更新公告（管理端）

    权限：管理员
    方法：PUT /api/announcements/{announcement_id}

    路径参数：
    - announcement_id: 公告 UUID

    请求体（所有字段均可选）：
    {
      "title": "新标题",
      "content": "新内容",
      "status": "active" | "archived",
      "meta": {}
    }

    返回：
    - 更新后的完整公告数据

    异常：
    - 404 NOT_FOUND：公告不存在

    注意：
    - 仅更新提供的字段，未提供的字段保持原值
    - 自动更新 updated_at 时间戳
    - 可通过设置 status="archived" 归档公告

    示例：
    PUT /api/announcements/123e4567-e89b-12d3-a456-426614174000
    {"content": "更新后的公告内容"}
    """
    updated = Announcements.update(announcement_id, form_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return updated


@router.delete("/{announcement_id}", response_model=AnnouncementModel)
async def delete_announcement(
    announcement_id: str,
    user=Depends(get_admin_user),
):
    """
    归档公告（管理端）

    权限：管理员
    方法：DELETE /api/announcements/{announcement_id}

    路径参数：
    - announcement_id: 公告 UUID

    返回：
    - 归档后的完整公告数据（status 变为 "archived"）

    异常：
    - 404 NOT_FOUND：公告不存在

    注意：
    - 软删除，不物理删除数据
    - 归档后的公告不会在用户端显示（/latest 不返回）
    - 管理员仍可通过 GET /?status=archived 查看已归档公告
    - 归档后可通过 PUT 接口重新激活：{"status": "active"}

    示例：
    DELETE /api/announcements/123e4567-e89b-12d3-a456-426614174000
    """
    deleted = Announcements.archive(announcement_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return deleted


@router.delete("/{announcement_id}/hard")
async def hard_delete_announcement(
    announcement_id: str,
    user=Depends(get_admin_user),
):
    """
    物理删除公告及其阅读记录（管理端）

    权限：管理员
    方法：DELETE /api/v1/announcements/{announcement_id}/hard

    返回：
    - {"success": True} 删除成功

    注意：
    - 会删除公告本身以及 announcement_read 中所有关联记录
    - 不可恢复，请谨慎调用
    """
    deleted = Announcements.delete(announcement_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return {"success": True}
