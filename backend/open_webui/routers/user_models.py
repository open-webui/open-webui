"""
用户私有模型凭据管理 - API 路由层

提供的接口：
- GET    /api/user/models/credentials      - 获取当前用户的所有私有模型凭据
- POST   /api/user/models/credentials      - 创建新的私有模型凭据
- PUT    /api/user/models/credentials/{id} - 更新指定的私有模型凭据
- DELETE /api/user/models/credentials/{id} - 删除指定的私有模型凭据

安全设计：
- 所有接口都需要用户认证（get_verified_user）
- 返回数据时自动掩码 API Key（仅显示前 4 位和后 4 位）
- 更新/删除操作强制用户隔离（仅能操作自己的凭据）
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.models.user_model_credentials import (
    UserModelCredentialForm,
    UserModelCredentialResponse,
    UserModelCredentials,
    mask_api_key,
)

log = logging.getLogger(__name__)

router = APIRouter()


def _mask_response(model):
    """
    响应数据掩码处理 - 保护 API Key 不被前端完整获取

    转换流程：
    1. 将内部模型（包含明文 api_key）转换为响应模型
    2. 不回传明文 api_key，只返回掩码字段 api_key_masked

    Args:
        model: UserModelCredentialModel（包含明文 api_key）

    Returns:
        UserModelCredentialResponse: 掩码后的响应对象
    """
    return UserModelCredentialResponse(
        **{
            **{
                k: v
                for k, v in model.model_dump().items()
                if k not in ["api_key"]
            },
            "api_key_masked": mask_api_key(model.api_key),  # 掩码 API Key
        }
    )


@router.get("/", response_model=list[UserModelCredentialResponse])
async def list_user_credentials(user=Depends(get_verified_user)):
    """
    获取当前用户的所有私有模型凭据

    用途：前端模型选择器初始化时调用，获取用户保存的所有私有 API 配置
    返回：掩码后的凭据列表（api_key_masked 字段，不暴露明文）

    权限：仅返回当前用户的凭据

    Returns:
        list[UserModelCredentialResponse]: 用户的所有私有模型凭据列表
    """
    # 查询当前用户的所有凭据
    creds = UserModelCredentials.get_credentials_by_user_id(user.id)
    # 掩码 API Key 后返回
    return [_mask_response(c) for c in creds]


@router.post("/", response_model=UserModelCredentialResponse)
async def create_user_credential(
    form_data: UserModelCredentialForm, user=Depends(get_verified_user)
):
    """
    创建新的私有模型凭据

    用途：用户在前端添加自己的 LLM API（如自己的 OpenAI Key、Claude Key 等）
    流程：
    1. 接收前端提交的表单数据（model_id、base_url、api_key 等）
    2. 自动关联当前用户 ID
    3. 生成唯一凭据 ID
    4. 保存到数据库
    5. 返回掩码后的凭据对象

    Args:
        form_data: 前端提交的凭据表单（不包含 id 和 user_id）
        user: 当前认证用户（由依赖注入自动获取）

    Returns:
        UserModelCredentialResponse: 创建成功的凭据对象（API Key 已掩码）

    Raises:
        HTTPException(400): 创建失败时抛出
    """
    # 创建新凭据，自动关联当前用户 ID
    cred = UserModelCredentials.insert_new_credential(user.id, form_data)
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
    # 掩码 API Key 后返回
    return _mask_response(cred)


@router.put("/{cred_id}", response_model=UserModelCredentialResponse)
async def update_user_credential(
    cred_id: str, form_data: UserModelCredentialForm, user=Depends(get_verified_user)
):
    """
    更新指定的私有模型凭据

    用途：用户编辑自己保存的 API 凭据（修改 base_url、api_key、model_id 等）
    安全校验：
    - 凭据必须存在
    - 凭据必须属于当前用户（user_id 匹配）
    - 不满足条件返回 404

    更新策略：仅更新前端提交的字段（部分更新）

    Args:
        cred_id: 凭据 ID（路径参数）
        form_data: 更新的数据
        user: 当前认证用户（由依赖注入自动获取）

    Returns:
        UserModelCredentialResponse: 更新后的凭据对象（API Key 已掩码）

    Raises:
        HTTPException(404): 凭据不存在或不属于当前用户
    """
    # 更新凭据，自动校验用户权限
    cred = UserModelCredentials.update_credential_by_id_and_user_id(
        cred_id, user.id, form_data
    )
    if not cred:
        # 凭据不存在或权限不足
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    # 掩码 API Key 后返回
    return _mask_response(cred)


@router.delete("/{cred_id}", response_model=bool)
async def delete_user_credential(cred_id: str, user=Depends(get_verified_user)):
    """
    删除指定的私有模型凭据

    用途：用户删除自己保存的 API 凭据
    安全校验：
    - 凭据必须存在
    - 凭据必须属于当前用户（user_id 匹配）
    - 不满足条件返回 404

    Args:
        cred_id: 凭据 ID（路径参数）
        user: 当前认证用户（由依赖注入自动获取）

    Returns:
        bool: 删除成功返回 True

    Raises:
        HTTPException(404): 凭据不存在或不属于当前用户
    """
    # 删除凭据，自动校验用户权限
    result = UserModelCredentials.delete_credential_by_id_and_user_id(
        cred_id, user.id
    )
    if not result:
        # 凭据不存在或权限不足
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return True
