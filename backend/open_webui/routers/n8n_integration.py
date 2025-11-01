"""
N8N Integration Router

API endpoints for managing N8N workflow configurations and triggering executions.
Supports SSE (Server-Sent Events) streaming for real-time workflow updates.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
import httpx
import asyncio
import json
import time
import logging

from open_webui.models.n8n_config import (
    N8NConfigs,
    N8NExecutions,
    N8NConfigForm,
    N8NConfigModel,
    N8NExecutionForm,
    N8NExecutionModel,
)
from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.models.users import Users

log = logging.getLogger(__name__)
router = APIRouter()


######################
# Configuration Management
######################


@router.post("/config", response_model=N8NConfigModel)
async def create_n8n_config(
    form_data: N8NConfigForm,
    user=Depends(get_verified_user)
):
    """
    Create new N8N workflow configuration

    Requires authentication. Users can only create configs for themselves.
    """
    try:
        config = N8NConfigs.create(form_data, user.id)
        log.info(f"N8N config created: {config.id} by user {user.id}")
        return config
    except Exception as e:
        log.error(f"Failed to create N8N config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create configuration: {str(e)}"
        )


@router.get("/configs", response_model=list[N8NConfigModel])
async def get_n8n_configs(user=Depends(get_verified_user)):
    """
    Get all N8N configurations for the authenticated user
    """
    try:
        configs = N8NConfigs.get_by_user_id(user.id)
        return configs
    except Exception as e:
        log.error(f"Failed to fetch N8N configs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch configurations: {str(e)}"
        )


@router.get("/config/{config_id}", response_model=N8NConfigModel)
async def get_n8n_config(
    config_id: str,
    user=Depends(get_verified_user)
):
    """
    Get specific N8N configuration by ID

    Users can only access their own configurations.
    """
    config = N8NConfigs.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    if config.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this configuration"
        )

    return config


@router.put("/config/{config_id}", response_model=N8NConfigModel)
async def update_n8n_config(
    config_id: str,
    form_data: N8NConfigForm,
    user=Depends(get_verified_user)
):
    """
    Update N8N configuration

    Users can only update their own configurations.
    """
    config = N8NConfigs.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    if config.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this configuration"
        )

    try:
        updated = N8NConfigs.update(config_id, form_data)
        log.info(f"N8N config updated: {config_id} by user {user.id}")
        return updated
    except Exception as e:
        log.error(f"Failed to update N8N config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.delete("/config/{config_id}")
async def delete_n8n_config(
    config_id: str,
    user=Depends(get_verified_user)
):
    """
    Delete N8N configuration

    Users can only delete their own configurations.
    """
    config = N8NConfigs.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    if config.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this configuration"
        )

    try:
        N8NConfigs.delete(config_id)
        log.info(f"N8N config deleted: {config_id} by user {user.id}")
        return {"success": True, "message": "Configuration deleted"}
    except Exception as e:
        log.error(f"Failed to delete N8N config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}"
        )


######################
# Workflow Execution
######################


async def trigger_n8n_workflow_internal(
    config: N8NConfigModel,
    payload: dict,
    user_id: str
) -> N8NExecutionModel:
    """
    Internal function to trigger N8N workflow with retry logic
    """
    webhook_url = f"{config.n8n_url}/webhook/{config.webhook_id}"
    retry_config = config.retry_config
    max_retries = retry_config.get("max_retries", 3)
    backoff = retry_config.get("backoff", 2)

    start_time = time.time()
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            headers = {}
            if config.api_key:
                headers["Authorization"] = f"Bearer {config.api_key}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=config.timeout_seconds
                )

                response.raise_for_status()
                duration_ms = int((time.time() - start_time) * 1000)

                # Success
                execution = N8NExecutions.create(
                    config_id=config.id,
                    user_id=user_id,
                    status="success",
                    prompt=payload.get("prompt"),
                    response=response.text,
                    duration_ms=duration_ms,
                    metadata={"attempts": attempt + 1}
                )

                log.info(f"N8N workflow executed successfully: {execution.id}")
                return execution

        except httpx.TimeoutException as e:
            last_error = f"Workflow timeout after {config.timeout_seconds}s"
            log.warning(f"N8N workflow timeout (attempt {attempt + 1}): {str(e)}")

        except httpx.HTTPError as e:
            last_error = f"HTTP error: {str(e)}"
            log.warning(f"N8N workflow HTTP error (attempt {attempt + 1}): {str(e)}")

        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            log.error(f"N8N workflow error (attempt {attempt + 1}): {str(e)}")

        # Exponential backoff before retry
        if attempt < max_retries:
            await asyncio.sleep(backoff ** attempt)

    # All retries failed
    duration_ms = int((time.time() - start_time) * 1000)
    execution = N8NExecutions.create(
        config_id=config.id,
        user_id=user_id,
        status="failed",
        prompt=payload.get("prompt"),
        error_message=last_error,
        duration_ms=duration_ms,
        metadata={"attempts": max_retries + 1}
    )

    log.error(f"N8N workflow failed after {max_retries + 1} attempts: {execution.id}")
    return execution


@router.post("/trigger/{config_id}", response_model=N8NExecutionModel)
async def trigger_n8n_workflow(
    config_id: str,
    form_data: N8NExecutionForm,
    user=Depends(get_verified_user)
):
    """
    Trigger N8N workflow execution (non-streaming)

    Returns execution result after workflow completes.
    """
    config = N8NConfigs.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    if config.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to trigger this workflow"
        )

    if not config.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow configuration is disabled"
        )

    payload = {
        "prompt": form_data.prompt,
        "data": form_data.data,
        "user_id": user.id,
        "timestamp": int(time.time())
    }

    execution = await trigger_n8n_workflow_internal(config, payload, user.id)

    if execution.status != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=execution.error_message
        )

    return execution


@router.post("/trigger/{config_id}/stream")
async def trigger_n8n_workflow_stream(
    config_id: str,
    form_data: N8NExecutionForm,
    user=Depends(get_verified_user)
):
    """
    Trigger N8N workflow with Server-Sent Events (SSE) streaming

    Returns real-time updates as the workflow executes.
    """
    config = N8NConfigs.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    if config.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to trigger this workflow"
        )

    if not config.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow configuration is disabled"
        )

    if not config.is_streaming:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming not enabled for this configuration"
        )

    webhook_url = f"{config.n8n_url}/webhook/{config.webhook_id}"
    payload = {
        "prompt": form_data.prompt,
        "data": form_data.data,
        "user_id": user.id,
        "timestamp": int(time.time()),
        "streaming": True
    }

    async def event_stream() -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events stream"""
        start_time = time.time()

        try:
            headers = {}
            if config.api_key:
                headers["Authorization"] = f"Bearer {config.api_key}"

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=config.timeout_seconds
                ) as response:

                    # Send initial connection event
                    yield f"data: {json.dumps({'type': 'connected', 'config_id': config_id})}\n\n"

                    # Stream workflow updates
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            yield f"data: {chunk}\n\n"

                    # Send completion event
                    duration_ms = int((time.time() - start_time) * 1000)

                    # Record execution
                    N8NExecutions.create(
                        config_id=config.id,
                        user_id=user.id,
                        status="success",
                        prompt=form_data.prompt,
                        duration_ms=duration_ms,
                        metadata={"streaming": True}
                    )

                    yield f"data: {json.dumps({'type': 'completed', 'duration_ms': duration_ms})}\n\n"

        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            N8NExecutions.create(
                config_id=config.id,
                user_id=user.id,
                status="timeout",
                prompt=form_data.prompt,
                error_message=f"Workflow timeout after {config.timeout_seconds}s",
                duration_ms=duration_ms
            )
            yield f"data: {json.dumps({'type': 'error', 'message': 'Workflow timeout'})}\n\n"

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            N8NExecutions.create(
                config_id=config.id,
                user_id=user.id,
                status="failed",
                prompt=form_data.prompt,
                error_message=str(e),
                duration_ms=duration_ms
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


######################
# Execution History
######################


@router.get("/executions/{config_id}", response_model=list[N8NExecutionModel])
async def get_n8n_executions(
    config_id: str,
    limit: int = 100,
    user=Depends(get_verified_user)
):
    """
    Get execution history for a configuration
    """
    config = N8NConfigs.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    if config.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this execution history"
        )

    executions = N8NExecutions.get_by_config_id(config_id, limit=limit)
    return executions


@router.get("/analytics/{config_id}")
async def get_n8n_analytics(
    config_id: str,
    user=Depends(get_verified_user)
):
    """
    Get execution analytics for a configuration
    """
    config = N8NConfigs.get_by_id(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    if config.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this analytics"
        )

    analytics = N8NExecutions.get_analytics(config_id)
    return analytics
