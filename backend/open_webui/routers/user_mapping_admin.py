"""
Production admin endpoints for user mapping monitoring and validation.
Provides tools for administrators to monitor and validate user mapping functionality.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.models.users import Users
from open_webui.utils.auth import get_admin_user
from open_webui.utils.user_mapping import (
    user_mapping_service, 
    get_external_user_id,
    validate_user_mapping
)
from open_webui.config import ORGANIZATION_NAME, OPENROUTER_EXTERNAL_USER

router = APIRouter()
logger = logging.getLogger(__name__)

class UserMappingStatus(BaseModel):
    """User mapping status response model"""
    user_id: str
    user_name: str
    external_user_id: str
    mapping_valid: bool
    error_message: Optional[str] = None

class UserMappingValidationReport(BaseModel):
    """Complete validation report for user mapping system"""
    configuration_valid: bool
    total_users: int
    successful_mappings: int
    failed_mappings: int
    validation_timestamp: str
    organization_name: str
    mapping_configuration: Dict[str, str]
    user_statuses: List[UserMappingStatus]
    errors: List[str]

@router.get("/validate", response_model=UserMappingValidationReport)
async def validate_user_mapping_system(admin_user=Depends(get_admin_user)):
    """
    Comprehensive validation of the user mapping system.
    
    Returns detailed report on configuration and individual user mappings.
    """
    try:
        logger.info(f"Admin {admin_user.name} requested user mapping validation")
        
        # Validate configuration
        config_valid, config_error = validate_user_mapping()
        
        # Get all users
        all_users = Users.get_users()
        user_statuses = []
        errors = []
        successful_count = 0
        failed_count = 0
        
        # Validate mapping for each user
        for user in all_users:
            try:
                external_user_id = get_external_user_id(user.id, user.name)
                user_statuses.append(UserMappingStatus(
                    user_id=user.id,
                    user_name=user.name,
                    external_user_id=external_user_id,
                    mapping_valid=True
                ))
                successful_count += 1
                
            except Exception as e:
                error_msg = f"Failed to generate mapping for user {user.name}: {str(e)}"
                errors.append(error_msg)
                user_statuses.append(UserMappingStatus(
                    user_id=user.id,
                    user_name=user.name,
                    external_user_id="",
                    mapping_valid=False,
                    error_message=str(e)
                ))
                failed_count += 1
        
        if not config_valid:
            errors.append(f"Configuration error: {config_error}")
        
        # Create validation report
        report = UserMappingValidationReport(
            configuration_valid=config_valid,
            total_users=len(all_users),
            successful_mappings=successful_count,
            failed_mappings=failed_count,
            validation_timestamp=datetime.now().isoformat(),
            organization_name=ORGANIZATION_NAME or "Unknown",
            mapping_configuration=user_mapping_service.get_mapping_info(),
            user_statuses=user_statuses,
            errors=errors
        )
        
        # Log validation results
        logger.info(
            f"User mapping validation completed: "
            f"{successful_count}/{len(all_users)} successful, "
            f"config_valid={config_valid}"
        )
        
        return report
        
    except Exception as e:
        logger.error(f"User mapping validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )

@router.get("/configuration")
async def get_user_mapping_configuration(admin_user=Depends(get_admin_user)):
    """
    Get current user mapping configuration details.
    """
    try:
        config_valid, config_message = validate_user_mapping()
        mapping_info = user_mapping_service.get_mapping_info()
        
        return {
            "success": True,
            "configuration": mapping_info,
            "validation": {
                "is_valid": config_valid,
                "message": config_message
            },
            "environment": {
                "organization_name": ORGANIZATION_NAME,
                "openrouter_external_user": OPENROUTER_EXTERNAL_USER,
                "client_prefix": user_mapping_service.client_prefix
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get user mapping configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration retrieval failed: {str(e)}"
        )

@router.get("/user/{user_id}/mapping")
async def get_user_mapping_details(user_id: str, admin_user=Depends(get_admin_user)):
    """
    Get detailed mapping information for a specific user.
    """
    try:
        # Get user details
        user = Users.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate external user ID
        external_user_id = get_external_user_id(user.id, user.name)
        
        # Parse the external user ID to show components
        parsed_mapping = user_mapping_service.parse_external_user_id(external_user_id)
        
        return {
            "success": True,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "mapping": {
                "external_user_id": external_user_id,
                "parsed_components": parsed_mapping,
                "is_user_specific": user_mapping_service.is_user_specific_id(external_user_id)
            },
            "validation": {
                "mapping_valid": True,
                "format_correct": parsed_mapping is not None
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get user mapping for {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

@router.get("/statistics")
async def get_user_mapping_statistics(admin_user=Depends(get_admin_user)):
    """
    Get statistics about user mapping usage and performance.
    """
    try:
        # Get basic statistics
        all_users = Users.get_users()
        total_users = len(all_users)
        
        # Count successful mappings
        successful_mappings = 0
        failed_mappings = 0
        unique_external_ids = set()
        
        for user in all_users:
            try:
                external_user_id = get_external_user_id(user.id, user.name)
                unique_external_ids.add(external_user_id)
                successful_mappings += 1
            except Exception:
                failed_mappings += 1
        
        # Configuration status
        config_valid, _ = validate_user_mapping()
        
        return {
            "success": True,
            "statistics": {
                "total_users": total_users,
                "successful_mappings": successful_mappings,
                "failed_mappings": failed_mappings,
                "unique_external_ids": len(unique_external_ids),
                "mapping_success_rate": (successful_mappings / total_users * 100) if total_users > 0 else 0
            },
            "configuration": {
                "is_valid": config_valid,
                "organization_name": ORGANIZATION_NAME,
                "client_prefix": user_mapping_service.client_prefix
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get user mapping statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Statistics retrieval failed: {str(e)}"
        )

@router.post("/test-mapping")
async def test_user_mapping(admin_user=Depends(get_admin_user)):
    """
    Test user mapping functionality with the current admin user.
    """
    try:
        # Test mapping generation
        external_user_id = get_external_user_id(admin_user.id, admin_user.name)
        
        # Test parsing
        parsed_mapping = user_mapping_service.parse_external_user_id(external_user_id)
        
        # Test validation
        is_user_specific = user_mapping_service.is_user_specific_id(external_user_id)
        
        return {
            "success": True,
            "test_results": {
                "mapping_generation": {
                    "success": True,
                    "external_user_id": external_user_id
                },
                "mapping_parsing": {
                    "success": parsed_mapping is not None,
                    "parsed_data": parsed_mapping
                },
                "user_specific_check": {
                    "success": True,
                    "is_user_specific": is_user_specific
                }
            },
            "test_user": {
                "id": admin_user.id,
                "name": admin_user.name
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"User mapping test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "test_user": {
                "id": admin_user.id,
                "name": admin_user.name
            },
            "timestamp": datetime.now().isoformat()
        }