"""Provider management API endpoints.

This module provides CRUD operations for managing LLM provider configurations.
Admins can create, read, update, and delete provider entries that control
automatic logo assignment for models.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from open_webui.internal.db import get_session
from open_webui.utils.auth import get_admin_user
from open_webui.models.providers import Providers, ProviderModel, ProviderForm

router = APIRouter()


@router.get("/", response_model=list[ProviderModel])
async def get_providers(
    user=Depends(get_admin_user),
    db: Session = Depends(get_session)
):
    """Get all providers (admin only).

    Returns all provider configurations sorted by priority (descending).
    """
    return Providers.get_all_providers(db=db)


@router.get("/{provider_id}", response_model=ProviderModel)
async def get_provider_by_id(
    provider_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session)
):
    """Get provider by ID (admin only).

    Args:
        provider_id: The provider identifier (e.g., "openai", "anthropic")

    Returns:
        Provider configuration

    Raises:
        HTTPException: 404 if provider not found
    """
    provider = Providers.get_provider_by_id(provider_id, db=db)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return provider


@router.post("/create", response_model=ProviderModel)
async def create_provider(
    form_data: ProviderForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session)
):
    """Create new provider (admin only).

    Args:
        form_data: Provider configuration including ID, name, logo URLs, and patterns

    Returns:
        Created provider

    Raises:
        HTTPException: 400 if provider with this ID already exists
    """
    # Check if provider already exists
    existing = Providers.get_provider_by_id(form_data.id, db=db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider with ID '{form_data.id}' already exists"
        )

    return Providers.create_provider(form_data, db=db)


@router.post("/{provider_id}/update", response_model=ProviderModel)
async def update_provider(
    provider_id: str,
    form_data: ProviderForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session)
):
    """Update provider (admin only).

    Args:
        provider_id: The provider identifier to update
        form_data: Updated provider configuration

    Returns:
        Updated provider

    Raises:
        HTTPException: 404 if provider not found
    """
    provider = Providers.update_provider_by_id(provider_id, form_data, db=db)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return provider


@router.delete("/{provider_id}/delete")
async def delete_provider(
    provider_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session)
):
    """Delete provider (admin only).

    Args:
        provider_id: The provider identifier to delete

    Returns:
        Success confirmation

    Raises:
        HTTPException: 404 if provider not found
    """
    success = Providers.delete_provider_by_id(provider_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return {"success": True}
