"""
Currency conversion utilities using NBP (Polish National Bank) exchange rates
"""

import logging
from typing import Optional, Dict, Any
from .nbp_client import nbp_client

log = logging.getLogger(__name__)

# Fallback exchange rate in case NBP API is unavailable
FALLBACK_USD_PLN_RATE = 4.1234

async def get_current_usd_pln_rate() -> float:
    """
    Get current USD to PLN exchange rate from NBP API.
    Returns fallback rate if API is unavailable.
    
    Returns:
        float: USD to PLN exchange rate
    """
    try:
        rate_data = await nbp_client.get_usd_pln_rate()
        if rate_data and rate_data.get('rate'):
            return float(rate_data['rate'])
    except Exception as e:
        log.warning(f"Failed to get NBP exchange rate: {e}")
    
    # Return fallback rate if API fails
    log.info(f"Using fallback USD/PLN rate: {FALLBACK_USD_PLN_RATE}")
    return FALLBACK_USD_PLN_RATE

async def get_exchange_rate_info() -> Dict[str, Any]:
    """
    Get detailed exchange rate information including metadata.
    
    Returns:
        Dict containing rate, effective_date, rate_source, etc.
    """
    try:
        rate_data = await nbp_client.get_usd_pln_rate()
        if rate_data and rate_data.get('rate'):
            return {
                'usd_pln': float(rate_data['rate']),
                'effective_date': rate_data.get('effective_date'),
                'rate_source': rate_data.get('rate_source', 'nbp'),
                'table_no': rate_data.get('table_no'),
                'is_fallback': False
            }
    except Exception as e:
        log.warning(f"Failed to get NBP exchange rate info: {e}")
    
    # Return fallback info if API fails
    return {
        'usd_pln': FALLBACK_USD_PLN_RATE,
        'effective_date': None,
        'rate_source': 'fallback',
        'table_no': None,
        'is_fallback': True
    }

async def convert_usd_to_pln(usd_amount: float) -> Dict[str, Any]:
    """
    Convert USD amount to PLN with detailed conversion info.
    
    Args:
        usd_amount: Amount in USD to convert
        
    Returns:
        Dict containing USD amount, PLN amount, rate, and metadata
    """
    rate_info = await get_exchange_rate_info()
    pln_amount = usd_amount * rate_info['usd_pln']
    
    return {
        'usd': usd_amount,
        'pln': round(pln_amount, 2),
        'rate': rate_info['usd_pln'],
        'effective_date': rate_info['effective_date'],
        'rate_source': rate_info['rate_source'],
        'is_fallback': rate_info['is_fallback']
    }

def convert_usd_to_pln_sync(usd_amount: float, rate: Optional[float] = None) -> float:
    """
    Synchronous USD to PLN conversion for cases where async is not possible.
    Uses provided rate or fallback rate.
    
    Args:
        usd_amount: Amount in USD to convert
        rate: Optional exchange rate to use (if None, uses fallback)
        
    Returns:
        float: Amount in PLN
    """
    if rate is None:
        rate = FALLBACK_USD_PLN_RATE
    
    return round(usd_amount * rate, 2)