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

import stripe

# This is your test secret API key.
stripe.api_key = os.environ.get('STRIPE_API_KEY')
price_id = os.environ.get('STRIPE_PRICE_ID')

app_url = 'http://localhost:8888'

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
        
class UserCreditsTopUp(BaseModel):
    url: str

@router.post("/checkout-session", response_model=Optional[UserCreditsTopUp])
async def start_user_checkout(cred=Depends(bearer_scheme)):
    token = cred.credentials
    user = Users.get_user_by_token(token)

    if user:        
        try:
            print('trying to create checkout session')
            checkout_session = stripe.checkout.Session.create(
                customer_email=user.email,
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 5,
                    },
                ],
                mode='payment',
                success_url=app_url + '/success.html',
                cancel_url=app_url + '/cancel.html',
            )
        except Exception as e:
            print(e)
            return str(e)

        print('checkout session created', checkout_session.url)
        
        return {
            "url": checkout_session.url
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )