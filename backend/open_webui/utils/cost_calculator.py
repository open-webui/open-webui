"""
Cost Calculation Utilities for mAI Usage Tracking

Provides standardized cost calculation functions to ensure consistency
across all usage tracking components (background sync, manual recording, etc.)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from open_webui.models.organization_usage import ClientOrganizationDB

log = logging.getLogger(__name__)


class CostCalculationError(Exception):
    """Custom exception for cost calculation errors"""
    pass


def validate_cost_inputs(raw_cost: float, tokens: int, markup_rate: float) -> None:
    """
    Validate inputs for cost calculations
    
    Args:
        raw_cost: Raw cost from OpenRouter
        tokens: Number of tokens
        markup_rate: Markup rate to apply
        
    Raises:
        CostCalculationError: If any input is invalid
    """
    if raw_cost < 0:
        raise CostCalculationError(f"Negative cost not allowed: ${raw_cost:.6f}")
    
    if tokens < 0:
        raise CostCalculationError(f"Negative tokens not allowed: {tokens}")
    
    if markup_rate <= 0:
        raise CostCalculationError(f"Invalid markup rate: {markup_rate}")


def calculate_markup_cost(raw_cost: float, markup_rate: float) -> float:
    """
    Calculate markup cost from raw cost and markup rate
    
    Args:
        raw_cost: Raw cost from OpenRouter
        markup_rate: Markup rate (e.g., 1.3 for 30% markup)
        
    Returns:
        Markup cost (raw_cost * markup_rate)
        
    Raises:
        CostCalculationError: If inputs are invalid
    """
    if raw_cost < 0:
        raise CostCalculationError(f"Negative cost not allowed: ${raw_cost:.6f}")
    
    if markup_rate <= 0:
        raise CostCalculationError(f"Invalid markup rate: {markup_rate}")
    
    return raw_cost * markup_rate


def get_client_cost_context(client_org_id: str) -> Dict[str, Any]:
    """
    Get cost calculation context for a client organization
    
    Args:
        client_org_id: Client organization ID
        
    Returns:
        Dictionary containing client info and markup rate
        
    Raises:
        CostCalculationError: If client not found or has invalid data
    """
    try:
        client = ClientOrganizationDB.get_client_by_id(client_org_id)
        if not client:
            raise CostCalculationError(f"Client organization not found: {client_org_id}")
        
        if client.markup_rate <= 0:
            raise CostCalculationError(f"Invalid markup rate for client {client.name}: {client.markup_rate}")
        
        return {
            "client_id": client.id,
            "client_name": client.name,
            "markup_rate": client.markup_rate,
            "monthly_limit": client.monthly_limit,
            "is_active": client.is_active
        }
    
    except Exception as e:
        if isinstance(e, CostCalculationError):
            raise
        raise CostCalculationError(f"Failed to get client context: {str(e)}")


def calculate_generation_costs(
    generation_data: Dict[str, Any], 
    client_org_id: str
) -> Tuple[float, float, int]:
    """
    Calculate costs for a single generation/API call
    
    Args:
        generation_data: Dictionary containing generation info
        client_org_id: Client organization ID
        
    Returns:
        Tuple of (raw_cost, markup_cost, tokens)
        
    Raises:
        CostCalculationError: If calculation fails
    """
    try:
        # Get client context
        context = get_client_cost_context(client_org_id)
        markup_rate = context["markup_rate"]
        
        # Extract generation details - use correct OpenRouter API field names
        # Use normalized tokens (not native tokens) as per OpenRouter docs
        prompt_tokens = generation_data.get("tokens_prompt", 0)
        completion_tokens = generation_data.get("tokens_completion", 0)
        tokens = prompt_tokens + completion_tokens
        # Use 'usage' field for cost (not 'total_cost')
        raw_cost = float(generation_data.get("usage", 0.0))
        
        # Validate inputs
        validate_cost_inputs(raw_cost, tokens, markup_rate)
        
        # Calculate markup cost
        markup_cost = calculate_markup_cost(raw_cost, markup_rate)
        
        log.debug(f"Cost calculation: {tokens} tokens, ${raw_cost:.6f} raw → ${markup_cost:.6f} markup (rate: {markup_rate})")
        
        return raw_cost, markup_cost, tokens
    
    except Exception as e:
        if isinstance(e, CostCalculationError):
            raise
        raise CostCalculationError(f"Generation cost calculation failed: {str(e)}")


def calculate_batch_costs(
    generations: list, 
    client_org_id: str
) -> Dict[str, Any]:
    """
    Calculate costs for a batch of generations
    
    Args:
        generations: List of generation dictionaries
        client_org_id: Client organization ID
        
    Returns:
        Dictionary with totals and per-generation breakdown
        
    Raises:
        CostCalculationError: If calculation fails
    """
    try:
        # Get client context once for the batch
        context = get_client_cost_context(client_org_id)
        markup_rate = context["markup_rate"]
        
        total_raw_cost = 0.0
        total_markup_cost = 0.0
        total_tokens = 0
        processed_count = 0
        skipped_count = 0
        generation_costs = []
        
        for generation in generations:
            try:
                # Extract and validate generation data - use correct OpenRouter API field names
                # Use normalized tokens (not native tokens) as per OpenRouter docs
                gen_prompt_tokens = generation.get("tokens_prompt", 0)
                gen_completion_tokens = generation.get("tokens_completion", 0)
                gen_tokens = gen_prompt_tokens + gen_completion_tokens
                # Use 'usage' field for cost (not 'total_cost')
                gen_raw_cost = float(generation.get("usage", 0.0))
                gen_id = generation.get("id", "unknown")
                
                # Validate individual generation
                validate_cost_inputs(gen_raw_cost, gen_tokens, markup_rate)
                
                # Calculate costs
                gen_markup_cost = calculate_markup_cost(gen_raw_cost, markup_rate)
                
                # Add to totals
                total_raw_cost += gen_raw_cost
                total_markup_cost += gen_markup_cost
                total_tokens += gen_tokens
                processed_count += 1
                
                # Store individual generation cost info
                generation_costs.append({
                    "id": gen_id,
                    "tokens": gen_tokens,
                    "raw_cost": gen_raw_cost,
                    "markup_cost": gen_markup_cost,
                    "model": generation.get("model", "unknown")
                })
                
            except CostCalculationError as e:
                log.warning(f"Skipping generation {generation.get('id', 'unknown')}: {str(e)}")
                skipped_count += 1
                continue
        
        return {
            "client_context": context,
            "totals": {
                "raw_cost": total_raw_cost,
                "markup_cost": total_markup_cost,
                "tokens": total_tokens,
                "processed_count": processed_count,
                "skipped_count": skipped_count
            },
            "generations": generation_costs
        }
    
    except Exception as e:
        if isinstance(e, CostCalculationError):
            raise
        raise CostCalculationError(f"Batch cost calculation failed: {str(e)}")


def format_cost_for_display(cost: float) -> str:
    """
    Format cost for frontend display (matches frontend formatCurrency logic)
    
    Args:
        cost: Cost amount to format
        
    Returns:
        Formatted cost string
    """
    value = cost or 0.0
    
    if value > 0 and value < 0.01:
        # For very small amounts, show 6 decimal places
        return f"${value:.6f}"
    else:
        # Standard 2 decimal places
        return f"${value:.2f}"


def validate_monthly_limit(
    current_cost: float, 
    additional_cost: float, 
    monthly_limit: Optional[float]
) -> Dict[str, Any]:
    """
    Check if adding additional cost would exceed monthly limit
    
    Args:
        current_cost: Current month's cost
        additional_cost: Cost to be added
        monthly_limit: Monthly spending limit (None for no limit)
        
    Returns:
        Dictionary with validation results
    """
    if monthly_limit is None:
        return {
            "within_limit": True,
            "limit_exceeded": False,
            "remaining_budget": None,
            "message": "No monthly limit set"
        }
    
    new_total = current_cost + additional_cost
    within_limit = new_total <= monthly_limit
    remaining_budget = max(0, monthly_limit - current_cost)
    
    return {
        "within_limit": within_limit,
        "limit_exceeded": not within_limit,
        "current_cost": current_cost,
        "additional_cost": additional_cost,
        "new_total": new_total,
        "monthly_limit": monthly_limit,
        "remaining_budget": remaining_budget,
        "message": (
            "Within monthly limit" if within_limit 
            else f"Would exceed monthly limit by ${new_total - monthly_limit:.2f}"
        )
    }