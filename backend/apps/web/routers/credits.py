import os

from fastapi import Depends, HTTPException, status
from typing import Optional

import requests

from fastapi import APIRouter
from pydantic import BaseModel

from apps.web.models.users import Users

from utils.utils import (    
    bearer_scheme,    
)
from constants import ERROR_MESSAGES

class UserCredits(BaseModel):
    email: str
    balance: float

router = APIRouter()

@router.get("/", response_model=Optional[UserCredits])
async def get_user_credits(cred=Depends(bearer_scheme)):
    token = cred.credentials
    user = Users.get_user_by_token(token)

    if user:
        url = "https://app.meteron.ai/api/credits?user=" + user.email

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ["METERON_API_KEY"]
        }

        response = requests.get(url, headers=headers)
        
        return {
          "email": user.email,
          "balance": response.json()['balance'] 
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )
        

