"""Proxy endpoints for managing external RAG volumes and exclusions."""
import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.config import RAG_OPENAI_API_BASE_URL
from open_webui.utils.auth import get_admin_user


router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


def _resolve_rag_base_url() -> str:
    base_url = os.getenv("RAG_AGENTIC_API_BASE_URL", "").strip()
    if not base_url:
        try:
            base_url = str(RAG_OPENAI_API_BASE_URL.value)
        except Exception:
            base_url = str(RAG_OPENAI_API_BASE_URL)
    base_url = base_url.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    return base_url


async def _proxy_request(method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
    base_url = _resolve_rag_base_url()
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG agentic base URL is not configured",
        )

    url = f"{base_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, url, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to contact RAG agentic API: {exc}",
        ) from exc

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

    if response.content:
        return response.json()
    return {}


@router.get("/volumes", dependencies=[Depends(get_admin_user)])
async def get_volumes() -> Any:
    return await _proxy_request("GET", "/volumes")


@router.get("/volumes/status", dependencies=[Depends(get_admin_user)])
async def get_volume_status() -> Any:
    return await _proxy_request("GET", "/volumes/status")


@router.post("/volumes", dependencies=[Depends(get_admin_user)])
async def update_volumes(payload: Dict[str, Any]) -> Any:
    return await _proxy_request("POST", "/volumes", payload)


@router.post("/volumes/add", dependencies=[Depends(get_admin_user)])
async def add_volume(payload: Dict[str, Any]) -> Any:
    return await _proxy_request("POST", "/volumes/add", payload)


@router.put("/volumes/{volume_name}", dependencies=[Depends(get_admin_user)])
async def update_volume(volume_name: str, payload: Dict[str, Any]) -> Any:
    return await _proxy_request("PUT", f"/volumes/{volume_name}", payload)


@router.delete("/volumes/{volume_name}", dependencies=[Depends(get_admin_user)])
async def delete_volume(volume_name: str) -> Any:
    return await _proxy_request("DELETE", f"/volumes/{volume_name}")


@router.post("/volumes/{volume_name}/mark-available", dependencies=[Depends(get_admin_user)])
async def mark_volume_available(volume_name: str) -> Any:
    return await _proxy_request("POST", f"/volumes/{volume_name}/mark-available")


@router.get("/exclusions", dependencies=[Depends(get_admin_user)])
async def get_exclusions() -> Any:
    return await _proxy_request("GET", "/exclusions")


@router.post("/exclusions", dependencies=[Depends(get_admin_user)])
async def update_exclusions(payload: Dict[str, Any]) -> Any:
    return await _proxy_request("POST", "/exclusions", payload)
