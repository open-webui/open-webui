"""
Content Sources Router

Generic router for managing content source providers.
Provides provider-agnostic endpoints for listing providers and getting provider information.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.content_sources import content_source_factory, content_source_registry
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# Response Models
############################


class ProviderInfo(BaseModel):
    """Information about a content source provider."""
    name: str
    display_name: str
    description: str
    configured: bool
    metadata: Optional[Dict[str, Any]] = None


class ProviderServiceInfo(BaseModel):
    """Service information for a specific provider."""
    provider: str
    configured: bool
    metadata: Dict[str, Any]


class ProviderListResponse(BaseModel):
    """Response containing list of available providers."""
    providers: List[ProviderInfo]


############################
# Helper Functions
############################


def get_provider_display_info(provider_name: str) -> Dict[str, str]:
    """Get display information for providers."""
    # This could be expanded with more providers
    provider_info = {
        "google_drive": {
            "display_name": "Google Drive",
            "description": "Sync files from Google Drive folders"
        },
        "onedrive": {
            "display_name": "Microsoft OneDrive",
            "description": "Sync files from OneDrive folders"
        },
        "dropbox": {
            "display_name": "Dropbox",
            "description": "Sync files from Dropbox folders"
        },
        "sharepoint": {
            "display_name": "SharePoint",
            "description": "Sync files from SharePoint document libraries"
        }
    }
    
    return provider_info.get(provider_name, {
        "display_name": provider_name.replace("_", " ").title(),
        "description": f"Content source provider: {provider_name}"
    })


############################
# Endpoints
############################


@router.get("/", response_model=ProviderListResponse)
async def list_content_source_providers(
    user: UserModel = Depends(get_verified_user)
) -> ProviderListResponse:
    """
    List all available content source providers.
    
    Returns information about each provider including whether it's configured.
    """
    providers = []
    
    # Get available provider types from factory
    available_providers = content_source_factory.get_available_providers()
    
    for provider_name in available_providers:
        try:
            # Try to get the provider instance from registry
            provider = content_source_registry.get_provider(provider_name)
            
            if provider:
                # Provider is registered, check if it's configured
                try:
                    service_info = await provider.get_service_info()
                    configured = service_info.get('configured', False)
                except Exception as e:
                    log.warning(f"Failed to get service info for {provider_name}: {e}")
                    configured = False
            else:
                # Provider is available but not registered
                configured = False
                
            # Get display information
            display_info = get_provider_display_info(provider_name)
            
            providers.append(ProviderInfo(
                name=provider_name,
                display_name=display_info["display_name"],
                description=display_info["description"],
                configured=configured
            ))
            
        except Exception as e:
            log.error(f"Error processing provider {provider_name}: {e}")
            continue
    
    return ProviderListResponse(providers=providers)


@router.get("/{provider}/info", response_model=ProviderServiceInfo)
async def get_provider_info(
    provider: str,
    user: UserModel = Depends(get_verified_user)
) -> ProviderServiceInfo:
    """
    Get provider-specific information.
    
    This endpoint returns provider-specific metadata such as service account emails,
    API endpoints, quotas, or any other provider-specific information.
    
    Args:
        provider: The provider name (e.g., 'google_drive', 'onedrive')
        
    Returns:
        Provider service information including configuration status and metadata
    """
    # Check if provider exists in factory
    available_providers = content_source_factory.get_available_providers()
    if provider not in available_providers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown content source provider: {provider}. Available providers: {', '.join(available_providers.keys())}"
        )
    
    # Try to get provider from registry
    provider_instance = content_source_registry.get_provider(provider)
    
    if not provider_instance:
        # Provider is available but not initialized/registered
        try:
            # Try to initialize the provider
            provider_instance = content_source_factory.get_provider(provider)
            content_source_registry.register_provider(provider, provider_instance)
        except Exception as e:
            log.error(f"Failed to initialize provider {provider}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize provider {provider}: {str(e)}"
            )
    
    try:
        # Get service information from the provider
        service_info = await provider_instance.get_service_info()
        
        # Extract metadata, removing the 'configured' field to avoid duplication
        metadata = {k: v for k, v in service_info.items() if k not in ['configured', 'provider']}
        
        return ProviderServiceInfo(
            provider=provider,
            configured=service_info.get('configured', False),
            metadata=metadata
        )
        
    except Exception as e:
        log.error(f"Error getting service info for provider {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service information: {str(e)}"
        )


@router.get("/{provider}/capabilities", response_model=Dict[str, Any])
async def get_provider_capabilities(
    provider: str,
    user: UserModel = Depends(get_verified_user)
) -> Dict[str, Any]:
    """
    Get capabilities and features supported by a provider.
    
    This endpoint returns information about what operations the provider supports,
    such as folder sync, file filtering, nested folder support, etc.
    
    Args:
        provider: The provider name
        
    Returns:
        Dictionary of provider capabilities
    """
    # Check if provider exists
    available_providers = content_source_factory.get_available_providers()
    if provider not in available_providers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown content source provider: {provider}"
        )
    
    # Define capabilities for known providers
    # This could be moved to each provider class as a method
    capabilities = {
        "google_drive": {
            "supports_folder_sync": True,
            "supports_nested_folders": True,
            "supports_file_filtering": True,
            "supports_incremental_sync": True,
            "supports_oauth": False,  # Currently using service account
            "supports_webhooks": False,
            "file_size_limit": "5TB",
            "supported_file_types": ["documents", "spreadsheets", "presentations", "pdfs", "text", "images"],
            "export_formats": {
                "google-docs": ["docx", "pdf", "txt", "html"],
                "google-sheets": ["xlsx", "csv", "pdf"],
                "google-slides": ["pptx", "pdf"]
            }
        },
        # Add more providers as they are implemented
        # This is an example, MUST be changed in the real implementation
        "onedrive": {
            "supports_folder_sync": True,
            "supports_nested_folders": True,
            "supports_file_filtering": True,
            "supports_incremental_sync": True,
            "supports_oauth": True,
            "supports_webhooks": True,
            "file_size_limit": "250GB",
            "supported_file_types": ["documents", "spreadsheets", "presentations", "pdfs", "text", "images"]
        },
        "dropbox": {
            "supports_folder_sync": True,
            "supports_nested_folders": True,
            "supports_file_filtering": True,
            "supports_incremental_sync": True,
            "supports_oauth": True,
            "supports_webhooks": True,
            "file_size_limit": "50GB",
            "supported_file_types": ["documents", "spreadsheets", "presentations", "pdfs", "text", "images"]
        }
    }
    
    provider_capabilities = capabilities.get(provider, {
        "supports_folder_sync": False,
        "supports_nested_folders": False,
        "supports_file_filtering": False,
        "supports_incremental_sync": False,
        "supports_oauth": False,
        "supports_webhooks": False,
        "message": "Capabilities not defined for this provider"
    })
    
    return {
        "provider": provider,
        "capabilities": provider_capabilities
    }