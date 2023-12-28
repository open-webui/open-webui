import os

from fastapi import Depends, HTTPException, status, Request
from typing import Optional

import requests
import json

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
webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

app_url = os.environ.get('WEBUI_API_BASE_URL', 'https://chat.meteron.ai')

class UserCredits(BaseModel):
    email: str
    balance: float

router = APIRouter()

# Get user's credits from Meteron's API
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

# Checkout session is created in Stripe and the URL is returned to the client. UI
# then redirects to the given URL to being the payment
@router.post("/checkout-session", response_model=Optional[UserCreditsTopUp])
async def start_user_checkout(cred=Depends(bearer_scheme)):
    token = cred.credentials
    user = Users.get_user_by_token(token)

    if user:        
        try:
            checkout_session = stripe.checkout.Session.create(
                customer_email=user.email,
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 5,
                    },
                ],
                mode='payment',
                success_url=app_url + '/',
                cancel_url=app_url + '/',
            )
        except Exception as e:
            print(e)
            return str(e)
        
        return {
            "url": checkout_session.url
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )

# One-off payments in Stripe produce 'checkout.session.completed' events. We need to
# read the event, extract the email and call Meteron's API to top up the user's credits.
@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            invoice = event['data']['object']
            customer_email = invoice['customer_email']
            amount = invoice["amount_total"]/100  # Stripe amounts are in cents
            checkout_session_id = invoice["id"]

            # Print the customer's email address
            print(f"Customer email: {customer_email}, amount: {amount}, checkout session id: {checkout_session_id}")

            # Call Meteron's API to top up the user's credits
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + os.environ["METERON_API_KEY"]
            }
            
            try:
                requests.put("https://app.meteron.ai/api/credits", headers=headers, data=json.dumps({
                    "user": customer_email,
                    "amount": amount
                }))
            except Exception as e:
                print(e)                
                # Failed to topup
                return {"status": "error", "message": str(e)}
            
            return

        return {"status": "success"}
    except ValueError as e:
        # Invalid payload
        return {"status": "error", "message": str(e)}
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return {"status": "error", "message": str(e)}
    except Exception as e:
        # Other error
        return {"status": "error", "message": str(e)}