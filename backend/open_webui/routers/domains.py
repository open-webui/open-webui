from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from open_webui.models.domains import DomainTable, DomainForm, DomainModel, Domains
from open_webui.utils.auth import get_admin_user

router = APIRouter()


############################
# GetDomains
############################


@router.get("/", response_model=list[DomainModel])
async def get_domains(user=Depends(get_admin_user)):
    return Domains.get_domains()


############################
# GetAvailableDomains
############################


@router.get("/available", response_model=list[str])
async def get_available_domains(user=Depends(get_admin_user)):
    """Get all available domains (predefined + from users)"""
    return Domains.get_available_domains_list()


############################
# CreateDomain
############################


@router.post("/create", response_model=DomainModel)
async def create_domain(form_data: DomainForm, user=Depends(get_admin_user)):
    # Check if domain already exists
    if Domains.get_domain_by_domain(form_data.domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain '{form_data.domain}' already exists",
        )

    domain = Domains.insert_new_domain(form_data)
    if domain:
        return domain
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create domain",
        )


############################
# GetDomainById
############################


@router.get("/id/{domain_id}", response_model=DomainModel)
async def get_domain_by_id(domain_id: str, user=Depends(get_admin_user)):
    domain = Domains.get_domain_by_id(domain_id)
    if domain:
        return domain
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
        )


############################
# UpdateDomainById
############################


@router.post("/id/{domain_id}/update", response_model=DomainModel)
async def update_domain_by_id(
    domain_id: str, form_data: DomainForm, user=Depends(get_admin_user)
):
    domain = Domains.update_domain_by_id(domain_id, form_data)
    if domain:
        return domain
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
        )


############################
# DeleteDomainById
############################


@router.delete("/id/{domain_id}/delete")
async def delete_domain_by_id(domain_id: str, user=Depends(get_admin_user)):
    result = Domains.delete_domain_by_id(domain_id)
    if result:
        return {"message": "Domain deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
        )
