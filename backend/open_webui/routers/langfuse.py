from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from open_webui.integrations.langfuse.connections import (
    get_connection_by_id,
    list_enabled_connections,
    redact_langfuse_connections_for_response,
)
from open_webui.integrations.langfuse.provider import LangfusePromptError, LangfusePromptProvider
from open_webui.utils.auth import get_admin_user

router = APIRouter()


@router.get('/connections')
async def list_langfuse_connections(user=Depends(get_admin_user)):
    """List enabled Langfuse connections without secret keys (admin-only global browse)."""
    connections = await list_enabled_connections()
    return {
        'connections': redact_langfuse_connections_for_response(connections),
    }


@router.get('/connections/{connection_id}/prompts')
async def list_langfuse_prompts(
    connection_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    name: str | None = None,
    label: str | None = None,
    user=Depends(get_admin_user),
):
    """Proxy Langfuse prompt list for an enabled connection (admin-only global browse)."""
    connection = await _get_enabled_connection_or_404(connection_id)
    provider = LangfusePromptProvider()
    try:
        return await provider.list_prompts(
            connection,
            page=page,
            limit=limit,
            name=name,
            label=label,
        )
    except LangfusePromptError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get('/connections/{connection_id}/prompts/{prompt_name:path}')
async def get_langfuse_prompt(
    connection_id: str,
    prompt_name: str,
    label: str | None = None,
    version: str | None = None,
    user=Depends(get_admin_user),
):
    """Proxy Langfuse prompt fetch for an enabled connection (admin-only global browse)."""
    connection = await _get_enabled_connection_or_404(connection_id)
    provider = LangfusePromptProvider()
    try:
        return await provider.get_prompt(
            connection,
            prompt_name,
            label=label,
            version=version,
        )
    except LangfusePromptError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


async def _get_enabled_connection_or_404(connection_id: str) -> dict[str, Any]:
    connection = await get_connection_by_id(connection_id)
    if not connection or not connection.get('enabled', True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Langfuse connection not found',
        )
    return connection
