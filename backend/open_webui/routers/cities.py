import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.utils.auth import SupabaseClient
from pydantic import BaseModel

router = APIRouter()
log = logging.getLogger(__name__)

class City(BaseModel):
    name: str

class ActivityResponse(BaseModel):
    id: str
    name: str
    description: str
    city: str
    location: Dict[str, float] = None
    category: str = None
    rating: float = None
    price_level: int = None
    image_url: str = None
    website: str = None
    opening_hours: Dict = None
    contact: Dict = None
    tags: List[str] = None

@router.get("/cities", response_model=List[str])
async def get_cities():
    """
    Get all available cities
    """
    try:
        cities = await SupabaseClient.get_cities()
        return cities
    except Exception as e:
        log.error(f"Error getting cities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cities"
        )

@router.get("/cities/{city}/activities", response_model=List[ActivityResponse])
async def get_activities_by_city(city: str):
    """
    Get activities for a specific city
    """
    try:
        activities = await SupabaseClient.get_activities_by_city(city)
        return activities
    except Exception as e:
        log.error(f"Error getting activities for city {city}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activities for city {city}"
        ) 