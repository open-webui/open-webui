import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request

from beyond_the_loop.models.companies import Companies, CompanyConfigResponse, CompanyModel, UpdateCompanyConfigRequest, UpdateCompanyForm
from open_webui.utils.auth import get_current_user, get_admin_user
from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import save_config, get_config

router = APIRouter()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


############################
# Company Config
############################


@router.get("/config", response_model=CompanyConfigResponse)
async def get_company_config(request: Request, user=Depends(get_current_user)):
    """
    Get the configuration for the user's company
    
    Args:
        request: The FastAPI request object
        user: The current authenticated user
        
    Returns:
        CompanyConfigResponse: The company configuration
    """
    try:
        company_id = user.company_id
        if not company_id:
            raise HTTPException(status_code=400, detail="User is not associated with a company")
        
        # Get the company config from the database
        config = get_config(company_id)

        # Remove security relevant fields
        config.get("audio", {}).get("stt", {}).get("openai", {}).pop("api_key", None)
        config.get("audio", {}).get("tts", {}).get("openai", {}).pop("api_key", None)

        config.get("image_generation", {}).get("openai", {}).pop("api_key", None)

        config.get("rag", {}).pop("openai_api_key", None)

        config.get("rag", {}).get("web", {}).get("search", {}).pop("google_pse_api_key", None)
        config.get("rag", {}).get("web", {}).get("search", {}).pop("google_pse_engine_id", None)
        
        return {"config": config}
    except Exception as e:
        log.error(f"Error getting company config: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting company config: {str(e)}")



@router.post("/config", response_model=CompanyConfigResponse)
async def update_company_config(
    request: Request, 
    form_data: UpdateCompanyConfigRequest, 
    user=Depends(get_admin_user)
):
    """
    Update specific configuration settings for the user's company
    
    Args:
        request: The FastAPI request object
        form_data: The specific configuration settings to update
        user: The current authenticated admin user
        
    Returns:
        CompanyConfigResponse: The updated company configuration
    """
    try:
        company_id = user.company_id
        if not company_id:
            raise HTTPException(status_code=400, detail="User is not associated with a company")
        
        # Get the current config
        current_config = get_config(company_id)
        
        # Update only the specific fields that were provided
        if form_data.hide_model_logo_in_chat is not None:
            if "ui" not in current_config:
                current_config["ui"] = {}
            current_config["ui"]["hide_model_logo_in_chat"] = form_data.hide_model_logo_in_chat
            
        if form_data.chat_retention_days is not None:
            if "data" not in current_config:
                current_config["data"] = {}
            current_config["data"]["chat_retention_days"] = form_data.chat_retention_days
            
        if form_data.custom_user_notice is not None:
            if "ui" not in current_config:
                current_config["ui"] = {}
            current_config["ui"]["custom_user_notice"] = form_data.custom_user_notice
            
        if form_data.features_web_search is not None:
            if "rag" not in current_config:
                current_config["rag"] = {}
            if "web" not in current_config["rag"]:
                current_config["rag"]["web"] = {}
            if "search" not in current_config["rag"]["web"]:
                current_config["rag"]["web"]["search"] = {}
            current_config["rag"]["web"]["search"]["enable"] = form_data.features_web_search
            
        if form_data.features_image_generation is not None:
            if "image_generation" not in current_config:
                current_config["image_generation"] = {}
            current_config["image_generation"]["enable"] = form_data.features_image_generation

        # Save the updated config to the database
        success = save_config(current_config, company_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save company configuration")
        
        # Get the updated config
        updated_config = get_config(company_id)
        
        return {"config": updated_config}
    except Exception as e:
        log.error(f"Error updating company config: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating company config: {str(e)}")



############################
# Company Details
############################

@router.get("/details", response_model=CompanyModel)
async def get_company_details(request: Request, user=Depends(get_current_user)):
    """
    Get details of the user's company
    
    Args:
        request: The FastAPI request object
        user: The current authenticated user
        
    Returns:
        CompanyModel: The company details
    """
    try:
        company_id = user.company_id
        if not company_id:
            raise HTTPException(status_code=400, detail="User is not associated with a company")
        
        company = Companies.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        return company
    except Exception as e:
        log.error(f"Error getting company details: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting company details: {str(e)}")



@router.post("/details", response_model=CompanyModel)
async def update_company_details(
    request: Request, 
    form_data: UpdateCompanyForm, 
    user=Depends(get_admin_user)
):
    """
    Update details of the user's company
    
    Args:
        request: The FastAPI request object
        form_data: The company details to update
        user: The current authenticated admin user
        
    Returns:
        CompanyModel: The updated company details
    """
    try:
        company_id = user.company_id
        if not company_id:
            raise HTTPException(status_code=400, detail="User is not associated with a company")
        
        # Create a dict with only the non-None values
        update_data = {k: v for k, v in form_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updated_company = Companies.update_company_by_id(company_id, update_data)
        if not updated_company:
            raise HTTPException(status_code=404, detail="Company not found or update failed")
        
        return updated_company
    except Exception as e:
        log.error(f"Error updating company details: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating company details: {str(e)}")
