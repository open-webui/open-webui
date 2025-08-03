"""
Migration script to safely transition from monolithic to modular implementation
This ensures backward compatibility during the transition
"""

import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

# Flag to control which implementation to use
USE_NEW_IMPLEMENTATION = True

if USE_NEW_IMPLEMENTATION:
    # Import from new modular implementation
    from open_webui.utils.openrouter_models import get_dynamic_model_pricing as new_get_pricing
    
    async def get_dynamic_model_pricing(force_refresh: bool = False) -> Dict[str, Any]:
        """Wrapper to use new implementation"""
        log.info("Using new modular implementation for OpenRouter models")
        return await new_get_pricing(force_refresh)
else:
    # Import from old implementation
    from open_webui.utils.openrouter_models_old import get_dynamic_model_pricing as old_get_pricing
    
    async def get_dynamic_model_pricing(force_refresh: bool = False) -> Dict[str, Any]:
        """Wrapper to use old implementation"""
        log.info("Using old monolithic implementation for OpenRouter models")
        return await old_get_pricing(force_refresh)

# Migration utilities
async def compare_implementations(force_refresh: bool = False):
    """Compare results from old and new implementations"""
    from open_webui.utils.openrouter_models_old import get_dynamic_model_pricing as old_impl
    from open_webui.utils.openrouter_models import get_dynamic_model_pricing as new_impl
    
    # Get results from both
    old_result = await old_impl(force_refresh)
    new_result = await new_impl(force_refresh)
    
    # Compare
    differences = []
    
    # Check model count
    old_count = len(old_result.get("models", []))
    new_count = len(new_result.get("models", []))
    if old_count != new_count:
        differences.append(f"Model count differs: old={old_count}, new={new_count}")
    
    # Check model IDs
    old_ids = {m["id"] for m in old_result.get("models", [])}
    new_ids = {m["id"] for m in new_result.get("models", [])}
    
    missing_in_new = old_ids - new_ids
    if missing_in_new:
        differences.append(f"Models missing in new: {missing_in_new}")
    
    extra_in_new = new_ids - old_ids
    if extra_in_new:
        differences.append(f"Extra models in new: {extra_in_new}")
    
    # Check pricing for common models
    common_ids = old_ids & new_ids
    for model_id in common_ids:
        old_model = next(m for m in old_result["models"] if m["id"] == model_id)
        new_model = next(m for m in new_result["models"] if m["id"] == model_id)
        
        if old_model["price_per_million_input"] != new_model["price_per_million_input"]:
            differences.append(
                f"Input price differs for {model_id}: "
                f"old=${old_model['price_per_million_input']}, "
                f"new=${new_model['price_per_million_input']}"
            )
        
        if old_model["price_per_million_output"] != new_model["price_per_million_output"]:
            differences.append(
                f"Output price differs for {model_id}: "
                f"old=${old_model['price_per_million_output']}, "
                f"new=${new_model['price_per_million_output']}"
            )
    
    return {
        "differences": differences,
        "old_result": old_result,
        "new_result": new_result,
        "models_match": len(differences) == 0
    }